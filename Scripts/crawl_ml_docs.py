#!/usr/bin/env python3
"""
crawl_ml_docs.py — Baixa toda a documentação do Mercado Livre (developers.mercadolivre.com.br/pt_br)
e o portal de notícias, converte para Markdown e salva em:
  ~/Documentos/Mega/Drive/Projetos/Documentacoes/Mercado-Livre-API/
"""
import json
import os
import re
import subprocess
import sys
import time
import html as html_mod
from pathlib import Path

BASE = "https://developers.mercadolivre.com.br"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
DEST = Path(os.path.expanduser("~/Documentos/Mega/Drive/Projetos/Documentacoes/Mercado-Livre-API"))
PAGES_DIR = DEST / "paginas"
NEWS_DIR = DEST / "news"
MANIFEST = DEST / "manifest.json"

HEADERS = ["authorization", "cookie", "set-cookie", "x-request-id"]


def fetch(url, timeout=25):
    r = subprocess.run(
        ["curl", "-s", "-L", "-A", UA, "--connect-timeout", "10", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    return r.stdout if r.returncode == 0 else None


def extract_content(html):
    """Pega o <div id="content"> balanceado."""
    m = re.search(r'<div class="content" id="content">', html)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(html) and depth > 0:
        o = html.find("<div", i)
        c = html.find("</div>", i)
        if o == -1 or (c != -1 and c < o):
            depth -= 1
            i = c + 6
        else:
            depth += 1
            i = o + 4
    content = html[start:i] if depth == 0 else html[start:]

    # corta o menu lateral: conteúdo real começa no primeiro heading (h1/h2)
    hm = re.search(r'<h[12][^>]*>', content)
    if hm:
        content = content[hm.start():]
    return content


def html_to_markdown(html, page_url):
    """Converte HTML do conteúdo para Markdown (sem recursão)."""
    html = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)

    def abs_url(u):
        if u.startswith("http") or u.startswith("//") or u.startswith("mailto"):
            return u
        return BASE + (u if u.startswith("/") else "/" + u)

    # blocos que viram markdown
    def h(m, n):
        t = re.sub(r'<[^>]+>', '', m.group(0)).strip()
        return f"\n{'#'*n} {t}\n" if t else ""

    html = re.sub(r'<h1[^>]*>.*?</h1>', lambda m: h(m, 1), html, flags=re.S)
    html = re.sub(r'<h2[^>]*>.*?</h2>', lambda m: h(m, 2), html, flags=re.S)
    html = re.sub(r'<h3[^>]*>.*?</h3>', lambda m: h(m, 3), html, flags=re.S)
    html = re.sub(r'<h4[^>]*>.*?</h4>', lambda m: h(m, 4), html, flags=re.S)
    html = re.sub(r'<h5[^>]*>.*?</h5>', lambda m: h(m, 5), html, flags=re.S)
    html = re.sub(r'<h6[^>]*>.*?</h6>', lambda m: h(m, 6), html, flags=re.S)

    # tabelas
    def table(mt):
        rows = []
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', mt.group(0), flags=re.S):
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
        return "\n" + "\n".join(rows) + "\n" if rows else ""

    html = re.sub(r'<table[^>]*>.*?</table>', table, html, flags=re.S)

    # listas
    def ul(mt):
        items = re.findall(r'<li[^>]*>(.*?)</li>', mt.group(0), flags=re.S)
        lines = []
        for it in items:
            t = re.sub(r'<[^>]+>', '', it).strip()
            t = html_mod.unescape(t)
            if t:
                lines.append(f"- {t}")
        return "\n" + "\n".join(lines) + "\n"

    html = re.sub(r'<ul[^>]*>.*?</ul>', ul, html, flags=re.S)
    html = re.sub(r'<ol[^>]*>.*?</ol>', ul, html, flags=re.S)

    # blocos de código
    def pre(mt):
        code = re.sub(r'<[^>]+>', '', mt.group(0))
        code = html_mod.unescape(code).strip()
        return f"\n```\n{code}\n```\n"

    html = re.sub(r'<pre[^>]*>.*?</pre>', pre, html, flags=re.S)

    # quebras de bloco
    html = re.sub(r'</(p|div|section|article|li|h[1-6]|tr)>', '\n', html, flags=re.I)
    html = re.sub(r'<(p|div|section|article|li|br)[^>]*>', '\n', html, flags=re.I)

    # restante: remove tags, preserva links
    def link(m):
        txt = re.sub(r'<[^>]+>', '', m.group(0))
        url = m.group(1)
        return f"[{txt}]({abs_url(url)})" if txt else url

    html = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?</a>', link, html, flags=re.S)
    html = re.sub(r'<code[^>]*>(.*?)</code>', lambda m: f"`{re.sub(chr(60)+'[^>]+'+chr(62), '', m.group(1))}`", html, flags=re.S)
    html = re.sub(r'<[^>]+>', '', html)

    md = html_mod.unescape(html)
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = re.sub(r'[ \t]+\n', '\n', md)
    md = re.sub(r'\n[ \t]+', '\n', md)
    return md.strip()


def slugify(name):
    s = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
    return s[:80] or "pagina"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(exist_ok=True)
    NEWS_DIR.mkdir(exist_ok=True)

    # 1. Pega a lista de links do hub (guia tem o menu completo)
    idx = fetch(f"{BASE}/pt_br/guia-para-produtos")
    if not idx:
        print("❌ Não consegui baixar o índice")
        sys.exit(1)
    links = set()
    for m in re.finditer(r'href="([^"]+)"', idx):
        href = m.group(1)
        if not href or href.startswith(('#', 'mailto:', 'javascript:', '//', 'http')):
            continue
        if href.endswith(('.png', '.jpg', '.svg', '.pdf', '.css', '.js', '.webp')):
            continue
        if any(x in href for x in ('login', 'registre', 'buscar?', '/news', 'logout')):
            continue
        if href.startswith('/pt_br/'):
            links.add(href)
        else:
            links.add('/pt_br/' + href.lstrip('/'))
    paginas = sorted(links)
    print(f"📚 {len(paginas)} páginas para baixar")

    manifest = {}
    ok = fail = 0
    for i, path in enumerate(paginas, 1):
        url = BASE + path
        slug = slugify(path.replace('/pt_br/', ''))
        outfile = PAGES_DIR / f"{slug}.md"
        if outfile.exists():
            ok += 1
            manifest[url] = str(outfile)
            continue
        html = fetch(url)
        if not html:
            fail += 1
            print(f"  ❌ {i}/{len(paginas)} {path}")
            time.sleep(0.5)
            continue
        title_m = re.search(r'<title>([^<]+)</title>', html)
        title = html_mod.unescape(title_m.group(1).strip()) if title_m else slug
        content = extract_content(html)
        md = html_to_markdown(content, url) if content else "(conteúdo não extraído)"
        text = f"# {title}\n\n> Fonte: {url}\n\n{md}\n"
        outfile.write_text(text, encoding="utf-8")
        manifest[url] = str(outfile)
        ok += 1
        if i % 25 == 0:
            print(f"  … {i}/{len(paginas)} ok")
        time.sleep(0.4)

    print(f"✅ Docs: {ok} ok, {fail} falhas")

    # 2. Página de notícias
    news = fetch(f"{BASE}/devcenter/news")
    if news:
        news_md = html_to_markdown(news, f"{BASE}/devcenter/news")
        (NEWS_DIR / "news.md").write_text(f"# Notícias / Mudanças da API\n\n> Fonte: {BASE}/devcenter/news\n\n{news_md}\n", encoding="utf-8")
        # links de posts individuais
        posts = sorted(set(f"{BASE}{u}" for u in re.findall(r'href="(/[^"]*news[^"]*)"', news) if u.startswith('/')))
        for p in posts:
            if '/devcenter/news' in p and p != f"{BASE}/devcenter/news":
                continue
            if p.startswith(f"{BASE}/devcenter/news/"):
                ph = fetch(p)
                if ph:
                    slug = slugify(p.split('/')[-1])
                    pmd = html_to_markdown(ph, p)
                    (NEWS_DIR / f"{slug}.md").write_text(f"# Notícia\n\n> Fonte: {p}\n\n{pmd}\n", encoding="utf-8")
                    print(f"  📰 {slug}")
                    time.sleep(0.4)
        print("✅ News baixadas")
    else:
        print("⚠️ News falhou")

    # 3. Índice + manifest
    lines = ["# Documentação API Mercado Livre — cópia local\n",
             f"> Crawl em {time.strftime('%Y-%m-%d %H:%M')} · {ok} páginas · fonte: developers.mercadolivre.com.br\n",
             "\n## Índice\n"]
    for path in paginas:
        slug = slugify(path.replace('/pt_br/', ''))
        lines.append(f"- [{path}](paginas/{slug}.md)")
    (DEST / "README.md").write_text("\n".join(lines), encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Índice + manifest salvos em {DEST}")


if __name__ == "__main__":
    main()
