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

  const CASES = [
    { level: 'ISO 6', bsl: 'BSL-2（P2）', pressureRange: '-10~-15', pressureValue: '-20' },
    { level: 'ISO 7', bsl: 'BSL-2（P2）', pressureRange: '-10~-15', pressureValue: '-20' },
    { level: 'ISO 8', bsl: 'BSL-2（P2）', pressureRange: '-10~-15', pressureValue: '-20' },
    { level: 'ISO 9', bsl: 'BSL-2（P2）', pressureRange: '-10~-15', pressureValue: '-20' }
  ];

  await login();
  const results = [];

  for (const c of CASES) {
    const saveRes = await page.evaluate(async (c) => {
      const payload = {
        project_name: `前台真验-bsl-${c.level}`,
        report_number: `PDJC-BG2026-19WEB-BSL-${c.level.replace(/\s+/g,'')}`,
        client_name: '前台真验客户',
        contact_info: '13800000000',
        project_address: '上海市浦东新区测试路1号',
        inspection_area: `前台真验BSL实验室-${c.level}`,
        detection_date: '2026-05-03',
        detection_state: '静态',
        weather: { temperature: '22', humidity: '50', pressure: '1013' },
        domain: 'biosafety',
        domain_name: '生物安全',
        detection_type: 'bsl',
        detection_type_name: '生物安全实验室',
        basis: ['GB 50346-2011'],
        judgement: ['GB 50346-2011'],
        rooms: [{
          id: 'r1',
          name: `前台真验P2实验室-${c.level}`,
          type_id: 'bsl',
          type_name: '生物安全实验室',
          level_name: c.level,
          clean_class: c.level,
          bsl: c.bsl,
          context: { bsl_level: c.bsl },
          basis: ['GB 50346-2011'],
          basis_dataset: ['GB 50346-2011'],
          judgement: ['GB 50346-2011'],
          judgement_checked: ['GB 50346-2011'],
          judgement_active: ['GB 50346-2011'],
          judgement_priority: ['GB 50346-2011'],
          params: {
            pressure: {
              pairs: [{ refRoom: '走廊', type: 'negative', range: c.pressureRange, values: [c.pressureValue] }],
              primarySummary: `走廊:${c.pressureValue}.0 Pa[数据库:${c.pressureRange}]`,
              result: '不合格'
            },
            temperature: { values: ['30'], result: '不合格' },
            humidity: { values: ['80'], result: '不合格' },
            noise: { background: '40', room_noise: '70', result: '不合格' }
          },
          summary: {
            result_state: '不合格',
            input_result_state: '合格',
            judgement_engine: 'bsl_v1',
            judgement_reason: '存在超出标准范围的检测项',
            judgement_overridden: true,
            abnormal_items: []
          }
        }],
        inspector: 'admin'
      };
      return fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      }).then(r=>r.json());
    }, c);

    const draftId = saveRes.record_id || saveRes.draft_id || '';
    await page.evaluate((id) => loadRecordForEdit(id), draftId);
    await page.waitForTimeout(2800);

    const probe = await page.evaluate((level) => {
      const card = document.querySelector('#roomsContainer .room-card');
      const getResultText = (pk) => {
        const pb = card?.querySelector(`[data-pk="${pk}"]`);
        return pb?.querySelector('.cv[data-res]')?.textContent?.trim() || null;
      };
      return {
        level,
        roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
        dataset: card ? {...card.dataset} : null,
        pressureResult: getResultText('pressure'),
        temperatureResult: getResultText('temperature'),
        humidityResult: getResultText('humidity'),
        noiseResult: getResultText('noise'),
        bodySnippet: document.body.innerText.slice(0, 4500)
      };
    }, c.level);

    results.push({ level: c.level, draftId, probe });
  }

  const jsonPath = path.join(OUT, `frontend_restore_bsl_multilevel_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ results }, null, 2), 'utf8');
  console.log(JSON.stringify({ jsonPath, results }, null, 2));
  await browser.close();
})();
