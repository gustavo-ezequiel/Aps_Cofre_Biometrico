"""
Configurações gerais do Sistema de Identificação e Autenticação Biométrica.
Altere aqui o banco de dados, a câmera e os parâmetros de reconhecimento.
"""
import os

# ----------------------------------------------------------------- Pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
ROSTOS_DIR = os.path.join(DADOS_DIR, "rostos")          # amostras de cada usuário
INTRUSOS_DIR = os.path.join(DADOS_DIR, "intrusos")      # fotos de acessos negados
RELATORIOS_DIR = os.path.join(DADOS_DIR, "relatorios")  # relatórios HTML/CSV
MODELO_PATH = os.path.join(DADOS_DIR, "modelo_lbph.yml")

# ------------------------------------------------------- Banco de dados
# "sqlite" funciona sem instalar nada.
# "mysql" usa o MySQL do XAMPP (inicie o MySQL no painel do XAMPP antes).
DB_ENGINE = "sqlite"
SQLITE_PATH = os.path.join(DADOS_DIR, "cofre.db")
MYSQL = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "cofre_biometrico",
}

# ------------------------------------------------------------- Câmera
CAMERA_INDEX = 0            # 0 = webcam padrão; troque para 1, 2... se tiver outra

# ------------------------------------------------------ Reconhecimento
TAMANHO_ROSTO = (200, 200)  # tamanho padronizado do rosto (Fase 4)
AMOSTRAS_CADASTRO = 30      # quantas fotos capturar no cadastro
LIMIAR_LBPH = 65.0          # distância máxima aceita pelo LBPH (menor = mais rígido)
FRAMES_CONFIRMACAO = 8      # quadros seguidos com a mesma identidade para decidir
TEMPO_MAX_VERIFICACAO = 20  # segundos até desistir da verificação

# ----------------------------------------------------------- Segurança
PROVA_DE_VIDA = True        # exige uma piscada (dificulta fraude com foto impressa)
MAX_TENTATIVAS = 3          # negações seguidas antes de bloquear o terminal
TEMPO_BLOQUEIO = 60         # segundos de bloqueio após exceder as tentativas

NIVEIS = {
    1: "Permissao geral",
    2: "Diretor de divisao",
    3: "Ministro do Meio Ambiente",
}
