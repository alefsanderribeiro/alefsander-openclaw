#!/usr/bin/env python3
"""Debug: ver notificationIDList real."""
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
m = api.get_monitor(1)
print("Monitor 1 keys com 'notif':")
for k in m.keys():
    if 'notif' in k.lower():
        print(f"  {k} = {m[k]}")
print("\nFull notificationIDList:", m.get("notificationIDList"))
# ver como o Kuma chama o campo - talvez nao seja notificationIDList
print("\nTodos os campos do monitor:")
for k in sorted(m.keys()):
    print(f"  {k}")
api.disconnect()
