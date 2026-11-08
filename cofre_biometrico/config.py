import os

# ----------------------------------------------------------------- Pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
ROSTOS_DIR = os.path.join(DADOS_DIR, "rostos")          
INTRUSOS_DIR = os.path.join(DADOS_DIR, "intrusos")      
RELATORIOS_DIR = os.path.join(DADOS_DIR, "relatorios")  
MODELO_PATH = os.path.join(DADOS_DIR, "modelo_lbph.yml")

# ------------------------------------------------------- Banco de dados
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
CAMERA_INDEX = 0            

# ------------------------------------------------------ Reconhecimento
TAMANHO_ROSTO = (200, 200)  
AMOSTRAS_CADASTRO = 30      
LIMIAR_LBPH = 65.0          
FRAMES_CONFIRMACAO = 8      
TEMPO_MAX_VERIFICACAO = 20  

# ----------------------------------------------------------- Segurança
PROVA_DE_VIDA = True       
MAX_TENTATIVAS = 3          
TEMPO_BLOQUEIO = 60         

NIVEIS = {
    1: "Permissao geral",
    2: "Diretor de divisao",
    3: "Ministro do Meio Ambiente",
}
