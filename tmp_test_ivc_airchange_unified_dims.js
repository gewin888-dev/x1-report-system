#!/usr/bin/env node
(async () => {
  const fs = require('fs');
  const path = require('path');
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1800 } });
  const page = await context.newPage();
  const BASE = 'http://127.0.0.1:8082';
  const OUT = path.join(process.cwd(), 'reports_x1');
  if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 12);

  async function login(){
    await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await page.fill('input[name="username"], #username', 'admin');
    await page.fill('input[name="password"], #password', 'admin123');
    await Promise.all([
      page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20000 }),
      page.click('button[type="submit"], .btn-login, input[type="submit"]')
    ]);
    await page.waitForLoadState('networkidle');
  }

  await login();
  await page.goto(`${BASE}/record`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);

  const result = await page.evaluate(async () => {
    const domainBtn = Array.from(document.querySelectorAll('.domain-btn')).find(el => (el.textContent || '').includes('生物安全'));
    if (domainBtn) domainBtn.click();
    await new Promise(r => setTimeout(r, 300));
    const ivcBtn = Array.from(document.querySelectorAll('#detectionTypeList .level-btn')).find(el => (el.textContent || '').includes('IVC'));
    if (ivcBtn) ivcBtn.click();
    await new Promise(r => setTimeout(r, 300));
    const addBtn = document.querySelector('.add-room-btn');
    if (addBtn) addBtn.click();
    await new Promise(r => setTimeout(r, 300));
    const card = document.querySelector('#roomsContainer .room-card:last-child');
    if (!card) return { ok:false, error:'room card not found' };
    const rid = card.dataset.rid;

    const topDims = card.querySelector('[data-room-dimensions]');
    const ivcDims = card.querySelector('[data-ivc-airchange-dimensions]');
    const sizeBlock = card.querySelector('[data-room-size-block]');
    const paramsTop = card.querySelector('.rparams-top');
    const airchangePb = card.querySelector('[data-pk="airchange"]');
    if (!topDims) return { ok:false, error:'top dimensions missing' };
    if (!airchangePb) return { ok:false, error:'airchange block missing' };

    topDims.querySelector('[data-dim="length"]').value = '4';
    topDims.querySelector('[data-dim="width"]').value = '3';
    topDims.querySelector('[data-dim="height"]').value = '2';

    const area = airchangePb.querySelector('[data-va]');
    const speed = airchangePb.querySelector('[data-vs]');
    if (!area || !speed) return { ok:false, error:'airchange vent inputs missing' };
    area.value = '0.2';
    speed.value = '0.5';

    if (typeof calc_airchange === 'function') calc_airchange(rid, 'airchange');
    const volume = (typeof getRoomVolume === 'function') ? getRoomVolume(rid) : null;
    const resultText = airchangePb.querySelector('.cv[data-res]')?.textContent?.trim() || '';
    const resultState = airchangePb.querySelector('.cv[data-res]')?.dataset?.res || '';

    return {
      ok: true,
      rid,
      hasTopDimensions: !!topDims,
      hasIvcInlineDimensions: !!ivcDims,
      sizeBlockInParamsTop: !!(sizeBlock && paramsTop && sizeBlock.parentElement === paramsTop),
      volume,
      resultText,
      resultState
    };
  });

  const pngPath = path.join(OUT, `ivc_airchange_unified_dims_${stamp}.png`);
  const jsonPath = path.join(OUT, `ivc_airchange_unified_dims_${stamp}.json`);
  await page.screenshot({ path: pngPath, fullPage: true });
  fs.writeFileSync(jsonPath, JSON.stringify({ result, pngPath }, null, 2), 'utf8');
  console.log(JSON.stringify({ result, pngPath, jsonPath }, null, 2));
  await browser.close();
})();
