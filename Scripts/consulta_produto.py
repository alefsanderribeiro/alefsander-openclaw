#!/usr/bin/env python3
"""consulta_produto.py — Consulta produtos no banco SQLite

Uso:
    python3 consulta_produto.py --codigo 9RV3YA-XXXX
    python3 consulta_produto.py --ultimos 10
    python3 consulta_produto.py --busca "termo"
    python3 consulta_produto.py --stats
"""

import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from Scripts.db_produtos import consultar_por_codigo, consultar_ultimos, buscar_por_titulo, get_conn


def format_row(row):
    """Formata uma linha para exibição amigável"""
    saida = [
        f"Código:      {row.get('codigo', 'N/A')}",
        f"Título:      {row.get('titulo', 'N/A')[:80]}",
        f"Preço:       {row.get('preco', 'N/A')}",
        f"Fonte:       {row.get('fonte', 'N/A')}",
        f"Avaliação:   {row.get('avaliacao', 'N/A')}",
    ]
    if row.get('descricao'):
        saida.append(f"Descrição:   {row['descricao'][:100]}")
    if row.get('features'):
        try:
            features = json.loads(row['features']) if isinstance(row['features'], str) else row['features']
            if features:
                saida.append(f"Features:    {' | '.join(features[:5])}")
        except (json.JSONDecodeError, TypeError):
            pass
    saida.append(f"Imagem ID:   {row.get('imagem_id', 'N/A')}")
    img_path = row.get('imagem_path')
    if img_path:
        existe = "✅" if Path(img_path).exists() else "❌"
        saida.append(f"Imagem Path: {img_path} {existe}")
    saida.append(f"Atualizado:  {row.get('atualizado_em', 'N/A')}")
    saida.append(f"Link:        {row.get('link_original', 'N/A')}")
    saida.append(f"Caption:     {row.get('caption', 'N/A')[:120]}")
    return "\n".join(saida)


def cmd_codigo(codigo):
    row = consultar_por_codigo(codigo)
    if row:
        print(format_row(row))
        print("-" * 60)
        if row.get("caption"):
            print(f"\n{row['caption']}")
    else:
        print(f"❌ Produto não encontrado: {codigo}", file=sys.stderr)
        sys.exit(1)


def cmd_ultimos(limite):
    rows = consultar_ultimos(limite)
    if not rows:
        print("📭 Nenhum produto encontrado no banco.", file=sys.stderr)
        sys.exit(1)
    print(f"📦 Últimos {len(rows)} produtos extraídos:\n")
    for i, row in enumerate(rows, 1):
        print(f"{'='*60}")
        print(f"#{i}")
        print(format_row(row))
        print()


def cmd_busca(termo):
    rows = buscar_por_titulo(termo)
    if not rows:
        print(f"📭 Nenhum produto encontrado para: {termo}", file=sys.stderr)
        sys.exit(1)
    print(f"🔍 {len(rows)} resultado(s) para \"{termo}\":\n")
    for i, row in enumerate(rows, 1):
        print(f"{'='*60}")
        print(f"#{i}")
        print(format_row(row))
        print()


def cmd_stats():
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        com_preco = conn.execute("SELECT COUNT(*) FROM produtos WHERE preco IS NOT NULL AND preco != '' AND preco != 'N/D'").fetchone()[0]
        com_imagem = conn.execute("SELECT COUNT(*) FROM produtos WHERE imagem_id IS NOT NULL").fetchone()[0]
        com_imagem_path = conn.execute("SELECT COUNT(*) FROM produtos WHERE imagem_path IS NOT NULL AND imagem_path != ''").fetchone()[0]
        com_avaliacao = conn.execute("SELECT COUNT(*) FROM produtos WHERE avaliacao IS NOT NULL AND avaliacao != ''").fetchone()[0]
        ultima = conn.execute("SELECT MAX(atualizado_em) FROM produtos").fetchone()[0]
        fontes = conn.execute("SELECT fonte, COUNT(*) as qtd FROM produtos GROUP BY fonte ORDER BY qtd DESC").fetchall()

        print("📊 Estatísticas do banco de produtos\n")
        print(f"Total de produtos:     {total}")
        print(f"Com preço:             {com_preco}")
        print(f"Com imagem_id:         {com_imagem}")
        print(f"Com imagem_path:       {com_imagem_path}")

        # Conta imagens disponíveis em disco
        img_dir = Path("/home/node/.openclaw/workspace/img_produtos_mercado_livre")
        if img_dir.exists():
            imgs_disco = len(list(img_dir.glob("*")))
            print(f"Imagens em disco:      {imgs_disco}")

        print(f"Com avaliação:         {com_avaliacao}")
        print(f"Última atualização:    {ultima or 'N/A'}")
        print()
        print("Distribuição por fonte:")
        for fonte, qtd in fontes:
            print(f"  • {fonte}: {qtd}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Consulta produtos no banco SQLite (.produtos.db)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 consulta_produto.py --codigo 9RV3YA-XXXX
  python3 consulta_produto.py --ultimos 10
  python3 consulta_produto.py --busca "fone de ouvido"
  python3 consulta_produto.py --stats
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--codigo", help="Código do produto (ex: 9RV3YA-XXXX)")
    group.add_argument("--ultimos", type=int, nargs="?", const=10,
                       help="Últimos N produtos (padrão: 10)")
    group.add_argument("--busca", help="Busca por termo no título")
    group.add_argument("--stats", action="store_true", help="Estatísticas do banco")

    args = parser.parse_args()

    if args.codigo:
        cmd_codigo(args.codigo.strip())
    elif args.ultimos is not None:
        cmd_ultimos(args.ultimos)
    elif args.busca:
        cmd_busca(args.busca.strip())
    elif args.stats:
        cmd_stats()


if __name__ == "__main__":
    main()
