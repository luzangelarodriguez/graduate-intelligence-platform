import fs from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUTPUT_DIR = path.resolve(ROOT, 'outputs', 'qa', 'visual');
const BASE_URL = process.env.VISUAL_QA_BASE_URL || 'http://127.0.0.1:4173';
const PLAYWRIGHT_ENTRY = path.resolve(ROOT, 'graduate_intelligence_platform', 'frontend', 'node_modules', 'playwright', 'index.mjs');
const { chromium } = await import(pathToFileURL(PLAYWRIGHT_ENTRY).href);

function mapApiPath(pathname) {
  const apiPrefixRoutes = [
    '/api/programas',
    '/api/specializations',
    '/api/dashboard',
    '/api/recommendations',
    '/api/programs/related-universities',
    '/api/alumni',
    '/api/microcurriculum',
    '/api/bootstrap',
  ];
  const rootRoutes = [
    '/api/program-intelligence',
    '/api/executive-observatory',
    '/api/executive-narrative',
    '/api/program-summary',
    '/api/recommendation-explanation',
    '/api/ask-observatory',
    '/api/critical-programs',
    '/api/curriculum-simulator',
    '/api/forecast-summary',
    '/api/company-intelligence',
    '/api/emerging-skills',
    '/api/market-forecast',
    '/api/curriculum-risk',
    '/api/alignment',
  ];
  if (rootRoutes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return pathname.replace(/^\/api/, '');
  }
  if (apiPrefixRoutes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return pathname;
  }
  return pathname;
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function capture(page, name) {
  const file = path.resolve(OUTPUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function main() {
  await ensureDir(OUTPUT_DIR);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1600 }, colorScheme: 'light' });
  await context.addInitScript(() => {
    const store = new Map([
      ['gi_access_token', 'qa-token'],
      ['gi_refresh_token', 'qa-refresh-token'],
    ]);
    const fakeStorage = {
      getItem(key) {
        return store.has(key) ? store.get(key) : null;
      },
      setItem(key, value) {
        store.set(key, String(value));
      },
      removeItem(key) {
        store.delete(key);
      },
      clear() {
        store.clear();
      },
      key(index) {
        return Array.from(store.keys())[index] ?? null;
      },
      get length() {
        return store.size;
      },
    };
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: fakeStorage,
    });
  });

  const log = {
    pages: {},
    console_errors: [],
    page_errors: [],
  };

  context.on('page', (page) => {
    page.on('console', (message) => {
      if (['error', 'warning'].includes(message.type())) {
        log.console_errors.push({ type: message.type(), text: message.text() });
      }
    });
    page.on('pageerror', (error) => {
      log.page_errors.push(error.message);
    });
  });

  await context.route('**/auth/me**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        email: 'qa@institucion.edu.co',
        full_name: 'QA Academic Reviewer',
        roles: ['admin', 'academico'],
        active: true,
      }),
    });
  });

  await context.route('**/api/**', async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname.endsWith('/auth/me')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          email: 'qa@institucion.edu.co',
          full_name: 'QA Academic Reviewer',
          roles: ['admin', 'academico'],
          active: true,
        }),
      });
    }
    const mappedPath = mapApiPath(requestUrl.pathname);
    const targetUrl = `http://127.0.0.1:8010${mappedPath}${requestUrl.search}`;
    try {
      const response = await route.fetch({ url: targetUrl, timeout: 8000 });
      await route.fulfill({ response });
    } catch (error) {
      await route.fulfill({
        status: 504,
        contentType: 'application/json',
        body: JSON.stringify({
          error: error instanceof Error ? error.message : String(error),
          targetUrl,
          path: requestUrl.pathname,
        }),
      });
    }
  });

  const page = await context.newPage();
  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  log.pages.executive_summary = {
    title: await page.locator('h1, h2').first().innerText().catch(() => ''),
    bodyLength: (await page.locator('body').innerText().catch(() => '')).length,
  };
  await capture(page, '01-executive-summary');

  await page.goto(`${BASE_URL}/programas`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  const firstProgramHref = await page.locator('a[href^="/programs/"]').first().getAttribute('href').catch(() => null);
  const firstProgramName = await page.locator('a[href^="/programs/"] h4, a[href^="/programs/"] strong').first().innerText().catch(() => '');
  log.pages.programs = {
    firstProgramHref,
    firstProgramName,
    bodyLength: (await page.locator('body').innerText().catch(() => '')).length,
  };
  await capture(page, '02-programs-ranking');

  const resolvedProgramId = Number(process.env.VISUAL_QA_PROGRAM_ID || 108);
  const programId = Number.isFinite(resolvedProgramId) && resolvedProgramId > 0
    ? resolvedProgramId
    : Number((firstProgramHref || '').match(/\/programs\/(\d+)/)?.[1] || 0);
  if (!Number.isFinite(programId) || programId <= 0) {
    throw new Error('No se pudo resolver un programa válido desde /programas');
  }

  await page.goto(`${BASE_URL}/programs/${programId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1400);
  log.pages.program_detail = {
    title: await page.locator('h2').first().innerText().catch(() => ''),
    bodyLength: (await page.locator('body').innerText().catch(() => '')).length,
  };
  await capture(page, '03-program-detail');
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)).catch(() => {});
  await page.waitForTimeout(700);
  await page.waitForFunction(
    () => {
      const text = document.body?.innerText || '';
      return (
        text.includes('Diagnóstico institucional') ||
        text.includes('Programas prioritarios') ||
        text.includes('Brechas críticas') ||
        text.includes('Preguntar al observatorio') ||
        text.includes('No fue posible cargar el programa')
      );
    },
    { timeout: 15000 },
  );
  const copilotBody = await page.locator('body').innerText().catch(() => '');
  const copilotSignals = [
    'Diagnóstico institucional',
    'Programas prioritarios',
    'Brechas críticas',
    'Acciones recomendadas',
    'Impacto esperado',
    'Evidencia utilizada',
    'Preguntar al observatorio',
  ];
  const matchedSignals = copilotSignals.filter((signal) => copilotBody.includes(signal));
  if (matchedSignals.length < 4) {
    throw new Error(`El copiloto no muestra el briefing ejecutivo automático esperado. Señales encontradas: ${matchedSignals.join(', ') || 'ninguna'}`);
  }
  log.pages.copilot = {
    heading: await page.locator('h3').first().innerText().catch(() => ''),
    matchedSignals,
    bodyLength: copilotBody.length,
  };
  await capture(page, '07-copilot');

  await page.goto(`${BASE_URL}/programs/${programId}/microcurriculum`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1400);
  log.pages.microcurriculum = {
    title: await page.locator('h2').first().innerText().catch(() => ''),
    bodyLength: (await page.locator('body').innerText().catch(() => '')).length,
  };
  await capture(page, '04-microcurriculum');

  await page.goto(`${BASE_URL}/programs/${programId}/forecast`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1400);
  log.pages.forecast = {
    title: await page.locator('h2').first().innerText().catch(() => ''),
    bodyLength: (await page.locator('body').innerText().catch(() => '')).length,
  };
  await capture(page, '05-forecast');

  await page.goto(`${BASE_URL}/programs/${programId}/simulation`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1400);
  const customSkillInput = page.locator('input[type="text"]').first();
  const addSkillButton = page.getByRole('button', { name: 'Agregar skill' });
  const inputCount = await customSkillInput.count().catch(() => 0);
  if (inputCount > 0) {
    await customSkillInput.fill('Azure').catch(() => {});
    await addSkillButton.click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(1200);
  }
  log.pages.simulation_interaction = {
    selectedSkillsText: await page.locator('text=Skills seleccionadas').first().innerText().catch(() => ''),
    bodyHasAzure: (await page.locator('body').innerText().catch(() => '')).includes('Azure'),
  };
  log.pages.simulation = {
    title: await page.locator('h2').first().innerText().catch(() => ''),
    bodyLength: (await page.locator('body').innerText().catch(() => '')).length,
  };
  await capture(page, '06-simulation');

  await fs.writeFile(
    path.resolve(OUTPUT_DIR, 'visual-qa-summary.json'),
    JSON.stringify(
      {
        baseUrl: BASE_URL,
        programId,
        ...log,
      },
      null,
      2,
    ),
    'utf-8',
  );

  await browser.close();
}

main().catch(async (error) => {
  await fs.writeFile(
    path.resolve(OUTPUT_DIR, 'visual-qa-error.json'),
    JSON.stringify({ error: error instanceof Error ? error.message : String(error) }, null, 2),
    'utf-8',
  ).catch(() => {});
  console.error(error);
  process.exit(1);
});
