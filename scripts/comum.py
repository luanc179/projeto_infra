"""Funções compartilhadas pelos scripts do laboratório."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_env(caminho=None):
    """Lê o arquivo .env da raiz do projeto (sem dependências externas).

    Variáveis já definidas no ambiente têm prioridade sobre o arquivo.
    """
    arquivo = Path(caminho) if caminho else RAIZ / ".env"
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def env(chave, padrao=None):
    return os.environ.get(chave, padrao)


def nomes_dos_hosts(quantidade):
    """Nomes dos hosts simulados: Servidor-Simulado-01 ... Servidor-Simulado-NN."""
    return [f"Servidor-Simulado-{i:02d}" for i in range(1, quantidade + 1)]
