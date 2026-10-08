import time
import random
from zabbix_utils import Sender, ItemValue

# Aponta para o contentor do Zabbix Server local
sender = Sender(server="127.0.0.1", port=10051)

print("A iniciar simulação para 20 servidores... Pressione Ctrl+C para parar.")

while True:
    metricas = [] # Lista vazia para acumular os dados
    
    # Ciclo for que vai do número 1 ao 20
    for i in range(1, 21):
        # Formata o nome para ter dois dígitos (ex: Servidor-Simulado-01)
        nome_host = f"Servidor-Simulado-{i:02d}"
        
        # Gera a carga de CPU aleatória
        uso_cpu = random.randint(10, 95)
        
        # Adiciona a métrica à lista
        metricas.append(ItemValue(nome_host, "cpu.simulada", uso_cpu))
    
    # Envia as 20 métricas de uma só vez para o Zabbix
    resposta = sender.send(metricas)
    
    print(f"20 métricas enviadas | Status da resposta: {resposta}")
    print("-" * 45)
    
    # Aguarda 5 segundos antes do próximo envio
    time.sleep(5)