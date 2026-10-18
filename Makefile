.PHONY: env up down ps logs setup simulate reset

env:  ## cria o .env a partir do exemplo (se ainda nao existir)
	@test -f .env || (cp .env.example .env && echo '.env criado: edite as senhas antes de subir')

up: env  ## sobe o ambiente
	docker compose up -d

down:  ## derruba o ambiente (mantem os dados)
	docker compose down

ps:  ## status dos conteineres
	docker compose ps

logs:  ## logs em tempo real
	docker compose logs -f --tail=50

setup:  ## cria template, item, trigger e hosts simulados via API
	python scripts/setup_zabbix.py

simulate:  ## envia metricas simuladas ao Zabbix
	python scripts/simulador_zabbix.py

reset:  ## APAGA os volumes (banco e Grafana) e recomeca do zero
	docker compose down -v
