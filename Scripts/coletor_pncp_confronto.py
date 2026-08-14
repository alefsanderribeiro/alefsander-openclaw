#!/usr/bin/env python3
"""
Coletor de CONFRONTO — segunda amostra PNCP com dados novos:
  - busca: termos novos, modalidades não cobertas (leilão, pré-qualificação), tipos doc
  - detalhes novos: compra + itens + arquivos + RESULTADOS de itens + ATAS
  - contratos novos + EMPENHOS
  - PCA (planos de contratação) — dado ainda não coletado
Salva em: licitacoes/confronto/
"""
import json
import os
import sys
import time

import requests

BASE_SEARCH = "https://pncp.gov.br/api/search/"
BASE_PNCP = "https://pncp.gov.br/api/pncp/v1/"
BASE_CONSULTA = "https://pncp.gov.br/api/consulta/v1/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://pncp.gov.br/app/editais",
    "Origin": "https://pncp.gov.br",
}
DELAY = 0.7
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "licitacoes", "confronto"))

TERMOS_NOVOS = ["cafe", "energia solar", "fardamento", "odontologia", "tinta",
                "pneus", "software", "vigilancia", "merenda", "combustivel"]
MODALIDADES_NOVAS = {1: "leilao", 11: "pre_qualificacao"}


def get(url, params=None, tentativas=2, timeout=25):
    for t in range(tentativas):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 403):
                time.sleep(3)
                continue
            print(f"  !! HTTP {r.status_code} {url[:110]}", file=sys.stderr)
        except Exception as e:
            print(f"  !! erro {url[:110]}: {e}", file=sys.stderr)
        time.sleep(1.5 * (t + 1))
    return None


def salvar(nome, payload):
    with open(os.path.join(OUT, nome), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)


def main():
    os.makedirs(OUT, exist_ok=True)
    coletados = {}

    # ---- FASE 1: buscas novas ----
    print(">>> FASE 1: buscas novas")
    for termo in TERMOS_NOVOS:
        d = get(BASE_SEARCH, params={"q": termo, "tipos_documento": "edital", "status": "divulgada", "pagina": 1, "tam_pagina": 50})
        if d:
            salvar(f"busca_termo_{termo.replace(' ','_')}.json", d)
            for it in d.get("items", []):
                coletados[it["id"]] = it
        print(f"  termo '{termo}': {d.get('total') if d else 'FALHOU'}", flush=True)
        time.sleep(DELAY)
    for mid, nome in MODALIDADES_NOVAS.items():
        d = get(BASE_SEARCH, params={"tipos_documento": "edital", "modalidade": mid, "status": "recebendo_proposta", "pagina": 1, "tam_pagina": 50})
        if d:
            salvar(f"busca_mod_{mid}_{nome}.json", d)
            for it in d.get("items", []):
                coletados[it["id"]] = it
        print(f"  modalidade {mid} ({nome}): {d.get('total') if d else 'FALHOU'}", flush=True)
        time.sleep(DELAY)

    # também atas via search (document_type=ata)
    d = get(BASE_SEARCH, params={"tipos_documento": "ata", "status": "divulgada", "pagina": 1, "tam_pagina": 50})
    if d:
        salvar("busca_atas.json", d)
        for it in d.get("items", []):
            coletados[it["id"]] = it
    print(f"  atas: {d.get('total') if d else 'FALHOU'}", flush=True)
    time.sleep(DELAY)

    lista = list(coletados.values())
    salvar("consolidado_busca.json", lista)
    print(f">>> TOTAL busca nova: {len(lista)}")

    # ---- FASE 2: detalhes novos (com resultados e atas) ----
    print(">>> FASE 2: detalhes novos")
    editais = [i for i in lista if i.get("document_type") in ("edital", "aviso") and i.get("numero_sequencial")]
    # diversifica: embaralha com seed, pega 10 espalhados
    import random
    random.Random(7).shuffle(editais)
    escolhidos = editais[:10]
    for it in escolhidos:
        cnpj, ano, seq = it["orgao_cnpj"], it["ano"], it["numero_sequencial"]
        rid = it["id"]
        payload = {"search_item": it, "detalhe": None, "itens": [], "arquivos": [], "atas": [], "resultados": []}
        det = get(f"{BASE_CONSULTA}orgaos/{cnpj}/compras/{ano}/{seq}")
        if det is not None:
            payload["detalhe"] = det
        time.sleep(DELAY)
        its = get(f"{BASE_PNCP}orgaos/{cnpj}/compras/{ano}/{seq}/itens")
        if its:
            payload["itens"] = its if isinstance(its, list) else []
        time.sleep(DELAY)
        arq = get(f"{BASE_PNCP}orgaos/{cnpj}/compras/{ano}/{seq}/arquivos")
        if arq:
            payload["arquivos"] = arq if isinstance(arq, list) else []
        time.sleep(DELAY)
        atas = get(f"{BASE_PNCP}orgaos/{cnpj}/compras/{ano}/{seq}/atas")
        if atas:
            payload["atas"] = atas if isinstance(atas, list) else []
        time.sleep(DELAY)
        # resultados dos 2 primeiros itens (novo endpoint p/ confronto)
        for item_curto in (payload["itens"] or [])[:2]:
            n_item = item_curto.get("numeroItem")
            if n_item is None:
                continue
            res = get(f"{BASE_PNCP}orgaos/{cnpj}/compras/{ano}/{seq}/itens/{n_item}/resultados")
            if res:
                payload["resultados"].append({"numeroItem": n_item, "resultados": res if isinstance(res, list) else []})
            time.sleep(DELAY)
        salvar(f"detalhe_{rid}.json", payload)
        print(f"  [{len(os.listdir(OUT))}] {cnpj}/{ano}/{seq} {it.get('modalidade_licitacao_nome')} {it.get('uf')} — itens={len(payload['itens'])} arq={len(payload['arquivos'])} atas={len(payload['atas'])} res={len(payload['resultados'])}", flush=True)

    # ---- FASE 3: contratos novos + empenhos ----
    print(">>> FASE 3: contratos + empenhos")
    contratos = [i for i in lista if i.get("document_type") == "contrato" and i.get("numero_sequencial")]
    random.Random(7).shuffle(contratos)
    for it in contratos[:4]:
        cnpj, ano, seq = it["orgao_cnpj"], it["ano"], it["numero_sequencial"]
        payload = {"search_item": it, "detalhe": None, "empenhos": []}
        det = get(f"{BASE_CONSULTA}orgaos/{cnpj}/contratos/{ano}/{seq}")
        if det is not None:
            payload["detalhe"] = det
        time.sleep(DELAY)
        emp = get(f"{BASE_PNCP}orgaos/{cnpj}/contratos/{ano}/{seq}/empenhos")
        if emp:
            payload["empenhos"] = emp if isinstance(emp, list) else []
        time.sleep(DELAY)
        salvar(f"contrato_{cnpj}_{ano}_{seq}.json", payload)
        print(f"  contrato {cnpj}/{ano}/{seq} — empenhos={len(payload['empenhos'])}", flush=True)

    # ---- FASE 4: PCA (planos de contratação) ----
    print(">>> FASE 4: PCA")
    # usa o CNPJ do Comando da Marinha (órgão grande, tem PCA)
    for cnpj_pca in ["00394502000144", "00394452000103"]:
        pca = get(f"{BASE_PNCP}orgaos/{cnpj_pca}/pca/2026/consolidado")
        if pca:
            salvar(f"pca_{cnpj_pca}_2026.json", pca)
            print(f"  PCA {cnpj_pca}: {len(pca) if isinstance(pca, list) else 'obj'}", flush=True)
        time.sleep(DELAY)
        pca_itens = get(f"{BASE_PNCP}orgaos/{cnpj_pca}/pca/2026/1/itens")
        if pca_itens:
            salvar(f"pca_itens_{cnpj_pca}_2026.json", pca_itens)
            print(f"  PCA itens {cnpj_pca}: {len(pca_itens) if isinstance(pca_itens, list) else 'obj'}", flush=True)
        time.sleep(DELAY)

    print(">>> Coleta de confronto concluída.")


if __name__ == "__main__":
    main()
