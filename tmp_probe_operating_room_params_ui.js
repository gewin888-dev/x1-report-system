const { chromium } = require('playwright');
(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage();
  const errors = [];
  page.on('console', msg => {
    const text = msg.text();
    console.log('CONSOLE', msg.type(), text);
    if(msg.type() === 'error') errors.push(text);
  });
  page.on('pageerror', err => {
    const text = err.stack || err.message;
    console.log('PAGEERROR', text);
    errors.push(text);
  });
  await page.goto('http://127.0.0.1:8082/', { waitUntil: 'networkidle' });

  await page.locator('.domain-btn', { hasText: '医院洁净' }).click();
  await page.locator('.add-room-btn').click();
  await page.locator('.type-btn', { hasText: '洁净手术部' }).click();
  await page.locator('.room-card .room-surgery-type-options .level-btn', { hasText: '手术室' }).click();
  await page.locator('.room-card .room-clean-options .level-btn', { hasText: 'Ⅰ级（百级）' }).click();
  await page.waitForTimeout(300);
  const main = await page.evaluate(() => {
    const room = document.querySelector('.room-card');
    return {
      pbCount: room?.querySelectorAll('.pb').length || 0,
      prompt: room?.querySelector('.rparams')?.innerText?.slice(0,120) || '',
      surgeryRoomType: room?.dataset?.surgeryRoomType || '',
      cleanClass: room?.dataset?.cleanClass || ''
    };
  });

  await page.locator('.room-card .room-surgery-type-options .level-btn', { hasText: '眼科手术室' }).click();
  await page.locator('.room-card .room-clean-options .level-btn', { hasText: 'Ⅰ级（百级）' }).click();
  await page.waitForTimeout(300);
  const eye = await page.evaluate(() => {
    const room = document.querySelector('.room-card');
    return {
      pbCount: room?.querySelectorAll('.pb').length || 0,
      prompt: room?.querySelector('.rparams')?.innerText?.slice(0,120) || '',
      surgeryRoomType: room?.dataset?.surgeryRoomType || '',
      cleanClass: room?.dataset?.cleanClass || ''
    };
  });

  console.log('RESULT', JSON.stringify({ main, eye, errors }, null, 2));
  await browser.close();
})();
