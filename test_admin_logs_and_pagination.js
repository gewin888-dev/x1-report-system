const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async() => {
  const base = 'http://127.0.0.1:8082';
  const reportsDir = path.join(__dirname, 'reports_x1');
  fs.mkdirSync(reportsDir, { recursive: true });
  const ts = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 12);
  const out = {
    case: 'admin_logs_and_pagination',
    ts,
    login_ok: false,
    logs_panel_ok: false,
    log_keyword_search_ok: false,
    log_keyword_hit: null,
    records_panel_ok: false,
    pagination_visible: false,
    page1_ids: [],
    page2_ids: [],
    pagination_switch_ok: false,
    records_search_ok: false,
    records_search_hit: null,
    ok: false
  };

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);

  try {
    await page.goto(base + '/login');
    await page.fill('input[name="username"], input[type="text"]', 'admin');
    await page.fill('input[name="password"], input[type="password"]', 'admin123');
    await Promise.all([
      page.waitForLoadState('networkidle'),
      page.click('button[type="submit"], button:has-text("登录"), .login-btn')
    ]);
    out.login_ok = /record|admin|X1/i.test(await page.content());

    await page.goto(base + '/admin');
    await page.waitForLoadState('networkidle');

    await page.click('.nav-item:has-text("操作日志")');
    await page.waitForTimeout(1200);
    out.logs_panel_ok = await page.locator('#panel-logs').evaluate(el => el.classList.contains('active'));

    const keywordInput = page.locator('#log-keyword');
    if (await keywordInput.count()) {
      await keywordInput.fill('导出');
      await page.waitForTimeout(1000);
      const rowsText = await page.locator('#tb-logs').innerText();
      out.log_keyword_hit = rowsText.slice(0, 200);
      out.log_keyword_search_ok = rowsText.includes('导出');
    }

    await page.click('.nav-item:has-text("报告管理")');
    await page.waitForTimeout(1500);
    out.records_panel_ok = await page.locator('#panel-records').evaluate(el => el.classList.contains('active'));

    out.pagination_visible = await page.locator('#record-pagination .pagination').count().catch(() => 0) > 0;
    const page1Cards = await page.locator('.record-item .record-title').allInnerTexts();
    out.page1_ids = page1Cards.slice(0, 5);

    const nextBtn = page.locator('#record-pagination button:has-text("下一页")');
    if (await nextBtn.count()) {
      const disabled = await nextBtn.isDisabled().catch(() => true);
      if (!disabled) {
        await nextBtn.click();
        await page.waitForTimeout(1200);
        const page2Cards = await page.locator('.record-item .record-title').allInnerTexts();
        out.page2_ids = page2Cards.slice(0, 5);
        out.pagination_switch_ok = JSON.stringify(out.page1_ids) !== JSON.stringify(out.page2_ids);
      }
    }

    const searchInput = page.locator('#record-search');
    if (await searchInput.count()) {
      await searchInput.fill('页面真验');
      await page.waitForTimeout(1200);
      const titles = await page.locator('.record-item .record-title').allInnerTexts();
      out.records_search_hit = (titles[0] || '').slice(0, 120);
      out.records_search_ok = titles.length > 0;
    }

    await page.screenshot({ path: path.join(reportsDir, `admin_logs_and_pagination_${ts}.png`), fullPage: true });

    out.ok = !!(
      out.login_ok &&
      out.logs_panel_ok &&
      out.log_keyword_search_ok &&
      out.records_panel_ok &&
      out.pagination_visible &&
      out.pagination_switch_ok &&
      out.records_search_ok
    );
  } catch (e) {
    out.error = String(e && e.stack || e);
  } finally {
    fs.writeFileSync(path.join(reportsDir, `admin_logs_and_pagination_${ts}.json`), JSON.stringify(out, null, 2), 'utf-8');
    await browser.close();
  }

  console.log(JSON.stringify(out, null, 2));
})();
