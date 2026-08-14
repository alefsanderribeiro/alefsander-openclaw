# bwproxy — Proxy TLS local para Vaultwarden

O **bw CLI** (Bitwarden CLI 2026+) **bloqueia HTTP** (exige HTTPS) e o
domínio público do Vaultwarden não resolve dentro do container Docker.
Este proxy escuta em `https://localhost:8443` e encaminha para
`http://vaultwarden:80` (rede Docker).

## Setup (uma vez)

```bash
# 1. Diretório e certificado auto-assinado
mkdir -p ~/.openclaw/workspace/.bwproxy
cd ~/.openclaw/workspace/.bwproxy
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 3650 \
  -subj "/CN=localhost"

# 2. Subir o proxy (em background)
python3 proxy.py &

# 3. Configurar o bw CLI para usar o proxy (só na primeira vez)
export NODE_TLS_REJECT_UNAUTHORIZED=0
bw config server https://localhost:8443
```

## Uso

```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
export BW_PASSWORD="SUA_SENHA"

# Desbloquear e sincronizar
export BW_SESSION=$(bw unlock --passwordenv BW_PASSWORD --raw)
bw sync --session "$BW_SESSION"

# Buscar credencial
bw get item "NOME_DO_ITEM" --session "$BW_SESSION"
```

## Notas

- O `cert.pem`/`key.pem` são gerados localmente (no `.gitignore`).
- `NODE_TLS_REJECT_UNAUTHORIZED=0` é necessário porque o certificado é auto-assinado.
- O proxy é idempotente: `pgrep -f bwproxy/proxy.py || python3 proxy.py &`
