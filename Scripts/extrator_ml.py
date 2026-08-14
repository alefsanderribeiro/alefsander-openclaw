#!/usr/bin/env python3
"""extrator_ml.py — Extrai dados de produtos do Mercado Livre (Camoufox + API oficial)

Estratégia principal (validada 06/08/2026 — ML bloqueia Playwright headless com
account-verification, mas Camoufox passa e gera link de afiliado etiquetado):

    Procedimento A (código + link):
        python3 extrator_ml.py CODIGO "https://meli.la/XXXX"
        → sessão Camoufox → abre meli.la (ativa etiqueta) → busca código → clica produto
    Procedimento B (só link):
        python3 extrator_ml.py "https://meli.la/XXXX"
        → sessão Camoufox → abre meli.la → perfil social → clica 1º produto

Depois (comum): API oficial do ML (/products, /items, /reviews) + download da
foto do CDN + gravação no SQLite (.produtos.db) + JSON temporário.

Saída padrão (fluxo do grupo): JSON com titulo, preco, imagem_path, caption,
link_original. A caption inclui preço PIX + preço cheio + % de desconto.

Uso:
    python3 extrator_ml.py CODIGO [LINK_AFILIADO]
    python3 extrator_ml.py LINK_AFILIADO

Exemplos:
    python3 extrator_ml.py "9RV3YA-4LKT" "https://meli.la/XXXX"
    python3 extrator_ml.py "https://meli.la/XXXX"
"""

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent  # workspace
sys.path.insert(0, str(BASE_DIR))                   # workspace na raiz do path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # Scripts p/ importar ml_token
from Scripts.db_produtos import init_db, upsert_produto, consultar_por_codigo

init_db()

# --- Config de ambiente ---
PYTHONPATH_EXTRA = "/home/node/.openclaw/py-libs"
CAMOUFOX_HOME = "/home/node/.openclaw/fakehome"
CAMOUFOX_CACHE = "/home/node/.openclaw/cache"
CAMOUFOX_TMP = "/home/node/.openclaw/tmp"
IMAGENS_DIR = Path("/home/node/.openclaw/workspace/img_produtos_mercado_livre")
TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

ML_API = "https://api.mercadolibre.com"


# --- Helpers ---

def log(msg):
    print(f"[extrator] {msg}", file=sys.stderr, flush=True)


def detect_kind(arg, second_arg=None):
    """Detecta se o 1º argumento é link (http) ou código. Retorna ('link'|'code')."""
    return "link" if arg.lower().startswith("http") else "code"


# --- Camoufox (subprocess com HOME=fakehome) ---

_CAMOUFOX_MARKER = "__CAMOUFOX_RESULT__"


def run_camoufox_phase(code, link_afiliado):
    """Executa a navegação Camoufox num subprocess isolado (HOME=fakehome),
    para não interferir no ~/.openclaw/secrets da etapa de API (processo principal).

    Retorna dict com url_final, product_id, item_id, titulo_pagina, preco_pagina
    ou None em caso de falha.
    """
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        "--camoufox-phase", code or "", link_afiliado or "",
    ]
    env = os.environ.copy()
    env["HOME"] = CAMOUFOX_HOME
    env["PYTHONPATH"] = PYTHONPATH_EXTRA
    env["XDG_CACHE_HOME"] = CAMOUFOX_CACHE
    env["TMPDIR"] = CAMOUFOX_TMP
    # evita propagar PLAYWRIGHT_BROWSERS_PATH (não usado aqui) e PLAYWRIGHT qq
    env.pop("PLAYWRIGHT_BROWSERS_PATH", None)

    log("🌐 Rodando Camoufox (subprocess isolado)...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=240
        )
    except subprocess.TimeoutExpired:
        log("❌ Camoufox excedeu o tempo (240s)")
        return None

    for line in result.stdout.splitlines():
        if line.startswith(_CAMOUFOX_MARKER):
            try:
                return json.loads(line[len(_CAMOUFOX_MARKER):].strip())
            except json.JSONDecodeError:
                log("⚠️ Resultado Camoufox inválido (JSON)")
                return None

    if result.returncode != 0:
        log(f"❌ Camoufox falhou (rc={result.returncode})")
        # últimos erros relevantes
        err_tail = (result.stderr or "").strip().splitlines()[-6:]
        for el in err_tail:
            log(f"   ↳ {el[:160]}")
    return None


def _camoufox_inner(code, link_afiliado):
    """Corpo da fase Camoufox (roda no subprocess com HOME=fakehome).
    Imprime o resultado no stdout com o marcador.
    """
    from camoufox.sync_api import Camoufox
    try:
        from playwright.sync_api import TimeoutError as CamoTimeout
    except ImportError:
        class CamoTimeout(Exception):
            pass

    meli_home = "https://www.mercadolivre.com.br"

    # O link de afiliado é a FONTE DE VERDADE: se houver um link meli.la em
    # qualquer argumento, ele define o alvo do Camoufox (abrir → redirect →
    # extrair product_id). O código 9RV3YA-XXXX serve apenas para rotular o
    # produto (não é usado para navegação — não resolve na busca do ML).
    # A busca pelo código só é executada como fallback quando NÃO há link.
    target_meli = None
    search_code = None

    if code and code.lower().startswith("http"):
        target_meli = code          # link no 1º arg (só link, ou link + código)
    elif link_afiliado and link_afiliado.lower().startswith("http"):
        target_meli = link_afiliado # link no 2º arg (código + link)

    if not target_meli:
        # Sem link: excecional — tenta pela busca do código
        if code and not code.lower().startswith("http"):
            search_code = code
        elif link_afiliado and not link_afiliado.lower().startswith("http"):
            search_code = link_afiliado

    try:
        with Camoufox(headless=True, os="windows") as browser:
            page = browser.new_page()

            # 1. Entra no ML primeiro (gera cookies de sessão)
            page.goto(meli_home, timeout=60000)
            page.wait_for_timeout(4000)
            try:
                btn = page.query_selector('button:has-text("Aceitar")')
                if btn:
                    btn.click(timeout=3000)
                    page.wait_for_timeout(1500)
            except Exception:
                pass

            # 2. Abre o meli.la (ativa etiqueta de afiliado) e aguarda redirect
            if target_meli:
                log(f"🔗 Abrindo {target_meli}...")
                try:
                    page.goto(target_meli, timeout=60000)
                except CamoTimeout:
                    pass
                page.wait_for_timeout(8000)

            final = page.url
            product_id = item_id = None

            # Tenta extrair product_id/item_id direto do redirect do meli.la,
            # antes de qualquer navegação/busca (a etiqueta resolve o produto aqui).
            m_prod = re.search(r'/p/(MLB\d+)', final)
            m_item = re.search(r'wid=(MLB\d+)', final)
            product_id = m_prod.group(1) if m_prod else None
            item_id = m_item.group(1) if m_item else None

            # Igual ao Procedimento B: o redirect do meli.la normalmente cai numa
            # página-slug com cards de produto (/p/MLB). Se ainda não resolveu o
            # product_id, clica no 1º card da página. Isso vale tanto para A quanto
            # para B (o link de afiliado é o mesmo produto). Só vai pra busca como
            # fallback quando não houver card pra clicar.
            if not product_id:
                try:
                    page.wait_for_selector("a[href*='/p/MLB']", timeout=30000)
                    cards = page.query_selector_all("a[href*='/p/MLB']")
                except CamoTimeout:
                    log("⚠️ Redirect não trouxe card /p/MLB")
                    cards = []

                if cards:
                    log("🖱️ Clicando no 1º /p/MLB da página redirecionada (sem busca)")
                    card = cards[0]
                    try:
                        card.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    page.wait_for_timeout(800)
                    try:
                        card.hover()
                    except Exception:
                        pass
                    page.wait_for_timeout(600)
                    try:
                        with page.expect_navigation(timeout=60000, wait_until="domcontentloaded"):
                            card.click()
                    except Exception:
                        with page.expect_navigation(timeout=60000, wait_until="domcontentloaded"):
                            pass
                    page.wait_for_timeout(10000)
                    final = page.url
                    m_prod = re.search(r'/p/(MLB\d+)', final)
                    m_item = re.search(r'wid=(MLB\d+)', final)
                    product_id = m_prod.group(1) if m_prod else None
                    item_id = m_item.group(1) if m_item else None

                elif search_code:
                    # Fallback para Procedimento A: sem redirect útil, busca o código
                    log(f"🔍 Procedimento A — buscando '{search_code}' (fallback)")
                    search_url = f"{meli_home}/search?as_word={quote_plus(search_code)}"
                    try:
                        page.goto(search_url, timeout=60000)
                    except CamoTimeout:
                        pass
                    page.wait_for_timeout(8000)
                    try:
                        page.wait_for_selector("a[href*='/p/MLB']", timeout=30000)
                    except CamoTimeout:
                        log("⚠️ Nenhum produto na busca")
                        print(_CAMOUFOX_MARKER + json.dumps({
                            "url_final": page.url, "product_id": None, "item_id": None,
                            "titulo_pagina": page.title(), "preco_pagina": None,
                            "erro": "sem_resultados_busca",
                        }, ensure_ascii=False))
                        return 0
                    cards = page.query_selector_all("a[href*='/p/MLB']")
                    card = cards[0]
                    try:
                        card.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    page.wait_for_timeout(800)
                    try:
                        card.hover()
                    except Exception:
                        pass
                    page.wait_for_timeout(600)
                    try:
                        with page.expect_navigation(timeout=60000, wait_until="domcontentloaded"):
                            card.click()
                    except Exception:
                        pass
                    page.wait_for_timeout(10000)
                    final = page.url
                    m_prod = re.search(r'/p/(MLB\d+)', final)
                    m_item = re.search(r'wid=(MLB\d+)', final)
                    product_id = m_prod.group(1) if m_prod else None
                    item_id = m_item.group(1) if m_item else None

                else:
                    # Sem search_code e sem card (Procedimento B puro sem produto)
                    log("⚠️ Nenhum produto encontrado na página")
                    print(_CAMOUFOX_MARKER + json.dumps({
                        "url_final": final, "product_id": None, "item_id": None,
                        "titulo_pagina": page.title(), "preco_pagina": None,
                        "erro": "sem_produtos",
                    }, ensure_ascii=False))
                    return 0

            if product_id:
                log(f"✅ Produto resolvido: {product_id} (item: {item_id})")

            # preço da página (referência)
            preco_pagina = None
            try:
                preco = page.query_selector(".andes-money-amount__fraction")
                if preco:
                    preco_pagina = preco.inner_text().strip()
            except Exception:
                pass

            anti_bot = "account-verification" in final

            result = {
                "url_final": final,
                "product_id": product_id,
                "item_id": item_id,
                "titulo_pagina": page.title(),
                "preco_pagina": preco_pagina,
                "anti_bot": anti_bot,
                "etiquetado": "matt_" in final,
                "codigo_busca": search_code,
            }
            print(_CAMOUFOX_MARKER + json.dumps(result, ensure_ascii=False))
            return 0
    except Exception as e:
        log(f"❌ Erro na fase Camoufox: {e}")
        # registra parcial mesmo com erro
        try:
            print(_CAMOUFOX_MARKER + json.dumps({
                "url_final": final if 'final' in dir() else "",
                "product_id": product_id if 'product_id' in dir() else None,
                "item_id": item_id if 'item_id' in dir() else None,
                "titulo_pagina": page.title() if 'page' in dir() else "",
                "preco_pagina": None,
                "erro": str(e),
            }, ensure_ascii=False))
        except Exception:
            pass
        return 1


# --- ML API ---

def ml_get(url, token):
    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode()[:500])
        except Exception:
            body = {}
        return e.code, body


def collect_from_api(code, link_afiliado, cam_result):
    """Usa a API oficial do ML para coletar dados estruturados.
    cam_result: dict do Camoufox ({product_id, item_id, ...}).
    """
    from Scripts.ml_token import get_access_token
    token, _ = get_access_token()

    product_id = (cam_result or {}).get("product_id")
    item_id = (cam_result or {}).get("item_id")
    url_final = (cam_result or {}).get("url_final", "")

    data = {
        "titulo": "",
        "preco": "",
        "preco_pix": None,
        "preco_cheio": None,
        "desconto_pct": None,
        "imagem": "",
        "imagem_id": None,
        "imagem_path": None,
        "descricao": "",
        "features": [],
        "link_original": link_afiliado or url_final,
        "fonte": "mercadolivre",
        "avaliacao": "",
        "num_fotos": 0,
        "product_id": product_id,
        "item_id": item_id,
        "url_final": url_final,
        "titulo_pagina": (cam_result or {}).get("titulo_pagina", ""),
        "preco_pagina": (cam_result or {}).get("preco_pagina"),
    }

    # 1. /products/{product_id} → name + pictures
    if product_id:
        st, d = ml_get(f"{ML_API}/products/{product_id}", token)
        if st == 200:
            data["titulo"] = d.get("name", "")
            pics = d.get("pictures", [])
            data["num_fotos"] = len(pics)
            if pics:
                data["imagem"] = pics[0].get("url") or pics[0].get("secure_url", "")

    # 2. /products/{product_id}/items → results[0]: price, original_price, shipping, condition
    if product_id:
        st, d = ml_get(f"{ML_API}/products/{product_id}/items", token)
        if st == 200:
            results = d.get("results", [])
            if results:
                it = results[0]
                if not data.get("item_id"):
                    data["item_id"] = it.get("item_id")
                pix = it.get("price")
                orig = it.get("original_price")
                if not data.get("titulo"):
                    data["titulo"] = it.get("title") or it.get("name") or data["titulo"]
                # variações de título do produto
                shipping = it.get("shipping", {}) or {}
                data["free_shipping"] = bool(shipping.get("free_shipping"))
                data["condition"] = it.get("condition", "")
                data["preco_pix"] = pix
                data["preco_cheio"] = orig if orig and orig > pix else None
                # build de preço PIX
                if pix is not None:
                    data["preco"] = f"R$ {format_brl(pix)}"
                    if data["preco_cheio"]:
                        data["desconto_pct"] = round((1 - pix / data["preco_cheio"]) * 100)
                        if data["desconto_pct"] < 0:
                            data["desconto_pct"] = 0

    # 3. /items/{item_id}/description → plain_text
    if item_id:
        st, d = ml_get(f"{ML_API}/items/{item_id}/description", token)
        if st == 200:
            data["descricao"] = d.get("plain_text", "")

    # 4. /reviews/item/{item_id}
    if item_id:
        st, d = ml_get(f"{ML_API}/reviews/item/{item_id}", token)
        if st == 200:
            reviews = d.get("reviews", [])
            rating = d.get("rating_average") or d.get("rating")
            if rating is not None:
                data["avaliacao"] = f"{rating} ({len(reviews)} avaliações)"
            else:
                data["avaliacao"] = f"{len(reviews)} avaliações"

    # fallback de título
    if not data["titulo"]:
        data["titulo"] = (cam_result or {}).get("titulo_pagina", "") or code

    return data


def format_brl(value):
    """Formata número para R$ brasileiro com 2 casas (ex: 733 -> '733,00', 441.349 -> '441,35')."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value) if value else ""
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_caption(data, link_afiliado=None):
    lines = []
    if data.get("titulo"):
        lines.append(f"🔥 {data['titulo']}")

    # Preço com PIX + cheio + desconto (quando houver)
    pix = data.get("preco_pix")
    if pix is not None:
        if data.get("preco_cheio"):
            desc = data.get("desconto_pct")
            desc_str = f" — {desc}% OFF" if desc is not None else ""
            lines.append(f"💰 R$ {format_brl(pix)} no Pix (de R$ {format_brl(data['preco_cheio'])}{desc_str})")
        else:
            lines.append(f"💰 R$ {format_brl(pix)}")
    elif data.get("preco"):
        lines.append(f"💰 {data['preco']}")

    if data.get("avaliacao"):
        lines.append(f"⭐ {data['avaliacao']}")
    if data.get("descricao"):
        lines.append(f"📝 {data['descricao'][:200]}")
    if data.get("free_shipping"):
        lines.append("🚚 Frete grátis!")

    link = link_afiliado or data.get("link_original") or data.get("url_final", "")
    if link:
        lines.append(f"🔗 {link}")
        lines.append("📌 Preço promocional por tempo limitado!")
    return "\n".join(lines)


def download_image(img_url, code):
    if not img_url:
        return None, None
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    IMAGENS_DIR.mkdir(parents=True, exist_ok=True)
    img_id = f"{uuid.uuid4().hex[:12]}.jpg"
    img_path = IMAGENS_DIR / img_id

    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", USER_AGENT,
             "--max-time", "20", "-o", str(img_path), img_url],
            capture_output=True, timeout=25
        )
        if result.returncode == 0 and img_path.exists() and img_path.stat().st_size > 1000:
            with open(img_path, "rb") as f:
                header = f.read(4)
            if header[:3] == b'\xff\xd8\xff' or header[:4] in (b'\x89PNG', b'RIFF') or header[:3] == b'GIF':
                log(f"🖼️  Imagem OK: {img_id} ({img_path.stat().st_size} bytes)")
                return img_id, str(img_path)
            else:
                log(f"⚠️ Magic bytes inválidos: {header.hex()}")
                img_path.unlink()
                return None, None
        return None, None
    except Exception as e:
        log(f"❌ Erro imagem: {e}")
        if img_path.exists():
            img_path.unlink()
        return None, None


def save_json_temp(data, code):
    """Salva JSON intermediário no padrão ml_resultado_CODIGO.json (workspace)."""
    prefix = re.sub(r'[^A-Za-z0-9_-]', '_', code)[:40] or "produto"
    out = Path("/home/node/.openclaw/workspace") / f"ml_resultado_{prefix}.json"
    try:
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log(f"📄 JSON salvo: {out}")
        return str(out)
    except Exception as e:
        log(f"⚠️ Falha ao salvar JSON: {e}")
        return None


# --- Main ---

def extract(code, link_afiliado=None):
    """Fluxo principal: Camoufox (subprocess) → API → download → banco."""
    # Fase 1: Camoufox
    cam_result = run_camoufox_phase(code, link_afiliado)
    if not cam_result:
        log("⚠️ Camoufox não retornou resultado — tentando método clássico...")
        return extract_classic(code, link_afiliado)

    if cam_result.get("erro"):
        log(f"⚠️ Camoufox: {cam_result['erro']} — tentando método clássico...")
        return extract_classic(code, link_afiliado)

    product_id = cam_result.get("product_id")
    log(f"📍 URL final: {str(cam_result.get('url_final'))[:100]}")
    if product_id:
        log(f"🔑 product_id: {product_id} | item_id: {cam_result.get('item_id')}")
        log(f"🧪 Anti-bot: {cam_result.get('anti_bot')} | Etiquetada: {cam_result.get('etiquetado')}")
    else:
        log("⚠️ Sem product_id na URL — não dá para usar a API; caindo pro clássico.")
        return extract_classic(code, link_afiliado)

    # Fase 2: API
    data = collect_from_api(code, link_afiliado, cam_result)

    # Fase 3: imagem
    if data.get("imagem"):
        img_id, img_path = download_image(data["imagem"], code)
        data["imagem_id"] = img_id
        data["imagem_path"] = img_path
    else:
        data["imagem_id"] = None
        data["imagem_path"] = None

    return data


def extract_classic(code, link_afiliado=None):
    """Método clássico (Playwright/curl) mantido como fallback para compat."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None

    product_url = None

    # Seguir link afiliado
    if link_afiliado:
        final = curl_head(link_afiliado) if link_afiliado.lower().startswith("http") else link_afiliado
        if final and "mercadolivre" in final:
            product_url = final

    if not product_url and code.startswith("http"):
        product_url = code
    elif not product_url and "MLB" in code and len(code) > 8:
        product_url = f"https://www.mercadolivre.com.br/p/{code}"

    if not product_url:
        search_url = f"https://www.mercadolivre.com.br/search?as_word={quote_plus(code)}"
        html = curl_get(search_url)
        if html and len(html) > 10000:
            for pat in [r'href="(/p/MLB\d+)"', r'href="(https?://[^"]*MLB\d+[^"]*)"']:
                m = re.search(pat, html)
                if m:
                    href = m.group(1)
                    product_url = href if href.startswith("http") else f"https://www.mercadolivre.com.br{href}"
                    break

    if not product_url:
        log("❌ Não foi possível determinar URL do produto (clássico)")
        return None

    data = None
    if sync_playwright:
        data = extract_with_playwright(product_url, link_afiliado)

    if not data:
        html = curl_get(product_url)
        if html:
            meta = extract_from_html(html)
            data = {
                "titulo": meta.get("titulo", code),
                "preco": meta.get("preco", "N/D"),
                "imagem": meta.get("imagem", ""),
                "descricao": meta.get("descricao", ""),
                "features": [],
                "link_original": link_afiliado or product_url,
                "fonte": "mercadolivre",
                "avaliacao": "",
            }

    if not data:
        return None

    if data.get("imagem"):
        img_id, img_path = download_image(data["imagem"], code)
        data["imagem_id"] = img_id
        data["imagem_path"] = img_path
    else:
        data["imagem_id"] = None
        data["imagem_path"] = None

    return data


def curl_get(url, timeout=TIMEOUT):
    result = subprocess.run(
        ["curl", "-s", "-L", "-A", USER_AGENT,
         "--connect-timeout", "10", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 5
    )
    if result.returncode == 0 and result.stdout:
        return result.stdout
    return None


def curl_head(url):
    result = subprocess.run(
        ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{url_effective}",
         "-A", USER_AGENT, "--connect-timeout", "10", "--max-time", "15", url],
        capture_output=True, text=True, timeout=20
    )
    return result.stdout.strip() or url


def extract_from_html(html):
    data = {}
    jd_match = re.search(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if jd_match:
        try:
            jd = json.loads(jd_match.group(1))
            if isinstance(jd, dict) and jd.get("@type") == "Product":
                data["titulo"] = jd.get("name", "")
                offers = jd.get("offers", {})
                if isinstance(offers, dict) and offers.get("price"):
                    data["preco"] = f"R$ {offers['price']}"
                img = jd.get("image", [])
                if isinstance(img, list) and img:
                    data["imagem"] = img[0]
                elif isinstance(img, str):
                    data["imagem"] = img
                if jd.get("description"):
                    data["descricao"] = jd["description"]
        except json.JSONDecodeError:
            pass
    if not data.get("titulo"):
        m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
        if m:
            data["titulo"] = m.group(1)
    if not data.get("imagem"):
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        if m:
            data["imagem"] = m.group(1)
    if not data.get("descricao"):
        m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
        if m:
            data["descricao"] = m.group(1)[:300]
    return data


def extract_with_playwright(url, link_afiliado=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("⚠️  Playwright não disponível")
        return None

    for attempt in range(2):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox", "--disable-setuid-sandbox",
                        "--disable-gpu", "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/149.0.0.0 Safari/537.36"
                    ),
                    locale="pt-BR",
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                """)
                log(f"🌐 Navegando: {url[:80]}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)
                page_text = page.locator("body").inner_text()[:500].lower()
                if "não sou um robô" in page_text or "captcha" in page_text:
                    log("⚠️  CAPTCHA detectado")
                    browser.close()
                    return None

                data = {
                    "titulo": "", "preco": "", "imagem": "", "descricao": "",
                    "features": [], "link_original": link_afiliado or url,
                    "fonte": "mercadolivre", "avaliacao": "",
                }
                try:
                    el = page.locator("h1.ui-pdp-title").first
                    if el.is_visible(timeout=3000):
                        data["titulo"] = el.inner_text().strip()
                except Exception:
                    pass
                if not data["titulo"]:
                    try:
                        el = page.locator('meta[property="og:title"]').first
                        data["titulo"] = el.get_attribute("content") or ""
                    except Exception:
                        pass
                price_sel = [".andes-money-amount__fraction", ".ui-pdp-price__second-line .andes-money-amount__fraction"]
                for sel in price_sel:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            price = el.inner_text().strip()
                            try:
                                cents = page.locator(sel.replace("__fraction", "__cents")).first
                                if cents.is_visible(timeout=500):
                                    price += f",{cents.inner_text().strip()}"
                            except Exception:
                                pass
                            data["preco"] = f"R$ {price}"
                            break
                    except Exception:
                        continue
                try:
                    el = page.locator(".ui-pdp-gallery__figure img[src*='http']").first
                    if el.is_visible(timeout=2000):
                        data["imagem"] = el.get_attribute("src") or ""
                except Exception:
                    pass
                if not data["imagem"]:
                    try:
                        el = page.locator('meta[property="og:image"]').first
                        data["imagem"] = el.get_attribute("content") or ""
                    except Exception:
                        pass
                try:
                    els = page.locator(".ui-pdp-list__item")
                    count = els.count()
                    if count > 0:
                        features = []
                        for i in range(min(count, 15)):
                            txt = els.nth(i).inner_text().strip()
                            if txt:
                                features.append(txt)
                        data["features"] = features
                        data["descricao"] = features[0][:300] if features else ""
                except Exception:
                    pass
                try:
                    el = page.locator(".ui-pdp-review__rating").first
                    if el.is_visible(timeout=1000):
                        rating = el.inner_text().strip()
                        data["avaliacao"] = rating
                except Exception:
                    pass
                browser.close()
                return data
        except Exception as e:
            log(f"❌ Tentativa {attempt+1}: {e}")
            if attempt == 0:
                log("🔄 Nova tentativa...")
    return None


def main():
    # Modo interno (subprocess Camoufox)
    if len(sys.argv) >= 2 and sys.argv[1] == "--camoufox-phase":
        code = sys.argv[2] if len(sys.argv) > 2 else ""
        link = sys.argv[3] if len(sys.argv) > 3 else ""
        rc = _camoufox_inner(code, link)
        sys.exit(rc)

    if len(sys.argv) < 2:
        print("Uso: python3 extrator_ml.py CODIGO [LINK_AFILIADO]", file=sys.stderr)
        print("     python3 extrator_ml.py LINK_AFILIADO", file=sys.stderr)
        print("Exemplo:", file=sys.stderr)
        print("  python3 extrator_ml.py '9RV3YA-4LKT' 'https://meli.la/XXXX'", file=sys.stderr)
        print("  python3 extrator_ml.py 'https://meli.la/XXXX'", file=sys.stderr)
        sys.exit(1)

    arg1 = sys.argv[1].strip()
    arg2 = sys.argv[2].strip() if len(sys.argv) > 2 else None

    # Resolução unificada: o link de afiliado é a fonte de verdade. Aceita o
    # link em qualquer argumento (só link, código+link, link+código). O código
    # 9RV3YA-XXXX serve apenas para rotular o produto; a navegação sempre usa
    # o link quando ele existe.
    def _eh_link(s):
        return bool(s) and s.lower().startswith("http")

    code = None
    link_afiliado = None
    if _eh_link(arg1):
        link_afiliado = arg1
        if arg2 and not _eh_link(arg2):
            code = arg2
    elif arg2 and _eh_link(arg2):
        link_afiliado = arg2
        code = arg1
    else:
        # Sem link: usa o 1º arg como código (busca como fallback)
        code = arg1

    if link_afiliado:
        log(f"🚀 Link afiliado (fonte de verdade): {link_afiliado}")
        if code:
            log(f"🏷️  Código (rótulo): {code}")
    else:
        log(f"🚀 Sem link — usando código (busca): {code}")

    code = code or ""

    data = extract(code, link_afiliado)

    if not data:
        data = {
            "titulo": f"Produto {code or link_afiliado}",
            "preco": "N/D",
            "imagem": "",
            "imagem_id": None,
            "imagem_path": None,
            "descricao": "",
            "features": [],
            "link_original": link_afiliado or f"https://meli.la/{code}",
            "fonte": "mercadolivre",
            "avaliacao": "",
        }
        log("⚠️ Usando fallback vazio")

    data["codigo"] = code or link_afiliado

    # Guarda anti-sobrescrita de preço: nunca apagar um preço válido do banco
    # com N/D (ou vazio) de uma extração falha. Se a extração atual não trouxe
    # preço mas já existe um bom no banco para o mesmo código, mantém o antigo.
    preco_extraido = (data.get("preco") or "").strip()
    eh_sem_preco = (
        not preco_extraido
        or preco_extraido.upper() in ("N/D", "ND", "N/D ", "", "S/D")
    )
    if eh_sem_preco:
        prev = consultar_por_codigo(data["codigo"])
        if prev and (prev.get("preco") or "").strip():
            prev_preco = (prev.get("preco") or "").strip()
            if prev_preco.upper() not in ("N/D", "ND", "S/D"):
                log(f"🛡️  Preço N/D na extração — preservando preço existente no banco: {prev_preco}")
                data["preco"] = prev_preco

    # Caption é montada DEPOIS da guarda de preço, pra refletir o preço final
    data["caption"] = build_caption(data, link_afiliado)

    # Salva no SQLite
    if upsert_produto(data):
        log("🗄️  Produto salvo no SQLite (.produtos.db)")
    else:
        log("⚠️  Falha ao salvar no SQLite")

    # JSON temporário
    save_json_temp(data, data["codigo"])

    # Exibe resultado (stdout limpo só com o JSON, p/ o fluxo do grupo)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
