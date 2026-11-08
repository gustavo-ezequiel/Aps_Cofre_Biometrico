
import os
import sqlite3
from datetime import datetime

import config
from dados_cofre import AREAS, TABELAS_ANTIGAS

SCHEMA_SQLITE = [
    """CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cargo TEXT,
        nivel INTEGER NOT NULL CHECK (nivel BETWEEN 1 AND 3),
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS acessos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        nivel_area INTEGER NOT NULL,
        resultado TEXT NOT NULL,
        motivo TEXT,
        distancia REAL,
        foto TEXT,
        data_hora TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id))""",
]

SCHEMA_MYSQL = [
    """CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        cargo VARCHAR(100),
        nivel TINYINT NOT NULL,
        ativo TINYINT NOT NULL DEFAULT 1,
        criado_em DATETIME NOT NULL,
        CHECK (nivel BETWEEN 1 AND 3))""",
    """CREATE TABLE IF NOT EXISTS acessos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NULL,
        nivel_area TINYINT NOT NULL,
        resultado VARCHAR(20) NOT NULL,
        motivo VARCHAR(255),
        distancia DOUBLE,
        foto VARCHAR(255),
        data_hora DATETIME NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id))""",
]


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BancoDeDados:
    def __init__(self):
        if config.DB_ENGINE == "mysql":
            try:
                import mysql.connector
            except ImportError:
                raise RuntimeError("Instale o driver: pip install mysql-connector-python")
            dados = dict(config.MYSQL)
            nome_banco = dados.pop("database")
            con = mysql.connector.connect(**dados)
            con.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {nome_banco}")
            con.close()
            self.con = mysql.connector.connect(database=nome_banco, **dados)
            self.marcador = "%s"
            schema = SCHEMA_MYSQL
        else:
            os.makedirs(config.DADOS_DIR, exist_ok=True)
            self.con = sqlite3.connect(config.SQLITE_PATH)
            self.con.execute("PRAGMA foreign_keys = ON")
            self.marcador = "?"
            schema = SCHEMA_SQLITE
        for comando in schema:
            self._executar(comando)
        self._criar_tabelas_cofre()

    # ------------------------------------------------- conteúdo do cofre
    def _criar_tabelas_cofre(self):
        """Recria as 3 tabelas do cofre (uma por nível) a partir de dados_cofre.py."""
        for antiga in TABELAS_ANTIGAS:
            self._executar(f"DROP TABLE IF EXISTS {antiga}")
        pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if self.marcador == "?" else "INT AUTO_INCREMENT PRIMARY KEY"
        for area in AREAS.values():
            self._executar(f"DROP TABLE IF EXISTS {area['tabela']}")
            cols = ", ".join(f"{nome} {tipo}" for nome, tipo, _ in area["colunas"])
            self._executar(f"CREATE TABLE {area['tabela']} (id {pk}, {cols})")
            nomes = ", ".join(c[0] for c in area["colunas"])
            marcas = ", ".join("?" for _ in area["colunas"])
            for linha in area["linhas"]:
                self._executar(f"INSERT INTO {area['tabela']} ({nomes}) VALUES ({marcas})", linha)

    def consultar_area(self, nivel):
        """Retorna (titulo, cabecalhos, linhas, observacao) da tabela do nível pedido."""
        area = AREAS[nivel]
        nomes = ", ".join(c[0] for c in area["colunas"])
        linhas = self._executar(f"SELECT {nomes} FROM {area['tabela']} ORDER BY id", buscar="todos")
        return (area["titulo"], [c[2] for c in area["colunas"]], [tuple(l) for l in linhas],
                area.get("observacao", ""))

    # -------------------------------------------------------- utilitários
    def _executar(self, sql, params=(), buscar=None):
        cur = self.con.cursor()
        cur.execute(sql.replace("?", self.marcador), params)
        resultado = None
        if buscar == "um":
            resultado = cur.fetchone()
        elif buscar == "todos":
            resultado = cur.fetchall()
        else:
            self.con.commit()
            resultado = cur.lastrowid
        cur.close()
        return resultado

    def fechar(self):
        self.con.close()

    # ----------------------------------------------------------- usuários
    def inserir_usuario(self, nome, cargo, nivel):
        if nivel not in config.NIVEIS:
            raise ValueError("Nivel deve ser 1, 2 ou 3.")
        return self._executar(
            "INSERT INTO usuarios (nome, cargo, nivel, ativo, criado_em) VALUES (?, ?, ?, 1, ?)",
            (nome, cargo, nivel, _agora()))

    def excluir_usuario(self, uid):
        """Exclusão definitiva (usada quando o cadastro é cancelado)."""
        self._executar("DELETE FROM usuarios WHERE id = ?", (uid,))

    def desativar_usuario(self, uid):
        self._executar("UPDATE usuarios SET ativo = 0 WHERE id = ?", (uid,))

    def alterar_nivel(self, uid, nivel):
        if nivel not in config.NIVEIS:
            raise ValueError("Nivel deve ser 1, 2 ou 3.")
        self._executar("UPDATE usuarios SET nivel = ? WHERE id = ?", (nivel, uid))

    def obter_usuario(self, uid):
        linha = self._executar(
            "SELECT id, nome, cargo, nivel, ativo, criado_em FROM usuarios WHERE id = ?",
            (uid,), buscar="um")
        if not linha:
            return None
        return dict(zip(("id", "nome", "cargo", "nivel", "ativo", "criado_em"), linha))

    def listar_usuarios(self, apenas_ativos=True):
        sql = "SELECT id, nome, cargo, nivel, ativo, criado_em FROM usuarios"
        if apenas_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nivel DESC, nome"
        chaves = ("id", "nome", "cargo", "nivel", "ativo", "criado_em")
        return [dict(zip(chaves, l)) for l in self._executar(sql, buscar="todos")]

    def ids_ativos(self):
        return {u["id"] for u in self.listar_usuarios(apenas_ativos=True)}

    # ------------------------------------------------------------ acessos
    def registrar_acesso(self, usuario_id, nivel_area, resultado, motivo,
                         distancia=None, foto=None):
        if distancia is not None and distancia == float("inf"):
            distancia = None
        return self._executar(
            "INSERT INTO acessos (usuario_id, nivel_area, resultado, motivo, distancia, foto, data_hora) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (usuario_id, nivel_area, resultado, motivo, distancia, foto, _agora()))

    def listar_acessos(self, limite=500):
        sql = ("SELECT a.id, a.data_hora, a.nivel_area, a.resultado, a.motivo, a.distancia, "
               "a.foto, u.nome, u.nivel FROM acessos a LEFT JOIN usuarios u ON u.id = a.usuario_id "
               "ORDER BY a.id DESC LIMIT ?")
        chaves = ("id", "data_hora", "nivel_area", "resultado", "motivo", "distancia",
                  "foto", "nome", "nivel_usuario")
        return [dict(zip(chaves, l)) for l in self._executar(sql, (limite,), buscar="todos")]

    def estatisticas(self):
        total = self._executar("SELECT COUNT(*) FROM acessos", buscar="um")[0]
        por_resultado = self._executar(
            "SELECT resultado, COUNT(*) FROM acessos GROUP BY resultado", buscar="todos")
        por_nivel = self._executar(
            "SELECT nivel_area, resultado, COUNT(*) FROM acessos GROUP BY nivel_area, resultado",
            buscar="todos")
        return {
            "total": total,
            "por_resultado": {r: int(c) for r, c in por_resultado},
            "por_nivel": [(int(n), r, int(c)) for n, r, c in por_nivel],
            "usuarios_ativos": len(self.ids_ativos()),
        }
