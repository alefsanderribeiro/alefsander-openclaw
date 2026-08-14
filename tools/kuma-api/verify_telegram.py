#!/usr/bin/env python3
"""Verifica notificationIDList em todos os monitores individualmente."""
import os
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
monitors = api.get_monitors()
com = 0
sem = []
for m in monitors:
    nids = (m.get("notificationIDList") or [])
    if 1 in nids:
        com += 1
    else:
        sem.append(m.get("name"))
print(f"Com Telegram (notificationIDList contém 1): {com}/{len(monitors)}")
if sem:
    print("Sem Telegram:")
    for s in sem:
        print("  ", s)
api.disconnect()
