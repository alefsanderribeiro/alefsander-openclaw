# OpenClaw Custom — Docker

OpenClaw personalizado em Docker com ferramentas locais integradas:
Whisper (transcrição de áudio), PDF/OCR, Browser automation, ffmpeg, e mais.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- Bash v4+ (macOS: `brew install bash`)
- 2 GB+ RAM disponível
- Pelo menos uma chave de API de IA (Anthropic, OpenAI, Gemini, etc.)

## Quick Start

### 1. Clone o repositório

```bash
git clone https://github.com/alefsanderribeiro/alefsander-openclaw.git
cd alefsander-openclaw
```

### 2. Configure o ambiente

```bash
cp .env.example .env
nano .env  # Edite com suas chaves de API
```

### 3. Rode o setup

```bash
chmod +x docker-setup.sh
./docker-setup.sh
```

O script vai:
- Buildar a imagem Docker customizada
- Gerar um token de gateway seguro
- Rodar o onboarding interativo
- Iniciar o gateway

### 4. Acesse

Abra no navegador: **http://127.0.0.1:18789/**

---

## Setup Manual (sem script)

Se preferir controle total sem o script:

```bash
# 1. Copie e edite o .env
cp .env.example .env
nano .env

# 2. Gere um token de gateway
openssl rand -hex 32
# Cole o resultado no .env como OPENCLAW_GATEWAY_TOKEN=...

# 3. Build da imagem
docker compose build

# 4. Onboarding
docker compose run --rm cli onboard --no-install-daemon

# 5. Inicie o gateway
docker compose up -d
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
| **nano, vim** | Editores de texto no container |
| **git, curl, jq** | Utilitários de desenvolvimento |
| **htop, tmux** | Monitoramento e sessões |
| **python3 + pip** | Para instalar skills Python |
| **sudo (NOPASSWD)** | Instalar pacotes em runtime |

### Sobre o Whisper

O [Whisper](https://github.com/openai/whisper) (openai-whisper) e um sistema de
reconhecimento de fala open-source da OpenAI. Ele roda 100% localmente no container
— sem enviar audio para servidores externos, sem custo de API.
Suporta multiplos idiomas (inclusive portugues) e faz transcreicao de audio e video
para texto com alta precisao.

O Whisper usa **PyTorch** com aceleracao GPU via CUDA (se disponivel). Se nao
houver GPU, ele roda em CPU automaticamente como fallback.

> GitHub: https://github.com/openai/whisper
> Documentacao oficial: https://github.com/openai/whisper#readme
### Modelos Whisper Disponíveis

| Modelo | Tamanho | RAM | Uso |
|---|---|---|---|
| `tiny` | 39 MB | ~1 GB | Rápido, menos preciso |
| `base` | 74 MB | ~1 GB | **Padrão** — bom equilíbrio |
| `small` | 244 MB | ~2 GB | Boa precisão |
| `medium` | 769 MB | ~5 GB | Alta precisão |
| `large` | 1550 MB | ~10 GB | Máxima precisão |

O modelo `base` é baixado na **primeira execução** e persistido automaticamente em `~/.openclaw/.cache/whisper/`.

Para trocar de modelo, basta usar o modelo desejado — ele será baixado e cacheado:

```bash
# Dentro do container, baixe outro modelo
docker compose exec gateway python3 -c "import whisper; whisper.load_model('small')"
```

---

## GPU NVIDIA — Setup

Se seu host tem GPU NVIDIA, o Whisper usará GPU automaticamente.

### Pré-requisitos no Host

```bash
# 1. Verifique se o driver NVIDIA está instalado
nvidia-smi

# 2. Instale o nvidia-container-toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's|deb |deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] |' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

# 3. Restart Docker
sudo systemctl restart docker

# 4. Verifique no container
docker compose exec gateway nvidia-smi
```

Se **não** tiver GPU NVIDIA, o Whisper roda em CPU automaticamente — não precisa configurar nada.

---

## Como Usar `OPENCLAW_EXTRA_MOUNTS`

Permite montar diretórios adicionais do host no container.

### Formato

```
host_path:container_path[:rw|ro]
```

- `rw` = leitura e escrita (padrão)
- `ro` = somente leitura

### Exemplos no `.env`

```bash
# Um único diretório
OPENCLAW_EXTRA_MOUNTS="/home/alefs/projetos:/home/node/projetos:rw"

# Múltiplos diretórios (separados por vírgula, sem espaços)
OPENCLAW_EXTRA_MOUNTS="/home/alefs/docs:/home/node/docs:ro,/home/alefs/data:/home/node/data:rw"

# Usando variáveis de ambiente
OPENCLAW_EXTRA_MOUNTS="$HOME/Projects:/home/node/projects:rw,$HOME/Downloads:/home/node/downloads:ro"
```

### Após alterar

```bash
docker compose down && docker compose up -d
```

### Verificar mounts

```bash
docker compose exec gateway ls -la /home/node/
```

---

## Comandos Úteis

### Gateway

```bash
# Iniciar
docker compose up -d

# Parar
docker compose down

# Ver logs em tempo real
docker compose logs -f gateway

# Verificar saúde
docker compose exec gateway node dist/index.js health --token "$OPENCLAW_GATEWAY_TOKEN"

# Reiniciar
docker compose restart

# Ver containers (prefixados com openclaw-alefe)
docker ps --filter name=openclaw-alefe
```

### CLI Interativo

```bash
# Abrir shell no container
docker compose run --rm cli

# Onboarding
docker compose run --rm cli onboard

# Ver configuração
docker compose run --rm cli config show

# Validar configuração
docker compose run --rm cli doctor

# Dashboard URL
docker compose run --rm cli dashboard --no-open
```

### Canais de Mensagem

```bash
# WhatsApp (QR code)
docker compose run --rm cli channels login

# Telegram
docker compose run --rm cli channels add --channel telegram --token "SEU_TOKEN"

# Discord
docker compose run --rm cli channels add --channel discord --token "SEU_TOKEN"
```

### Skills

```bash
# Listar skills instaladas
docker compose run --rm cli skills list

# Instalar skill do ClawHub
docker compose run --rm cli skills install <package>

# Instalar dependência Python no container (ex: Whisper)
docker compose exec gateway sudo pip3 install <package>

# Instalar pacote apt no container
docker compose exec gateway sudo apt update && sudo apt install -y <package>
```

### Update

```bash
# Pull nova imagem
docker compose pull

# Rebuild imagem custom
docker compose build --no-cache

# Restart
docker compose down && docker compose up -d
```

---

## Segurança

### O que o agente PODE fazer:

- Ler/escrever em `/home/node/.openclaw/workspace`
- Acessar diretórios montados via `OPENCLAW_EXTRA_MOUNTS`
- Acessar a internet (URLs, APIs)
- Instalar pacotes dentro do container (`sudo apt`, `sudo pip3`, `npm`)
- Executar comandos no container

### O que o agente NÃO PODE fazer:

- Acessar arquivos do host que não estão montados
- Executar comandos no servidor/host
- Escalonar privilégios no host (container isolado)
- Criar/destruir containers no host (Docker socket é `:ro`)
- Acessar `/etc`, `/root`, `/var` do host

### Hardening aplicado:

- Container roda como usuário `node` (não root)
- Filesystem read-only (exceto volumes montados e `/tmp`)
- `no-new-privileges` ativado
- Capacidades Linux removidas (exceto mínimas necessárias)
- Rate limiting contra brute force
- Token de gateway obrigatório para acesso não-loopback

---

## Estrutura de Containers

Todos os containers são agrupados sob o projeto `openclaw-alefe`:

```
$ docker ps --filter name=openclaw-alefe

CONTAINER ID   IMAGE                          NAMES
abc123         ghcr.io/alefsanderribeiro/alefsander-openclaw:latest     openclaw-alefe-gateway-1
```

## Estrutura de Arquivos

```
alefsander-openclaw/
├── Dockerfile              # Imagem custom (Debian + Node 24 + ferramentas)
├── docker-compose.yml      # Gateway + CLI com security hardening
├── .env.example            # Todas as variáveis documentadas
├── .env                    # Suas configurações (não commite!)
├── docker-setup.sh         # Script de setup automatizado
├── openclaw.json.example   # Configuração segura de exemplo
├── README.md               # Este arquivo
└── .gitignore
```

### Diretórios no Host

```
~/.openclaw/
├── openclaw.json           # Configuração principal
├── .env                    # Variáveis de ambiente
├── workspace/              # Área de trabalho do agente
├── skills/                 # Skills instaladas
├── memory/                 # Memória de conversas
├── plugins/                # Plugins instalados
└── agents/                 # Config por agente
```

---

## Troubleshooting

### Gateway não inicia

```bash
# Ver logs
docker compose logs gateway

# Verifique se a porta está em uso
ss -tlnp | grep 18789
```

### Token inválido

```bash
# Gere um novo token
openssl rand -hex 32

# Atualize no .env e restart
docker compose down && docker compose up -d
```

### Permissão negada nos volumes

```bash
# Corrija ownership (container roda como uid 1000)
sudo chown -R 1000:1000 ~/.openclaw
```

### Whisper não encontra modelo

```bash
# Verifique se o modelo está cacheado
docker compose exec gateway ls ~/.cache/whisper/

# Baixe manualmente outro modelo (ex: small)
docker compose exec gateway \
  python3 -c "import whisper; whisper.load_model('small')"

# Verifique se está usando GPU
docker compose exec gateway \
  python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"

# Forçar re-download (deleta cache e baixa de novo)
rm -rf ~/.openclaw/.cache/whisper/
docker compose exec gateway \
  python3 -c "import whisper; whisper.load_model('base')"
```

### GPU não é detectada

```bash
# Verifique no host
nvidia-smi

# Verifique no container
docker compose exec gateway nvidia-smi

# Se falhar, instale nvidia-container-toolkit no host (ver seção GPU NVIDIA acima)
```

### DNS não funciona no CLI

```bash
# Workaround para Docker Desktop
printf '%s\n' \
  'services:' \
  '  cli:' \
  '    cap_drop: !reset []' \
  > docker-compose.cli-no-dropped-caps.local.yml

docker compose -f docker-compose.yml -f docker-compose.cli-no-dropped-caps.local.yml \
  run --rm cli <comando>
```

---

## Links

- [Documentação oficial do OpenClaw](https://docs.openclaw.ai/)
- [GitHub do OpenClaw](https://github.com/openclaw/openclaw)
- [Discord da comunidade](https://discord.gg/clawd)
