#!/usr/bin/env python3
"""Prepara o Zabbix para o laboratório usando a API (idempotente: pode rodar várias vezes).

Cria:
  * grupos de hosts e de templates;
  * o template "Template Lab Servidor Simulado" com um item do tipo trapper (cpu.simulada)
    e uma trigger de CPU alta;
  * N hosts simulados (Servidor-Simulado-01 ... NN) ligados a esse template;
  * ajusta a interface do host "Zabbix server" para o contêiner do agente (melhor esforço).
"""
import argparse
import time

from zabbix_utils import ZabbixAPI
from zabbix_utils.exceptions import APIRequestError

from comum import carregar_env, env, nomes_dos_hosts

NOME_TEMPLATE = "Template Lab Servidor Simulado"
CHAVE_ITEM = "cpu.simulada"
GRUPO_HOSTS = "Lab/Servidores Simulados"
GRUPO_TEMPLATES = "Lab/Templates"
LIMITE_CPU = 90


def conectar(url, usuario, senha, tentativas=30, espera=5):
    """Aguarda o Zabbix Web/API ficar disponível e faz login."""
    ultimo_erro = None
    for n in range(1, tentativas + 1):
        try:
            return ZabbixAPI(url=url, user=usuario, password=senha)
        except APIRequestError as erro:
            # A API respondeu, então o problema é de credenciais/permissão: não adianta tentar de novo.
            raise SystemExit(f"A API do Zabbix recusou o login ({erro}). "
                             "Confira ZABBIX_ADMIN_USER e ZABBIX_ADMIN_PASSWORD no .env.")
        except Exception as erro:  # conexão recusada, banco ainda inicializando, etc.
            ultimo_erro = erro
            print(f"[{n}/{tentativas}] Zabbix ainda não respondeu ({type(erro).__name__}). Aguardando {espera}s...")
            time.sleep(espera)
    raise SystemExit(f"Não foi possível conectar à API do Zabbix em {url}: {ultimo_erro}")


def grupo_de_hosts(api, nome):
    achados = api.hostgroup.get(filter={"name": [nome]}, output=["groupid"])
    if achados:
        return achados[0]["groupid"]
    return api.hostgroup.create(name=nome)["groupids"][0]


def grupo_de_templates(api, nome):
    achados = api.templategroup.get(filter={"name": [nome]}, output=["groupid"])
    if achados:
        return achados[0]["groupid"]
    return api.templategroup.create(name=nome)["groupids"][0]


def garantir_template(api, grupo_id):
    achados = api.template.get(filter={"host": [NOME_TEMPLATE]}, output=["templateid"])
    if achados:
        return achados[0]["templateid"], False
    criado = api.template.create(host=NOME_TEMPLATE, name=NOME_TEMPLATE, groups=[{"groupid": grupo_id}])
    return criado["templateids"][0], True


def garantir_item(api, template_id):
    achados = api.item.get(templateids=template_id, filter={"key_": CHAVE_ITEM}, output=["itemid"])
    if achados:
        return False
    api.item.create(
        name="CPU simulada (%)",
        key_=CHAVE_ITEM,
        hostid=template_id,
        type=2,          # Zabbix trapper: o valor chega por push (zabbix_sender / zabbix_utils.Sender)
        value_type=0,    # numérico (float)
        units="%",
        history="7d",
        trends="30d",
    )
    return True


def garantir_trigger(api, template_id):
    descricao = f"CPU simulada acima de {LIMITE_CPU}% em {{HOST.NAME}}"
    achados = api.trigger.get(templateids=template_id, filter={"description": [descricao]}, output=["triggerid"])
    if achados:
        return False
    api.trigger.create(
        description=descricao,
        expression=f"last(/{NOME_TEMPLATE}/{CHAVE_ITEM})>{LIMITE_CPU}",
        priority=3,      # 3 = Average
    )
    return True


def garantir_hosts(api, quantidade, grupo_id, template_id):
    nomes = nomes_dos_hosts(quantidade)
    existentes = {h["host"] for h in api.host.get(filter={"host": nomes}, output=["host"])}
    criados = 0
    for nome in nomes:
        if nome in existentes:
            continue
        api.host.create(
            host=nome,
            groups=[{"groupid": grupo_id}],
            templates=[{"templateid": template_id}],
        )
        criados += 1
    return criados


def ajustar_agente_do_zabbix_server(api):
    """O host padrão 'Zabbix server' aponta para 127.0.0.1; o agente roda em outro contêiner."""
    try:
        hosts = api.host.get(
            filter={"host": ["Zabbix server"]},
            output=["hostid"],
            selectInterfaces=["interfaceid", "type"],
        )
        if not hosts:
            return False
        for interface in hosts[0].get("interfaces", []):
            if str(interface["type"]) == "1":  # 1 = agente
                api.hostinterface.update(interfaceid=interface["interfaceid"], useip=0, dns="zabbix-agent", ip="")
        return True
    except Exception as erro:
        print(f"Aviso: não consegui ajustar a interface do agente automaticamente ({erro}).\n"
              "  Ajuste manualmente: Data collection > Hosts > 'Zabbix server' > interface Agent > "
              "Connect to: DNS, DNS name: zabbix-agent.")
        return False


def main():
    carregar_env()
    ap = argparse.ArgumentParser(description="Configura o Zabbix do laboratório via API.")
    ap.add_argument("--hosts", type=int, default=20, help="quantidade de hosts simulados (padrão: 20)")
    ap.add_argument("--url", default=env("ZABBIX_WEB_URL", "http://localhost:8080"))
    ap.add_argument("--usuario", default=env("ZABBIX_ADMIN_USER", "Admin"))
    ap.add_argument("--senha", default=env("ZABBIX_ADMIN_PASSWORD", "zabbix"))
    args = ap.parse_args()

    print(f"Conectando à API do Zabbix em {args.url} ...")
    api = conectar(args.url, args.usuario, args.senha)
    try:
        gh = grupo_de_hosts(api, GRUPO_HOSTS)
        gt = grupo_de_templates(api, GRUPO_TEMPLATES)
        template_id, template_novo = garantir_template(api, gt)
        item_novo = garantir_item(api, template_id)
        trigger_nova = garantir_trigger(api, template_id)
        hosts_criados = garantir_hosts(api, args.hosts, gh, template_id)
        agente_ok = ajustar_agente_do_zabbix_server(api)
    finally:
        try:
            api.logout()
        except Exception:
            pass

    print("\nResumo:")
    print(f"  template: {'criado' if template_novo else 'já existia'} ({NOME_TEMPLATE})")
    print(f"  item {CHAVE_ITEM}: {'criado' if item_novo else 'já existia'}")
    print(f"  trigger CPU > {LIMITE_CPU}%: {'criada' if trigger_nova else 'já existia'}")
    print(f"  hosts simulados criados agora: {hosts_criados} (total desejado: {args.hosts})")
    print(f"  interface do agente do 'Zabbix server': {'ajustada' if agente_ok else 'verifique manualmente'}")
    print("\nPróximo passo: python scripts/simulador_zabbix.py")


if __name__ == "__main__":
    main()
