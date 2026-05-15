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
  const stamp='20260503_1539';

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
      project_name: '前台真验-operating_room',
      report_number: 'PDJC-BG2026-19WEB-OR1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验手术部',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'hospital',
      domain_name: '医院洁净部',
      detection_type: 'operating_room',
      detection_type_name: '手术室',
      basis: ['GB 50333-2013'],
      judgement: ['GB 50333-2013'],
      rooms: [{
        id: 'r1',
        name: '前台真验刷手间',
        type_id: 'operating_room',
        type_name: '手术室',
        level_name: 'Ⅱ级（7级）',
        clean_class: 'Ⅱ级（7级）',
        context: { surgery_room_type: '辅房', surgery_aux_room: '刷手间', surgery_aux_clean_class: 'Ⅱ级辅房' },
        basis: ['GB 50333-2013'],
        basis_dataset: ['GB 50333-2013'],
        judgement: ['GB 50333-2013'],
        judgement_checked: ['GB 50333-2013'],
        judgement_active: ['GB 50333-2013'],
        judgement_priority: ['GB 50333-2013'],
        params: {
          temperature: { values: ['35'], result: '不合格' },
          humidity: { values: ['80'], result: '不合格' },
          noise: { background: '40', room_noise: '65', result: '不合格' }
        },
        summary: {
          result_state: '不合格',
          input_result_state: '合格',
          judgement_engine: 'operating_room_v1',
          judgement_reason: '存在超出标准范围的检测项',
          judgement_overridden: true,
          abnormal_items: [
            { key: 'temperature', value: 35, range: '21~27℃', passed: false },
            { key: 'humidity', value: 80, range: '35~60%', passed: false },
            { key: 'noise', value: 65, range: '≤52dB(A)', passed: false }
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
        temperatureInputs: getInputValues('temperature'),
        humidityInputs: getInputValues('humidity'),
        noiseInputs: getInputValues('noise'),
        temperatureResult: getResultText('temperature'),
        humidityResult: getResultText('humidity'),
        noiseResult: getResultText('noise')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const shot = path.join(OUT, `frontend_restore_operating_room_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const jsonPath = path.join(OUT, `frontend_restore_operating_room_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
