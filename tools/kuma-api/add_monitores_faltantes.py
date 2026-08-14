#!/usr/bin/env python3
"""
Adiciona monitores FALTANTES no Uptime Kuma (idempotente):
- Docker - atelie-web   (app de produção novo)
- HTTP atelie-web       (verificação de página)
- Docker - homeassistant       (tinha só HTTP)
- Docker - netdata             (tinha só HTTP)
Corrige: liga alerta Telegram (notif_id=1) no Home Assistant HTTP (id=29).
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

NOTIF_ID = 1  # Telegram
DOCKER_HOST = 1  # servidor-local (socket local)

alvos = [
    {"type": MonitorType.DOCKER, "name": "Docker - atelie-web",
     "kwargs": {"docker_container": "atelie-web", "docker_host": DOCKER_HOST, "interval": 60}},
    {"type": MonitorType.HTTP, "name": "Ateliê ERP (HTTP)",
     "kwargs": {"url": "https://atelie.SEU_DOMINIO.com/login", "interval": 60,
                "accepted_statuscodes": ["200-299", "300-399"]}},
    {"type": MonitorType.DOCKER, "name": "Docker - homeassistant",
     "kwargs": {"docker_container": "homeassistant", "docker_host": DOCKER_HOST, "interval": 60}},
    {"type": MonitorType.DOCKER, "name": "Docker - netdata",
     "kwargs": {"docker_container": "netdata", "docker_host": DOCKER_HOST, "interval": 60}},
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

# --- Aplicar alerta Telegram nos novos + corrigir Home Assistant HTTP ---
print("\nAplicando alerta Telegram...")
for m in api.get_monitors():
    nids = list(m.get("notificationIDList") or [])
    precisa = m["name"] in criados or m["id"] == 29  # 29 = Home Assistant HTTP
    if precisa and NOTIF_ID not in nids:
        try:
            api.edit_monitor(m["id"], **{"notificationIDList": nids + [NOTIF_ID]})
            print(f"  ✅ Telegram ligado em: {m['name']} (id={m['id']})")
        except Exception as e:
            print(f"  ❌ Telegram em {m['name']}: {e}")
        time.sleep(0.3)

# --- Resumo ---
print("\n=== RESUMO ===")
print(f"Criados: {criados}")
print(f"Já existiam: {ja_existiam}")
monitors = api.get_monitors()
nomes_alvo = [a["name"] for a in alvos] + ["Home Assistant (interno)"]
for m in monitors:
    if m["name"] in nomes_alvo:
        tg = "🔔 Telegram" if NOTIF_ID in (m.get("notificationIDList") or []) else "❌ sem Telegram"
        print(f"  {m['name']} (id={m['id']}) - {tg}")
api.disconnect()
print("\n✅ Concluído!")
