#!/usr/bin/env node
(async () => {
  const fs = require('fs');
  const path = require('path');
  const { chromium } = require('playwright');
  const BASE='http://localhost:8082';
  const OUT=path.join(process.cwd(),'reports_x1');
  if(!fs.existsSync(OUT)) fs.mkdirSync(OUT,{recursive:true});
  const stamp=new Date().toISOString().replace(/[-:TZ.]/g,'').slice(0,12);

  const CASES = [
    { level: 'ISO 5', params: { particle: { values: ['4000', '30'], result: '不合格' }, wind_speed: { values: ['0.10'], result: '不合格' }, pressure: { pairs: [{ refRoom: '相对房间1', range: '≥5', values: ['3'] }], primarySummary: '相对房间1:3.0 Pa[数据库:≥5]', result: '不合格' } } },
    { level: 'ISO 6', params: { particle: { values: ['40000', '400'], result: '不合格' }, airchange: { values: ['40'], result: '不合格' }, pressure: { pairs: [{ refRoom: '相对房间1', range: '≥5', values: ['3'] }], primarySummary: '相对房间1:3.0 Pa[数据库:≥5]', result: '不合格' } } },
    { level: 'ISO 8', params: { particle: { values: ['4000000', '40000'], result: '不合格' }, airchange: { values: ['8'], result: '不合格' }, pressure: { pairs: [{ refRoom: '相对房间1', range: '≥5', values: ['3'] }], primarySummary: '相对房间1:3.0 Pa[数据库:≥5]', result: '不合格' } } },
    { level: 'ISO 9', params: { particle: { values: ['40000000', '400000'], result: '不合格' }, airchange: { values: ['8'], result: '不合格' }, pressure: { pairs: [{ refRoom: '相对房间1', range: '≥5', values: ['3'] }], primarySummary: '相对房间1:3.0 Pa[数据库:≥5]', result: '不合格' } } }
  ];

  const results = [];

  for (const c of CASES) {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1600, height: 2200 } });
    const page = await context.newPage();

    await page.goto(`${BASE}/login`, { waitUntil:'networkidle' });
    await page.fill('input[name="username"], #username', 'admin');
    await page.fill('input[name="password"], #password', 'admin123');
    await Promise.all([
      page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20000 }),
      page.click('button[type="submit"], .btn-login, input[type="submit"]')
    ]);
    await page.waitForLoadState('networkidle');

    const saveRes = await page.evaluate(async (c) => {
      const payload = {
        project_name: `前台真验-electronics-${c.level}`,
        report_number: `PDJC-BG2026-19WEB-E-${c.level.replace(/\s+/g,'')}`,
        client_name: '前台真验客户',
        contact_info: '13800000000',
        project_address: '上海市浦东新区测试路1号',
        inspection_area: `前台真验电子区-${c.level}`,
        detection_date: '2026-05-03',
        detection_state: '静态',
        weather: { temperature: '22', humidity: '50', pressure: '1013' },
        domain: 'electronics',
        domain_name: '电子工业',
        detection_type: 'electronics_workshop',
        detection_type_name: '电子洁净车间',
        basis: ['GB 50591-2010'],
        judgement: ['GB 50472-2008'],
        rooms: [{
          id: 'r1',
          name: `前台真验电子车间-${c.level}`,
          type_id: 'electronics_workshop',
          type_name: '电子洁净车间',
          level_name: c.level,
          clean_class: c.level,
          context: { iso_level: c.level },
          basis: ['GB 50591-2010'],
          basis_dataset: ['GB 50591-2010'],
          judgement: ['GB 50472-2008'],
          judgement_checked: ['GB 50472-2008'],
          judgement_active: ['GB 50472-2008'],
          judgement_priority: ['GB 50472-2008'],
          params: c.params,
          summary: {
            result_state: '不合格',
            input_result_state: '合格',
            judgement_engine: 'electronics_workshop_v1',
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
    await page.waitForTimeout(3000);

    const probe = await page.evaluate((level) => {
      const card = document.querySelector('#roomsContainer .room-card');
      const getResultText = (pk) => {
        const pb = card?.querySelector(`[data-pk="${pk}"]`);
        return pb?.querySelector('.cv[data-res]')?.textContent?.trim() || null;
      };
      return {
        level,
        title: document.title,
        dataset: card ? {...card.dataset} : null,
        roomSummaryText: document.querySelector('.room-summary')?.innerText || '',
        projectSummary: document.getElementById('projectInfoSummary')?.innerText || '',
        particleResult: getResultText('particle'),
        windSpeedResult: getResultText('wind_speed'),
        airchangeResult: getResultText('airchange'),
        pressureResult: getResultText('pressure'),
        bodySnippet: document.body.innerText.slice(0, 4000)
      };
    }, c.level);

    const shot = path.join(OUT, `frontend_restore_electronics_${c.level.replace(/\s+/g,'_')}_${stamp}.png`);
    await page.screenshot({ path: shot, fullPage: true });
    results.push({ level: c.level, draftId, probe, screenshot: shot });
    await browser.close();
  }

  const jsonPath = path.join(OUT, `frontend_restore_electronics_multilevel_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify({ results }, null, 2), 'utf8');
  console.log(JSON.stringify({ jsonPath, results }, null, 2));
})();
