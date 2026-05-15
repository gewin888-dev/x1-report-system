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
      project_name: '前台真验-food_workshop',
      report_number: 'PDJC-BG2026-19WEB-FOOD1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验食品车间',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'food',
      domain_name: '食品加工',
      detection_type: 'food_workshop',
      detection_type_name: '洁净车间',
      basis: ['GB 50591-2010'],
      judgement: ['GB 50687-2011'],
      rooms: [{
        id: 'r1',
        name: '前台真验食品Ⅲ级车间',
        type_id: 'food_workshop',
        type_name: '洁净车间',
        level_name: 'Ⅲ级',
        clean_class: 'Ⅲ级',
        context: { food_grade: 'Ⅲ级' },
        basis: ['GB 50591-2010'],
        basis_dataset: ['GB 50591-2010'],
        judgement: ['GB 50687-2011'],
        judgement_checked: ['GB 50687-2011'],
        judgement_active: ['GB 50687-2011'],
        judgement_priority: ['GB 50687-2011'],
        params: {
          airchange: { values: ['10'], result: '不合格' },
          pressure: { pairs: [{ refRoom: '相对房间1', range: '≥10', values: ['8'] }], primarySummary: '相对房间1:8.0 Pa[手动:≥10]', result: '不合格' },
          noise: { background: '40', room_noise: '70', result: '不合格' }
        },
        summary: {
          result_state: '不合格',
          input_result_state: '合格',
          judgement_engine: 'food_workshop_v1',
          judgement_reason: '存在超出标准范围的检测项',
          judgement_overridden: true,
          abnormal_items: [
            { key: 'airchange', value: 10, range: '≥15次/h', passed: false },
            { key: 'pressure', value: 8, range: '≥10Pa', passed: false },
            { key: 'noise', value: 70, range: '≤65dB(A)', passed: false }
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
    const getResultText = (pk) => {
      const pb = card?.querySelector(`[data-pk="${pk}"]`);
      return pb?.querySelector('.cv[data-res]')?.textContent?.trim() || null;
    };
    const getInputValues = (pk) => {
      const pb = card?.querySelector(`[data-pk="${pk}"]`);
      if(!pb) return [];
      return Array.from(pb.querySelectorAll('input'))
        .filter(i => !['button','submit','checkbox','radio'].includes(i.type || 'text'))
        .map(i => i.value);
    };
    return {
      title: document.title,
      activeTab: document.querySelector('.tab-btn.active')?.innerText || '',
      roomCount: document.getElementById('roomsContainer')?.children?.length || 0,
      projectSummary: document.getElementById('projectInfoSummary')?.innerText || '',
      roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
      dataset: card ? {...card.dataset} : null,
      restoredParams: {
        airchangeInputs: getInputValues('airchange'),
        pressureInputs: getInputValues('pressure'),
        noiseInputs: getInputValues('noise'),
        airchangeResult: getResultText('airchange'),
        pressureResult: getResultText('pressure'),
        noiseResult: getResultText('noise')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const pngName = `frontend_restore_food_workshop_${stamp}_food_workshop.png`;
  const jsonName = `frontend_restore_food_workshop_${stamp}_food_workshop.json`;
  const shot = path.join(OUT, pngName);
  await page.screenshot({ path: shot, fullPage: true });

  const jsonPath = path.join(OUT, jsonName);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
