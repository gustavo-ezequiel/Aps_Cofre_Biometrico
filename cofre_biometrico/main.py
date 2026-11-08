"""
COFRE BIOMÉTRICO - Ministério do Meio Ambiente
Sistema de Identificação e Autenticação Biométrica por reconhecimento facial.

Execute:  python main.py
"""
import os
import shutil
import sys
import time
import unicodedata
import webbrowser
from datetime import datetime

import cv2
import numpy as np

import config
import processamento as pdi
import relatorios
from banco import BancoDeDados

JANELA = "Cofre Biometrico - MMA"
VERDE, VERMELHO, AMARELO, BRANCO, AZUL = (0, 200, 0), (0, 0, 220), (0, 215, 255), (255, 255, 255), (255, 140, 0)
EXTENSOES = (".jpg", ".jpeg", ".png", ".bmp")


# ===================================================== utilidades de tela
def texto(img, msg, pos, cor=BRANCO, escala=0.6, esp=2):
    """putText não aceita acentos: as mensagens na janela ficam sem acento."""
    cv2.putText(img, msg, pos, cv2.FONT_HERSHEY_SIMPLEX, escala, (0, 0, 0), esp + 3, cv2.LINE_AA)
    cv2.putText(img, msg, pos, cv2.FONT_HERSHEY_SIMPLEX, escala, cor, esp, cv2.LINE_AA)


def faixa_titulo(img, titulo, cor=AZUL):
    cv2.rectangle(img, (0, 0), (img.shape[1], 36), cor, -1)
    texto(img, titulo, (10, 25), BRANCO, 0.65)


def ler_int(msg, validos=None):
    while True:
        valor = input(msg).strip()
        if valor.isdigit() and (validos is None or int(valor) in validos):
            return int(valor)
        print("  Valor invalido.")


def pausar():
    input("\nPressione ENTER para continuar...")


# =================================================================== cadastro
def _salvar_amostra(uid, rosto, indice):
    pasta = os.path.join(config.ROSTOS_DIR, str(uid))
    os.makedirs(pasta, exist_ok=True)
    cv2.imwrite(os.path.join(pasta, f"{indice:03d}.png"), rosto)


def _dados_novo_usuario():
    nome = input("Nome completo: ").strip()
    while not nome:
        nome = input("Nome completo (obrigatorio): ").strip()
    cargo = input("Cargo/divisao: ").strip()
    print("Niveis de acesso:")
    for n, desc in config.NIVEIS.items():
        print(f"  {n} - {desc}")
    nivel = ler_int("Nivel (1-3): ", config.NIVEIS)
    return nome, cargo, nivel


def _cancelar_cadastro(db, uid):
    db.excluir_usuario(uid)
    shutil.rmtree(os.path.join(config.ROSTOS_DIR, str(uid)), ignore_errors=True)


def cadastrar_por_camera(db, rec):
    print("\n=== CADASTRO PELA CAMERA ===")
    nome, cargo, nivel = _dados_novo_usuario()
    uid = db.inserir_usuario(nome, cargo, nivel)
    print(f"\nOlhe para a camera e mova levemente a cabeca. ESC cancela.")
    salvas, quadro_n = 0, 0
    try:
        with pdi.Camera() as cam:
            while salvas < config.AMOSTRAS_CADASTRO:
                quadro = cam.ler()                                  # Fase 1
                cinza = pdi.pre_processar(quadro)                   # Fase 2
                rostos = pdi.detectar_rostos(cinza)                 # Fase 3
                faixa_titulo(quadro, f"Cadastro: {nome} (nivel {nivel})")
                status, cor = "Nenhum rosto detectado", AMARELO
                if len(rostos) > 1:
                    status = "Apenas uma pessoa na frente da camera"
                elif rostos:
                    r = rostos[0]
                    x, y, w, h = r
                    rosto = pdi.extrair_rosto(cinza, r)             # Fase 4
                    ok, motivo = pdi.avaliar_qualidade(rosto)
                    cor = VERDE if ok else AMARELO
                    status = "Capturando..." if ok else motivo
                    cv2.rectangle(quadro, (x, y), (x + w, y + h), cor, 2)
                    quadro_n += 1
                    if ok and quadro_n % 3 == 0:                    # varia as poses
                        salvas += 1
                        _salvar_amostra(uid, rosto, salvas)
                # barra de progresso
                larg = int(quadro.shape[1] * salvas / config.AMOSTRAS_CADASTRO)
                cv2.rectangle(quadro, (0, quadro.shape[0] - 12), (larg, quadro.shape[0]), VERDE, -1)
                texto(quadro, f"{status}  {salvas}/{config.AMOSTRAS_CADASTRO}",
                      (10, quadro.shape[0] - 22), cor)
                cv2.imshow(JANELA, quadro)
                if cv2.waitKey(1) & 0xFF == 27:
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        _cancelar_cadastro(db, uid)
        print("Cadastro cancelado.")
        return
    except RuntimeError as erro:
        _cancelar_cadastro(db, uid)
        print(f"ERRO: {erro}")
        return
    total = rec.treinar(db.ids_ativos())
    print(f"Usuario #{uid} cadastrado com {salvas} amostras. Modelo treinado com {total} imagens.")


def cadastrar_por_imagens(db, rec):
    """Aquisição alternativa (scanner/câmera fotográfica): pasta com fotos."""
    print("\n=== CADASTRO POR PASTA DE IMAGENS ===")
    pasta = input("Caminho da pasta com as fotos do usuario: ").strip().strip('"')
    if not os.path.isdir(pasta):
        print("Pasta nao encontrada.")
        return
    arquivos = sorted(f for f in os.listdir(pasta) if f.lower().endswith(EXTENSOES))
    if not arquivos:
        print("Nenhuma imagem (.jpg/.png/.bmp) na pasta.")
        return
    nome, cargo, nivel = _dados_novo_usuario()
    uid = db.inserir_usuario(nome, cargo, nivel)
    salvas, ignoradas = 0, 0
    for arq in arquivos:
        try:
            img = pdi.carregar_imagem(os.path.join(pasta, arq))
        except ValueError:
            ignoradas += 1
            continue
        cinza = pdi.pre_processar(img)
        r = pdi.maior_rosto(pdi.detectar_rostos(cinza, tamanho_min=(60, 60)))
        if r is None:
            ignoradas += 1
            continue
        rosto = pdi.extrair_rosto(cinza, r)
        salvas += 1
        _salvar_amostra(uid, rosto, salvas)
        salvas += 1                                   # aumento de dados: espelho
        _salvar_amostra(uid, cv2.flip(rosto, 1), salvas)
    if salvas < 6:
        _cancelar_cadastro(db, uid)
        print(f"Rostos insuficientes ({salvas // 2} fotos validas). Use ao menos 3 fotos nitidas.")
        return
    total = rec.treinar(db.ids_ativos())
    print(f"Usuario #{uid} cadastrado: {salvas} amostras ({ignoradas} arquivos sem rosto ignorados).")
    print(f"Modelo treinado com {total} imagens.")


# ============================================================ verificação
class ControleTentativas:
    """Bloqueia o terminal após várias negações seguidas."""

    def __init__(self):
        self.negacoes = 0
        self.bloqueado_ate = 0.0

    def restante(self):
        return max(0, int(self.bloqueado_ate - time.time()))

    def registrar(self, concedido, db, nivel_area):
        if concedido:
            self.negacoes = 0
            return
        self.negacoes += 1
        if self.negacoes >= config.MAX_TENTATIVAS:
            self.bloqueado_ate = time.time() + config.TEMPO_BLOQUEIO
            self.negacoes = 0
            db.registrar_acesso(None, nivel_area, "BLOQUEIO",
                                f"{config.MAX_TENTATIVAS} negacoes seguidas - terminal bloqueado")
            print(f"\n!!! ALERTA: terminal bloqueado por {config.TEMPO_BLOQUEIO}s !!!")


def _salvar_intruso(quadro):
    os.makedirs(config.INTRUSOS_DIR, exist_ok=True)
    caminho = os.path.join(config.INTRUSOS_DIR, f"intruso_{datetime.now():%Y%m%d_%H%M%S}.jpg")
    cv2.imwrite(caminho, quadro)
    return caminho


def _tela_resultado(cam, concedido, linhas, segundos=3):
    fim = time.time() + segundos
    while time.time() < fim:
        quadro = cam.ler()
        sobre = quadro.copy()
        cv2.rectangle(sobre, (0, 0), (quadro.shape[1], quadro.shape[0]), VERDE if concedido else VERMELHO, -1)
        quadro = cv2.addWeighted(sobre, 0.45, quadro, 0.55, 0)
        texto(quadro, "ACESSO CONCEDIDO" if concedido else "ACESSO NEGADO", (30, 80), BRANCO, 1.2, 3)
        for i, l in enumerate(linhas):
            texto(quadro, l, (30, 130 + i * 32), BRANCO, 0.7)
        cv2.imshow(JANELA, quadro)
        cv2.waitKey(1)


def _cortar(txt, largura_px, fonte, escala):
    txt = str(txt)
    while txt and cv2.getTextSize(txt, fonte, escala, 1)[0][0] > largura_px:
        txt = txt[:-4] + "..." if len(txt) > 4 else ""
    return txt


def _sem_acento(txt):
    """cv2.putText não desenha acentos: remove-os só para exibir na janela."""
    txt = unicodedata.normalize("NFKD", str(txt))
    return "".join(c for c in txt if not unicodedata.combining(c))


def _quebrar(txt, largura_px, fonte, escala):
    """Quebra o texto em linhas que caibam na largura da coluna."""
    linhas, atual = [], ""
    for palavra in _sem_acento(txt).split():
        teste = f"{atual} {palavra}".strip()
        if cv2.getTextSize(teste, fonte, escala, 1)[0][0] <= largura_px or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    return [_cortar(l, largura_px, fonte, escala) for l in linhas]


COR_NIVEL = {1: (60, 130, 0), 2: (0, 120, 200), 3: (0, 0, 170)}   # verde, laranja, vermelho


def _janela_conteudo(nivel, titulo, cabecalhos, linhas, observacao=""):
    """Mostra a tabela do cofre numa janela (para a apresentação)."""
    fonte, esc, alt_texto = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 22
    larguras = []
    for i, cab in enumerate(cabecalhos):
        valores = [cab] + [l[i] for l in linhas]
        maior = max(cv2.getTextSize(_sem_acento(v), fonte, esc, 1)[0][0] for v in valores)
        larguras.append(min(maior + 30, 380))
    largura = max(sum(larguras) + 20, 760)
    celulas = [[_quebrar(v, larguras[i] - 20, fonte, esc) for i, v in enumerate(l)]
               for l in [cabecalhos] + list(linhas)]
    alturas = [max(len(c) for c in linha) * alt_texto + 14 for linha in celulas]
    obs = _quebrar("Observacao: " + observacao, largura - 30, fonte, 0.45) if observacao else []
    topo = 60
    altura = topo + sum(alturas) + len(obs) * 20 + 60
    tela = np.full((altura, largura, 3), 28, np.uint8)
    cv2.rectangle(tela, (0, 0), (largura, 45), COR_NIVEL.get(nivel, (0, 0, 150)), -1)
    cv2.putText(tela, _sem_acento(titulo), (10, 30), fonte, 0.75, BRANCO, 2, cv2.LINE_AA)
    y = topo
    for r, linha in enumerate(celulas):
        fundo = (90, 60, 0) if r == 0 else ((45, 45, 45) if r % 2 else (35, 35, 35))
        cv2.rectangle(tela, (10, y), (largura - 10, y + alturas[r]), fundo, -1)
        x = 18
        for i, partes in enumerate(linha):
            for k, parte in enumerate(partes):
                cv2.putText(tela, parte, (x, y + 22 + k * alt_texto), fonte, esc,
                            AMARELO if r == 0 else BRANCO, 1, cv2.LINE_AA)
            x += larguras[i]
        y += alturas[r]
    y += 25
    for parte in obs:
        cv2.putText(tela, parte, (12, y), fonte, 0.45, (170, 200, 255), 1, cv2.LINE_AA)
        y += 20
    cv2.putText(tela, "Pressione qualquer tecla para fechar o cofre", (10, altura - 15),
                fonte, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.imshow("Conteudo do Cofre", tela)
    cv2.waitKey(0)
    cv2.destroyWindow("Conteudo do Cofre")


def mostrar_conteudo_cofre(db, nivel_area):
    """Abre a tabela correspondente à área liberada (terminal + janela)."""
    titulo, cabecalhos, linhas, observacao = db.consultar_area(nivel_area)
    rotulo = max(len(c) for c in cabecalhos)
    print("\n" + "#" * 60 + f"\n  {titulo}\n" + "#" * 60)
    for n, linha in enumerate(linhas, 1):
        print(f"\n[{n}/{len(linhas)}]")
        for cab, valor in zip(cabecalhos, linha):
            print(f"  {cab.ljust(rotulo)} : {valor}")
    if observacao:
        print(f"\nObservação: {observacao}")
    print("\n" + "#" * 60 + f"\n{len(linhas)} registro(s). Feche a janela do cofre para continuar.")
    _janela_conteudo(nivel_area, titulo, cabecalhos, linhas, observacao)


def verificar_acesso(db, rec, controle):
    print("\n=== ACESSO AO COFRE ===")
    if controle.restante():
        print(f"Terminal bloqueado. Aguarde {controle.restante()}s.")
        return
    if not rec.treinado:
        print("Nenhum usuario cadastrado/treinado. Cadastre alguem primeiro.")
        return
    for n, desc in config.NIVEIS.items():
        print(f"  {n} - Area nivel {n} ({desc})")
    nivel_area = ler_int("Qual area deseja acessar? ", config.NIVEIS)

    votos = {}            # id -> quadros seguidos reconhecidos
    desconhecidos = 0
    ultimo_id = "inicio"
    melhor_dist = float("inf")
    vida = pdi.ProvaDeVida()
    inicio = time.time()
    decisao = None        # (usuario_id, concedido, motivo, distancia, quadro)
    original = None

    try:
        with pdi.Camera() as cam:
            while decisao is None:
                decorrido = time.time() - inicio
                if decorrido > config.TEMPO_MAX_VERIFICACAO:
                    if votos and not vida.confirmada:
                        uid_visto = max(votos, key=votos.get)
                        decisao = (uid_visto, False, "Prova de vida falhou (possivel foto/video)",
                                   melhor_dist, original)
                    else:
                        decisao = (None, False, "Tempo esgotado sem identificacao", melhor_dist, original)
                    break
                quadro = cam.ler()                                       # Fase 1
                original = quadro.copy()
                cinza = pdi.pre_processar(quadro)                        # Fase 2
                rostos = pdi.detectar_rostos(cinza)                      # Fase 3
                faixa_titulo(quadro, f"Area nivel {nivel_area} - "
                                     f"{config.TEMPO_MAX_VERIFICACAO - int(decorrido)}s")

                if not rostos:
                    texto(quadro, "Posicione o rosto na frente da camera", (10, 65), AMARELO)
                    votos.clear(); desconhecidos = 0
                elif len(rostos) > 1:
                    texto(quadro, "Apenas UMA pessoa por vez!", (10, 65), VERMELHO)
                    for (x, y, w, h) in rostos:
                        cv2.rectangle(quadro, (x, y), (x + w, y + h), VERMELHO, 2)
                    votos.clear(); desconhecidos = 0
                else:
                    r = rostos[0]
                    x, y, w, h = r
                    olhos = pdi.detectar_olhos(cinza, r)
                    vivo = vida.atualizar(len(olhos))
                    rosto = pdi.extrair_rosto(cinza, r)                  # Fase 4
                    uid, dist = rec.reconhecer(rosto)                    # Fase 5
                    melhor_dist = min(melhor_dist, dist)

                    if uid is None:
                        desconhecidos += 1
                        votos.clear()
                        rotulo, cor = f"Desconhecido", VERMELHO
                    else:
                        desconhecidos = 0
                        if uid != ultimo_id:
                            votos.clear()
                        votos[uid] = votos.get(uid, 0) + 1
                        u = db.obter_usuario(uid)
                        nome = u["nome"] if u else "?"
                        rotulo = f"{nome} ({rec.similaridade(dist):.0f}%)"
                        cor = VERDE
                    ultimo_id = uid

                    cv2.rectangle(quadro, (x, y), (x + w, y + h), cor, 2)
                    texto(quadro, rotulo, (x, max(50, y - 10)), cor)
                    for (ex, ey, ew, eh) in olhos:
                        cv2.rectangle(quadro, (ex, ey), (ex + ew, ey + eh), AZUL, 1)
                    if not vivo:
                        texto(quadro, "Prova de vida: PISQUE os olhos", (10, 65), AMARELO)

                    if desconhecidos >= config.FRAMES_CONFIRMACAO * 2:
                        decisao = (None, False, "Rosto nao reconhecido", dist, original)
                    elif uid is not None and votos[uid] >= config.FRAMES_CONFIRMACAO and vivo:
                        u = db.obter_usuario(uid)
                        if not u or not u["ativo"]:
                            decisao = (uid, False, "Usuario inativo", dist, original)
                        elif u["nivel"] >= nivel_area:
                            decisao = (uid, True, f"Nivel {u['nivel']} >= area {nivel_area}", dist, original)
                        else:
                            decisao = (uid, False, f"Nivel insuficiente ({u['nivel']} < {nivel_area})",
                                       dist, original)

                cv2.imshow(JANELA, quadro)
                if cv2.waitKey(1) & 0xFF == 27:
                    print("Verificacao cancelada.")
                    return

            uid, concedido, motivo, dist, foto_quadro = decisao
            foto = None if concedido or foto_quadro is None else _salvar_intruso(foto_quadro)
            db.registrar_acesso(uid, nivel_area, "CONCEDIDO" if concedido else "NEGADO",
                                motivo, dist, foto)
            u = db.obter_usuario(uid) if uid else None
            linhas = [f"Usuario: {u['nome']}" if u else "Usuario: nao identificado",
                      f"Nivel do usuario: {u['nivel']}" if u else "",
                      f"Area solicitada: nivel {nivel_area}",
                      motivo]
            _tela_resultado(cam, concedido, [l for l in linhas if l])
    except RuntimeError as erro:
        print(f"ERRO: {erro}")
        return

    print(("ACESSO CONCEDIDO" if concedido else "ACESSO NEGADO") + f" - {motivo}")
    if foto:
        print(f"Foto registrada: {foto}")
    controle.registrar(concedido, db, nivel_area)
    if concedido:
        mostrar_conteudo_cofre(db, nivel_area)


# ============================================================ gerenciamento
def listar_usuarios(db):
    usuarios = db.listar_usuarios(apenas_ativos=False)
    if not usuarios:
        print("\nNenhum usuario cadastrado.")
        return
    print(f"\n{'ID':>4}  {'Nome':<28} {'Cargo':<22} {'Nivel':<5} Situacao")
    print("-" * 72)
    for u in usuarios:
        pasta = os.path.join(config.ROSTOS_DIR, str(u["id"]))
        amostras = len(os.listdir(pasta)) if os.path.isdir(pasta) else 0
        print(f"{u['id']:>4}  {u['nome'][:28]:<28} {(u['cargo'] or '-')[:22]:<22} {u['nivel']:<5} "
              f"{'Ativo' if u['ativo'] else 'Inativo'} ({amostras} amostras)")


def desativar_usuario(db, rec):
    listar_usuarios(db)
    uid = ler_int("\nID do usuario a desativar (0 cancela): ")
    if uid == 0:
        return
    u = db.obter_usuario(uid)
    if not u:
        print("Usuario nao encontrado.")
        return
    if input(f"Confirma desativar {u['nome']}? (s/n) ").lower() != "s":
        return
    db.desativar_usuario(uid)
    rec.treinar(db.ids_ativos())
    print("Usuario desativado e modelo retreinado. O historico de acessos foi mantido.")


def alterar_nivel(db):
    listar_usuarios(db)
    uid = ler_int("\nID do usuario (0 cancela): ")
    if uid == 0 or not db.obter_usuario(uid):
        return
    nivel = ler_int("Novo nivel (1-3): ", config.NIVEIS)
    db.alterar_nivel(uid, nivel)
    print("Nivel alterado.")


def menu_relatorios(db):
    print("\n1 - Relatorio HTML (abre no navegador)\n2 - Exportar CSV (Excel)\n3 - Ultimos 15 acessos aqui")
    op = ler_int("Opcao: ", {1, 2, 3})
    if op == 1:
        caminho = relatorios.gerar_html(db)
        print(f"Relatorio gerado: {caminho}")
        webbrowser.open("file://" + os.path.abspath(caminho))
    elif op == 2:
        print(f"CSV gerado: {relatorios.exportar_csv(db)}")
    else:
        for a in db.listar_acessos(15):
            print(f"{a['data_hora']}  area {a['nivel_area']}  {a['resultado']:<9} "
                  f"{(a['nome'] or 'Desconhecido'):<22} {a['motivo']}")


# =================================================================== menu
def main():
    try:   # evita erro com acentos em terminais antigos do Windows
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    for pasta in (config.DADOS_DIR, config.ROSTOS_DIR, config.INTRUSOS_DIR, config.RELATORIOS_DIR):
        os.makedirs(pasta, exist_ok=True)
    try:
        db = BancoDeDados()
    except Exception as erro:
        print(f"ERRO ao conectar ao banco ({config.DB_ENGINE}): {erro}")
        return
    rec = pdi.Reconhecedor()
    controle = ControleTentativas()

    opcoes = {
        "1": ("Acessar o cofre (reconhecimento facial)", lambda: verificar_acesso(db, rec, controle)),
        "2": ("Cadastrar usuario pela camera", lambda: cadastrar_por_camera(db, rec)),
        "3": ("Cadastrar usuario por pasta de imagens", lambda: cadastrar_por_imagens(db, rec)),
        "4": ("Listar usuarios", lambda: listar_usuarios(db)),
        "5": ("Alterar nivel de acesso", lambda: alterar_nivel(db)),
        "6": ("Desativar usuario", lambda: desativar_usuario(db, rec)),
        "7": ("Relatorios de acesso", lambda: menu_relatorios(db)),
        "8": ("Retreinar modelo", lambda: print(f"Modelo treinado com {rec.treinar(db.ids_ativos())} imagens.")),
    }
    while True:
        print("\n" + "=" * 52)
        print("   COFRE BIOMETRICO - MINISTERIO DO MEIO AMBIENTE")
        print("=" * 52)
        for k, (desc, _) in opcoes.items():
            print(f" {k} - {desc}")
        print(" 0 - Sair")
        op = input("Opcao: ").strip()
        if op == "0":
            break
        if op in opcoes:
            try:
                opcoes[op][1]()
            except KeyboardInterrupt:
                print("\nOperacao interrompida.")
            cv2.destroyAllWindows()
            pausar()
        else:
            print("Opcao invalida.")
    db.fechar()


if __name__ == "__main__":
    main()
