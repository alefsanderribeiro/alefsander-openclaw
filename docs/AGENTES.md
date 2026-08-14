# 🤖 Agentes

Este setup roda com **4 agentes de IA**: um principal (orquestrador) e três
subagentes especialistas. A arquitetura segue o princípio: *o main conversa com
você e delega trabalho especializado*.

```
Você (humano)
   │
   ▼
┌─────────┐   delega   ┌──────────┐
│  main   │ ─────────▶ │   dev    │  programação
│  (Aura) │            ├──────────┤
│         │            │ extrator │  produtos e-commerce
│         │            ├──────────┤
│         │            │  orion   │  LinkedIn/carreira
└─────────┘            └──────────┘
```

## main (Aura ✨) — Orquestradora

- **Função:** interface com o humano, gerencia canais (WhatsApp, Telegram, WebChat), decide quem faz o quê
- **Workspace:** `~/.openclaw/workspace`
- **Modelo:** DeepSeek V4 Flash (opencode-go) com fallback free
- **Skills ativas:** browser-automation, clawhub, github, google-workspace-assistant, healthcheck, home-assistant-rest, meme-maker, monitorador-de-servidor, openai-whisper, python-debugpy, skill-creator, spike, taskflow, tmux, video-frames, weather
- **Subagentes permitidos:** dev, extrator, orion

### Fluxo padrão de delegação

```text
1. Humano pede algo
2. Main avalia qual subagente é mais adequado
3. Spawn: sessions_spawn(agentId="...", task="...", context="fork")
4. Aguarda o resultado (sessions_yield)
5. Compila o resultado e entrega ao humano (resumo, não raw dump)
6. Se o subagente falhar → main assume ou pergunta ao humano
```

### O que a main NÃO faz (delega)

| Tarefa | Subagente |
|---|---|
| Código, testes, debugging, automação | `dev` |
| Extração de produtos (ML, Amazon, Shopee) | `extrator` |
| LinkedIn, vagas, posts, candidaturas | `orion` |

> ⚠️ **Nunca delega:** configuração do gateway, canais, credenciais, heartbeats.

## dev 💻 — Programação

- **Função:** expert em código — TypeScript, Next.js, Django, Python, Prisma, Docker, git
- **Workspace:** `~/.openclaw/agents/dev/workspace`
- **Modelo:** DeepSeek V4 Flash com fallback free
- **Regras:** testes obrigatórios (Vitest), factories tipadas, Docker para isolar dependências, não commita sem autorização

## extrator 🔍 — Produtos e-commerce

- **Função:** extrai título, preço, imagem e descrição de produtos (Mercado Livre, Amazon, Shopee)
- **Workspace:** `~/.openclaw/agents/extrator/workspace`
- **Modelo:** DeepSeek V4 Flash com fallback free
- **Regra de ouro:** **NUNCA envia mensagem** — retorna JSON para a main postar com imagem
- **Ferramentas restritas:** web_fetch, web_search, exec, read/write/edit, memory, image, pdf, message

## orion 🌌 — Carreira/LinkedIn

- **Função:** busca de vagas, candidaturas, posts, monitoramento de carreira
- **Workspace:** `~/.openclaw/agents/orion/workspace`
- **Modelo:** DeepSeek V4 Flash com fallback free
- **Credenciais:** Vaultwarden (organização compartilhada `openclaw-agents`) + sessão LinkedIn via Playwright

## Como adicionar um agente novo

1. Crie a pasta `agents/<id>/workspace/` com os arquivos base (AGENTS.md, SOUL.md, IDENTITY.md, USER.md, TOOLS.md, HEARTBEAT.md)
2. Adicione a entrada em `agents.list` no `openclaw.json`
3. Defina modelo, skills e tools (use `profile: "full"` + `allow` para restringir)
4. Se for subagente do main, adicione o id em `main.subagents.allowAgents`
5. Reinicie o gateway: `docker compose restart gateway`
