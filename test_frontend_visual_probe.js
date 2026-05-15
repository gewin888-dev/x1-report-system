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
  const stamp='20260503_1450';

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
      project_name: '前台真验-pass_box',
      report_number: 'PDJC-BG2026-19WEB1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验区',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'pharma',
      domain_name: '制药工业',
      detection_type: 'pass_box',
      detection_type_name: '传递窗',
      basis: ['GB 50591-2010'],
      judgement: ['JG/T 382-2012','GB 50591-2010'],
      rooms: [{
        id: 'r1',
        name: '前台真验传递窗',
        type_id: 'pass_box',
        type_name: '传递窗',
        basis: ['GB 50591-2010'],
        basis_dataset: ['GB 50591-2010'],
        judgement: ['JG/T 382-2012','GB 50591-2010'],
        judgement_checked: ['JG/T 382-2012','GB 50591-2010'],
        judgement_active: ['JG/T 382-2012','GB 50591-2010'],
        judgement_priority: ['JG/T 382-2012','GB 50591-2010'],
        business_domain_hint: 'pharma',
        pass_box_judgement_active: ['JG/T 382-2012','GB 50591-2010'],
        pass_box_result_state: '不合格',
        params: {
          noise: { background: 40, room_noise: 80, result: '不合格' },
          hepa_leak: { points: [{ value: 0.05 }], result: '不合格' }
        },
        summary: {
          result_state: '不合格',
          input_result_state: '合格',
          judgement_engine: 'pass_box_v1',
          judgement_reason: '存在超出标准范围的检测项',
          judgement_overridden: true,
          abnormal_items: [
            { key: 'noise', value: 80, range: '≤68', passed: false },
            { key: 'hepa_leak', value: 0.05, range: '≤0.01%', passed: false }
          ]
        }
      }],
      inspector: 'admin'
    };
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    }).then(r=>r.json());
    return res;
  });
  const draftId = saveRes.record_id || saveRes.draft_id || '';

  await page.evaluate((id) => loadRecordForEdit(id), draftId);
  await page.waitForTimeout(2500);

  const probe = await page.evaluate(() => {
    const card = document.querySelector('#roomsContainer .room-card');
    return {
      title: document.title,
      activeTab: document.querySelector('.tab-btn.active')?.innerText || '',
      roomCount: document.getElementById('roomsContainer')?.children?.length || 0,
      projectSummary: document.getElementById('projectInfoSummary')?.innerText || '',
      roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
      dataset: card ? {...card.dataset} : null,
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const shot = path.join(OUT, `frontend_restore_pass_box_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const jsonPath = path.join(OUT, `frontend_restore_visual_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
