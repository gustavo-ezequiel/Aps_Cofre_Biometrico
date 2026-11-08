import csv
import html
import os
from datetime import datetime

import config


def _nome_arquivo(extensao):
    os.makedirs(config.RELATORIOS_DIR, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(config.RELATORIOS_DIR, f"relatorio_{carimbo}.{extensao}")


def exportar_csv(db):
    caminho = _nome_arquivo("csv")
    acessos = db.listar_acessos(limite=100000)
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Data/Hora", "Nivel da area", "Resultado", "Motivo",
                    "Usuario", "Nivel do usuario", "Distancia LBPH", "Foto"])
        for a in acessos:
            w.writerow([a["id"], a["data_hora"], a["nivel_area"], a["resultado"], a["motivo"],
                        a["nome"] or "Desconhecido", a["nivel_usuario"] or "-",
                        f"{a['distancia']:.1f}" if a["distancia"] is not None else "-",
                        a["foto"] or ""])
    return caminho


def gerar_html(db):
    caminho = _nome_arquivo("html")
    est = db.estatisticas()
    usuarios = db.listar_usuarios(apenas_ativos=False)
    acessos = db.listar_acessos(limite=1000)
    e = lambda t: html.escape(str(t)) if t is not None else "-"

    concedidos = est["por_resultado"].get("CONCEDIDO", 0)
    negados = est["por_resultado"].get("NEGADO", 0)
    bloqueios = est["por_resultado"].get("BLOQUEIO", 0)
    taxa = f"{100 * concedidos / est['total']:.1f}%" if est["total"] else "-"

    linhas_nivel = ""
    for nivel in (1, 2, 3):
        c = sum(q for n, r, q in est["por_nivel"] if n == nivel and r == "CONCEDIDO")
        n_ = sum(q for n, r, q in est["por_nivel"] if n == nivel and r == "NEGADO")
        linhas_nivel += f"<tr><td>Nivel {nivel} - {e(config.NIVEIS[nivel])}</td><td>{c}</td><td>{n_}</td></tr>"

    linhas_usuarios = "".join(
        f"<tr><td>{u['id']}</td><td>{e(u['nome'])}</td><td>{e(u['cargo'])}</td>"
        f"<td>{u['nivel']}</td><td>{'Ativo' if u['ativo'] else 'Inativo'}</td><td>{e(u['criado_em'])}</td></tr>"
        for u in usuarios)

    linhas_acessos = ""
    for a in acessos:
        foto = ""
        if a["foto"] and os.path.exists(a["foto"]):
            rel = os.path.relpath(a["foto"], config.RELATORIOS_DIR).replace(os.sep, "/")
            foto = f'<a href="{e(rel)}"><img src="{e(rel)}" alt="foto"></a>'
        dist = f"{a['distancia']:.1f}" if a["distancia"] is not None else "-"
        linhas_acessos += (
            f'<tr class="{e(a["resultado"]).lower()}"><td>{a["id"]}</td><td>{e(a["data_hora"])}</td>'
            f'<td>{a["nivel_area"]}</td><td><b>{e(a["resultado"])}</b></td><td>{e(a["motivo"])}</td>'
            f'<td>{e(a["nome"] or "Desconhecido")}</td><td>{dist}</td><td>{foto}</td></tr>')

    pagina = f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<title>Relatorio de Acessos - Cofre</title>
<style>
 body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
 h1 {{ margin-bottom: 4px; }} .sub {{ color: #666; margin-top: 0; }}
 .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; }}
 .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px 18px; min-width: 130px; }}
 .card b {{ display: block; font-size: 26px; }}
 table {{ border-collapse: collapse; width: 100%; margin-bottom: 28px; font-size: 14px; }}
 th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: middle; }}
 th {{ background: #f2f2f2; }}
 tr.concedido td:nth-child(4) {{ color: #1a7f37; }}
 tr.negado td:nth-child(4), tr.bloqueio td:nth-child(4) {{ color: #c62828; }}
 img {{ height: 48px; border-radius: 4px; }}
</style></head><body>
<h1>Relatorio de Acessos ao Cofre</h1>
<p class="sub">Sistema de Identificacao e Autenticacao Biometrica &middot; gerado em {datetime.now():%d/%m/%Y %H:%M}</p>
<div class="cards">
 <div class="card">Tentativas<b>{est['total']}</b></div>
 <div class="card">Concedidos<b>{concedidos}</b></div>
 <div class="card">Negados<b>{negados}</b></div>
 <div class="card">Bloqueios<b>{bloqueios}</b></div>
 <div class="card">Taxa de concessao<b>{taxa}</b></div>
 <div class="card">Usuarios ativos<b>{est['usuarios_ativos']}</b></div>
</div>
<h2>Acessos por nivel de seguranca</h2>
<table><tr><th>Area</th><th>Concedidos</th><th>Negados</th></tr>{linhas_nivel}</table>
<h2>Usuarios cadastrados</h2>
<table><tr><th>ID</th><th>Nome</th><th>Cargo</th><th>Nivel</th><th>Situacao</th><th>Cadastro</th></tr>{linhas_usuarios}</table>
<h2>Historico de tentativas (mais recentes primeiro)</h2>
<table><tr><th>#</th><th>Data/Hora</th><th>Nivel area</th><th>Resultado</th><th>Motivo</th><th>Usuario</th><th>Distancia</th><th>Foto</th></tr>{linhas_acessos}</table>
</body></html>"""
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(pagina)
    return caminho
