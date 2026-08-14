# 🔌 Integrações Self-Hosted

O container do OpenClaw conecta a uma **rede Docker externa**
(`OPENCLAW_NETWORK` no `.env`) para acessar serviços self-hosted pelo nome.
Essa é a base de todas as integrações:

```bash
# Crie a rede uma única vez (o docker-setup.sh faz isso automaticamente)
docker network create selfhosted-net

# Conecte os serviços à rede (exemplos)
docker network connect selfhosted-net searxng
docker network connect selfhosted-net homeassistant
```

| Serviço | Hostname no container | Uso |
|---|---|---|
| **SearXNG** | `http://searxng:8080` | Busca web privada (provider do `web_search`) |
| **Home Assistant** | `http://homeassistant:8123` | Controle da casa (skill home-assistant-rest) |
| **Vaultwarden** | `http://vaultwarden:80` | Senhas compartilhadas (bw CLI via proxy TLS) |
| **Uptime Kuma** | `http://uptime-kuma:3001` | Monitoramento (tools/kuma-api) |
| **Netdata** | `http://netdata:19999` | Métricas do servidor |

---

## 🔍 SearXNG — Busca web privada

Metabusca self-hosted (Google, Bing, Brave, GitHub, npm, PyPI...). Substitui o
DuckDuckGo no `web_search` (que bloqueava com bot-detection).

**Configuração (openclaw.json):**

```json
"plugins": {
  "entries": {
    "searxng": {
      "enabled": true,
      "config": { "webSearch": { "baseUrl": "http://searxng:8080" } }
    }
  }
},
"tools": { "web": { "search": { "provider": "searxng", "enabled": true } } }
```

**Teste rápido:**

```bash
curl 'http://searxng:8080/search?q=teste&format=json'
```

---

## 🏠 Home Assistant — Casa automatizada

Skill `home-assistant-rest` com 3 camadas (todas com o mesmo token LLAT):

1. **REST API oficial** — estados, serviços, eventos, histórico, câmera
2. **WebSocket API** — registries, zonas, automações, dashboards
3. **Assist (Conversation)** — linguagem natural (NLU do HA)

**Configuração:**

```bash
export HOME_ASSISTANT_URL=http://homeassistant:8123
export HOME_ASSISTANT_TOKEN=<LLAT gerado no perfil do usuário>
```

**Exemplos:**

```bash
# REST direto
curl -H "Authorization: Bearer $HOME_ASSISTANT_TOKEN" \
     "$HOME_ASSISTANT_URL/api/states"

# Assist em linguagem natural
curl -X POST -H "Authorization: Bearer $HOME_ASSISTANT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"text": "apaga a luz da sala"}' \
     "$HOME_ASSISTANT_URL/api/conversation/process"
```

> ⚠️ Prefira **usuário restrito (non-admin)** para o token do agente.

---

## 🔐 Vaultwarden — Senhas compartilhadas

Cada agente tem **seu próprio usuário** no Vaultwarden e vê **só o que foi
compartilhado com ele** (organização `openclaw-agents`). O bw CLI 2026 exige
HTTPS e não resolve domínios públicos no container → usa o **proxy TLS local**
(`tools/bwproxy`).

```bash
# 1. Proxy (uma vez): gera cert + sobe
cd ~/.openclaw/workspace/.bwproxy && openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 3650 -subj "/CN=localhost"
python3 proxy.py &

# 2. Uso
export NODE_TLS_REJECT_UNAUTHORIZED=0
export BW_SESSION=$(bw unlock --passwordenv BW_PASSWORD --raw)
bw sync --session "$BW_SESSION"
bw get item "www.linkedin.com" --session "$BW_SESSION"
```

> ⚠️ Lições: email com case exato importa (é o salt do hash); 5+ tentativas
> falhas → IP bloqueado ~10 min; senhas sempre via `--passwordenv`.

---

## 📊 Uptime Kuma + Netdata — Monitoramento

**Kuma** = disponibilidade ("está no ar?") · **Netdata** = saúde ("está lento? por quê?").
Alertas Telegram em todos os monitores via bot.

Scripts em `tools/kuma-api/` (criação de monitores, alertas, diagnósticos).
Credenciais em `~/.openclaw/secrets/kuma-credentials`:

```
KUMA_URL=https://health.seu-dominio.com
KUMA_USER=admin
KUMA_PASSWORD=***
TELEGRAM_BOT_TOKEN=***
TELEGRAM_CHAT_ID=***
```

Skill `monitorador-de-servidor` documenta o procedimento completo de deploy.

---

## 📧 Google Workspace — Gmail/Calendar/Drive

Plugin `openclaw-google-workspace` com OAuth (Desktop Client):

- Gmail: busca, leitura, envio
- Calendar: eventos, reuniões
- Drive: listar/buscar/ler (read-only)
- Contacts / Tasks / Sheets

**Configuração:** credenciais OAuth em `~/.openclaw/secrets/gmail-credentials.json`
e tokens em `~/.openclaw/secrets/gmail-tokens.json` (auto-refresh).

---

## 🗨️ Canais de mensagem

- **Telegram:** bot token + allowlist de usuários
- **WhatsApp:** QR code via `channels login` (múltiplas contas — Aura e Alef)
- **WebChat:** Control UI do gateway

## 🧠 Memória e conhecimento

- **memory-core:** memória de longo prazo + daily notes + dreaming (resumo noturno automático)
- **memory-wiki:** wiki compilada a partir da memória (vault bridge)
- **workboard:** quadro de tarefas para trabalho organizado
