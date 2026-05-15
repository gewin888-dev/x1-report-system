const { chromium } = require('playwright');
(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR', err.stack || err.message));
  await page.goto('http://127.0.0.1:8082/', {waitUntil:'networkidle'});
  await page.click('text=🏥 医院洁净');
  await page.click('text=+ 添加房间/设备');
  await page.click('text=洁净手术部');
  await page.click('text=手术室');
  await page.waitForTimeout(1000);
  console.log('AFTER_MAIN_OK');
  await page.click('text=眼科手术室');
  await page.waitForTimeout(1000);
  console.log('AFTER_EYE_OK');
  await browser.close();
})();
