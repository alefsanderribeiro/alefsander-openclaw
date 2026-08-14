#!/usr/bin/env python3
"""
teste_rotas_ml.py — Testa as rotas da API do ML documentadas na cópia local
e gera um relatório de conformidade (200/403/404/...).

Uso: python3 Scripts/teste_rotas_ml.py
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from Scripts.ml_token import get_access_token

DOCS = Path.home() / "Documentos/Mega/Drive/Projetos/Documentacoes/Mercado-Livre-API"
REPORTE = DOCS / f"teste-rotas-{time.strftime('%Y-%m-%d')}.md"

# Valores de exemplo para placeholders
EX = {
    "$ITEM_ID": "MLB4443086631", "{item_id}": "MLB4443086631", "{itemId}": "MLB4443086631",
    "$SELLER_ID": "355451777", "$USER_ID": "355451777", "$ADVERTISER_ID": "355451777",
    "$ADVERTISER_SITE_ID": "MLB", "{site_id}": "MLB",
    "$USER_PRODUCT_ID": "MLB4443086631", "{up_id}": "MLB4443086631",
    "$PROMOTION_ID": "123456789", "$CAMPAIGN_ID": "123456789", "{offer_id}": "123456789",
    "$RESOURCE_ID": "123456789", "{KEY}": "teste", "{key}": "teste",
    "{order_id}": "123456789", ":id": "123456789", "{id}": "123456789",
    "{shipping_id}": "123456789", "{compatibility_id}": "123456789", "$SHIPPING_ID": "123456789",
}


def norm_rota(rota):
    r = rota.rstrip(". :")
    for k, v in EX.items():
        r = r.replace(k, v)
    return r


def extrair_rotas():
    rotas = {}
    for f in (DOCS / "paginas").glob("*.md"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'https?://api\.mercadolibre(?:\.com(?:\.br)?)?(/[^\s]+)', txt):
            r = m.group(1).rstrip('.,;)"')
            r = r.split("?")[0]
            if len(r) > 1:
                rotas.setdefault(r, {"metodos": set(), "pagina": f.name})
        for m in re.finditer(r'\b(GET|POST|PUT|DELETE)\s+/([A-Za-z0-9_${}.\-/:]+)', txt):
            r = "/" + m.group(2).rstrip(". :")
            if len(r) > 1:
                rotas.setdefault(r, {"metodos": set(), "pagina": f.name})
                rotas[r]["metodos"].add(m.group(1))
    return rotas


def testar(url, token, timeout=20):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode()[:300])
            msg = body.get("message", body.get("error", ""))
        except Exception:
            msg = ""
        return e.code, str(msg)[:100]
    except Exception as ex:
        return 0, str(ex)[:80]


def main():
    token, _ = get_access_token()
    rotas = extrair_rotas()
    print(f"📚 {len(rotas)} rotas encontradas na doc — testando GET em cada uma...\n")

    resultados = []
    for rota in sorted(rotas):
        url = "https://api.mercadolibre.com" + norm_rota(rota)
        st, msg = testar(url, token)
        metodos = ",".join(sorted(rotas[rota]["metodos"])) or "GET"
        resultados.append({"rota": rota, "url": url, "status": st, "msg": msg, "metodos": metodos, "pagina": rotas[rota]["pagina"]})
        print(f"  {st} {rota}  {msg[:45]}")
        time.sleep(0.25)

    # Relatório
    linhas = [
        f"# Teste de rotas da API do Mercado Livre\n",
        f"> Data: {time.strftime('%Y-%m-%d %H:%M')} · token: conta {token.split('-')[-1] if '-' in token else '?'} · método testado: GET\n",
        f"> Fonte: documentação local (`paginas/*.md`) — {len(resultados)} rotas\n",
        "\n## Resumo\n",
    ]
    cont = {}
    for r in resultados:
        k = {200: "✅ 200 OK", 400: "⚠️ 400 (rota existe, params)", 401: "🔐 401", 403: "🚫 403 bloqueado", 404: "❓ 404", 405: "⛔ 405 método", 0: "💥 erro de rede"}.get(r["status"], f"❓ {r['status']}")
        cont[k] = cont.get(k, 0) + 1
    for k, v in sorted(cont.items(), key=lambda x: -x[1]):
        linhas.append(f"- {k}: {v}")

    linhas.append("\n## Detalhes\n")
    linhas.append("| Status | Rota (normalizada) | Método doc | Resposta | Página |")
    linhas.append("|---|---|---|---|---|")
    for r in resultados:
        linhas.append(f"| {r['status']} | `{r['url'].replace('https://api.mercadolibre.com','')}` | {r['metodos']} | {r['msg'] or '-'} | {r['pagina']} |")

    REPORTE.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\n✅ Relatório: {REPORTE}")


if __name__ == "__main__":
    main()
