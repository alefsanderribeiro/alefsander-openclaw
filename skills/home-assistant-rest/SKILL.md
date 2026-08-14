---
name: "home-assistant-rest"
description: "Controle completo do Home Assistant via REST + WebSocket + Assist (linguagem natural). Rotas verificadas no HA 2026.8. Substitui home-assistant-agent-secure."
metadata:
  openclaw:
    emoji: "🏠"
    requires:
      bins: ["curl"]
      env: ["HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN"]
    primaryEnv: "HOME_ASSISTANT_TOKEN"
---

# Home Assistant — Operação Completa (REST + WebSocket + Assist)

Opera o Home Assistant de forma completa em três camadas, todas com o mesmo token (LLAT):
1. **REST API oficial** — estados, serviços, eventos, histórico, template, diagnóstico, câmera, calendário, Assist.
2. **WebSocket API** — registries (entidade/device/área/andar/label), zonas, automações, blueprints, energia, dashboards.
3. **Assist (Conversation)** — linguagem natural, delega ao NLU do HA (ideal para comandos vagos do dia a dia).

**Todas as rotas REST e comandos WebSocket abaixo foram verificados contra um HA 2026.8 real.** Esta skill **substitui a `home-assistant-agent-secure`** (que era só Assist): aqui o Assist está integrado, junto com REST e WebSocket, numa skill única.

## Configuração

- `HOME_ASSISTANT_URL` (ex: `http://homeassistant:8123`) e `HOME_ASSISTANT_TOKEN` (LLAT)
- Precedência: env do processo → `~/.openclaw/.env` → `openclaw.json`
- Fallback: `~/.openclaw/secrets/homeassistant-token`

```bash
TOKEN=$(cat ~/.openclaw/secrets/homeassistant-token)
HA="http://homeassistant:8123"
AUTH="Authorization: Bearer $TOKEN"
```

**Recomendação (segurança):** idealmente o token pertence a um **usuário restrito (non-admin)** do HA, com acesso limitado a áreas/entidades específicas. Se o seu token for de admin (como o atual do Alef), use com responsabilidade — só leitura e comandos pedidos.

## ASSIST — Linguagem Natural 🗣️ (herdado da agent-secure)

Para comandos do usuário em linguagem natural, use o **Assist** (Conversation API). Ele delega ao NLU do HA — entende sinônimos e não precisa de entity_id exato.

Endpoint: `POST /api/conversation/process`

> **Nota:** use `/api/conversation/process`, **NÃO** `/api/services/conversation/process`.

```bash
curl -sk -X POST "$HOME_ASSISTANT_URL/api/conversation/process" \
  -H "Authorization: Bearer $HOME_ASSISTANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "apaga a luz da sala", "language": "pt"}'
```

- O parâmetro `language` é o código do idioma detectado (ex: `"pt"`, `"en"`, `"pl"`, `"de"`).
- `-k` permite certificado auto-assinado; se o HA usar Let's Encrypt, pode remover.

### Request Body
```json
{"text": "turn on the kitchen lights", "language": "en"}
```

### Success Response
```json
{
  "response": {
    "speech": {"plain": {"speech": "Turned on the light"}},
    "response_type": "action_done",
    "data": {"success": [{"name": "Kitchen Light", "id": "light.kitchen"}], "failed": []}
  }
}
```

### Tratamento de resposta
Relaye `response.speech.plain.speech` diretamente ao usuário:
- `"Turned on the light"` → sucesso
- `"Sorry, I couldn't understand that"` → Assist não entendeu
- `"Sorry, there are multiple devices called X"` → nome ambíguo

### Erros (`response_type: "error"`)
| Erro | O que dizer |
|------|-------------|
| `no_intent_match` | Tentar retry nominativo (se língua flexionada). Se falhar: "O HA não reconheceu esse comando." |
| `no_valid_targets` | Tentar retry nominativo. Se falhar: "Entidade não encontrada — confira o nome ou adicione alias no HA." |
| Múltiplas correspondências | "Várias entidades compartilham esse nome — considere adicionar aliases únicos no HA." |

### Retry de línguas flexionadas (Nominative Retry)
Em línguas com casos gramaticais (polonês, tcheco, alemão, finlandês, húngaro, russo, croata/sérvio — e em PT pode ajudar com flexões), os usuários usam palavras flexionadas, mas as entidades estão no nominativo. Ex: *"apaga as luzes do quarto"* → entidade `light.quarto`. Se o Assist responder erro (`no_valid_targets`/`no_intent_match`) e o texto estiver flexionado:
1. Identifique o nome da entidade no comando
2. Converta para a forma base/nominativo
3. Reenvie o request corrigido
4. Se falhar de novo, avise que não encontrou

**Importante:** tentar **apenas uma vez** — sem loop.

## ROTAS REST OFICIAIS (verificadas ✅ 2026.8)

### Status e configuração
```bash
GET /api/                        # {"message":"API running."}
GET /api/config                  # versão, time_zone, unit_system, components...
GET /api/components              # lista de componentes carregados
POST /api/config/core/check_config   # valida configuration.yaml
```

### Estados
```bash
GET /api/states                                  # todos os estados
GET /api/states/<entity_id>                      # estado de 1 entidade (ex: light.pera_neo_10w_sala)
# POST /api/states/<entity_id>  ⚠️ NÃO USAR p/ dispositivos reais (cria estado manual — só p/ testes/mocks)
```

### Serviços (ações)
```bash
GET /api/services                                # lista todos os domínios/serviços disponíveis
POST /api/services/<domain>/<service>            # chamar ação (ex: light/turn_on)
# body: {"entity_id":"light.x"} ou {"entity_id":["light.a","light.b"]} + parâmetros
# Exemplos:
#   light.turn_on  {entity_id, brightness:128, color_temp_kelvin: 6500}
#   light.turn_off / light.toggle
#   switch.turn_on/off, scene.turn_on {entity_id: scene.x}, automation.turn_on/off
#   homeassistant.turn_on/off/toggle (qualquer entidade), script.<nome>
#   notify.<notify> {message, title} — notificações (ex: notify.pocox7)
```

### Eventos
```bash
GET /api/events                                  # eventos registrados + listener_count
POST /api/events/<event_type>                    # disparar evento customizado (avançado)
```

### Histórico e logbook
```bash
GET /api/history/period/<timestamp>?filter_entity_id=<id>&end_time=<ts>&minimal_response&no_attributes&significant_changes_only
GET /api/logbook/<timestamp>?entity=<id>&end_time=<ts>
# <timestamp> opcional (default 1 dia atrás); filtrar por entidade(s) separadas por vírgula
```

### Templates (valores computados — muito útil)
```bash
POST /api/template   {"template": "{{ states('light.pera_neo_10w_sala') }}"}
POST /api/template   {"template": "{{ states.sensor.pocox7_battery_level.state }}"}
```

### Calendários (se houver integração)
```bash
GET /api/calendars                               # lista de calendários
GET /api/calendars/<calendar_id>?start=<ts>&end=<ts>   # eventos no período
```

### Câmeras (se houver)
```bash
GET /api/camera_proxy/<camera_entity_id>?time=<ts>    # snapshot (binário) → salvar imagem
```

### Diagnóstico
```bash
GET /api/error_log                               # erros/tracebacks recentes
GET /api/config/config_entries/entry             # integrações + estado (loaded/error/setup_retry)
```

### Intent (legado, raramente usado)
```bash
POST /api/intent/handle
```

## WebSocket API (avançado — registries, zonas, automações)

Endpoint: `ws://<host>:8123/api/websocket` — autentica com o mesmo token (type: auth). Comandos úteis:

### ✅ Comandos CONFIRMADOS na 2026.8 (testados 08/08)
```json
{"type": "config/entity_registry/list"}                  // 390 entidades (platform, disabled_by, device_id, unique_id)
{"type": "config/entity_registry/get", "entity_id": "light.x"}   // detalhe 1 entidade (aliases, area_id, categories)
{"type": "config/entity_registry/list_for_display"}      // NOVO: versão compacta p/ UI (banda reduzida)
{"type": "config/device_registry/list"}                  // 30 devices
{"type": "config/device_registry/list_composite_splits"} // NOVO
{"type": "config/area_registry/list"}                    // 4 áreas
{"type": "config/floor_registry/list"}                   // NOVO: andares (0)
{"type": "config/label_registry/list"}                   // NOVO: labels (0)
{"type": "zone/list"}                                    // zonas (lat/lon/raio) — SEM prefixo config/
{"type": "person/list"}                                  // pessoas (storage+config) — SEM prefixo config/
{"type": "config/auth/list"}                             // usuários — COM prefixo config/
{"type": "lovelace/dashboards/list"}                     // dashboards — SEM prefixo config/
{"type": "lovelace/info"}                                // SEM parâmetros (não aceita url_path!)
{"type": "energy/info"} / {"type": "energy/validate"}    // energia (get_prefs → not_found se não configurado)
{"type": "blueprint/list", "domain": "automation"}       // blueprints por domínio
{"type": "automation/config", "entity_id": "automation.x"}  // config da automação (usa entity_id!)
{"type": "script/config", "entity_id": "script.x"}       // config de script (usa entity_id)
{"type": "validate_config", "triggers": [...], "conditions": [...], "actions": [...]}  // PLURAL!
{"type": "get_states"} / {"type": "get_config"} / {"type": "get_services"}   // dumps completos
{"type": "auth/current_user"}                           // usuário atual (is_owner, is_admin)
{"type": "persistent_notification/get"}                 // notificações pendentes
{"type": "config/entity_registry/update"} / {"type": "config/entity_registry/remove"}   // habilitar/desabilitar, aliases
{"type": "config/area_registry/create"} / {"type": "config/area_registry/update"}
```

### ❌ NÃO EXISTEM na 2026.8 (removidos — doc antiga desatualizada)
```json
{"type": "config/automation/list"}      // REMOVIDO — listar automações = config/entity_registry/list filtrando "automation."
{"type": "config/automation/config"}    // REMOVIDO — usar automation/config com entity_id
{"type": "automation/list"}             // nunca existiu
{"type": "config/script/list"} / {"type": "config/scene/list"} / {"type": "config/template/list"} / {"type": "config/trigger/list"}
{"type": "config/zone/list"}            // usar zone/list
{"type": "config/person/list"}          // usar person/list
{"type": "config/lovelace/dashboards/list"}  // usar lovelace/dashboards/list
{"type": "config/energy/list"} / {"type": "energy/get_preferences"}  // usar energy/info / energy/get_prefs
{"type": "config/device_registry/get_config"}   // removido
{"type": "config/flow/*"}               // config/flow/init, progress, abort, result — não existem
{"type": "config/core/check_config"}    // só existe via REST (POST /api/config/core/check_config)
{"type": "config/user/list"} / {"type": "auth/list"}  // usar config/auth/list
{"type": "config/auth/refresh_tokens"}  // removido
{"type": "scene/config"} / {"type": "template/config"} / {"type": "trigger/config"}
```

### ⚠️ Schemas que DIFEREM da doc oficial
1. **`automation/config`** → a doc antiga dizia `automation_id`; a 2026.8 usa **`entity_id`** (retorna `{"config": raw_config}`; `not_found` se entity não existe)
2. **`validate_config`** → a doc mostra `trigger`/`condition`/`action` (singular); o schema real usa **`triggers`/`conditions`/`actions` (plural)** — singular dá `invalid_format: extra keys not allowed`
3. **`lovelace/info`** → a doc sugere `url_path`; o schema real **não aceita** nenhum parâmetro (só `{"type": "lovelace/info"}`)
4. **`script/config`** → usa `entity_id` (não `object_id`/`script_id`)
5. **`energy/get_prefs`** → retorna `not_found: No prefs` quando energia não configurada (comando existe, mas sem prefs dá erro)

### Como listar automações na 2026.8 (sem config/automation/list)
```python
# 1. Pega todos os entity_ids do domínio automation via entity_registry
config/entity_registry/list → filter entity_id startswith "automation."
# 2. Para cada uma, busca o config:
automation/config {"entity_id": "automation.desligar_luz_ao_sair_de_casa"}
```

## Padrão de uso recomendado

1. **Comando natural do usuário** → **Assist** (`/api/conversation/process`) — entende sinônimos, não precisa de entity_id
2. **Operação múltipla / verificação / quando o Assist falhar** → **REST direto** (`/api/services`, `/api/states`)
3. **Antes de agir em entidade desconhecida** → `GET /api/states` (confirmar entity_id)
4. **Após chamar serviço Tuya** → aguardar ~5s e reconferir estado (retry 1x — a nuvem Tuya atrasa)
5. **Erros** → `GET /api/error_log` + `GET /api/config/config_entries/entry`

## Regras de segurança

1. **NUNCA** imprimir/expor o token
2. **NUNCA** usar `POST /api/states/<entity_id>` para controlar dispositivos reais
3. Verificar entity_id antes de chamar serviços; cuidado com ações destrutivas
4. Câmera/calendário: tratar 404 como "não configurado", não como erro da rota
5. Comandos destrutivos (deletar config entries, desligar serviços críticos): confirmar antes
6. **Trusted Networks Login Bypass:** se o HA usar `trusted_networks` com `allow_bypass_login: true`, qualquer um na rede local loga como qualquer usuário (inclusive admin) sem senha → anula o modelo restrito. Fix: `allow_bypass_login: false` no provider, ou remover o provider. NUNCA logar na UI web — sempre via token/API.

## Troubleshooting

- **401 Unauthorized**: Token inválido/expirado. Gerar novo no perfil do usuário.
- **Connection refused**: `HOME_ASSISTANT_URL` errada ou HA fora do ar.
- **Command not understood (Assist)**: reformular ou conferir se a entidade está exposta ao usuário.
- **Entity not found**: o usuário pode não ter acesso àquela área/entidade; atualizar permissões.

## Local Notes — deployment de referência (2026-08-08)

> ⚠️ Dados pessoais (endereço, nomes de cômodos reais, modelos de celular) foram
> removidos para o repositório público — substitua pelos do seu setup.

- **URL:** `http://homeassistant:8123` (rede docker `vaultwarden_tailscale-net`) · público `https://home.seu-dominio.com`
- **Token:** `~/.openclaw/secrets/homeassistant-token` (owner/admin — NÃO é usuário restrito; considerar criar usuário restrito p/ operações)
- **Luzes (Tuya):** `light.lampada_sala`, `light.lampada_quarto` — on/off + brilho (0-255); **sem RGB** (branco ajustável); `color_temp` → HTTP 400 (bug lib tuya)
- **Tracker:** `device_tracker.celular` (GPS via companion app) — zona home configurada no app
- **Automações (4):** `automation.ligar_luz_ai` (duplicada — apagar), `automation.desligar_luz_ao_sair_de_casa`, `automation.teste_01`, `automation.teste_02`
- **Integrações:** Tuya, Uptime Kuma (23 devices/monitores), mobile_app, backup
- **HA 2026.8+:** config HTTP pela UI (Settings → System → Network), não pelo YAML
- **Testado 08/08:** 13 rotas REST → 200 ✅ (calendars/camera_proxy = 404 esperado sem integração); 60+ comandos WS testados (mapeamento de inconsistências acima)
- **Assist em PT:** reconhece cômodos ("apaga a luz do quarto alef" → OFF); falha em frases compostas (necessário aliases nas entidades); não responde contagem ("quantas luzes existem?")
