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
  const result = await page.evaluate(() => {
    const out = {};
    const domainBtn = [...document.querySelectorAll('.domain-btn')].find(b => b.textContent.includes('医院洁净'));
    if(domainBtn) domainBtn.click();
    const addBtn = document.querySelector('.add-room-btn');
    if(addBtn) addBtn.click();
    const rid = document.querySelector('.room-card')?.dataset?.rid;
    const room = document.querySelector(`.room-card[data-rid="${rid}"]`);
    const detType = SYSTEM_DB.detectionTypes?.hospital?.find(t => t.id === 'operating_room');
    room.dataset.domain = 'hospital';
    room.dataset.typeId = 'operating_room';
    room.dataset.typeName = '洁净手术部';
    currentDetectionType = detType;
    renderRoomTypeOptions(rid, detType, 'hospital');

    selSurgeryRoomType(rid, '手术室');
    selCleanClass(rid, 'Ⅰ级（百级）');
    out.mainPbCount = room.querySelectorAll('.pb').length;
    out.mainFirstKeys = [...room.querySelectorAll('.pb')].slice(0,5).map(x => x.dataset.pk);
    out.mainPrompt = room.querySelector('.rparams')?.innerText?.slice(0,80) || '';

    selSurgeryRoomType(rid, '眼科手术室');
    selCleanClass(rid, 'Ⅰ级（百级）');
    out.eyePbCount = room.querySelectorAll('.pb').length;
    out.eyeFirstKeys = [...room.querySelectorAll('.pb')].slice(0,5).map(x => x.dataset.pk);
    out.eyePrompt = room.querySelector('.rparams')?.innerText?.slice(0,80) || '';
    out.dataset = {
      surgeryRoomType: room.dataset.surgeryRoomType || '',
      cleanClass: room.dataset.cleanClass || '',
      levelName: room.dataset.levelName || ''
    };
    return out;
  });
  console.log('RESULT', JSON.stringify({result, errors}, null, 2));
  await browser.close();
})();
