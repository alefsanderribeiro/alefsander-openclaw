#!/usr/bin/env python3
"""
Organiza os monitores do Uptime Kuma por TAGS (agrupamento por projeto).
Idempotente: cria as tags se não existirem e vincula os monitores.
"""
import os, time

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

from uptime_kuma_api import UptimeKumaApi

api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
print("✅ Login OK")

# ---------- Definição das tags ----------
TAGS = [
    {"name": "atelie",          "color": "#8b5cf6"},  # roxo
    {"name": "ms-dashboard",    "color": "#3b82f6"},  # azul
    {"name": "ms-automatizar",  "color": "#22c55e"},  # verde
    {"name": "infra",           "color": "#f97316"},  # laranja
    {"name": "servicos",        "color": "#eab308"},  # amarelo
    {"name": "sites",           "color": "#ef4444"},  # vermelho
]

# Monitor -> tags (por nome exato do monitor)
MONITOR_TAGS = {
    # ---- ATELIÊ ERP ----
    "Docker - atelie-db":  ["atelie"],
    "Docker - atelie-web": ["atelie"],
    "Ateliê ERP (HTTP)":       ["atelie"],
    # ---- MS-DASHBOARD ----
    "Docker - ms-dashboard-app":     ["ms-dashboard"],
    "Docker - ms-dashboard-redis":   ["ms-dashboard"],
    "Docker - ms-dashboard-postgres":["ms-dashboard"],
    # ---- MS-AUTOMATIZAR ----
    "Docker - ms-automatizar-mongodb":  ["ms-automatizar"],
    "Docker - ms-automatizar-redis":    ["ms-automatizar"],
    "Docker - ms-automatizar-whatsapp": ["ms-automatizar"],
    # ---- INFRA (servidor) ----
    "Docker - caddy-proxy":     ["infra"],
    "Docker - uptime-kuma":               ["infra"],
    "Uptime Kuma (interno)":              ["infra"],
    "Docker - netdata":                   ["infra"],
    "Netdata (interno)":                  ["infra"],
    "Docker - openclaw-gateway-1": ["infra"],
    "OpenClaw Gateway (HTTP)":            ["infra"],
    # ---- SERVIÇOS (aplicações) ----
    "Docker - vaultwarden": ["servicos"],
    "Vaultwarden (interno)":       ["servicos"],
    "Docker - stirling-pdf":       ["servicos"],
    "Stirling-PDF (interno)":      ["servicos"],
    "Docker - searxng":            ["servicos"],
    "SearXNG (interno)":           ["servicos"],
    "Docker - homeassistant":      ["servicos"],
    "Home Assistant (interno)":    ["servicos"],
    # ---- SITES (externos) ----
    "Site pessoal - SEU_DOMINIO.com": ["sites"],
    "Site empresa - msservicos.com": ["sites"],
}

# ---------- 1. Criar tags (idempotente) ----------
tags_existentes = {t["name"]: t for t in api.get_tags()}
tag_ids = {}

for t in TAGS:
    if t["name"] in tags_existentes:
        tag_ids[t["name"]] = tags_existentes[t["name"]]["id"]
        print(f"⏭️  Tag já existe: {t['name']} (id={tag_ids[t['name']]})")
    else:
        try:
            novo = api.add_tag(name=t["name"], color=t["color"])
            # add_tag retorna dict com o id
            tid = novo.get("id") or novo.get("tagID")
            if not tid:
                # re-busca
                time.sleep(0.5)
                for tg in api.get_tags():
                    if tg["name"] == t["name"]:
                        tid = tg["id"]
                        break
            tag_ids[t["name"]] = tid
            print(f"✅ Tag criada: {t['name']} (id={tid})")
        except Exception as e:
            print(f"❌ Tag {t['name']}: {e}")
    time.sleep(0.3)

# ---------- 2. Vincular tags aos monitores (idempotente) ----------
monitores = {m["name"]: m for m in api.get_monitors()}
print(f"\nMonitores atuais: {len(monitores)}")

# Para checar vínculos existentes, olha o campo 'tags' de cada monitor
def tags_do_monitor(m):
    return [t.get("id") for t in (m.get("tags") or [])]

aplicados = 0
for nome_mon, lista_tags in MONITOR_TAGS.items():
    if nome_mon not in monitores:
        print(f"⚠️  Monitor não encontrado: {nome_mon}")
        continue
    m = monitores[nome_mon]
    atuais = tags_do_monitor(m)
    for tag_nome in lista_tags:
        tid = tag_ids.get(tag_nome)
        if not tid:
            print(f"⚠️  Sem id para tag {tag_nome}")
            continue
        if tid in atuais:
            print(f"⏭️  [{nome_mon}] já tem tag {tag_nome}")
        else:
            try:
                api.add_monitor_tag(tag_id=tid, monitor_id=m["id"])
                print(f"✅ [{nome_mon}] + tag {tag_nome}")
                aplicados += 1
            except Exception as e:
                print(f"❌ [{nome_mon}] + {tag_nome}: {e}")
            time.sleep(0.3)

# ---------- 3. Resumo ----------
print("\n=== RESUMO FINAL ===")
tags_agora = api.get_tags()
print(f"Tags existentes ({len(tags_agora)}):")
for t in tags_agora:
    print(f"  [{t['id']}] {t['name']} {t.get('color')}")

print(f"\nVínculos aplicados agora: {aplicados}")
monitores = api.get_monitors()
for m in sorted(monitores, key=lambda x: x['id']):
    tg = [t['name'] for t in (m.get('tags') or [])]
    if tg:
        print(f"  {m['name']}: {tg}")

api.disconnect()
print("\n✅ Concluído!")
