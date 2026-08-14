#!/usr/bin/env python3
"""
Coletor de amostra PNCP — busca multi-filtro (UFs, modalidades, status, termos).
Uso: python3 coletor_pncp_amostra.py
Salva: licitacoes/amostra/search_raw/*.json (por combinação)
       licitacoes/amostra/licitacoes_consolidadas.json (deduplicado)
       licitacoes/amostra/licitacoes_consolidadas.csv (resumo)
"""
import csv
import json
import os
import sys
import time

import requests

BASE = "https://pncp.gov.br/api/search/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://pncp.gov.br/app/editais",
    "Origin": "https://pncp.gov.br",
}
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "licitacoes", "amostra", "search_raw")
OUT_DIR = os.path.abspath(OUT_DIR)
DELAY = 0.6  # politeness entre requests

UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

# modalidades PNCP (ids vistos na API de domínio)
MODALIDADES = {
    4: "concorrencia_eletronica",
    5: "concorrencia_presencial",
    6: "pregao_eletronico",
    7: "pregao_presencial",
    8: "dispensa",
    9: "inexigibilidade",
    12: "credenciamento",
    15: "chamada_publica",
}

TERMOS = ["informatica", "obras", "limpeza", "alimentacao", "medicamentos",
          "mobiliario", "seguranca", "transporte", "manutencao", "construcao"]

TIPOS_DOC = ["edital", "ata", "contrato"]

ESFERAS = {"F": "federal", "E": "estadual", "M": "municipal"}


def buscar(params, tentativas=3):
    for t in range(tentativas):
        try:
            r = requests.get(BASE, params=params, headers=HEADERS, timeout=40)
            if r.status_code == 200:
                return r.json()
            print(f"  !! HTTP {r.status_code} params={params}", file=sys.stderr)
        except Exception as e:
            print(f"  !! erro: {e}", file=sys.stderr)
        time.sleep(2 * (t + 1))
    return None


def salvar_raw(nome, payload):
    with open(os.path.join(OUT_DIR, nome), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    coletados = {}  # id -> item

    # 0) filtros disponíveis (documentação empírica)
    f = buscar({"tipos_documento": "edital"})
    if f:
        salvar_raw("_filters.json", f)
        print(">>> filters.json salvo")

    # 1) por UF (status obrigatório)
    print(">>> Buscando por UF (27)")
    for uf in UFS:
        d = buscar({"tipos_documento": "edital", "uf": uf, "status": "divulgada", "pagina": 1, "tam_pagina": 50})
        if not d:
            continue
        salvar_raw(f"uf_{uf}.json", d)
        for it in d.get("items", []):
            coletados[it["id"]] = it
        print(f"  {uf}: total={d.get('total')} coletados={len(d.get('items', []))}", flush=True)
        time.sleep(DELAY)

    # 1b) por esfera
    print(">>> Buscando por esfera")
    for esf, nome in ESFERAS.items():
        d = buscar({"tipos_documento": "edital", "esfera": esf, "status": "divulgada", "pagina": 1, "tam_pagina": 50})
        if not d:
            continue
        salvar_raw(f"esfera_{nome}.json", d)
        for it in d.get("items", []):
            coletados[it["id"]] = it
        print(f"  esfera {nome}: total={d.get('total')} coletados={len(d.get('items', []))}", flush=True)
        time.sleep(DELAY)

    # 2) por modalidade (recebendo proposta)
    print(">>> Buscando por modalidade (recebendo proposta)")
    for mid, nome in MODALIDADES.items():
        d = buscar({"tipos_documento": "edital", "modalidade": mid,
                    "status": "recebendo_proposta", "pagina": 1, "tam_pagina": 50})
        if not d:
            continue
        salvar_raw(f"modalidade_{mid}_{nome}.json", d)
        for it in d.get("items", []):
            coletados[it["id"]] = it
        print(f"  mod {mid} ({nome}): total={d.get('total')} coletados={len(d.get('items', []))}", flush=True)
        time.sleep(DELAY)

    # 3) por termo de busca (status obrigatório)
    print(">>> Buscando por termos")
    for termo in TERMOS:
        d = buscar({"q": termo, "tipos_documento": "edital", "status": "divulgada", "pagina": 1, "tam_pagina": 50})
        if not d:
            continue
        salvar_raw(f"termo_{termo}.json", d)
        for it in d.get("items", []):
            coletados[it["id"]] = it
        print(f"  termo '{termo}': total={d.get('total')} coletados={len(d.get('items', []))}", flush=True)
        time.sleep(DELAY)

    # 4) por tipo de documento (ata/contrato)
    print(">>> Buscando por tipos de documento (ata/contrato)")
    for td in TIPOS_DOC:
        d = buscar({"tipos_documento": td, "status": "divulgada", "pagina": 1, "tam_pagina": 50})
        if not d:
            continue
        salvar_raw(f"tipodoc_{td}.json", d)
        for it in d.get("items", []):
            coletados[it["id"]] = it
        print(f"  tipo {td}: total={d.get('total')} coletados={len(d.get('items', []))}", flush=True)
        time.sleep(DELAY)

    # consolida
    lista = list(coletados.values())
    print(f"\n>>> TOTAL ÚNICO: {len(lista)} licitações/documentos")
    with open(os.path.join(OUT_DIR, "..", "licitacoes_consolidadas.json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)

    # csv resumo
    campos = ["numero_controle_pncp", "title", "document_type", "modalidade_licitacao_nome",
              "situacao_nome", "uf", "municipio_nome", "orgao_cnpj", "orgao_nome",
              "data_publicacao_pncp", "data_fim_vigencia", "valor_global", "item_url"]
    with open(os.path.join(OUT_DIR, "..", "licitacoes_consolidadas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for it in lista:
            w.writerow(it)
    print("CSV salvo.")


if __name__ == "__main__":
    main()
