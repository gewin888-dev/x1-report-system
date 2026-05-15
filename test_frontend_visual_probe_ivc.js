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
      project_name: '前台真验-ivc',
      report_number: 'PDJC-BG2026-19WEB-IVC1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验IVC笼具',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'biosafety',
      domain_name: '生物安全',
      detection_type: 'ivc',
      detection_type_name: 'IVC笼具',
      basis: ['GB 14925-2023'],
      judgement: ['GB 14925-2023'],
      rooms: [{
        id: 'r1', name: 'IVC笼具01', type_id: 'ivc', type_name: 'IVC笼具',
        level_name: 'IVC', clean_class: 'IVC', length: '4', width: '3', height: '4.2',
        basis: ['GB 14925-2023'], basis_dataset: ['GB 14925-2023'],
        judgement: ['GB 14925-2023'], judgement_checked: ['GB 14925-2023'], judgement_active: ['GB 14925-2023'], judgement_priority: ['GB 14925-2023'],
        params: {
          airflow_speed: { values: ['0.10'], result: '不合格' },
          airchange: { type: 'airchange_speed', vents: [{ area: '0.20', speed: '0.56', volume: '403.2' }], result: '不合格' },
          airtightness: { values: ['0.20'], result: '不合格' },
          hepa_integrity: { values: ['0.20'], result: '不合格' }
        },
        summary: {
          result_state: '不合格', input_result_state: '合格', judgement_engine: 'ivc_v1', judgement_reason: '存在超出标准范围的检测项', judgement_overridden: true,
          abnormal_items: [
            { key: 'airflow_speed', value: 0.10, range: '符合设备设定', passed: false },
            { key: 'airchange', value: 8, range: '符合设备设定', passed: false },
            { key: 'airtightness', value: 0.20, range: '≤0.05', passed: false },
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
    const rid = card?.dataset?.rid || null;
    const getResultText = (pk) => document.querySelector(`[data-pk="${pk}"] .cv[data-res]`)?.textContent?.trim() || null;
    const getInputValues = (pk) => Array.from(document.querySelectorAll(`[data-pk="${pk}"] input`)).map(i => i.value);
    const ivcDimWrap = card?.querySelector('[data-ivc-airchange-dimensions]');
    const ivcDimensions = ivcDimWrap ? {
      length: ivcDimWrap.querySelector('[data-dim="length"]')?.value || '',
      width: ivcDimWrap.querySelector('[data-dim="width"]')?.value || '',
      height: ivcDimWrap.querySelector('[data-dim="height"]')?.value || ''
    } : null;
    const roomVolume = (rid && typeof getRoomVolume === 'function') ? getRoomVolume(rid) : null;
    return {
      title: document.title,
      projectSummary: document.getElementById('projectInfoSummary')?.innerText || '',
      roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
      dataset: card ? {...card.dataset} : null,
      ivcStoredDimensions: card ? {
        roomLength: card.dataset.roomLength || '',
        roomWidth: card.dataset.roomWidth || '',
        roomHeight: card.dataset.roomHeight || ''
      } : null,
      ivcDimensions,
      roomVolume,
      restoredParams: {
        airflowInputs: getInputValues('airflow_speed'),
        airchangeInputs: getInputValues('airchange'),
        airtightnessInputs: getInputValues('airtightness'),
        hepaInputs: getInputValues('hepa_integrity'),
        airflowResult: getResultText('airflow_speed'),
        airchangeResult: getResultText('airchange'),
        airtightnessResult: getResultText('airtightness'),
        hepaResult: getResultText('hepa_integrity')
      },
      bodySnippet: document.body.innerText.slice(0, 5000)
    };
  });

  const pngName = `frontend_restore_ivc_${stamp}_ivc.png`;
  const jsonName = `frontend_restore_ivc_${stamp}_ivc.json`;
  const shot = path.join(OUT, pngName);
  await page.screenshot({ path: shot, fullPage: true });
  const jsonPath = path.join(OUT, jsonName);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
