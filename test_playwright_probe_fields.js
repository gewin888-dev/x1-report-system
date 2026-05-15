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

  const inputs = await page.locator('input, select, textarea').evaluateAll(nodes => nodes.map(n => ({
    tag:n.tagName,
    type:n.getAttribute('type'),
    id:n.id,
    name:n.getAttribute('name'),
    placeholder:n.getAttribute('placeholder'),
    cls:n.className
  })));
  console.log('FIELDS_BEFORE', JSON.stringify(inputs.slice(0,120), null, 2));

  await page.click('button.add-room-btn');
  await page.waitForTimeout(1000);
  const after = await page.locator('input, select, textarea').evaluateAll(nodes => nodes.map(n => ({
    tag:n.tagName,
    type:n.getAttribute('type'),
    id:n.id,
    name:n.getAttribute('name'),
    placeholder:n.getAttribute('placeholder'),
    cls:n.className
  })));
  console.log('FIELDS_AFTER', JSON.stringify(after.slice(0,200), null, 2));
  const body = await page.locator('body').innerText();
  console.log('BODY_AFTER', body.slice(0,4000));
  await browser.close();
})();
