#!/usr/bin/env node
(async () => {
  const fs = require('fs');
  const path = require('path');
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 2200 } });
  const page = await context.newPage();
  const BASE='http://localhost:8082';
  const OUT=path.join(process.cwd(),'reports_x1');
  if(!fs.existsSync(OUT)) fs.mkdirSync(OUT,{recursive:true});
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g,'').slice(0,14);
  const targetName = 'feishu_fail_probe_20260503_151802';

  async function login(){
    await page.goto(`${BASE}/login`, { waitUntil:'networkidle' });
    await page.fill('input[name="username"], #username', 'admin');
    await page.fill('input[name="password"], #password', 'admin123');
    await Promise.all([
      page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20000 }),
      page.click('button[type="submit"], .btn-login, input[type="submit"]')
    ]);
    await page.waitForLoadState('networkidle');
  }

  await login();
  await page.goto(`${BASE}/admin`, { waitUntil:'networkidle' });
  await page.waitForTimeout(1500);
  await page.click('text=报告管理');
  await page.waitForTimeout(2500);

  const probe = await page.evaluate((targetName) => {
    const items = Array.from(document.querySelectorAll('.record-item'));
    const target = items.find(el => el.innerText.includes(targetName));
    return {
      found: !!target,
      targetText: target ? target.innerText : '',
      hasReportSuccess: target ? target.innerText.includes('报告飞书✅') : false,
      hasExportSuccess: target ? target.innerText.includes('记录飞书✅') : false,
      pageTextSnippet: document.body.innerText.slice(0, 8000)
    };
  }, targetName);

  const shot = path.join(OUT, `admin_feishu_status_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const result = {
    targetName,
    probe,
    screenshot: shot,
    ok: probe.found && probe.hasReportSuccess && probe.hasExportSuccess
  };

  const jsonPath = path.join(OUT, `admin_feishu_status_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2), 'utf8');
  console.log(JSON.stringify({ ...result, jsonPath }, null, 2));
  await browser.close();
  if(!result.ok) process.exit(1);
})();
