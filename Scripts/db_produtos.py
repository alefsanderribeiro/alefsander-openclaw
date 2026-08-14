#!/usr/bin/env python3
"""db_produtos.py — Gerenciamento do banco SQLite de produtos"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / ".produtos.db"


def get_conn():
    """Retorna conexão com o banco SQLite"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """Cria a tabela produtos se não existir"""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                codigo TEXT PRIMARY KEY,
                titulo TEXT,
                preco TEXT,
                imagem_url TEXT,
                imagem_id TEXT,
                imagem_path TEXT,
                descricao TEXT,
                features TEXT,
                link_original TEXT,
                fonte TEXT,
                avaliacao TEXT,
                caption TEXT,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migração: adiciona coluna imagem_path se não existir (para bancos existentes)
        try:
            conn.execute("ALTER TABLE produtos ADD COLUMN imagem_path TEXT")
        except sqlite3.OperationalError:
            pass  # coluna já existe
        conn.commit()
    finally:
        conn.close()


def upsert_produto(data):
    """Insere ou atualiza um produto no banco"""
    conn = get_conn()
    try:
        features_json = json.dumps(data.get("features", []), ensure_ascii=False)
        conn.execute("""
            INSERT INTO produtos (
                codigo, titulo, preco, imagem_url, imagem_id, imagem_path,
                descricao, features, link_original, fonte,
                avaliacao, caption, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(codigo) DO UPDATE SET
                titulo = excluded.titulo,
                preco = excluded.preco,
                imagem_url = excluded.imagem_url,
                imagem_id = excluded.imagem_id,
                imagem_path = excluded.imagem_path,
                descricao = excluded.descricao,
                features = excluded.features,
                link_original = excluded.link_original,
                fonte = excluded.fonte,
                avaliacao = excluded.avaliacao,
                caption = excluded.caption,
                atualizado_em = CURRENT_TIMESTAMP
        """, (
            data.get("codigo", ""),
            data.get("titulo", ""),
            data.get("preco", ""),
            data.get("imagem", ""),
            data.get("imagem_id"),
            data.get("imagem_path"),
            data.get("descricao", ""),
            features_json,
            data.get("link_original", ""),
            data.get("fonte", "mercadolivre"),
            data.get("avaliacao", ""),
            data.get("caption", ""),
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[db] Erro ao salvar produto: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def consultar_por_codigo(codigo):
    """Retorna dados de um produto pelo código"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM produtos WHERE codigo = ?", (codigo,)
        ).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def consultar_ultimos(limite=10):
    """Retorna os últimos N produtos extraídos"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM produtos ORDER BY atualizado_em DESC LIMIT ?",
            (limite,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def buscar_por_titulo(termo):
    """Busca produtos por título (LIKE)"""
    conn = get_conn()
    try:
        pattern = f"%{termo}%"
        rows = conn.execute(
            "SELECT * FROM produtos WHERE titulo LIKE ? ORDER BY atualizado_em DESC",
            (pattern,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def init_if_needed():
    """Inicializa o banco se chamado diretamente"""
    init_db()
    print(f"✅ Banco inicializado: {DB_PATH}")


if __name__ == "__main__":
    init_if_needed()
