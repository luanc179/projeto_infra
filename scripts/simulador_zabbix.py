#!/usr/bin/env python3
"""Envia métricas de CPU simuladas para o Zabbix (item trapper cpu.simulada).

Os hosts e o item precisam existir: rode antes `python scripts/setup_zabbix.py`.
"""
import argparse
import random
import time

from zabbix_utils import ItemValue, Sender

from comum import carregar_env, env, nomes_dos_hosts

CHAVE_ITEM = "cpu.simulada"


def main():
    carregar_env()
    ap = argparse.ArgumentParser(description="Simula a carga de CPU de servidores e envia ao Zabbix.")
    ap.add_argument("--hosts", type=int, default=20, help="quantidade de hosts simulados (padrão: 20)")
    ap.add_argument("--intervalo", type=float, default=5.0, help="segundos entre os envios (padrão: 5)")
    ap.add_argument("--ciclos", type=int, default=0, help="número de envios (0 = até Ctrl+C)")
    ap.add_argument("--servidor", default=env("ZABBIX_SERVER_HOST", "127.0.0.1"))
    ap.add_argument("--porta", type=int, default=int(env("ZABBIX_SERVER_PORT", "10051")))
    args = ap.parse_args()

    sender = Sender(server=args.servidor, port=args.porta)
    nomes = nomes_dos_hosts(args.hosts)
    cpu = {nome: random.randint(20, 60) for nome in nomes}

    print(f"Simulando {len(nomes)} servidores -> {args.servidor}:{args.porta} (Ctrl+C para parar)")
    ciclo = 0
    try:
        while args.ciclos == 0 or ciclo < args.ciclos:
            ciclo += 1
            itens = []
            for nome in nomes:
                # Passeio aleatório entre 5% e 99%, com picos ocasionais para disparar a trigger (> 90%)
                cpu[nome] = max(5, min(99, cpu[nome] + random.randint(-8, 8)))
                if random.random() < 0.02:
                    cpu[nome] = random.randint(92, 99)
                itens.append(ItemValue(nome, CHAVE_ITEM, str(cpu[nome])))

            resposta = sender.send(itens)
            print(f"ciclo {ciclo}: enviados={resposta.total} processados={resposta.processed} falhas={resposta.failed}")
            if resposta.failed:
                print("  Dica: falhas indicam host/item inexistente. Rode `python scripts/setup_zabbix.py`.")
            if args.ciclos == 0 or ciclo < args.ciclos:
                time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nSimulação encerrada.")


if __name__ == "__main__":
    main()
