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
  const stamp='20260503_1907_negative_pressure';

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
      project_name: '前台真验-negative_pressure',
      report_number: 'PDJC-BG2026-19WEB-NP1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验负压病房',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'hospital',
      domain_name: '医院洁净部',
      detection_type: 'negative_pressure',
      detection_type_name: '负压病房',
      basis: ['GB/T 35428-2017'],
      judgement: ['GB/T 35428-2017'],
      rooms: [{
        id: 'r1',
        name: '前台真验负压病房01',
        type_id: 'negative_pressure',
        type_name: '负压病房',
        level_name: '默认',
        clean_class: '默认',
        basis: ['GB/T 35428-2017'],
        basis_dataset: ['GB/T 35428-2017'],
        judgement: ['GB/T 35428-2017'],
        judgement_checked: ['GB/T 35428-2017'],
        judgement_active: ['GB/T 35428-2017'],
        judgement_priority: ['GB/T 35428-2017'],
        params: {
          temperature: { values: ['30'], result: '不合格' },
          humidity: { values: ['80'], result: '不合格' },
          pressure: { values: ['-20'], result: '不合格' },
          noise: { background: '40', room_noise: '70', result: '不合格' }
        },
        summary: {
          result_state: '不合格',
          input_result_state: '合格',
          judgement_engine: 'negative_pressure_v1',
          judgement_reason: '存在超出标准范围的检测项',
          judgement_overridden: true,
          abnormal_items: [
            { key: 'temperature', value: 30, range: '18~26℃', passed: false },
            { key: 'humidity', value: 80, range: '30~60%', passed: false },
            { key: 'pressure', value: -20, range: '-15~-10Pa', passed: false },
            { key: 'noise', value: 70, range: '≤60dB(A)', passed: false }
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
      roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
      dataset: card ? {...card.dataset} : null,
      restoredParams: {
        temperatureInputs: getInputValues('temperature'),
        humidityInputs: getInputValues('humidity'),
        pressureInputs: getInputValues('pressure'),
        noiseInputs: getInputValues('noise'),
        temperatureResult: getResultText('temperature'),
        humidityResult: getResultText('humidity'),
        pressureResult: getResultText('pressure'),
        noiseResult: getResultText('noise')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const shot = path.join(OUT, `frontend_restore_negative_pressure_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const jsonPath = path.join(OUT, `frontend_restore_negative_pressure_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
