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
      project_name: '前台真验-laminar_hood',
      report_number: 'PDJC-BG2026-19WEB-LH1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验层流罩',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'pharma',
      domain_name: '制药工业',
      detection_type: 'laminar_hood',
      detection_type_name: '层流罩',
      basis: ['GB 50591-2010'],
      judgement: ['GB 50591-2010'],
      rooms: [{
        id: 'r1', name: '层流罩01', type_id: 'laminar_hood', type_name: '层流罩',
        level_name: '层流罩', clean_class: '层流罩', business_domain_hint: 'pharma',
        basis: ['GB 50591-2010'], basis_dataset: ['GB 50591-2010'],
        judgement: ['GB 50591-2010'], judgement_checked: ['GB 50591-2010'], judgement_active: ['GB 50591-2010'], judgement_priority: ['GB 50591-2010'],
        params: {
          avg_speed: { values: ['0.55'], result: '不合格' },
          hepa_leak: { values: ['0.02'], result: '不合格' },
          airflow_pattern: { value: '不符合要求', result: '不合格' }
        },
        summary: {
          result_state: '不合格', input_result_state: '合格', judgement_engine: 'laminar_hood_v1', judgement_reason: '存在超出标准范围的检测项', judgement_overridden: true,
          abnormal_items: [
            { key: 'avg_speed', value: 0.55, range: '0.36~0.54m/s', passed: false },
            { key: 'hepa_leak', value: 0.02, range: '≤0.01%', passed: false },
            { key: 'airflow_pattern', value: '不符合要求', range: '气流垂直向下、无旋涡', passed: false }
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
    return {
      title: document.title,
      projectSummary: document.getElementById('projectInfoSummary')?.innerText || '',
      roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
      dataset: card ? {...card.dataset} : null,
      restoredParams: {
        avgSpeedResult: getResultText('avg_speed'),
        hepaLeakResult: getResultText('hepa_leak'),
        airflowPatternResult: getResultText('airflow_pattern')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const pngName = `frontend_restore_laminar_hood_${stamp}_laminar_hood.png`;
  const jsonName = `frontend_restore_laminar_hood_${stamp}_laminar_hood.json`;
  const shot = path.join(OUT, pngName);
  await page.screenshot({ path: shot, fullPage: true });
  const jsonPath = path.join(OUT, jsonName);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
