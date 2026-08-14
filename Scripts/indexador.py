#!/usr/bin/env python3
"""
Indexador de Arquivos — MEGA Drive
Varre ~/Documentos/Mega/Drive/ e indexa metadados + conteúdo em SQLite.

Modos:
  python3 indexador.py          → estrutura rápida (metadados, ~1s)
  python3 indexador.py --completo → completa (+ extração de conteúdo)
  python3 indexador.py --busca "termo" → busca no índice
  python3 indexador.py --stats   → estatísticas do índice
"""

import os
import sys
import json
import sqlite3
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

# ─── Configuração ───────────────────────────────────────────────────────────
RAIZ = os.path.expanduser("~/Documentos/Mega/Drive")

# Diretórios adicionais para monitorar (além do MEGA Drive)
DIRS_ADICIONAIS = [
    os.path.expanduser("~/.openclaw/workspace/Scripts"),
    os.path.expanduser("~/.openclaw/workspace/img_produtos_mercado_livre"),
]
DB_PATH = os.path.expanduser("~/.openclaw/workspace/.catalogo.db")

# Extensões de texto para extrair conteúdo
EXT_TEXTO = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".less",
    ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".txt", ".log", ".csv", ".env", ".sh", ".bash", ".zsh",
    ".bat", ".ps1", ".sql", ".prisma", ".graphql", ".proto", ".dockerfile",
    ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".pl", ".lua", ".r", ".vue", ".svelte", ".astro",
    ".terraform", ".tf", ".tfvars",
}

# Extensões de documentos para extrair texto via comandos externos
EXT_DOC = {
    ".pdf": ["pdftotext", "{path}", "-"],
    ".docx": ["python3", "-c", """
import sys, zipfile, xml.etree.ElementTree as ET
try:
    z = zipfile.ZipFile(sys.argv[1])
    xml_content = z.read('word/document.xml')
    root = ET.fromstring(xml_content)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    texts = [t.text for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
    print(' '.join(texts))
except: pass
""", "{path}"],
}

# Extensões de planilha (metadados)
EXT_PLANILHA = {".xlsx", ".xls", ".ods"}

# Extensões a ignorar completamente
EXT_IGNORAR = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
    ".mp3", ".wav", ".ogg", ".flac", ".m4a",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pyc", ".pyo", ".pyd",
    ".o", ".obj", ".lib", ".a",
    ".class", ".jar",
    ".pak", ".unity", ".asset",
    ".db", ".sqlite", ".sqlite3",
}

TAMANHO_MAX_TEXTO = 500 * 1024  # 500KB max para extrair texto
TAMANHO_MAX_PDF = 50 * 1024 * 1024  # 50MB max para PDF


# ─── Banco de Dados ─────────────────────────────────────────────────────────

def conectar():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    return conn


def criar_tabelas(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS arquivos (
            path TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            extensao TEXT,
            tamanho INTEGER,
            modificado TEXT,
            tipo TEXT,
            projeto TEXT,
            hash_conteudo TEXT
        );
        CREATE TABLE IF NOT EXISTS conteudo (
            path TEXT PRIMARY KEY,
            texto TEXT,
            extraido_em TEXT,
            FOREIGN KEY (path) REFERENCES arquivos(path)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS conteudo_fts USING fts5(
            texto, content='conteudo', content_rowid='rowid'
        );
        CREATE TABLE IF NOT EXISTS stats (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_arquivos_ext ON arquivos(extensao);
        CREATE INDEX IF NOT EXISTS idx_arquivos_projeto ON arquivos(projeto);
        CREATE INDEX IF NOT EXISTS idx_arquivos_tipo ON arquivos(tipo);
    """)
    conn.commit()


# ─── Scanner ────────────────────────────────────────────────────────────────

def extrair_projeto(path_rel):
    """Extrai o nome do projeto do path relativo."""
    partes = path_rel.replace("\\", "/").split("/")
    if len(partes) >= 3 and partes[0] == "Projetos":
        if len(partes) >= 3:
            return f"{partes[1]}/{partes[2]}"
        return partes[1]
    return partes[0] if partes else "raiz"


def classificar_tipo(ext, nome):
    """Classifica o tipo do arquivo."""
    if ext in EXT_TEXTO:
        return "codigo"
    if ext in EXT_DOC:
        return "documento"
    if ext in EXT_PLANILHA:
        return "planilha"
    if ext in {".pdf"}:
        return "documento"
    if ext in {".doc", ".docx"}:
        return "documento"
    return "outro"


def scan_estrutura(conn, completo=False):
    """Varre a estrutura de arquivos e salva metadados."""
    print(f"📂 Escaneando: {RAIZ}")
    print()

    if not os.path.isdir(RAIZ):
        print(f"❌ Diretório não encontrado: {RAIZ}")
        return 0

    total = 0
    ignorados = 0
    erros = 0
    tipos = {}
    ext_stats = {}

    # Limpa índice anterior
    conn.execute("DELETE FROM arquivos")
    if completo:
        conn.execute("DELETE FROM conteudo")
    conn.commit()

    # Varre diretório principal (MEGA Drive)
    for raiz, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d != "node_modules"
                   and d != "__pycache__"
                   and d != ".git"
                   and d != "venv"
                   and d != ".venv"
                   and d != "env"
                   and d != ".env"]

        for nome in arquivos:
            path_completo = os.path.join(raiz, nome)
            path_rel = os.path.relpath(path_completo, RAIZ)

            if nome.startswith("."):
                ignorados += 1
                continue

            try:
                stat = os.stat(path_completo)
            except OSError:
                erros += 1
                continue

            ext = os.path.splitext(nome)[1].lower()
            if ext in EXT_IGNORAR:
                ignorados += 1
                continue

            tamanho = stat.st_size
            modificado = datetime.fromtimestamp(stat.st_mtime).isoformat()
            tipo = classificar_tipo(ext, nome)
            projeto = extrair_projeto(path_rel)

            hash_cont = None
            if completo and tipo == "codigo" and tamanho < TAMANHO_MAX_TEXTO:
                try:
                    with open(path_completo, "rb") as f:
                        hash_cont = hashlib.md5(f.read(1024 * 1024)).hexdigest()
                except OSError:
                    pass

            conn.execute(
                """INSERT OR REPLACE INTO arquivos
                   (path, nome, extensao, tamanho, modificado, tipo, projeto, hash_conteudo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (path_rel, nome, ext, tamanho, modificado, tipo, projeto, hash_cont)
            )

            total += 1
            tipos[tipo] = tipos.get(tipo, 0) + 1
            ext_stats[ext] = ext_stats.get(ext, 0) + 1

            if total % 1000 == 0:
                print(f"  📄 {total} arquivos processados...")
                conn.commit()

    # Varre diretórios adicionais (Scripts, imagens, etc.)
    for extra_dir in DIRS_ADICIONAIS:
        if not os.path.isdir(extra_dir):
            continue
        for raiz, dirs, arquivos in os.walk(extra_dir):
            for nome in arquivos:
                path_completo = os.path.join(raiz, nome)
                path_rel = os.path.relpath(path_completo, os.path.expanduser("~"))

                if nome.startswith("."):
                    ignorados += 1
                    continue

                try:
                    stat = os.stat(path_completo)
                except OSError:
                    erros += 1
                    continue

                ext = os.path.splitext(nome)[1].lower()
                if ext in EXT_IGNORAR:
                    ignorados += 1
                    continue

                tamanho = stat.st_size
                modificado = datetime.fromtimestamp(stat.st_mtime).isoformat()
                tipo = classificar_tipo(ext, nome)
                projeto = "openclaw-workspace"

                hash_cont = None
                if completo and tipo == "codigo" and tamanho < TAMANHO_MAX_TEXTO:
                    try:
                        with open(path_completo, "rb") as f:
                            hash_cont = hashlib.md5(f.read(1024 * 1024)).hexdigest()
                    except OSError:
                        pass

                conn.execute(
                    """INSERT OR REPLACE INTO arquivos
                       (path, nome, extensao, tamanho, modificado, tipo, projeto, hash_conteudo)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (path_rel, nome, ext, tamanho, modificado, tipo, projeto, hash_cont)
                )

                total += 1
                tipos[tipo] = tipos.get(tipo, 0) + 1
                ext_stats[ext] = ext_stats.get(ext, 0) + 1

                if total % 1000 == 0:
                    print(f"  📄 {total} arquivos processados...")
                    conn.commit()

    conn.commit()

    print()
    print(f"✅ Scan concluído!")
    print(f"   Total: {total} arquivos")
    print(f"   Ignorados: {ignorados}")
    print(f"   Erros: {erros}")
    print()
    print("   Por tipo:")
    for t, qtd in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"     • {t}: {qtd}")
    print()
    print("   Top extensões:")
    for ext, qtd in sorted(ext_stats.items(), key=lambda x: -x[1])[:10]:
        print(f"     • {ext or '(sem)'}: {qtd}")

    return total


# ─── Extração de Conteúdo ──────────────────────────────────────────────────

def extrair_conteudo(path_completo, ext):
    """Extrai texto de um arquivo."""
    try:
        if ext in EXT_TEXTO:
            with open(path_completo, "r", encoding="utf-8", errors="replace") as f:
                return f.read(TAMANHO_MAX_TEXTO)

        elif ext in EXT_DOC:
            cmd = [part.replace("{path}", path_completo) for part in EXT_DOC[ext]]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        timeout=30)
                return result.stdout[:TAMANHO_MAX_TEXTO] if result.stdout else None
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return None

    except Exception:
        return None
    return None


def scan_completo(conn):
    """Extrai conteúdo dos arquivos (completo)."""
    print("🔍 Extraindo conteúdo dos arquivos...")
    print()

    if not os.path.isdir(RAIZ):
        print(f"❌ Diretório não encontrado: {RAIZ}")
        return

    # Primeiro faz o scan de estrutura
    total = scan_estrutura(conn, completo=True)

    # Depois extrai conteúdo
    extraidos = 0
    erros = 0
    tipos_extrair = {"codigo", "documento"}
    ext_extrair = set(EXT_TEXTO) | set(EXT_DOC.keys())

    rows = conn.execute(
        "SELECT path, extensao FROM arquivos WHERE tipo IN (?, ?) ORDER BY tamanho ASC",
        ("codigo", "documento")
    ).fetchall()

    print(f"   {len(rows)} arquivos elegíveis para extração de conteúdo...")
    print()

    for i, (path_rel, ext) in enumerate(rows):
        path_completo = os.path.join(RAIZ, path_rel)

        if not os.path.isfile(path_completo):
            continue

        tamanho = os.path.getsize(path_completo) if os.path.exists(path_completo) else 0
        if ext == ".pdf" and tamanho > TAMANHO_MAX_PDF:
            continue

        texto = extrair_conteudo(path_completo, ext)
        if texto:
            conn.execute(
                "INSERT OR REPLACE INTO conteudo (path, texto, extraido_em) VALUES (?, ?, ?)",
                (path_rel, texto, datetime.now().isoformat())
            )
            extraidos += 1
        else:
            erros += 1

        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  📝 {i+1}/{len(rows)} processados ({extraidos} com texto)...")

    conn.commit()

    # Atualiza FTS
    print()
    print("   Atualizando índice de busca full-text...")
    try:
        conn.execute("INSERT INTO conteudo_fts(conteudo_fts) VALUES('rebuild')")
    except Exception:
        pass
    conn.commit()

    print()
    print(f"✅ Extração concluída!")
    print(f"   Arquivos com texto extraído: {extraidos}")
    print(f"   Erros/pulados: {erros}")
    print(f"   Total no índice: {len(rows)}")


# ─── Busca ──────────────────────────────────────────────────────────────────

def buscar(conn, termo):
    """Busca no índice full-text."""
    print(f"🔎 Buscando: '{termo}'")
    print()

    try:
        # Tenta FTS5 primeiro (mais rápido e preciso)
        # FTS5 faz escape automático, mas palavras isoladas precisam de aspas
        termo_fts = termo
        if ' ' not in termo_fts and '"' not in termo_fts:
            termo_fts = f'"{termo_fts}"'
        rows = conn.execute(
            """SELECT a.path, a.nome, a.tipo, a.projeto, length(c.texto) as tam
               FROM conteudo_fts f
               JOIN conteudo c ON f.rowid = c.rowid
               JOIN arquivos a ON c.path = a.path
               WHERE conteudo_fts MATCH ?
               ORDER BY rank
               LIMIT 30""",
            (termo_fts,)
        ).fetchall()
    except Exception:
        # Fallback: LIKE search
        rows = conn.execute(
            """SELECT c.path, a.nome, a.tipo, a.projeto, length(c.texto)
               FROM conteudo c
               JOIN arquivos a ON c.path = a.path
               WHERE c.texto LIKE ?
               LIMIT 30""",
            (f"%{termo}%",)
        ).fetchall()

    if not rows:
        print("   Nenhum resultado encontrado.")
        return

    print(f"   {len(rows)} resultado(s):")
    print()
    for path, nome, tipo, projeto, tam in rows:
        print(f"   📄 {nome}")
        print(f"      Path: {path}")
        print(f"      Tipo: {tipo} | Projeto: {projeto} | {tam} chars")
        print()


# ─── Estatísticas ───────────────────────────────────────────────────────────

def stats(conn):
    """Mostra estatísticas do índice."""
    total = conn.execute("SELECT COUNT(*) FROM arquivos").fetchone()[0]
    total_cont = conn.execute("SELECT COUNT(*) FROM conteudo").fetchone()[0]
    total_tam = conn.execute("SELECT SUM(tamanho) FROM arquivos").fetchone()[0] or 0
    db_tam = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

    projetos = conn.execute(
        "SELECT projeto, COUNT(*) as qtd FROM arquivos GROUP BY projeto ORDER BY qtd DESC LIMIT 20"
    ).fetchall()

    tipos = conn.execute(
        "SELECT tipo, COUNT(*) FROM arquivos GROUP BY tipo ORDER BY COUNT(*) DESC"
    ).fetchall()

    exts = conn.execute(
        "SELECT extensao, COUNT(*) FROM arquivos WHERE extensao != '' GROUP BY extensao ORDER BY COUNT(*) DESC LIMIT 15"
    ).fetchall()

    ultima = conn.execute(
        "SELECT valor FROM stats WHERE chave = 'ultima_atualizacao'"
    ).fetchone()

    print("📊 ESTATÍSTICAS DO ÍNDICE")
    print("=" * 50)
    print(f"   Arquivos indexados: {total:,}")
    print(f"   Conteúdo extraído:  {total_cont:,} arquivos")
    print(f"   Tamanho total:      {total_tam / 1024 / 1024:.1f} MB")
    print(f"   Banco de dados:     {db_tam / 1024 / 1024:.1f} MB")
    if ultima:
        print(f"   Última atualização: {ultima[0]}")
    print()

    print("📁 POR TIPO:")
    for t, qtd in tipos:
        print(f"   • {t}: {qtd}")
    print()

    print("🗂️ PRINCIPAIS PROJETOS:")
    for proj, qtd in projetos[:10]:
        print(f"   • {proj}: {qtd} arquivos")
    print()

    print("🔤 EXTENSÕES MAIS COMUNS:")
    for ext, qtd in exts:
        print(f"   • {ext or '(sem)'}: {qtd}")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    if not os.path.isdir(RAIZ):
        print(f"❌ Diretório MEGA não encontrado: {RAIZ}")
        print("   Verifique se o MEGA está sincronizado em ~/Documentos/Mega/Drive/")
        sys.exit(1)

    conn = conectar()
    criar_tabelas(conn)

    if "--busca" in sys.argv:
        idx = sys.argv.index("--busca")
        termo = " ".join(sys.argv[idx + 1:]) if len(sys.argv) > idx + 1 else ""
        if termo:
            buscar(conn, termo)
        else:
            print("❗ Uso: python3 indexador.py --busca \"termo de busca\"")
        conn.close()
        return

    if "--stats" in sys.argv:
        stats(conn)
        conn.close()
        return

    completo = "--completo" in sys.argv

    if completo:
        scan_completo(conn)
    else:
        scan_estrutura(conn)

    # Salva timestamp
    conn.execute(
        "INSERT OR REPLACE INTO stats (chave, valor) VALUES (?, ?)",
        ("ultima_atualizacao", datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    print()
    print(f"{'='*50}")
    print(f"✅ Indexação {'COMPLETA' if completo else 'RÁPIDA'} finalizada!")
    print(f"   Banco: {DB_PATH}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
