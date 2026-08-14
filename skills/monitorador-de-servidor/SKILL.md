---
name: "monitorador-de-servidor"
description: "Montar/operar monitoramento de servidor com Uptime Kuma (uptime) e Netdata (métricas), incluindo alertas Telegram."
---

# monitorador-de-servidor

Monitoramento completo de um servidor usando **Uptime Kuma** (uptime/status — "está no ar?") + **Netdata** (métricas — "está saudável?"). Inclui deploy em Docker atrás de reverse proxy, configuração de monitores, alertas Telegram e troubleshooting.

**Complemento:** o arquivo de memória `memory/monitoramento-servidor-setup.md` registra o que foi feito no servidor real (caminhos, domínios, credenciais). Esta skill é o **procedimento genérico e referência** de como fazer cada coisa.

---

## 1. Conceito — 2 camadas complementares

```
CAMADA 1 — Uptime Kuma    "O serviço caiu?"     → alertas rápidos de queda (Telegram)
CAMADA 2 — Netdata        "Por que está lento?" → dashboard profundo: CPU/RAM/disco/rede/processos (host + por container)
```

Não se substituem: Kuma = disponibilidade; Netdata = saúde/desempenho. Use os dois juntos.

---

## 2. Uptime Kuma

### O que é
Ferramenta open-source (MIT, grátis) self-hosted de monitoramento de uptime. Verifica periodicamente se serviços/containers/sites estão no ar. Dashboard web com status pages e histórico de uptime. Mais de 70 canais de notificação.

### Deploy (Docker Compose)

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:2        # ⚠️ NUNCA :latest (está preso na v1.x no Docker Hub)
    container_name: uptime-kuma
    restart: unless-stopped
    expose:
      - "3001"                           # não publica porta; reverse proxy encaminha
    volumes:
      - ./kuma-data:/app/data            # 📦 banco SQLite (CRÍTICO persistir)
      - /var/run/docker.sock:/var/run/docker.sock:ro   # p/ monitorar containers (segurança!)
    networks:
      - <rede-compartilhada>
```

**Pontos-chave:**
- **Tag `:2`** → v2.4.0+ (a tag `latest` do Kuma no Docker Hub está quebrada, presa em 1.x). Usar sempre `:2` para atualizar.
- **Persistência:** o volume `kuma-data` contém o banco SQLite (`kuma.db`) com todos os monitores/config/admin. Perder o volume = perder tudo.
- **docker.sock (ro):** necessário só para monitorar containers Docker. Montar read-only e **nunca expor publicamente**.
- **Reverse proxy:** o Kuma usa **WebSocket** — o proxy (Caddy/Nginx) precisa repassar os headers `Upgrade`/`Connection`. Caddy 2 encaminha websocket automaticamente via `reverse_proxy`.

### Tipos de monitor (principais)
| Tipo | Uso |
|------|-----|
| HTTP(s) | Sites/APIs disponíveis; configurável status code aceitos, redirect, auth |
| Docker Container | Container rodando/healthy (requer docker.sock) |
| TCP Port | Porta aceitando conexão |
| Ping | Host responde |
| SSL/TLS | Expiração de certificado (alerta antes) |
| Banco (Postgres, MySQL, Mongo...) | DB responde consultas |
| Push | Serviço manda heartbeat |

### Configuração de monitores — via API (Python)

Usar `uptime-kuma-api-v2` (Socket.IO). Exemplo de criar monitor Docker:

```python
from uptime_kuma_api import UptimeKumaApi, MonitorType, DockerType

api = UptimeKumaApi("http://uptime-kuma:3001")
api.login("usuario", "senha")

# 1. Registrar host Docker (socket local) — NECESSÁRIO antes de monitorar containers
hosts = api.get_docker_hosts()
if not hosts:
    api.add_docker_host(name="local", dockerType=DockerType.SOCKET, dockerDaemon="/var/run/docker.sock")
    hosts = api.get_docker_hosts()
docker_host_id = hosts[0]["id"]

# 2. Criar monitor Docker por container
api.add_monitor(type=MonitorType.DOCKER, name="Docker - meu-servico",
                docker_container="meu-servico", docker_host=docker_host_id, interval=60)
```

> 💡 **Alternativa:** o pacote `uptime-kuma-api-v2` (usado acima, já validado) funciona; porém, para melhor suporte à **v2.x** do Kuma, avalie o fork `uptime-kuma-api2` (mais completo/atualizado, compatível com Kuma 2.0–2.4). Ambos seguem a mesma interface de uso.

**Lição importante:** monitores HTTP de serviços LOCAIS devem apontar para os **containers internos** (`http://<container>:<porta>`), NÃO para domínios públicos que resolvam pra IP Tailscale/VPN — senão dão falso DOWN.

### Alertas Telegram

1. Bot: `@BotFather` → `/newbot` → token.
2. Chat ID: mandar msg pro bot, depois `curl https://api.telegram.org/bot<TOKEN>/getUpdates` → pegar `message.chat.id`.
3. No Kuma (UI): Settings → Notifications → Add → Telegram → bot token + chat id → Test.
   **Via API:** `api.add_notification(name="Telegram", type=NotificationType.TELEGRAM, telegramBotToken=..., telegramChatID=..., isDefault=True)`.
4. Aplicar aos monitores: garantir `notificationIDList` de cada monitor contém o id da notificação.

---

## 3. Netdata

### O que é
Plataforma open-source (GPL-3.0) de observabilidade em tempo real (coleta por segundo). Detecta automaticamente o host e containers Docker, mostrando CPU/RAM/disco/rede/processos do servidor inteiro + de cada container. Dashboard web rico, alertas pré-configurados (disco cheio, CPU alta), conecta-se a **Netdata Cloud** (conta Google) para acesso remoto.

### Deploy (Docker Compose)

```yaml
services:
  netdata:
    image: netdata/netdata:latest        # ⚠️ latest = canal NIGHTLY (rolling); estável = netdata/netdata:stable
    container_name: netdata
    restart: unless-stopped
    expose:
      - "19999"
    volumes:
      - netdata-config:/etc/netdata
      - netdata-lib:/var/lib/netdata
      - netdata-cache:/var/cache/netdata
      # ACESSO AO HOST — enxerga servidor inteiro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/host/root:ro
      - /etc/passwd:/host/etc/passwd:ro
      - /etc/group:/host/etc/group:ro
      - /etc/localtime:/etc/localtime:ro
      # ACESSO AOS CONTAINERS — monitora cada um
      - /var/run/docker.sock:/var/run/docker.sock:ro
    cap_add:
      - SYS_PTRACE
    security_opt:
      - apparmor:unconfined
    networks:
      - <rede-compartilhada>

volumes:
  netdata-config:
  netdata-lib:
  netdata-cache:
```

**Pontos-chave:**
- **Tag `:latest` = canal NIGHTLY** (rolling, ex.: `v2.10.0-978-nightly`). Para versão **estável** use `netdata/netdata:stable`. No servidor do Alef roda `:latest` (nightly) — ok para uso doméstico, mas saiba que atualiza com frequência.
- **Como enxerga tudo:** os bind mounts de `/proc`, `/sys`, `/` dão acesso ao host; o `docker.sock` dá acesso aos containers. **Um único container monitora o servidor inteiro + container por container.**

### Como ver os dados
- **Dashboard local:** `https://metrics.DOMINIO` (ou `:19999`).
- **Menu lateral:** Overview, System/CPU, Memory, Disks, Networking, Applications, e seção **Docker/cgroups** (cada container).
- **Netdata Cloud:** conectar conta Google → acesso remoto via `app.netdata.cloud` (qualquer rede, não precisa VPN).
- **Via API (para eu/OpenClaw consultar):** `curl http://netdata:19999/api/v1/charts` (lista tudo), `/api/v1/data?chart=<id>&after=-120` (valores). Ex.: chart `app.mega-cmd-server_cpu_utilization`.

### Alertas/Notificações (Netdata)
- **Pré-configurados:** centenas de alertas automáticos (disco cheio, CPU, memória, `docker_container_unhealthy`, `docker_container_down`, etc.).
- **Canais:** Telegram, email, Slack, Discord, PagerDuty...
- **Config:** editar `health_alarm_notify.conf` (ex.: `SEND_TELEGRAM="YES"`) e reiniciar o agente.
- **Via Cloud:** quando agente é "claimed" no Netdata Cloud, as notificações podem ser centralizadas via integrações da Cloud.
- **Custom alerts:** arquivos em `health.d/` (montar num volume e referenciar).

> ⚠️ **Atenção:** o alerta `docker_container_down` vem **desabilitado por padrão** no Netdata. Para ativá-lo (v2.x), edite/monte `health.d/docker.conf` no volume de config e ajuste o **filtro de labels do chart** — troque `container_name=!*` para os containers desejados (ex.: `container_name=*`); em versões antigas bastava `enabled: YES`. Sem isso, o Netdata NÃO avisa quando um container específico para — apenas o Kuma cobre isso.

---

## 4. Integração Kuma + Netdata

- Adicionar um **monitor HTTP no Kuma** apontando pro Netdata (`http://netdata:19999` ou `https://metrics.DOMINIO`) → se o Netdata cair, o Kuma alerta. (O que fizemos: `Netdata (interno)`).
- O Netdata também pode alimentar status pages do Kuma (avançado).

---

## 5. Acesso & segurança (padrão do servidor)

- Tudo atrás de **Caddy compartilhado** com TLS via Cloudflare DNS-01 (`tls { dns cloudflare {env.CF_API_TOKEN} }`).
- Domínios resolvem pro **IP Tailscale** (VPN) — **sem expor porta pública**.
- Docker.sock montado read-only; **nunca expor estes painéis publicamente sem autenticação extra**.
- Credenciais/tokens ficam em `~/.openclaw/secrets/` (nunca commitados).

---

## 6. Troubleshooting comum

| Sintoma | Causa | Correção |
|---------|-------|----------|
| Kuma "não é possível conectar ao socket" | Volume `kuma-data` montado na pasta errada / banco perdido (comum ao reestruturar repo) | `docker logs uptime-kuma`; garantir que monta a pasta com `kuma.db`; copiar banco se preciso |
| Monitor HTTP de serviço local dá DOWN falso | Aponta p/ domínio público (IP VPN) em vez de container interno | Editar monitor → `http://<container>:<porta>` |
| Monitor Docker UNHEALTHY | Healthcheck do serviço falha de verdade | Ver `docker ps`; corrigir healthcheck no compose do serviço |
| Não recebe alerta Telegram | Token/chat errado ou notificação não ligada no monitor | `getMe` confere token; aplicar `notificationIDList` |
| WebSocket da UI não conecta | Config/banco quebrado após recriar | Recuperar banco do volume; ver logs |
| `latest` do Kuma não atualiza | Tag latest presa na v1.x | Usar tag `:2` + `docker compose pull && up -d` |
| Tempo/DNS apontando pra VPN falha | Kuma fora da rede de destino | Usar containers internos (mesma rede Docker) |
| Netdata atualiza sozinho demais | `:latest` é canal nightly (rolling) | Trocar pra `netdata/netdata:stable` no compose |

---

## 7. Referências oficiais

- Uptime Kuma: https://github.com/louislam/uptime-kuma · Wiki: https://github.com/louislam/uptime-kuma/wiki
  - Reverse proxy: https://github.com/louislam/uptime-kuma/wiki/Reverse-Proxy
  - Monitor Docker: https://github.com/louislam/uptime-kuma/wiki/How-to-Monitor-Docker-Containers
- Netdata: https://www.netdata.cloud · Docs: https://learn.netdata.cloud
  - Docker: https://learn.netdata.cloud/docs/collecting-metrics/collectors/containers-and-vms/docker
  - Alertas: https://learn.netdata.cloud/docs/alerts-&-notifications
- Lib API Kuma (Python): https://pypi.org/project/uptime-kuma-api-v2/ · Fork p/ v2.x: https://pypi.org/project/uptime-kuma-api2/
