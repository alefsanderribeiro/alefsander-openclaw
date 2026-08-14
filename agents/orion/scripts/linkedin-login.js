// Script de login LinkedIn com salvamento de sessão
// Uso: PLAYWRIGHT_BROWSERS_PATH=/home/node/.openclaw/workspace/ms-playwright node linkedin-login.js

const { chromium } = require('/home/node/.openclaw/workspace/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const CREDS_PATH = path.join(__dirname, '..', 'secrets', 'linkedin-creds.json');
const SESSION_PATH = path.join(__dirname, '..', 'secrets', 'linkedin-session.json');

async function main() {
  // Carrega credenciais
  let creds;
  try {
    creds = JSON.parse(fs.readFileSync(CREDS_PATH, 'utf8'));
  } catch {
    console.error('❌ Credenciais não encontradas em:', CREDS_PATH);
    process.exit(1);
  }

  if (!creds.email || creds.email === 'COLOCAR_EMAIL_AQUI') {
    console.error('❌ Configure o email/senha em linkedin-creds.json primeiro');
    process.exit(1);
  }

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

  try {
    // PASSO 1: Navegar para login
    console.log('📄 Navegando para LinkedIn login...');
    await page.goto('https://www.linkedin.com/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000);

    // PASSO 2: Preencher email
    console.log('📧 Preenchendo email...');
    const emailField = page.locator('input[autocomplete="username"]').first();
    await emailField.fill(creds.email);
    await page.waitForTimeout(500);

    // PASSO 3: Preencher senha
    console.log('🔑 Preenchendo senha...');
    const passField = page.locator('input[autocomplete="current-password"]').first();
    await passField.fill(creds.password);
    await page.waitForTimeout(500);

    // PASSO 4: Clicar em Entrar
    console.log('🖱️ Clicando em Entrar...');
    const loginBtn = page.locator('button:has-text("Entrar")').first();
    await loginBtn.click();

    // PASSO 5: Aguardar navegação
    console.log('⏳ Aguardando login...');
    await page.waitForTimeout(5000);

    const currentUrl = page.url();
    console.log('📍 URL atual:', currentUrl);

    // Verificar se pediu 2FA
    if (currentUrl.includes('checkpoint') || currentUrl.includes('challenge')) {
      console.log('🔐 ⚠️  LinkedIn solicitou verificação (2FA)!');
      await page.screenshot({ path: path.join(__dirname, '..', 'imagens', 'linkedin-2fa.png') });
      console.log('📸 Screenshot salvo em imagens/linkedin-2fa.png');
      
      // Aguardar input manual do código
      console.log('⏳ Aguardando código de verificação... (30s timeout)');
      try {
        await page.waitForURL('https://www.linkedin.com/feed/**', { timeout: 120000 });
        console.log('✅ Verificação concluída!');
      } catch {
        console.log('⚠️ Timeout na verificação. Verifique se o código foi inserido.');
        // Tenta dar mais tempo
        try {
          await page.waitForURL('https://www.linkedin.com/feed/**', { timeout: 120000 });
        } catch {
          console.error('❌ Login não completado.');
          await browser.close();
          process.exit(1);
        }
      }
    }

    // PASSO 6: Verificar login bem-sucedido
    if (currentUrl.includes('feed') || currentUrl.includes('linkedin.com/')) {
      console.log('✅ Login bem-sucedido!');
    }

    // PASSO 7: Salvar sessão (cookies + localStorage)
    console.log('💾 Salvando sessão...');
    const cookies = await context.cookies();
    const localStorage = await page.evaluate(() => {
      const items = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        items[key] = localStorage.getItem(key);
      }
      return items;
    });

    const session = {
      savedAt: new Date().toISOString(),
      cookies,
      localStorage,
      url: page.url(),
    };

    fs.writeFileSync(SESSION_PATH, JSON.stringify(session, null, 2));
    console.log('✅ Sessão salva em:', SESSION_PATH);
    
    await browser.close();
    console.log('🎉 Login concluído com sucesso!');

  } catch (err) {
    console.error('❌ Erro:', err.message);
    await page.screenshot({ path: path.join(__dirname, '..', 'imagens', 'error.png') });
    await browser.close();
    process.exit(1);
  }
}

main();
