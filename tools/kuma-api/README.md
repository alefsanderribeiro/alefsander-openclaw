# kuma-api — Scripts do Uptime Kuma

Scripts Python para criar/corrigir monitores e configurar alertas
Telegram no [Uptime Kuma](https://github.com/louislam/uptime-kuma)
via API (lib `uptime-kuma-api-v2`).

## Credenciais

Todos os scripts leem `~/.openclaw/secrets/kuma-credentials`
(formato `CHAVE=valor`, uma por linha):

```
KUMA_URL=https://health.seu-dominio.com
KUMA_USER=admin
KUMA_PASSWORD=***
TELEGRAM_BOT_TOKEN=***
TELEGRAM_CHAT_ID=***
```

Copie o modelo: `cp kuma-credentials.example ~/.openclaw/secrets/kuma-credentials`

## Scripts

| Script | Função |
|---|---|
| `setup_monitors.py` | Cria os monitores principais |
| `setup_docker_monitors.py` | Cria monitores de containers Docker |
| `add_monitores_faltantes.py` | Adiciona monitores que faltam (idempotente) |
| `add_searxng_monitors.py` | Monitores específicos do SearXNG |
| `fix_monitors.py` | Corrige monitores existentes |
| `setup_telegram.py` / `apply_telegram.py` | Cria/aplica notificações Telegram |
| `check_telegram.py` / `test_telegram*.py` / `verify_telegram.py` | Diagnóstico dos alertas |
| `debug_notif.py` | Debug de notificações |
| `organizar_tags.py` | Organiza tags dos monitores |

## Dependência

```bash
python3 -m venv .venv
.venv/bin/pip install uptime-kuma-api-v2
```

(O `.venv/` está no `.gitignore`.)
