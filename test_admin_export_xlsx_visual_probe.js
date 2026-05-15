#!/usr/bin/env node
(async () => {
  const fs = require('fs');
  const path = require('path');
  const { chromium } = require('playwright');
  const BASE='http://localhost:8082';
  const ROOT='/Users/fuwuqi/检测报告生成系统_X1';
  const OUT=path.join(ROOT,'reports_x1');
  if(!fs.existsSync(OUT)) fs.mkdirSync(OUT,{recursive:true});
  const stamp=new Date().toISOString().replace(/[-:TZ.]/g,'').slice(0,14);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1680, height: 2400 } });
  const page = await context.newPage();

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

  // 先造一条最新导出，确保命中新链路 xlsx
  const saveRes = await page.evaluate(async () => {
    const payload = {
      project_name: 'xlsx导出页面真验',
      report_number: 'XLSX-WEB-001',
      client_name: '页面真验单位',
      contact_info: '13800000000',
      project_address: '上海市测试路excel1号',
      inspection_area: '电子车间导出真验区',
      detection_date: '2026-05-04',
      detection_state: '静态',
      domain: 'electronics',
      domain_name: '电子工业',
      rooms: [{
        room_id: 'r1',
        room_name: '电子车间1',
        type_id: 'electronics_workshop',
        type_name: '洁净车间',
        clean_class: 'ISO 6',
        context: { iso_level: 'ISO 6' },
        summary: { result_state: '不合格', input_result_state: '合格', judgement_engine: 'electronics_workshop_v1', judgement_reason: 'xlsx页面真验', judgement_overridden: true, abnormal_items: [{ item_name: '压差', result: '不合格' }] },
        params: { pressure: { pairs: [{ refRoom: '相对房间1', range: '≥5', values: ['3'] }], primarySummary: '相对房间1:3.0 Pa[数据库:≥5]', result: '不合格' } }
      }]
    };
    return fetch('/api/x/submit_export', { method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin', body: JSON.stringify({ project: payload }) }).then(r=>r.json());
  });

  const exportId = saveRes.export_id;
  await page.goto(`${BASE}/admin`, { waitUntil:'networkidle' });
  await page.waitForTimeout(1200);
  await page.click('text=报告管理');
  await page.waitForTimeout(2200);

  const probe = await page.evaluate((exportId) => {
    const items = Array.from(document.querySelectorAll('.record-item'));
    const target = items.find(el => el.innerText.includes(exportId));
    if(!target) return { found:false };
    const links = Array.from(target.querySelectorAll('a')).map(a => ({ text: a.innerText.trim(), href: a.getAttribute('href') || '' }));
    return {
      found: true,
      text: target.innerText,
      links,
      localExportHref: (links.find(x => x.text.includes('本地记录')) || {}).href || '',
      hasFeishuExport: links.some(x => x.text.includes('飞书记录')),
      hasLocalExport: links.some(x => x.text.includes('本地记录')),
      localExportIsXlsx: ((links.find(x => x.text.includes('本地记录')) || {}).href || '').endsWith('.xlsx')
    };
  }, exportId);

  const shot = path.join(OUT, `admin_export_xlsx_visual_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const result = { exportId, xlsxPath: saveRes.xlsx_path || '', docxPath: saveRes.docx_path || '', probe, screenshot: shot, ok: !!saveRes.xlsx_path && probe.found && probe.hasFeishuExport && probe.hasLocalExport && probe.localExportIsXlsx };
  const jsonPath = path.join(OUT, `admin_export_xlsx_visual_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2), 'utf8');
  console.log(JSON.stringify({ ...result, jsonPath }, null, 2));
  await browser.close();
  if(!result.ok) process.exit(1);
})();
