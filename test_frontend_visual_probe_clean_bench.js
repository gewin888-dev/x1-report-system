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
      project_name: '前台真验-clean_bench',
      report_number: 'PDJC-BG2026-19WEB-CB1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验洁净工作台',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'biosafety',
      domain_name: '生物安全',
      detection_type: 'clean_bench',
      detection_type_name: '洁净工作台',
      basis: ['JG/T 292-2010'],
      judgement: ['JG/T 292-2010'],
      rooms: [{
        id: 'r1', name: '洁净工作台01', type_id: 'clean_bench', type_name: '洁净工作台',
        level_name: '洁净工作台', clean_class: '洁净工作台',
        basis: ['JG/T 292-2010'], basis_dataset: ['JG/T 292-2010'],
        judgement: ['JG/T 292-2010'], judgement_checked: ['JG/T 292-2010'], judgement_active: ['JG/T 292-2010'], judgement_priority: ['JG/T 292-2010'],
        params: {
          avg_speed: { values: ['0.10'], result: '不合格' },
          noise: { values: ['75'], result: '不合格' },
          illumination: { values: ['100'], result: '不合格' },
          hepa_leak: { values: ['0.20'], result: '不合格' }
        },
        summary: {
          result_state: '不合格', input_result_state: '合格', judgement_engine: 'clean_bench_v1', judgement_reason: '存在超出标准范围的检测项', judgement_overridden: true,
          abnormal_items: [
            { key: 'avg_speed', value: 0.10, range: '0.3~0.6m/s', passed: false },
            { key: 'noise', value: 75, range: '≤65dB(A)', passed: false },
            { key: 'illumination', value: 100, range: '≥300lx', passed: false },
            { key: 'hepa_leak', value: 0.20, range: '≤0.01%', passed: false }
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
        avgSpeedInputs: getInputValues('avg_speed'),
        noiseInputs: getInputValues('noise'),
        illuminationInputs: getInputValues('illumination'),
        hepaInputs: getInputValues('hepa_leak'),
        avgSpeedResult: getResultText('avg_speed'),
        noiseResult: getResultText('noise'),
        illuminationResult: getResultText('illumination'),
        hepaResult: getResultText('hepa_leak')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const pngName = `frontend_restore_clean_bench_${stamp}_clean_bench.png`;
  const jsonName = `frontend_restore_clean_bench_${stamp}_clean_bench.json`;
  const shot = path.join(OUT, pngName);
  await page.screenshot({ path: shot, fullPage: true });
  const jsonPath = path.join(OUT, jsonName);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
