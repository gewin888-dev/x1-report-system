#!/usr/bin/env node
(async () => {
  const { chromium } = require('playwright');
  const BASE = 'http://localhost:8082';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[name="username"], #username', 'admin');
  await page.fill('input[name="password"], #password', 'admin123');
  await Promise.all([
    page.waitForLoadState('networkidle'),
    page.click('button[type="submit"], .btn-login, input[type="submit"]')
  ]);
  console.log('URL', page.url());
  const title = await page.title();
  console.log('TITLE', title);
  const body = await page.locator('body').innerText();
  console.log('BODY_SNIPPET', body.slice(0, 2000));
  const buttons = await page.locator('button').evaluateAll(nodes => nodes.map(n => ({text:n.innerText, cls:n.className, onclick:n.getAttribute('onclick')})));
  console.log('BUTTONS', JSON.stringify(buttons, null, 2));
  const tabs = await page.locator('.tab-btn').evaluateAll(nodes => nodes.map(n => ({text:n.innerText, onclick:n.getAttribute('onclick')})));
  console.log('TABS', JSON.stringify(tabs, null, 2));
  await browser.close();
})();
