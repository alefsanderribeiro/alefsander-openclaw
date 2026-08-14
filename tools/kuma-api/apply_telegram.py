#!/usr/bin/env python3
"""Garante que a notificação Telegram está ligada em todos os monitores."""
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

notif_id = 1
monitors = api.get_monitors()
print(f"Monitores: {len(monitors)}")
sem = []
com = 0
for m in monitors:
    nids = m.get("notificationIDList") or []
    if notif_id in nids:
        com += 1
    else:
        sem.append(m)

print(f"  Com Telegram ligado: {com}")
print(f"  Sem Telegram: {len(sem)}")

# Aplicar nos que não têm
if sem:
    print("\nAplicando Telegram nos monitores sem notificação...")
    for m in sem:
        try:
            nids = (m.get("notificationIDList") or []) + [notif_id]
            api.edit_monitor(m["id"], **{"notificationIDList": nids})
            print(f"  ✅ {m['name']}")
        except Exception as e:
            print(f"  ❌ {m['name']}: {e}")
        time.sleep(0.3)

# Verificar final
print("\n=== Verificação final ===")
total_com = 0
for m in api.get_monitors():
    if notif_id in (m.get("notificationIDList") or []):
        total_com += 1
print(f"Monitores com alerta Telegram: {total_com}/{len(monitors)}")
api.disconnect()
