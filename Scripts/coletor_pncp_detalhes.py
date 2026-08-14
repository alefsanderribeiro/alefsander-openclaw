#!/usr/bin/env python3
"""
Coletor de DETALHES da amostra PNCP — via API oficial /api/pncp/v1.
Pega uma amostra diversificada (por modalidade + esfera + UF) e baixa:
  - detalhe da compra (contratação)
  - itens
  - lista de arquivos/documentos
  - atas relacionadas (quando houver)
Salva em: licitacoes/amostra/detalhes/{id}.json
"""
import json
import os
import random
import sys
import time

import requests

BASE_CONSULTA = "https://pncp.gov.br/api/consulta/v1/"
BASE = "https://pncp.gov.br/api/pncp/v1/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
DELAY = 0.4
AMOSTRA_TAMANHO = 15
SEED = 42

AMOSTRA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "licitacoes", "amostra"))
DET_DIR = os.path.join(AMOSTRA_DIR, "detalhes")


def get(path, tentativas=2, base=None):
    url = (base or BASE) + path.lstrip("/")
    for t in range(tentativas):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 403):
                time.sleep(3)
                continue
            print(f"  !! HTTP {r.status_code} {url}", file=sys.stderr)
        except Exception as e:
            print(f"  !! erro {url}: {e}", file=sys.stderr)
        time.sleep(1.5 * (t + 1))
    return None


def main():
    os.makedirs(DET_DIR, exist_ok=True)
    with open(os.path.join(AMOSTRA_DIR, "licitacoes_consolidadas.json"), encoding="utf-8") as f:
        itens = json.load(f)

    # só editais/avisos (têm rota de compra com itens/arquivos)
    editais = [i for i in itens if i.get("document_type") in ("edital", "aviso") and i.get("numero_sequencial")]
    contratos = [i for i in itens if i.get("document_type") == "contrato" and i.get("numero_sequencial")]
    print(f"Total consolidado: {len(itens)} | editais c/ sequencial: {len(editais)} | contratos c/ sequencial: {len(contratos)}")

    # estratificação: chave (modalidade, esfera) → amostra balanceada
    random.Random(SEED).shuffle(editais)
    por_grupo = {}
    for it in editais:
        chave = (it.get("modalidade_licitacao_id"), it.get("esfera_id"))
        por_grupo.setdefault(chave, []).append(it)

    escolhidos = []
    grupos = sorted(por_grupo.items(), key=lambda kv: len(kv[1]), reverse=True)
    # round-robin pelos grupos até completar AMOSTRA_TAMANHO
    i = 0
    while len(escolhidos) < AMOSTRA_TAMANHO and i < 200:
        for chave, lista in grupos:
            if lista and len(escolhidos) < AMOSTRA_TAMANHO:
                escolhidos.append(lista.pop(0))
        i += 1

    print(f"Selecionados {len(escolhidos)} editais + {len(contratos[:5])} contratos para detalhamento")
    escolhidos += contratos[:5]
    ok = 0
    for it in escolhidos:
        cnpj = it["orgao_cnpj"]
        ano = it["ano"]
        seq = it["numero_sequencial"]
        rid = it["id"]
        eh_contrato = it.get("document_type") == "contrato"
        payload = {"search_item": it, "detalhe": None, "itens": [], "arquivos": [], "atas": []}

        if eh_contrato:
            det = get(f"orgaos/{cnpj}/contratos/{ano}/{seq}")
            if det is not None:
                payload["detalhe"] = det
            time.sleep(DELAY)
        else:
            det = get(f"orgaos/{cnpj}/compras/{ano}/{seq}", base=BASE_CONSULTA)
            if det is not None:
                payload["detalhe"] = det
            time.sleep(DELAY)

            its = get(f"orgaos/{cnpj}/compras/{ano}/{seq}/itens")
            if its:
                payload["itens"] = its if isinstance(its, list) else its.get("itens", [])
            time.sleep(DELAY)

            arq = get(f"orgaos/{cnpj}/compras/{ano}/{seq}/arquivos")
            if arq:
                payload["arquivos"] = arq if isinstance(arq, list) else arq.get("arquivos", [])
            time.sleep(DELAY)

            atas = None  # endpoint lento; coletado na fase 2 se necessário
            time.sleep(DELAY)

        with open(os.path.join(DET_DIR, f"{rid}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        ok += 1
        status = f"detalhe={bool(payload['detalhe'])} itens={len(payload['itens'])} arquivos={len(payload['arquivos'])} atas={len(payload['atas'])}"
        print(f"  [{ok}/{len(escolhidos)}] {cnpj}/{ano}/{seq} ({it.get('document_type')}) {it.get('modalidade_licitacao_nome')} {it.get('uf')} — {status}", flush=True)

    print(f"\n>>> Detalhes salvos: {ok} arquivos em {DET_DIR}")


if __name__ == "__main__":
    main()
