# TOOLS.md — Orion

## Playwright / Browser Automation

- **Skill:** `browser-automation` (carregada — use o `browser` tool do OpenClaw)
- **Scripts legado:** `/home/node/.openclaw/agents/orion/workspace/scripts/`

### Método Preferido: browser tool

Use o `browser` tool do OpenClaw para navegação automatizada. Ele já gerencia:
- Perfil sandbox (isolado) ou user (navegador logado)
- Snapshots com acessibilidade (refs)
- Screenshots
- Ações: click, type, navigate, etc.

### Método Legado: Playwright direto

Se precisar rodar scripts Playwright diretamente:
- **Binário:** Chromium via Playwright
- **Browsers path:** `/home/node/.openclaw/workspace/ms-playwright`
- **Comando base:**
  ```bash
  cd /home/node/.openclaw/workspace
  PLAYWRIGHT_BROWSERS_PATH=/home/node/.openclaw/workspace/ms-playwright node script.js
  ```

### Scripts Existentes

| Script | Função |
|--------|--------|
| `scripts/linkedin-login.js` | Login no LinkedIn |
| `scripts/linkedin-session.js` | Gerenciar sessão salva |

## Vaultwarden / Bitwarden CLI

- **Wrapper bw:** `/home/node/.openclaw/workspace/bw` (instalado via npm)
- **Versão:** 2026.6.0
- **Config:** `/home/node/.openclaw/secrets/bw-orion-config/Bitwarden CLI/data.json`
- **Variável:** `BW_AGENT=orion` (sempre usar)
- **URL servidor (interno):** `https://localhost:8443` (via proxy TLS local — ver abaixo)
- **URL pública (NÃO resolve no container):** `https://vaultwarden.SEU_DOMINIO.com` (ENOTFOUND)
- **Org:** `openclaw-agents` (compartilhada pelo Alef)

> ⚠️ O wrapper `bw` em `/home/node/.openclaw/workspace/bw` já configura o `XDG_CONFIG_HOME` automaticamente para cada agente. Basta usar `BW_AGENT=orion`.

### ⚠️ Proxy TLS local (OBRIGATÓRIO desde 09/08/2026)

O bw CLI 2026.6.0 **bloqueia HTTP** (exige HTTPS) e o domínio público não resolve dentro do container Docker. Solução: proxy TLS local que escuta em `https://localhost:8443` e encaminha pro `http://vaultwarden` (vaultwarden:80, rede docker).

```bash
# 1. Subir o proxy (se não estiver rodando)
python3 ~/.openclaw/workspace/.bwproxy/proxy.py &

# 2. Sempre exportar antes de usar o bw:
export NODE_TLS_REJECT_UNAUTHORIZED=0
```

Arquivos em `~/.openclaw/workspace/.bwproxy/` (cert.pem, key.pem, proxy.py, orion_login.sh).

### Setup Inicial (se precisar refazer)

```bash
# Configurar servidor (só na primeira vez) — URL do proxy local, NÃO a pública
NODE_TLS_REJECT_UNAUTHORIZED=0 BW_AGENT=orion /home/node/.openclaw/workspace/bw config server https://localhost:8443
```

### Como pegar credencial

> ⚠️ Sempre usar `--passwordenv BW_PASSWORD` pra evitar prompt interativo · sempre com `NODE_TLS_REJECT_UNAUTHORIZED=0`

```bash
# 0. Garantir proxy TLS rodando
pgrep -f bwproxy/proxy.py || python3 ~/.openclaw/workspace/.bwproxy/proxy.py &
export NODE_TLS_REJECT_UNAUTHORIZED=0

# 1. Exportar senha e desbloquear
export BW_PASSWORD="***"
export BW_SESSION=$(BW_AGENT=orion /home/node/.openclaw/workspace/bw unlock --passwordenv BW_PASSWORD --raw)

# 2. Sync (sempre antes de listar)
BW_AGENT=orion /home/node/.openclaw/workspace/bw sync --session "$BW_SESSION"

# 3. Pegar credencial pelo nome
BW_AGENT=orion /home/node/.openclaw/workspace/bw get item "www.linkedin.com" --session "$BW_SESSION"
```

### Extrair usuário e senha rápido

```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
export BW_PASSWORD="***"
export BW_SESSION=$(BW_AGENT=orion /home/node/.openclaw/workspace/bw unlock --passwordenv BW_PASSWORD --raw)

BW_AGENT=orion /home/node/.openclaw/workspace/bw get item "www.linkedin.com" --session "$BW_SESSION" | \
  python3 -c "import json,sys; d=json.load(sys.stdin)['login']; print(f'User: {d[\"username\"]}'); print(f'Pass: {d[\"password\"]}')"
```

### Comandos Úteis

```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
# Listar organizações
export BW_SESSION=$(BW_AGENT=orion /home/node/.openclaw/workspace/bw unlock --passwordenv BW_PASSWORD --raw)
BW_AGENT=orion /home/node/.openclaw/workspace/bw list organizations --session "$BW_SESSION"

# Listar itens do cofre (incluindo da org)
BW_AGENT=orion /home/node/.openclaw/workspace/bw list items --session "$BW_SESSION"

# Forçar sync
BW_AGENT=orion /home/node/.openclaw/workspace/bw sync --session "$BW_SESSION"
```

### Dados da Conta

| Campo | Valor |
|-------|-------|
| Email | `COLOQUE_O_EMAIL_DO_COFRE_AQUI` (ex: seu-usuario+orion@gmail.com) |
| Senha | `COLOQUE_A_SENHA_AQUI` (definida via env `BW_PASSWORD` — nunca em texto puro) |
| Servidor | `https://localhost:8443` (proxy TLS local) |
| Acesso | LinkedIn e outras creds de trabalho via org `openclaw-agents` |

### ⚠️ Lições (09/08/2026)

- **Email com case exato importa:** o email é o *salt* do hash da senha — `+Aura` ≠ `+aura`. Sempre usar o email exato da conta.
- **Rate limit:** 5+ tentativas falhas → IP bloqueado ~10 min → TUDO retorna "incorrect" mesmo com senha certa. Se falhar 2-3x, PARAR e esperar.
- **Cada agente busca a própria senha na org compartilhada** — Orion vê `www.linkedin.com` (com TOTP); Aura vê `accounts.google.com`. Nunca tentar item de outro agente sem compartilhamento.
- **Extração de senha:** usar variável de ambiente (BW_PASSWORD), nunca grep/sed de arquivos.

## WhatsApp — Falar com o Alef

- **Número do Alef:** COLOQUE_O_NUMERO_AQUI (placeholder — preencher no setup local)
- **Store Aura:** `/home/node/.openclaw/workspace/.wacli-store-aura`
- **Comando pra mandar mensagem direta pra ele:**
  ```bash
  wacli --store .wacli-store-aura send text --to "COLOQUE_O_NUMERO_AQUI" --message "Mensagem aqui"
  ```

## Pastas

- `secrets/` — Sessões salvas do LinkedIn
  - `linkedin-session.json` — Cookies + localStorage
- `imagens/` — Screenshots capturados
- `memory/` — Notas diárias
- `scripts/` — Scripts Playwright

> ⚠️ Credenciais nunca ficam em secrets/. Sempre vêm do Vaultwarden.
