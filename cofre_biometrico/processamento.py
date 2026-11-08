"""
Pipeline de processamento de imagens digitais, organizado nas cinco fases
clássicas (Gonzalez & Woods):

  Fase 1 - Aquisição ............ Camera, carregar_imagem
  Fase 2 - Pré-processamento .... pre_processar, avaliar_qualidade
  Fase 3 - Segmentação .......... detectar_rostos, detectar_olhos
  Fase 4 - Representação e
           descrição ............ extrair_rosto (recorte, alinhamento,
                                  normalização) + histogramas LBP
  Fase 5 - Reconhecimento e
           interpretação ........ Reconhecedor (LBPH) e ProvaDeVida
"""
import os
import glob
import math

import cv2
import numpy as np

import config


# =====================================================================
# FASE 1 - AQUISIÇÃO
# =====================================================================
class Camera:
    """Captura quadros da webcam em tempo real."""

    def __init__(self, indice=config.CAMERA_INDEX):
        self.cap = cv2.VideoCapture(indice)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Nao foi possivel abrir a camera {indice}. "
                "Verifique se ela esta conectada ou altere CAMERA_INDEX em config.py."
            )

    def ler(self):
        ok, quadro = self.cap.read()
        if not ok or quadro is None:
            raise RuntimeError("Falha ao capturar imagem da camera.")
        return cv2.flip(quadro, 1)  # espelha para parecer um espelho

    def fechar(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.fechar()


def carregar_imagem(caminho):
    """Aquisição alternativa: imagem de arquivo (scanner, foto, câmera externa)."""
    imagem = cv2.imread(caminho)
    if imagem is None:
        raise ValueError(f"Arquivo de imagem invalido: {caminho}")
    return imagem


# =====================================================================
# FASE 2 - PRÉ-PROCESSAMENTO
# =====================================================================
_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def pre_processar(imagem):
    """Converte para tons de cinza, reduz ruído e equaliza o contraste."""
    if imagem.ndim == 3:
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    else:
        cinza = imagem.copy()
    cinza = cv2.GaussianBlur(cinza, (3, 3), 0)   # filtro passa-baixa (ruído)
    return _clahe.apply(cinza)                   # equalização adaptativa


def avaliar_qualidade(rosto_cinza):
    """Rejeita amostras escuras, estouradas ou borradas.
    Retorna (ok, mensagem)."""
    brilho = float(np.mean(rosto_cinza))
    nitidez = float(cv2.Laplacian(rosto_cinza, cv2.CV_64F).var())
    if brilho < 40:
        return False, "Ambiente muito escuro"
    if brilho > 220:
        return False, "Luz excessiva"
    if nitidez < 30:
        return False, "Imagem borrada - fique parado"
    return True, "OK"


# =====================================================================
# FASE 3 - SEGMENTAÇÃO
# =====================================================================
def _carregar_cascade(nome):
    """Usa o XML da pasta modelos/ do projeto; se faltar, tenta o do OpenCV
    (versões 5.x do pip não trazem mais esses arquivos)."""
    candidatos = [os.path.join(config.BASE_DIR, "modelos", nome)]
    if hasattr(cv2, "data") and getattr(cv2.data, "haarcascades", ""):
        candidatos.append(os.path.join(cv2.data.haarcascades, nome))
    for caminho in candidatos:
        if os.path.exists(caminho):
            c = cv2.CascadeClassifier(caminho)
            if not c.empty():
                return c
    raise RuntimeError(f"Classificador {nome} nao encontrado na pasta modelos/.")


_detector_rosto = _carregar_cascade("haarcascade_frontalface_default.xml")
_detector_olhos = _carregar_cascade("haarcascade_eye_tree_eyeglasses.xml")


def detectar_rostos(cinza, tamanho_min=(90, 90)):
    """Separa as regiões de rosto do restante da imagem (Viola-Jones)."""
    rostos = _detector_rosto.detectMultiScale(
        cinza, scaleFactor=1.1, minNeighbors=6, minSize=tamanho_min)
    return [tuple(int(v) for v in r) for r in rostos]


def maior_rosto(rostos):
    if not rostos:
        return None
    return max(rostos, key=lambda r: r[2] * r[3])


def detectar_olhos(cinza, rosto):
    """Procura olhos apenas na metade superior do rosto.
    Retorna coordenadas absolutas (x, y, w, h), ordenadas da esquerda p/ direita."""
    x, y, w, h = rosto
    roi = cinza[y:y + h // 2, x:x + w]
    olhos = _detector_olhos.detectMultiScale(
        roi, scaleFactor=1.1, minNeighbors=8, minSize=(w // 10, w // 10))
    olhos = [(x + ex, y + ey, ew, eh) for (ex, ey, ew, eh) in olhos]
    olhos.sort(key=lambda o: o[0])
    return olhos[:2] if len(olhos) >= 2 else olhos


# =====================================================================
# FASE 4 - REPRESENTAÇÃO E DESCRIÇÃO
# =====================================================================
def _alinhar(cinza, rosto, olhos):
    """Gira a imagem para deixar os olhos na horizontal."""
    if len(olhos) < 2:
        return cinza
    (x1, y1, w1, h1), (x2, y2, w2, h2) = olhos[0], olhos[1]
    c1 = (x1 + w1 / 2, y1 + h1 / 2)
    c2 = (x2 + w2 / 2, y2 + h2 / 2)
    angulo = math.degrees(math.atan2(c2[1] - c1[1], c2[0] - c1[0]))
    if abs(angulo) > 25:          # provavelmente detecção errada; não gira
        return cinza
    x, y, w, h = rosto
    centro = (x + w / 2, y + h / 2)
    m = cv2.getRotationMatrix2D(centro, angulo, 1.0)
    return cv2.warpAffine(cinza, m, (cinza.shape[1], cinza.shape[0]),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def extrair_rosto(cinza, rosto, alinhar=True):
    """Recorta, alinha e normaliza o rosto para o tamanho padrão.
    O descritor final (histogramas LBP) é calculado pelo LBPH na Fase 5."""
    if alinhar:
        cinza = _alinhar(cinza, rosto, detectar_olhos(cinza, rosto))
    x, y, w, h = rosto
    recorte = cinza[max(0, y):y + h, max(0, x):x + w]
    recorte = cv2.resize(recorte, config.TAMANHO_ROSTO, interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(recorte)


# =====================================================================
# FASE 5 - RECONHECIMENTO E INTERPRETAÇÃO
# =====================================================================
class Reconhecedor:
    """Classificador LBPH (Local Binary Patterns Histograms)."""

    def __init__(self):
        self.modelo = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8)
        self.treinado = False
        if os.path.exists(config.MODELO_PATH):
            try:
                self.modelo.read(config.MODELO_PATH)
                self.treinado = True
            except cv2.error:
                self.treinado = False

    @staticmethod
    def carregar_amostras(ids_permitidos=None):
        imagens, rotulos = [], []
        if not os.path.isdir(config.ROSTOS_DIR):
            return imagens, rotulos
        for pasta in os.listdir(config.ROSTOS_DIR):
            if not pasta.isdigit():
                continue
            uid = int(pasta)
            if ids_permitidos is not None and uid not in ids_permitidos:
                continue
            for arq in glob.glob(os.path.join(config.ROSTOS_DIR, pasta, "*.png")):
                img = cv2.imread(arq, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    imagens.append(cv2.resize(img, config.TAMANHO_ROSTO))
                    rotulos.append(uid)
        return imagens, rotulos

    def treinar(self, ids_permitidos=None):
        """Treina com as amostras de todos os usuários ativos.
        Retorna a quantidade de imagens usadas."""
        imagens, rotulos = self.carregar_amostras(ids_permitidos)
        if not imagens:
            self.treinado = False
            if os.path.exists(config.MODELO_PATH):
                os.remove(config.MODELO_PATH)
            return 0
        self.modelo = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8)
        self.modelo.train(imagens, np.array(rotulos, dtype=np.int32))
        os.makedirs(os.path.dirname(config.MODELO_PATH), exist_ok=True)
        self.modelo.write(config.MODELO_PATH)
        self.treinado = True
        return len(imagens)

    def reconhecer(self, rosto):
        """Retorna (id_usuario ou None, distancia)."""
        if not self.treinado:
            return None, float("inf")
        rotulo, distancia = self.modelo.predict(rosto)
        if distancia > config.LIMIAR_LBPH:
            return None, distancia
        return int(rotulo), distancia

    @staticmethod
    def similaridade(distancia):
        """Converte a distância LBPH em um percentual aproximado (0-100)."""
        if distancia == float("inf"):
            return 0.0
        return max(0.0, min(100.0, 100.0 - distancia))


class ProvaDeVida:
    """Detecta uma piscada: olhos abertos -> fechados -> abertos.
    Uma foto impressa ou tela parada não pisca."""

    def __init__(self):
        self.quadros_abertos = 0
        self.quadros_fechados = 0
        self.confirmada = not config.PROVA_DE_VIDA

    def atualizar(self, qtd_olhos):
        if self.confirmada:
            return True
        if qtd_olhos >= 2:
            if self.quadros_abertos >= 3 and 1 <= self.quadros_fechados <= 6:
                self.confirmada = True
            self.quadros_abertos += 1
            self.quadros_fechados = 0
        elif qtd_olhos == 0 and self.quadros_abertos >= 3:
            self.quadros_fechados += 1
            if self.quadros_fechados > 6:     # olhos sumiram por muito tempo
                self.quadros_abertos = 0
                self.quadros_fechados = 0
        return self.confirmada
