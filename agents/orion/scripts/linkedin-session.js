// Script para restaurar sessão salva do LinkedIn e executar ações
// Uso: PLAYWRIGHT_BROWSERS_PATH=/home/node/.openclaw/workspace/ms-playwright node linkedin-session.js <acao> [args...]
//
// Ações:
//   status          — Verifica se sessão ainda é válida
//   navigate <url>  — Navega para URL específica
//   screenshot      — Tira screenshot da página atual
//   search <query>  — Busca vagas no LinkedIn
//   post <arquivo>  — Publica post do arquivo de conteúdo
//   messages        — Lista mensagens recentes
//   notifications   — Lista notificações

const { chromium } = require('/home/node/.openclaw/workspace/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const SESSION_PATH = path.join(__dirname, '..', 'secrets', 'linkedin-session.json');
const CREDS_PATH = path.join(__dirname, '..', 'secrets', 'linkedin-creds.json');
const BASE_URL = 'https://www.linkedin.com';

async function restoreSession(context) {
  try {
    const session = JSON.parse(fs.readFileSync(SESSION_PATH, 'utf8'));
    if (session.cookies && session.cookies.length > 0) {
      await context.addCookies(session.cookies);
    }
    return session;
  } catch {
    return null;
  }
}

async function main() {
  const action = process.argv[2] || 'status';
  const args = process.argv.slice(3);

  console.log('🚀 Iniciando Chromium...');
  const browser = await chromium.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    headless: true,
  });

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    locale: 'pt-BR',
    viewport: { width: 1280, height: 800 },
  });

  const page = await context.newPage();

  // Restaura sessão salva
  const session = await restoreSession(context);
  if (session) {
    console.log('📋 Sessão carregada de:', session.savedAt);
  }

  const actions = {
    // Verificar status da sessão
    async status() {
      await page.goto(`${BASE_URL}/feed/`, { waitUntil: 'domcontentloaded', timeout: 20000 });
      await page.waitForTimeout(2000);
      const url = page.url();
      const loggedIn = url.includes('feed') || url.includes('/in/');
      console.log('📍 URL:', url);
      console.log(loggedIn ? '✅ Sessão ativa' : '❌ Sessão expirada');
      return loggedIn;
    },

    // Navegar para URL específica
    async navigate() {
      const url = args[0] || BASE_URL;
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2000);
      console.log('📍 Navegado para:', page.url());
      const title = await page.title();
      console.log('📄 Título:', title);
    },

    // Screenshot
    async screenshot() {
      const filename = args[0] || `screenshot-${Date.now()}.png`;
      const filepath = path.join(__dirname, '..', 'imagens', filename);
      await page.screenshot({ path: filepath, fullPage: true });
      console.log('📸 Screenshot salvo:', filepath);
    },

    // Buscar vagas
    async search() {
      const query = args.join(' ') || 'desenvolvedor';
      console.log(`🔍 Buscando: "${query}"`);
      await page.goto(`${BASE_URL}/jobs/search/?keywords=${encodeURIComponent(query)}`, 
        { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(3000);
      
      const title = await page.title();
      console.log('📄 Página:', title);
      
      // Extrai resultados
      const jobs = await page.evaluate(() => {
        const cards = document.querySelectorAll('.job-card-container, .jobs-search-results__list-item, article');
        return Array.from(cards).slice(0, 15).map(card => ({
          title: card.querySelector('[class*="job-title"], [class*="job-card-list__title"]')?.textContent?.trim() || '',
          company: card.querySelector('[class*="company-name"], [class*="job-card-container__company-name"]')?.textContent?.trim() || '',
          location: card.querySelector('[class*="job-card-container__metadata-wrapper"]')?.textContent?.trim() || '',
        })).filter(j => j.title || j.company);
      });

      if (jobs.length > 0) {
        console.log(`\n📋 ${jobs.length} vagas encontradas:`);
        jobs.forEach((j, i) => {
          console.log(`  ${i+1}. ${j.title || '(sem título)'} — ${j.company || '(sem empresa)'} ${j.location ? '('+j.location+')' : ''}`);
        });
      } else {
        console.log('⚠️ Nenhuma vaga encontrada na busca inicial. Pode precisar de scroll/JS.');
      }
    },

    // Publicar post
    async post() {
      const contentFile = args[0];
      if (!contentFile) {
        console.error('❌ Use: post <arquivo>');
        process.exit(1);
      }
      const content = fs.readFileSync(contentFile, 'utf8');
      console.log('📝 Publicando post...');

      await page.goto(`${BASE_URL}/feed/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(3000);

      // Clica no "Começar publicação"
      const startBtn = page.locator('button:has-text("Começar publicação"), div[role="button"]:has-text("Começar publicação")').first();
      if (await startBtn.isVisible()) {
        await startBtn.click();
        await page.waitForTimeout(2000);
      }

      // Preenche o editor
      const editor = page.locator('[contenteditable="true"]').first();
      if (await editor.isVisible()) {
        await editor.fill(content);
        await page.waitForTimeout(1000);
        console.log('✅ Conteúdo preenchido');
      } else {
        console.log('⚠️ Editor não encontrado');
      }

      // Publicar
      const publishBtn = page.locator('button:has-text("Publicar")').first();
      if (await publishBtn.isVisible()) {
        await publishBtn.click();
        await page.waitForTimeout(3000);
        console.log('✅ Post publicado!');
      } else {
        console.log('⚠️ Botão Publicar não encontrado');
      }
    },

    // Mensagens
    async messages() {
      await page.goto(`${BASE_URL}/messaging/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(3000);
      const title = await page.title();
      console.log('📄 Página:', title);
      
      const msgs = await page.evaluate(() => {
        const items = document.querySelectorAll('.msg-conversation-card__row, [class*="conversation-card"]');
        return Array.from(items).slice(0, 10).map(m => m.textContent?.trim()).filter(Boolean);
      });
      
      if (msgs.length > 0) {
        console.log(`💬 ${msgs.length} conversas encontradas:`);
        msgs.forEach((m, i) => console.log(`  ${i+1}. ${m.substring(0, 100)}`));
      } else {
        console.log('📭 Nenhuma mensagem encontrada');
      }
    },

    // Notificações
    async notifications() {
      await page.goto(`${BASE_URL}/notifications/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(3000);
      const title = await page.title();
      console.log('📄 Página:', title);
      
      const notifs = await page.evaluate(() => {
        const items = document.querySelectorAll('.notifications-list__item, [class*="notification-item"]');
        return Array.from(items).slice(0, 10).map(n => n.textContent?.trim()).filter(Boolean);
      });
      
      if (notifs.length > 0) {
        console.log(`🔔 ${notifs.length} notificações:`);
        notifs.forEach((n, i) => console.log(`  ${i+1}. ${n.substring(0, 120)}`));
      } else {
        console.log('🔔 Nenhuma notificação encontrada');
      }
    },
  };

  try {
    if (actions[action]) {
      await actions[action]();
    } else {
      console.error(`❌ Ação desconhecida: ${action}`);
      console.log('Ações disponíveis: status, navigate, screenshot, search, post, messages, notifications');
    }
  } catch (err) {
    console.error('❌ Erro:', err.message);
    await page.screenshot({ path: path.join(__dirname, '..', 'imagens', 'error.png') });
  } finally {
    await browser.close();
  }
}

main();
