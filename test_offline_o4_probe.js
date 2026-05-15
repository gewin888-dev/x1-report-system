#!/usr/bin/env node
(async () => {
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 2200 } });
  const page = await context.newPage();
  const BASE='http://localhost:8082';

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
  await page.evaluate(async () => {
    try { localStorage.clear(); } catch(e) {}
    try { sessionStorage.clear(); } catch(e) {}
    const req = indexedDB.deleteDatabase('pudi_records');
    await new Promise(resolve => { req.onsuccess=req.onerror=req.onblocked=()=>resolve(); });
  });
  await page.reload({ waitUntil:'networkidle' });
  await page.context().setOffline(true);

  await page.evaluate(async () => {
    const record = {
      project_name: '断网回填-O4',
      client_name: 'X1断网测试客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '测试区域A',
      detection_date: '2026-05-03',
      detection_state: '静态',
      domain_id: 'pharma',
      domain_name: '制药',
      rooms: [{
        type_id: 'pass_box',
        room_name: '传递窗-断网摘要回填',
        pass_box_result_state: '不合格',
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
      }]
    };
    await saveToLocal(record, 'save_draft');
  });

  const tasks = await page.evaluate(async () => {
    const all = await getAllLocalTasks();
    return all.map(t => ({ _localId: t._localId, project_name: t.project_name, queue: t._queueStatus }));
  });
  const hit = tasks.find(t => t.project_name === '断网回填-O4');
  if (!hit) throw new Error('未找到 seed 后本地记录');

  await page.evaluate(() => showTab('draft'));
  await page.waitForTimeout(1200);
  await page.evaluate((id) => loadRecordForEdit(`LOCAL_${id}`), hit._localId);
  await page.waitForTimeout(2500);

  const dump = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('#roomsContainer > *')].map((el,i) => ({
      i,
      tag: el.tagName,
      cls: el.className,
      dataset: {...el.dataset},
      text: (el.innerText || '').slice(0, 1500)
    }));
    return {
      title: document.title,
      activeTabText: document.querySelector('.tab-btn.active')?.innerText || '',
      body: document.body.innerText.slice(0, 5000),
      roomCount: document.getElementById('roomsContainer')?.children?.length || 0,
      cards
    };
  });
  console.log(JSON.stringify({ hit, dump }, null, 2));
  await browser.close();
})();
