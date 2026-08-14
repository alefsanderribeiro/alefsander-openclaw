# OpenClaw Custom — Docker

OpenClaw personalizado em Docker com ferramentas locais integradas:
Whisper (transcrição de áudio), PDF/OCR, Browser automation, ffmpeg,
GitHub CLI, Bitwarden CLI, integrações self-hosted (SearXNG, Home
Assistant, Uptime Kuma/Netdata) e 4 agentes pré-configurados.

> Este repositório é o **setup de referência** — espelha a instalação
> real em produção. Use-o para reproduzir o ambiente em outra máquina.

## O que vem pronto

| Componente | Descrição |
|---|---|
| **4 agentes** | `main` (orquestrador), `dev` (programação), `extrator` (produtos e-commerce), `orion` (LinkedIn/carreira) |
| **Plugins** | telegram, whatsapp, opencode/opencode-go (modelos), google (Gemini), searxng (busca), memory-core (dreaming), memory-wiki, workboard, openclaw-google-workspace, browser |
| **Skills custom** | `home-assistant-rest` (controlar HA via REST/WebSocket/Assist), `monitorador-de-servidor` (Uptime Kuma + Netdata) |
| **Scripts** | extrator de produtos ML, indexador de arquivos (MEGA), coletor PNCP, diagrama de licitações, docs do ML, sync WhatsApp |
| **Tools** | proxy TLS para Vaultwarden (`tools/bwproxy`), scripts de monitoramento Kuma (`tools/kuma-api`) |
| **Imagem** | Node 24 + Debian, Whisper (CUDA), ffmpeg, Chromium, Tesseract OCR, poppler, ripgrep, sqlite3, gh, bw |

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- Bash v4+ (macOS: `brew install bash`)
- 2 GB+ RAM disponível
- Chaves de API: **opencode-go** (modelos principais) e/ou Gemini/OpenAI/Anthropic
- [Tailscale](https://tailscale.com/download) (opcional, acesso remoto)

## Quick Start

```bash
# 1. Clone
git clone https://github.com/alefsanderribeiro/alefsander-openclaw.git
cd alefsander-openclaw

# 2. Configure o ambiente
cp .env.example .env
nano .env   # Chaves de API, canais, integrações

# 3. Instale a configuração de exemplo (sem segredos)
cp openclaw.json.example ~/.openclaw/openclaw.json
nano ~/.openclaw/openclaw.json   # ajuste agentes/canais

# 4. Rode o setup
chmod +x docker-setup.sh
./docker-setup.sh
```

O script vai:
- Verificar dependências (docker, compose)
- Criar a rede externa (se `OPENCLAW_NETWORK` definida)
- Buildar a imagem Docker customizada
- Gerar token/senha de gateway (se vazio)
- Rodar o onboarding interativo (pule com `OPENCLAW_SKIP_ONBOARDING=1`)
- Iniciar o gateway

Acesse a Control UI: **http://localhost:18789/**

### Instalação sem onboarding (config já pronta)

Se você já copiou o `openclaw.json.example` e preencheu o `.env`:

```bash
OPENCLAW_SKIP_ONBOARDING=1 ./docker-setup.sh
```

---

## Integrações self-hosted (rede Docker)

O container conecta a uma **rede Docker externa** (`OPENCLAW_NETWORK`)
para acessar serviços self-hosted pelo nome:

| Serviço | Hostname no container | Uso |
|---|---|---|
| **SearXNG** | `http://searxng:8080` | Busca web privada (provider do `web_search`) |
| **Home Assistant** | `http://homeassistant:8123` | Controle da casa (skill home-assistant-rest) |
| **Vaultwarden** | `http://vaultwarden:80` | Senhas compartilhadas (bw CLI via proxy TLS) |
| **Uptime Kuma** | `http://uptime-kuma:3001` | Monitoramento (scripts em tools/kuma-api) |
| **Netdata** | `http://netdata:19999` | Métricas do servidor |

```bash
# Crie a rede uma única vez
docker network create vaultwarden_tailscale-net

# Depois conecte os containers dos serviços a ela (ex:)
docker network connect vaultwarden_tailscale-net searxng
```

Se a rede não existir, o `docker-setup.sh` cria. Deixe
`OPENCLAW_NETWORK=` vazio no `.env` para pular.

---

## Agentes

Configuração em `agents/` (arquivos de identidade/instruções) +
definição em `openclaw.json` (`agents.list`).

| Agente | Função | Workspace |
|---|---|---|
| **main** | Orquestrador — conversa com você, delega tarefas | `~/.openclaw/workspace` |
| **dev** 💻 | Programação, testes, debugging, automação | `~/.openclaw/agents/dev/workspace` |
| **extrator** 🔍 | Extração de produtos (ML, Amazon, Shopee) — retorna JSON, nunca envia msg | `~/.openclaw/agents/extrator/workspace` |
| **orion** 🌌 | LinkedIn, vagas, candidaturas, posts | `~/.openclaw/agents/orion/workspace` |

Instale os workspaces dos agentes:

```bash
mkdir -p ~/.openclaw/agents
cp -r agents/* ~/.openclaw/agents/
```

---

## Scripts (`Scripts/`)

> 📁 **Instalação:** copie a pasta para o workspace do agente main para os
> imports internos funcionarem (`from Scripts.db_produtos import ...`):
> `cp -r Scripts ~/.openclaw/workspace/`

| Script | Função |
|---|---|
| `extrator_ml.py` | Extrai dados de produtos do Mercado Livre (título, preço, imagem) via link de afiliado |
| `indexador.py` | Indexa arquivos (ex: MEGA Drive) em SQLite para busca |
| `db_produtos.py` | Módulo de banco SQLite de produtos |
| `consulta_produto.py` | Consulta produtos (código, últimos, busca, stats) |
| `ml_token.py` | Gerencia access token da API do ML (refresh automático) |
| `crawl_ml_docs.py` | Crawl da documentação do ML para markdown local |
| `coletor_pncp_*.py` | Coleta de dados PNCP (licitações) |
| `confrontar_schema.py` | Confronto de schemas PNCP |
| `gerar_diagrama_licitacoes.py` | Gera diagrama de licitações |
| `cdp_shot.js` | Screenshot via Chrome DevTools Protocol |
| `wacli-sync.sh` | Sync das contas WhatsApp (wacli) — requer o binário `wacli` |

As credenciais dos scripts ficam em `~/.openclaw/secrets/` (nunca no repo).

---

## Tools (`tools/`)

### bwproxy — Proxy TLS para Vaultwarden

O bw CLI 2026+ exige HTTPS e não resolve domínios públicos dentro do
container. `proxy.py` escuta `https://localhost:8443` e encaminha para
`http://vaultwarden:80`.

```bash
# 1. Gere o certificado (uma vez)
mkdir -p ~/.openclaw/workspace/.bwproxy
cd ~/.openclaw/workspace/.bwproxy
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 3650 \
  -subj "/CN=localhost"

# 2. Rode o proxy (em background)
python3 proxy.py &

# 3. Use o bw CLI
export NODE_TLS_REJECT_UNAUTHORIZED=0
bw config server https://localhost:8443
bw login SEU_EMAIL --passwordenv BW_PASSWORD
```

### kuma-api — Scripts do Uptime Kuma

Criação/correção de monitores e alertas Telegram via API do Kuma.
Credenciais em `~/.openclaw/secrets/kuma-credentials`:

```
KUMA_URL=https://health.seu-dominio.com
KUMA_USER=admin
KUMA_PASSWORD=***
TELEGRAM_BOT_TOKEN=***
TELEGRAM_CHAT_ID=***
```

---

## Ferramentas Incluídas na Imagem

| Ferramenta | Uso |
|---|---|
| **Whisper** (openai-whisper) | Transcrição de áudio local (sem custo de API) |
| **PyTorch + CUDA** | GPU acceleration para Whisper e ML local |
| **pdftotext** (poppler-utils) | Extrair texto de PDFs |
| **Tesseract OCR** | OCR para PDFs escaneados e imagens |
| **ffmpeg + sox** | Processamento de áudio/vídeo |
| **Chromium** | Browser automation (Playwright) |
| **gh** (GitHub CLI) | Repos, issues, PRs, automação |
| **bw** (Bitwarden CLI) | Acesso ao Vaultwarden (senhas) |
| **ripgrep** | Busca rápida em arquivos |
| **sqlite3** | Banco local (produtos, catálogo) |
| **nano, vim, htop, tmux, tree, jq** | Utilitários |
| **python3 + pip + sudo NOPASSWD** | Instalar skills/pacotes em runtime |

### Modelos Whisper

| Modelo | Tamanho | Uso |
|---|---|---|
| `tiny` | 39 MB | Rápido, menos preciso |
| `base` | 74 MB | **Padrão** — bom equilíbrio |
| `small` | 244 MB | Boa precisão |
| `medium` | 769 MB | Alta precisão |
| `large` | 1550 MB | Máxima precisão |

Troque com `WHISPER_MODEL` no `.env` ou baixe manualmente:
`docker compose exec gateway python3 -c "import whisper; whisper.load_model('small')"`

---

## Comandos Úteis

```bash
# Gateway
docker compose up -d                  # iniciar
docker compose logs -f gateway        # logs
docker compose exec gateway nvidia-smi  # GPU

# CLI interativo
docker compose run --rm cli onboard          # onboarding
docker compose run --rm cli doctor           # diagnóstico
docker compose run --rm cli channels login   # WhatsApp QR code

# Canais
docker compose run --rm cli channels add --channel telegram --token "SEU_TOKEN"

# Update
docker compose build --no-cache && docker compose down && docker compose up -d
```

---

## Segurança

### O que o agente PODE fazer:

- Ler/escrever em `/home/node/.openclaw/workspace`
- Acessar diretórios montados via `OPENCLAW_EXTRA_MOUNTS` / `OPENCLAW_DOCS_MOUNT`
- Acessar a internet (URLs, APIs)
- Instalar pacotes dentro do container (`sudo apt`, `sudo pip3`, `npm`)

### O que o agente NÃO PODE fazer:

- Acessar arquivos do host que não estão montados
- Executar comandos no servidor/host
- Escalonar privilégios no host (container isolado)
- Criar/destruir containers no host (Docker socket é `:ro`)
- Acessar `/etc`, `/root`, `/var` do host

### Hardening aplicado:

- Container roda como usuário `node` (não root)
- Filesystem read-only (exceto volumes montados e `/tmp`)
- Capacidades Linux removidas (exceto mínimas necessárias)
- Auth por senha/token no gateway + rate limiting

### ⚠️ Nunca commite segredos

- `.env` está no `.gitignore`
- `openclaw.json` real tem chaves — use o `.example` com `${VAR}`
- Credenciais de scripts vivem em `~/.openclaw/secrets/` (fora do repo)

---

## Estrutura de Arquivos

```
alefsander-openclaw/
├── Dockerfile              # Imagem custom (Debian + Node 24 + ferramentas)
├── docker-compose.yml      # Gateway + CLI + rede externa + hardening
├── .env.example            # Todas as variáveis documentadas
├── openclaw.json.example   # Config espelhando a instalação real (sem segredos)
├── docker-setup.sh         # Setup automatizado (build, rede, onboarding)
├── agents/                 # Workspaces base dos agentes (dev, extrator, orion)
├── Scripts/                # Scripts de automação (ML, indexador, PNCP, wacli)
├── skills/                 # Skills custom (home-assistant-rest, monitorador)
├── tools/                  # bwproxy (Vaultwarden), kuma-api (monitoramento)
└── README.md
```

### Diretórios no Host

```
~/.openclaw/
├── openclaw.json           # Configuração principal
├── workspace/              # Área de trabalho do agente main
├── agents/                 # Workspaces dos subagentes (dev, extrator, orion)
├── skills/                 # Skills instaladas
├── memory/                 # Memória de conversas
├── plugins/                # Plugins instalados
├── secrets/                # Credenciais (NUNCA no git)
└── wiki/                   # Wiki (plugin memory-wiki)
```

---

## Troubleshooting

### Gateway não inicia

```bash
docker compose logs gateway
ss -tlnp | grep 18789
```

### Rede externa não acessa serviços

```bash
# Verifique se o container está na rede
docker network inspect vaultwarden_tailscale-net | grep -A2 openclaw

# Teste resolução de nome
docker compose exec gateway getent hosts searxng
```

### Permissão negada nos volumes

```bash
sudo chown -R 1000:1000 ~/.openclaw
```

### Whisper não encontra modelo

```bash
docker compose exec gateway ls ~/.cache/whisper/
docker compose exec gateway python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### DNS não funciona no CLI (Docker Desktop)

```bash
printf '%s\n' 'services:' '  cli:' '    cap_drop: !reset []' \
  > docker-compose.cli-no-dropped-caps.local.yml
docker compose -f docker-compose.yml -f docker-compose.cli-no-dropped-caps.local.yml run --rm cli <comando>
```

---

## Links

- [Documentação oficial do OpenClaw](https://docs.openclaw.ai/)
- [GitHub do OpenClaw](https://github.com/openclaw/openclaw)
- [Discord da comunidade](https://discord.gg/clawd)
