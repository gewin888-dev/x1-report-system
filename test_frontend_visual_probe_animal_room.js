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
  const stamp='20260503_1734';

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
      project_name: '前台真验-animal_room',
      report_number: 'PDJC-BG2026-19WEB-AR1',
      client_name: '前台真验客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '前台真验动物房',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'biosafety',
      domain_name: '生物安全',
      detection_type: 'animal_room',
      detection_type_name: '动物房',
      basis: ['GB 14925-2023'],
      judgement: ['GB 14925-2023'],
      rooms: [{
        id: 'r1',
        name: '前台真验动物房洁净走廊',
        type_id: 'animal_room',
        type_name: '动物房',
        level_name: '屏障环境',
        clean_class: '屏障环境',
        context: { barrier_room_class: '洁净辅房', barrier_aux_room: '洁净走廊' },
        barrier_room_class: '洁净辅房',
        barrier_aux_room: '洁净走廊',
        basis: ['GB 14925-2023'],
        basis_dataset: ['GB 14925-2023'],
        judgement: ['GB 14925-2023'],
        judgement_checked: ['GB 14925-2023'],
        judgement_active: ['GB 14925-2023'],
        judgement_priority: ['GB 14925-2023'],
        params: {
          temperature_aux: { values: ['30'], result: '不合格' },
          humidity_aux: { values: ['80'], result: '不合格' }
        },
        summary: {
          result_state: '不合格',
          input_result_state: '合格',
          judgement_engine: 'animal_room_v1',
          judgement_reason: '存在超出标准范围的检测项',
          judgement_overridden: true,
          abnormal_items: [
            { key: 'temperature', value: 30, range: '20~26℃', passed: false },
            { key: 'humidity', value: 80, range: '40~70%', passed: false }
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
        temperatureInputs: getInputValues('temperature_aux'),
        humidityInputs: getInputValues('humidity_aux'),
        temperatureResult: getResultText('temperature_aux'),
        humidityResult: getResultText('humidity_aux')
      },
      bodySnippet: document.body.innerText.slice(0, 5000),
      debug: {
        cardTypeId: card?.dataset?.typeId || '',
        cardDomain: card?.dataset?.domain || '',
        detTypeId: (() => {
          try { return (typeof getRoomDetType === 'function' ? (getRoomDetType(card?.dataset?.rid || '')?.id || '') : ''); } catch(e){ return `ERR:${e.message}`; }
        })(),
        detTypeParamKeys: (() => {
          try { return (typeof getRoomDetType === 'function' ? ((getRoomDetType(card?.dataset?.rid || '')?.params || []).map(p => p.key)) : []); } catch(e){ return [`ERR:${e.message}`]; }
        })(),
        animalRestoreBranch: card?.dataset?.animalRestoreBranch || '',
        animalRestoreCleanClass: card?.dataset?.animalRestoreCleanClass || '',
        animalRestoreBarrierRoomClass: card?.dataset?.animalRestoreBarrierRoomClass || '',
        animalRestoreBarrierAuxRoom: card?.dataset?.animalRestoreBarrierAuxRoom || '',
        restoreStage: card?.dataset?.restoreStage || '',
        barrierRoomClassDataset: card?.dataset?.barrierRoomClass || '',
        barrierAuxRoomDataset: card?.dataset?.barrierAuxRoom || '',
        barrierRoomOptionsHtml: card?.querySelector('.room-barrier-room-class-options')?.innerHTML || '',
        barrierAuxOptionsHtml: card?.querySelector('.room-barrier-aux-options')?.innerHTML || '',
        activeBarrierRoomButtons: Array.from(card?.querySelectorAll('.room-barrier-room-class-options .level-btn.active') || []).map(x => x.textContent.trim()),
        activeBarrierAuxButtons: Array.from(card?.querySelectorAll('.room-barrier-aux-options .level-btn.active') || []).map(x => x.textContent.trim())
      }
    };
  });

  const shot = path.join(OUT, `frontend_restore_animal_room_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const jsonPath = path.join(OUT, `frontend_restore_animal_room_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ draftId, probe, screenshot: shot }, null, 2), 'utf8');
  console.log(JSON.stringify({ draftId, probe, screenshot: shot, jsonPath }, null, 2));
  await browser.close();
})();
