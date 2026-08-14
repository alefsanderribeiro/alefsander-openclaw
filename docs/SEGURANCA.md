# 🔒 Segurança

## Regra nº 1: nunca commitar segredos

Este repositório é **público**. Qualquer token, senha, email, telefone, JID de
grupo ou endereço commitado fica visível para sempre no histórico (mesmo depois
de corrigido, o commit antigo pode ser acessado por URL direta até o GitHub
fazer garbage collection).

**Boas práticas aplicadas neste repo:**

| Item | Onde fica |
|---|---|
| Chaves de API / tokens | `.env` (ignorado) ou variáveis de ambiente |
| Config com segredos | `openclaw.json` real (o repo só tem `openclaw.json.example` com `${VAR}`) |
| Credenciais de scripts | `~/.openclaw/secrets/` (fora do repo) |
| Senhas de cofres | Vaultwarden + env vars (`--passwordenv`) |
| Certificados/chaves TLS | gerados localmente (ignorados) |

**Checklist antes de push:**

```bash
# Padrões de token/chave
grep -rniE "(ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN .*PRIVATE KEY-----)" .

# PII
grep -rniE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" .   # emails
grep -rniE "\+?55[\s.-]?\(?[0-9]{2}\)?[\s.-]?9[0-9]{4}[\s.-]?[0-9]{4}" .  # telefones BR
grep -rniE "[0-9]{10,}@g\.us" .   # JIDs WhatsApp

# Histórico (se já commitou algo, reescreva com amend/filter-repo e force push)
git log --all --oneline
```

## Hardening do container

- Roda como usuário `node` (não root)
- Filesystem **read-only** (exceções: volumes montados + `/tmp` em tmpfs)
- `cap_drop` remove capacidades Linux desnecessárias (NET_RAW, SYS_ADMIN, MKNOD...)
- Docker socket montado **somente leitura**
- Auth no gateway: senha/token + rate limiting contra brute force
- `sudo` sem senha **apenas dentro do container isolado**

## Limites do agente

**PODE:** ler/escrever no workspace · acessar mounts explícitos · internet ·
instalar pacotes no container (`sudo apt`, `pip`, `npm`)

**NÃO PODE:** acessar arquivos do host fora dos mounts · executar comandos no
host · escalonar privilégios no host · criar/destruir containers (socket `:ro`)

## Modelo de confiança dos agentes

- Cada agente tem **usuário próprio** no Vaultwarden e vê **só o compartilhado**
- Agentes especialistas têm **tools restritas** (`allow` list) — ex: extrator
  não gerencia canais
- O `extrator` **nunca envia mensagens** — só retorna JSON (a main posta)
- Subagentes não mexem em config do gateway/canais/credenciais

## Se um segredo vazar

1. **Rotacione imediatamente** o que vazou (senha, token, chave)
2. Remova o arquivo e faça `git commit --amend` + `git push --force-with-lease`
   (se o segredo está no último commit) ou `git filter-repo` (histórico longo)
3. Verifique no GitHub: `gh api repos/<user>/<repo>/git/trees/main?recursive=1`
4. Considere tornar o repo privado enquanto resolve
