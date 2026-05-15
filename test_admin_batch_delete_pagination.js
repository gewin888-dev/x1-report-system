const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async() => {
  const base = 'http://127.0.0.1:8082';
  const reportsDir = path.join(__dirname, 'reports_x1');
  fs.mkdirSync(reportsDir, { recursive: true });
  const ts = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 12);
  const out = {
    case: 'admin_batch_delete_pagination',
    ts,
    login_ok: false,
    createdDraftIds: [],
    search_ok: false,
    foundCountBeforeDelete: 0,
    batchDeleteTriggered: false,
    deleteToastSeen: false,
    foundCountAfterDelete: 0,
    deleteEffectOk: false,
    trashStatusText: null,
    ok: false
  };

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);

  try {
    // 先通过接口制造两条临时草稿，避免动真实重要数据
    for (let i = 1; i <= 2; i++) {
      const draftId = `X1DRAFT_AUDIT_${ts}_${i}`;
      const resp = await page.request.post(base + '/api/save', {
        data: {
          draft_id: draftId,
          project: {
            project_name: `批量删除联动验收_${ts}_${i}`,
            client_name: 'OpenClaw验收',
            detection_type: 'electronics_workshop',
            detection_date: '2026-05-04',
            rooms: [{ room_name: `验收房间${i}` }]
          }
        }
      });
      if (resp.ok()) out.createdDraftIds.push(draftId);
    }

    await page.goto(base + '/login');
    await page.fill('input[name="username"], input[type="text"]', 'admin');
    await page.fill('input[name="password"], input[type="password"]', 'admin123');
    await Promise.all([
      page.waitForLoadState('networkidle'),
      page.click('button[type="submit"], button:has-text("登录"), .login-btn')
    ]);
    out.login_ok = true;

    await page.goto(base + '/admin');
    await page.waitForLoadState('networkidle');
    await page.click('.nav-item:has-text("报告管理")');
    await page.waitForTimeout(1500);

    const keyword = `批量删除联动验收_${ts}`;
    await page.fill('#record-search', keyword);
    await page.waitForTimeout(1200);
    out.search_ok = true;

    const beforeItems = await page.locator('.record-item').count();
    out.foundCountBeforeDelete = beforeItems;

    if (beforeItems >= 2) {
      await page.check('#rec-check-all');
      page.once('dialog', d => d.accept());
      await page.click('button:has-text("批量删除")');
      out.batchDeleteTriggered = true;
      await page.waitForTimeout(1800);
      const bodyText = await page.locator('body').innerText();
      out.deleteToastSeen = bodyText.includes('已删除');

      await page.fill('#record-search', keyword);
      await page.waitForTimeout(1200);
      out.foundCountAfterDelete = await page.locator('.record-item').count();
      out.deleteEffectOk = out.foundCountAfterDelete === 0;
      out.trashStatusText = await page.locator('#trash-status').innerText().catch(() => null);
    }

    await page.screenshot({ path: path.join(reportsDir, `admin_batch_delete_pagination_${ts}.png`), fullPage: true });

    out.ok = !!(
      out.login_ok &&
      out.createdDraftIds.length === 2 &&
      out.search_ok &&
      out.foundCountBeforeDelete >= 2 &&
      out.batchDeleteTriggered &&
      out.deleteEffectOk
    );
  } catch (e) {
    out.error = String(e && e.stack || e);
  } finally {
    fs.writeFileSync(path.join(reportsDir, `admin_batch_delete_pagination_${ts}.json`), JSON.stringify(out, null, 2), 'utf-8');
    await browser.close();
  }

  console.log(JSON.stringify(out, null, 2));
})();
