const { chromium } = require('playwright');

(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR', err.stack || err.message));

  await page.goto('http://127.0.0.1:8082/login', {waitUntil:'networkidle'});
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await Promise.all([
    page.waitForURL('**/', {timeout: 15000}),
    page.click('button[type="submit"]')
  ]);

  const uniq = 'DRAFT_COVER_' + Date.now();

  await page.fill('#projectName', '暂存覆盖验证-' + uniq);
  await page.fill('#clientName', '测试客户');
  await page.fill('#contactInfo', '123456');
  await page.fill('#projectAddress', '测试地址');
  await page.fill('#inspectionArea', '测试区域');
  await page.fill('#detectionDate', '2026-05-04');
  await page.locator('.domain-btn').filter({ hasText: '医院洁净' }).first().click();
  await page.click('.add-room-btn');
  await page.locator('#roomsContainer .room-card .room-type-row .level-btn').filter({ hasText: '洁净手术部' }).first().click();
  await page.locator('#roomsContainer .room-card .room-surgery-type-options .level-btn').getByText('手术室', { exact: true }).click();
  await page.locator('#roomsContainer .room-card .room-clean-options .level-btn').getByText('Ⅰ级（百级）', { exact: true }).click();
  await page.waitForTimeout(800);

  await page.click('button:has-text("暂存记录")');
  await page.waitForTimeout(1500);

  await page.click('.tab-btn:has-text("录入编辑")');
  await page.fill('#contactInfo', '654321');
  await page.click('button:has-text("暂存记录")');
  await page.waitForTimeout(1500);

  await page.click('.tab-btn:has-text("暂存记录")');
  await page.waitForTimeout(1800);

  const result = await page.evaluate((uniq) => {
    const items = [...document.querySelectorAll('#draftRecordsList li')].map(li => li.innerText || '');
    const matched = items.filter(t => t.includes('暂存覆盖验证-' + uniq));
    return {
      totalItems: items.length,
      matchedCount: matched.length,
      matched
    };
  }, uniq);

  console.log('RESULT', JSON.stringify(result, null, 2));
  await browser.close();
})();
