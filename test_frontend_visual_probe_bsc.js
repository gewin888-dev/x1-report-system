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
  const stamp=new Date().toISOString().replace(/[-:TZ.]/g,'').slice(0,12);

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
  const saveRes = await page.evaluate(async () => {
    const payload = {
      project_name: '前台真验-bsc',
      report_number: 'PDJC-BG2026-19WEB-BSC1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验生物安全柜',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'biosafety',
      domain_name: '生物安全',
      detection_type: 'bsc',
      detection_type_name: '生物安全柜',
      basis: ['GB 41918-2022'],
      judgement: ['GB 41918-2022'],
      rooms: [{
        id: 'r1', name: '生物安全柜01', type_id: 'bsc', type_name: '生物安全柜',
        level_name: 'BSC', clean_class: 'BSC', context: { bsc_model: 'Ⅱ级A2型' }, bsc_model: 'Ⅱ级A2型',
        basis: ['GB 41918-2022'], basis_dataset: ['GB 41918-2022'],
        judgement: ['GB 41918-2022'], judgement_checked: ['GB 41918-2022'], judgement_active: ['GB 41918-2022'], judgement_priority: ['GB 41918-2022'],
        params: {
          downflow_speed: { values: ['0.10'], result: '不合格' },
          inflow_speed: { values: ['0.10'], result: '不合格' },
          noise: { values: ['75'], result: '不合格' },
          illumination: { values: ['200'], result: '不合格' },
          hepa_integrity: { values: ['0.20'], result: '不合格' }
        },
        summary: {
          result_state: '不合格', input_result_state: '合格', judgement_engine: 'bsc_v1', judgement_reason: '存在超出标准范围的检测项', judgement_overridden: true,
          abnormal_items: [
            { key: 'downflow_speed', value: 0.10, range: '0.25~0.5m/s', passed: false },
            { key: 'inflow_speed', value: 0.10, range: '≥0.45m/s', passed: false },
            { key: 'noise', value: 75, range: '≤67dB(A)', passed: false },
            { key: 'illumination', value: 200, range: '≥650lx', passed: false },
            { key: 'hepa_integrity', value: 0.20, range: '≤0.01%', passed: false }
          ]
        }
      }], inspector: 'admin'
    };
    return fetch('/api/save', { method: 'POST', headers: {'Content-Type':'application/json'}, credentials: 'same-origin', body: JSON.stringify(payload) }).then(r=>r.json());
  });
  const draftId = saveRes.record_id || saveRes.draft_id || '';
  await page.evaluate((id) => loadRecordForEdit(id), draftId);
  await page.waitForTimeout(2500);

  const probe = await page.evaluate(() => {
    const card = document.querySelector('#roomsContainer .room-card');
    const getResultText = (pk) => document.querySelector(`[data-pk="${pk}"] .cv[data-res]`)?.textContent?.trim() || null;
    const getInputValues = (pk) => Array.from(document.querySelectorAll(`[data-pk="${pk}"] input`)).map(i => i.value);
    return {
      title: document.title,
      projectSummary: document.getElementById('projectInfoSummary')?.innerText || '',
      roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
      dataset: card ? {...card.dataset} : null,
      restoredParams: {
        downflowInputs: getInputValues('downflow_speed'),
        inflowInputs: getInputValues('inflow_speed'),
        noiseInputs: getInputValues('noise'),
        illuminationInputs: getInputValues('illumination'),
        hepaInputs: getInputValues('hepa_integrity'),
        downflowResult: getResultText('downflow_speed'),
        inflowResult: getResultText('inflow_speed'),
        noiseResult: getResultText('noise'),
        illuminationResult: getResultText('illumination'),
        hepaResult: getResultText('hepa_integrity')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const pngName = `frontend_restore_bsc_${stamp}_bsc.png`;
  const jsonName = `frontend_restore_bsc_${stamp}_bsc.json`;
  const shot = path.join(OUT, pngName);
  await page.screenshot({ path: shot, fullPage: true });
  const jsonPath = path.join(OUT, jsonName);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
