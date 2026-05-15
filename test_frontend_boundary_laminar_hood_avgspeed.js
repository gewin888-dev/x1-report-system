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

  const cases = [
    { id: 'laminar_avgspeed_low_out_front', val: '0.35', expectPass: false },
    { id: 'laminar_avgspeed_low_in_front', val: '0.36', expectPass: true },
    { id: 'laminar_avgspeed_high_out_front', val: '0.55', expectPass: false },
  ];

  await login();
  const results = [];
  for (const c of cases) {
    const saveRes = await page.evaluate(async (c) => {
      const payload = {
        project_name: c.id, report_number: c.id, client_name: '边界测试单位', contact_info: '13800000000',
        project_address: '上海市浦东新区测试路1号', inspection_area: '层流罩边界真验', detection_date: '2026-05-03', detection_state: '静态',
        weather: { temperature: '22', humidity: '50', pressure: '1013' }, domain: 'pharma', domain_name: '制药工业', detection_type: 'laminar_hood', detection_type_name: '层流罩',
        basis: ['GB 50591-2010'], judgement: ['GB 50591-2010'],
        rooms: [{
          id: 'r1', name: c.id, type_id: 'laminar_hood', type_name: '层流罩', level_name: '层流罩', clean_class: '层流罩', business_domain_hint: 'pharma',
          basis: ['GB 50591-2010'], basis_dataset: ['GB 50591-2010'], judgement: ['GB 50591-2010'], judgement_checked: ['GB 50591-2010'], judgement_active: ['GB 50591-2010'], judgement_priority: ['GB 50591-2010'],
          params: { avg_speed: { values: [c.val], result: '' } },
          summary: {
            result_state: c.expectPass ? '合格' : '不合格', input_result_state: c.expectPass ? '合格' : '不合格', judgement_engine: 'laminar_hood_v1', judgement_reason: c.expectPass ? '边界值命中合格区间' : '边界值落在不合格区间', judgement_overridden: false,
            abnormal_items: c.expectPass ? [] : [{ key: 'avg_speed', value: Number(c.val), range: '0.36~0.54m/s', passed: false }]
          }
        }], inspector: 'admin'
      };
      return fetch('/api/save', { method: 'POST', headers: {'Content-Type':'application/json'}, credentials: 'same-origin', body: JSON.stringify(payload) }).then(r=>r.json());
    }, c);
    const draftId = saveRes.record_id || saveRes.draft_id || '';
    await page.evaluate((id) => loadRecordForEdit(id), draftId);
    await page.waitForTimeout(1800);
    const probe = await page.evaluate((c) => {
      const card = document.querySelector('#roomsContainer .room-card');
      const pb = document.querySelector('[data-pk="avg_speed"]');
      const resultText = pb?.querySelector('.cv[data-res]')?.textContent?.trim() || '';
      const roomSummaryText = document.querySelector('.room-summary')?.innerText || '';
      const pagePass = /✅|合格/.test(resultText) || /结果:合格/.test(roomSummaryText);
      return { caseId: c.id, expectedPass: c.expectPass, resultText, roomSummaryText, dataset: card ? {...card.dataset} : null, pagePass };
    }, c);
    results.push({ caseId: c.id, expectedPass: c.expectPass, actualPass: probe.pagePass, status: probe.pagePass === c.expectPass ? 'PASS' : 'FAIL', probe });
  }

  const jsonPath = path.join(OUT, `frontend_boundary_laminar_hood_avgspeed_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ cases: results }, null, 2), 'utf8');
  console.log(JSON.stringify({ jsonPath, cases: results }, null, 2));
  await browser.close();
})();
