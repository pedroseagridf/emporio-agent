"""Caminhos do projeto resolvidos a partir da raiz do repositório.

Permite rodar a aplicação e os testes de qualquer diretório de trabalho.
Limitação conhecida (documentada no README): instalação via wheel fora do
repositório não carrega a pasta ``data/`` — o protótipo pressupõe o clone.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
