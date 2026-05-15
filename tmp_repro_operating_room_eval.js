const { chromium } = require('playwright');
(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR', err.stack || err.message));
  await page.goto('http://127.0.0.1:8082/', {waitUntil:'networkidle'});
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('.domain-btn')].find(x => x.textContent.includes('医院洁净'));
    btn && btn.click();
  });
  await page.evaluate(() => addRoom());
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    const rid = document.querySelector('.room-card')?.dataset?.rid;
    const card = document.querySelector('.room-card');
    if(card){
      card.dataset.domain = 'hospital';
      card.dataset.typeId = 'operating_room';
      card.dataset.typeName = '洁净手术部';
    }
    const detType = SYSTEM_DB.detectionTypes?.hospital?.find(t => t.id === 'operating_room');
    renderRoomTypeOptions(rid, detType, 'hospital');
    selSurgeryRoomType(rid, '手术室');
    console.log('RID', rid, 'DONE_MAIN');
    selSurgeryRoomType(rid, '眼科手术室');
    console.log('RID', rid, 'DONE_EYE');
  });
  await page.waitForTimeout(1000);
  console.log('DONE');
  await browser.close();
})();
