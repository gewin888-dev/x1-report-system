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

  async function clearState(){
    await page.evaluate(async () => {
      try { localStorage.clear(); } catch(e) {}
      try { sessionStorage.clear(); } catch(e) {}
      const req = indexedDB.deleteDatabase('pudi_records');
      await new Promise(resolve => { req.onsuccess=req.onerror=req.onblocked=()=>resolve(); });
    });
    await page.reload({ waitUntil:'networkidle' });
  }

  await login();
  await clearState();
  await page.context().setOffline(true);

  const seeded = await page.evaluate(async () => {
    const record = {
      project_name: '断网恢复联网-O5',
      report_number: 'PDJC-BG2026-19O5',
      client_name: 'X1断网测试客户',
      contact_info: '13800000000',
      project_address: '上海市浦东新区测试路1号',
      inspection_area: '测试区域A',
      detection_date: '2026-05-03',
      detection_state: '静态',
      weather: { temperature: '22', humidity: '50', pressure: '1013' },
      domain: 'pharma',
      domain_name: '制药工业',
      detection_type: 'pass_box',
      detection_type_name: '传递窗',
      basis: ['GB 50591-2010'],
      judgement: ['JG/T 382-2012'],
      rooms: [{
        id: 'r1',
        name: 'O5传递窗',
        type_id: 'pass_box',
        type_name: '传递窗',
        basis: ['GB 50591-2010'],
        judgement: ['JG/T 382-2012'],
        business_domain_hint: 'pharma',
        pass_box_judgement_active: ['JG/T 382-2012'],
        pass_box_result_state: '合格',
        params: {
          appearance: { result: '合格' },
          interlock: { result: '合格' },
          noise: { background: 40, room_noise: 50, result: '合格' },
          hepa_leak: { points: [{ value: 0.005 }], result: '合格' }
        },
        summary: {
          result_state: '合格',
          input_result_state: '合格',
          judgement_engine: 'pass_box_v1',
          judgement_reason: '检测项均在标准范围内',
          abnormal_items: [],
          judgement_overridden: false
        }
      }],
      inspector: 'admin'
    };
    await saveToLocal(record, 'submit_and_export');
    const all = await getAllLocalTasks();
    return all.map(t => ({ _localId:t._localId, project_name:t.project_name, action:t._queueAction, status:t._queueStatus, basis:t.basis, judgement:t.judgement }));
  });

  await page.context().setOffline(false);
  await page.waitForTimeout(2000);
  const beforeSync = await page.evaluate(async () => {
    const all = await getAllLocalTasks();
    return all.map(t => ({ _localId:t._localId, action:t._queueAction, status:t._queueStatus, synced:!!t._synced }));
  });
  await page.evaluate(async () => { if (typeof syncPendingRecords === 'function') await syncPendingRecords(); });
  await page.waitForTimeout(8000);
  const afterSync = await page.evaluate(async () => {
    const all = await getAllLocalTasks();
    return all.map(t => ({ _localId:t._localId, action:t._queueAction, status:t._queueStatus, synced:!!t._synced, serverResult:t._serverResult || null, queueError:t._queueError || '' }));
  });
  const body = await page.locator('body').innerText();
  console.log(JSON.stringify({ seeded, beforeSync, afterSync, body: body.slice(0, 4000) }, null, 2));
  await browser.close();
})();
