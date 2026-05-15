#!/usr/bin/env node
/*
X1 断网专项浏览器真测（O1~O5）
- O1 在线录入中断网后暂存
- O2 纯断网新建暂存
- O3 断网草稿列表可见本地记录
- O4 断网摘要回填完整性
- O5 恢复联网后继续提交/导出
*/

(async () => {
  const fs = require('fs');
  const path = require('path');
  const { chromium } = require('playwright');

  const BASE = process.env.X1_BASE || 'http://localhost:8082';
  const OUT_DIR = path.join(process.cwd(), 'reports_x1');
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  const ts = new Date();
  const stamp = `${ts.getFullYear()}${String(ts.getMonth()+1).padStart(2,'0')}${String(ts.getDate()).padStart(2,'0')}_${String(ts.getHours()).padStart(2,'0')}${String(ts.getMinutes()).padStart(2,'0')}${String(ts.getSeconds()).padStart(2,'0')}`;

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 2200 } });
  const page = await context.newPage();
  const results = [];

  async function login() {
    await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await page.fill('input[name="username"], #username', 'admin');
    await page.fill('input[name="password"], #password', 'admin123');
    await Promise.all([
      page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20000 }),
      page.click('button[type="submit"], .btn-login, input[type="submit"]')
    ]);
    await page.waitForLoadState('networkidle');
  }

  async function resetClientState() {
    await page.evaluate(async () => {
      try { localStorage.clear(); } catch (e) {}
      try { sessionStorage.clear(); } catch (e) {}
      const req = indexedDB.deleteDatabase('pudi_records');
      await new Promise(resolve => {
        req.onsuccess = req.onerror = req.onblocked = () => resolve();
      });
    });
    const offline = await page.evaluate(() => !navigator.onLine);
    if (!offline) {
      await page.reload({ waitUntil: 'networkidle' });
    }
  }

  async function fillBaseForm(suffix) {
    await page.evaluate(() => showTab('new'));
    await page.waitForTimeout(400);
    await page.locator('#projectName').scrollIntoViewIfNeeded();
    await page.fill('#projectName', `断网专项测试-${suffix}`);
    await page.fill('#reportNumberSuffix', suffix);
    await page.fill('#clientName', 'X1断网测试客户');
    await page.fill('#contactInfo', '13800000000');
    await page.fill('#projectAddress', '上海市浦东新区测试路1号');
    await page.fill('#inspectionArea', '测试区域A');
    await page.fill('#detectionDate', '2026-05-03');
    await page.check('input[name="detectionState"][value="静态"]');
    await page.fill('#weatherTemp', '22');
    await page.fill('#weatherHumidity', '50');
    await page.fill('#weatherPressure', '1013');
  }

  async function getPendingTasks() {
    return await page.evaluate(async () => {
      if (typeof getAllLocalTasks !== 'function') return [];
      const tasks = await getAllLocalTasks();
      return tasks.map(t => ({
        _localId: t._localId,
        _queueAction: t._queueAction,
        _queueStatus: t._queueStatus,
        record_id: t.record_id || '',
        project_name: t.project_name || '',
        rooms_len: Array.isArray(t.rooms) ? t.rooms.length : 0,
        summary: (Array.isArray(t.rooms) && t.rooms[0] && t.rooms[0].summary) ? t.rooms[0].summary : null,
        pass_box_result_state: (Array.isArray(t.rooms) && t.rooms[0]) ? (t.rooms[0].pass_box_result_state || '') : ''
      }));
    });
  }

  async function seedOfflinePassBoxRecord(tag) {
    await page.evaluate(async (tag) => {
      const record = {
        project_name: `断网回填-${tag}`,
        client_name: 'X1断网测试客户',
        contact_info: '13800000000',
        project_address: '上海市浦东新区测试路1号',
        inspection_area: '测试区域A',
        detection_date: '2026-05-03',
        detection_state: '静态',
        domain_id: 'pharma',
        domain_name: '制药',
        record_id: '',
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
    }, tag);
    const tasks = await getPendingTasks();
    const hit = tasks.find(t => t.project_name === `断网回填-${tag}`);
    if (!hit) throw new Error('seed 后未找到本地 pass_box 记录');
    return hit._localId;
  }

  async function runCase(id, fn) {
    try {
      const detail = await fn();
      results.push({ id, ok: true, detail });
      console.log('PASS', id, JSON.stringify(detail || {}));
    } catch (e) {
      results.push({ id, ok: false, error: String(e && e.message || e) });
      console.log('FAIL', id, String(e && e.stack || e));
    }
  }

  await login();
  await resetClientState();

  await runCase('O1_online_edit_then_offline_save', async () => {
    await fillBaseForm('O1');
    await page.context().setOffline(true);
    await page.locator('button.btn-secondary-action').scrollIntoViewIfNeeded();
    await page.click('button.btn-secondary-action');
    await page.waitForTimeout(1500);
    const text = await page.locator('body').innerText();
    const tasks = await getPendingTasks();
    if (!text.includes('已保存到本地')) throw new Error('toast 未出现“已保存到本地”');
    if (!tasks.length) throw new Error('未生成本地离线任务');
    return { toastHit: true, pendingCount: tasks.length, firstTask: tasks[0] };
  });

  await runCase('O2_offline_new_draft', async () => {
    await resetClientState();
    await page.context().setOffline(true);
    await fillBaseForm('O2');
    await page.locator('button.btn-secondary-action').scrollIntoViewIfNeeded();
    await page.click('button.btn-secondary-action');
    await page.waitForTimeout(1500);
    const text = await page.locator('body').innerText();
    const tasks = await getPendingTasks();
    const visibleHit = text.includes('断网专项测试-O2') || text.includes('X1断网测试客户') || text.includes('已保存到本地');
    if (!tasks.length) throw new Error('纯断网未生成本地任务');
    if (!visibleHit) throw new Error('离线暂存后未见页面可见证据');
    return { toastOrVisibleHit: true, pendingCount: tasks.length, firstTask: tasks[0], bodySnippet: text.slice(0, 300) };
  });

  await runCase('O3_offline_draft_list', async () => {
    await page.locator('.tab-btn').nth(1).click();
    await page.waitForTimeout(1200);
    const body = await page.locator('body').innerText();
    const tasks = await getPendingTasks();
    const localHit = body.includes('LOCAL_') || body.includes('断网专项测试-O2') || body.includes('X1断网测试客户');
    if (!localHit) {
      throw new Error('草稿页未见本地离线记录展示痕迹');
    }
    if (!tasks.length) throw new Error('草稿页前置本地任务为空');
    return { listVisible: true, pendingCount: tasks.length, bodySnippet: body.slice(0, 400) };
  });

  await runCase('O4_offline_summary_restore', async () => {
    await resetClientState();
    await page.context().setOffline(true);
    const localId = await seedOfflinePassBoxRecord('O4');
    await page.locator('.tab-btn').nth(1).click();
    await page.waitForTimeout(1500);
    const before = await getPendingTasks();
    await page.evaluate((id) => loadRecordForEdit(`LOCAL_${id}`), localId);
    await page.waitForTimeout(1800);
    const probe = await page.evaluate(() => {
      const card = document.querySelector('#roomsContainer .room-card, #roomsContainer .room-item, #roomsContainer [data-type-id="pass_box"]');
      if (!card) return null;
      return {
        resultState: card.dataset.resultState || '',
        inputResultState: card.dataset.inputResultState || '',
        judgementEngine: card.dataset.judgementEngine || '',
        judgementReason: card.dataset.judgementReason || '',
        abnormalItems: card.dataset.abnormalItems || '',
        passBoxResultState: card.dataset.passBoxResultState || '',
        text: card.innerText || ''
      };
    });
    if (!probe) throw new Error('离线加载后未生成 pass_box 卡片');
    if (probe.resultState !== '不合格') throw new Error('dataset.resultState 未恢复为不合格');
    if (!probe.judgementReason.includes('存在超出标准范围的检测项')) throw new Error('dataset.judgementReason 未恢复');
    if (!probe.abnormalItems.includes('noise') && !probe.abnormalItems.includes('hepa_leak')) throw new Error('dataset.abnormalItems 未恢复');
    if (probe.passBoxResultState !== '不合格') throw new Error('dataset.passBoxResultState 未恢复');
    return { localId, pendingCount: before.length, probe };
  });

  await runCase('O5_reconnect_and_submit', async () => {
    await resetClientState();
    await page.context().setOffline(true);
    await fillBaseForm('O5');
    await page.locator('button.btn-primary-action').scrollIntoViewIfNeeded();
    await page.click('button.btn-primary-action');
    await page.waitForTimeout(1500);
    let tasks = await getPendingTasks();
    if (!tasks.length) throw new Error('离线导出未生成待同步任务');
    const beforeLen = tasks.length;
    await page.context().setOffline(false);
    await page.waitForTimeout(2500);
    await page.evaluate(async () => {
      if (typeof syncPendingRecords === 'function') await syncPendingRecords();
    });
    await page.waitForTimeout(5000);
    tasks = await getPendingTasks();
    const body = await page.locator('body').innerText();
    const afterLen = tasks.length;
    const successHit = body.includes('已同步') || body.includes('已同步并导出') || body.includes('导出');
    if (afterLen >= beforeLen) throw new Error(`恢复联网后待同步任务未减少: before=${beforeLen}, after=${afterLen}`);
    if (!successHit) throw new Error('恢复联网后未见同步/导出反馈');
    return { beforeLen, afterLen, successHit, bodySnippet: body.slice(0, 500) };
  });

  const summary = {
    generated_at: stamp,
    total: results.length,
    passed: results.filter(r => r.ok).length,
    failed: results.filter(r => !r.ok).length,
    results
  };

  const jsonPath = path.join(OUT_DIR, `offline_browser_flow_${stamp}.json`);
  const mdPath = path.join(OUT_DIR, `offline_browser_flow_${stamp}.md`);
  fs.writeFileSync(jsonPath, JSON.stringify(summary, null, 2), 'utf8');
  fs.writeFileSync(mdPath, [
    `# X1 断网浏览器真测结果 ${stamp}`,
    '',
    `- total: ${summary.total}`,
    `- passed: ${summary.passed}`,
    `- failed: ${summary.failed}`,
    '',
    ...results.map(r => r.ok ? `- ✅ ${r.id}` : `- ❌ ${r.id}: ${r.error}`)
  ].join('\n'), 'utf8');

  console.log(JSON.stringify({ jsonPath, mdPath, summary }, null, 2));
  await browser.close();
  process.exit(summary.failed ? 1 : 0);
})();
