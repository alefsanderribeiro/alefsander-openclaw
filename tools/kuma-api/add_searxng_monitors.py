#!/usr/bin/env python3
"""
Adiciona monitores do SearXNG no Uptime Kuma (idempotente).
- Docker: container searxng
- HTTP: https://search.SEU_DOMINIO.com
- SSL: search.SEU_DOMINIO.com
Aplica alerta Telegram (notif_id=1) nos monitores novos.
"""
import os, time

secrets = {}
with open(os.path.expanduser("~/.openclaw/secrets/kuma-credentials")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            secrets[k] = v

from uptime_kuma_api import UptimeKumaApi, MonitorType

api = UptimeKumaApi(secrets["KUMA_URL"])
api.login(secrets["KUMA_USER"], secrets["KUMA_PASSWORD"])
print("✅ Login OK")

NOTIF_ID = 1  # Telegram (padrão dos outros monitores)

# --- Monitores desejados para o SearXNG ---
alvos = [
    {"type": MonitorType.DOCKER, "name": "Docker - searxng",
     "kwargs": {"docker_container": "searxng", "interval": 60}},
    {"type": MonitorType.HTTP, "name": "SearXNG (HTTP)",
     "kwargs": {"url": "https://search.SEU_DOMINIO.com", "interval": 60,
                "accepted_statuscodes": ["200-299", "300-399"]}},
    {"type": MonitorType.HTTP, "name": "SSL - search.SEU_DOMINIO.com",
     "kwargs": {"url": "https://search.SEU_DOMINIO.com", "interval": 86400}},
]

monitors = api.get_monitors()
existentes = {m["name"]: m for m in monitors}
print(f"Monitores atuais: {len(monitors)}")

criados = []
ja_existiam = []
for alvo in alvos:
    nome = alvo["name"]
    if nome in existentes:
        ja_existiam.append(nome)
        print(f"⏭️  Já existe: {nome}")
        continue
    try:
        api.add_monitor(type=alvo["type"], name=nome, **alvo["kwargs"])
        criados.append(nome)
        print(f"✅ Criado: {nome}")
    except Exception as e:
        print(f"❌ {nome} -> {e}")
    time.sleep(0.5)

# --- Aplicar alerta Telegram nos novos ---
if criados:
    print("\nAplicando alerta Telegram...")
    for m in api.get_monitors():
        if m["name"] in criados:
            nids = (m.get("notificationIDList") or []) + [NOTIF_ID]
            try:
                api.edit_monitor(m["id"], **{"notificationIDList": nids})
                print(f"  ✅ Telegram ligado em: {m['name']}")
            except Exception as e:
                print(f"  ❌ Telegram em {m['name']}: {e}")
            time.sleep(0.3)

# --- Resumo ---
print("\n=== RESUMO ===")
print(f"Criados: {criados}")
print(f"Já existiam: {ja_existiam}")
monitors = api.get_monitors()
for m in monitors:
    if m["name"] in [a["name"] for a in alvos]:
        tg = "🔔 Telegram" if NOTIF_ID in (m.get("notificationIDList") or []) else "❌ sem Telegram"
        print(f"  {m['name']} (id={m['id']}) - {tg}")
api.disconnect()
print("\n✅ Concluído!")
