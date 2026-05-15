#!/usr/bin/env node
(async () => {
  const fs = require('fs');
  const path = require('path');
  const { chromium } = require('playwright');

  const ROOT = '/Users/fuwuqi/检测报告生成系统_X1';
  const OUT = path.join(ROOT, 'reports_x1');
  if(!fs.existsSync(OUT)) fs.mkdirSync(OUT,{recursive:true});
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g,'').slice(0,14);
  const BASE='http://localhost:8082';

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1680, height: 2400 } });
  const page = await context.newPage();

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

  // 1) 先调用现成 API 级脚本造一条“失败→重试成功”记录，拿 export_id
  const { execSync } = require('child_process');
  const pyOut = execSync(`cd ${ROOT} && python3 test_feishu_retry_chain.py`, { encoding: 'utf8' });
  const m = pyOut.match(/\{[\s\S]*\}\s*$/);
  if(!m) throw new Error('无法从 test_feishu_retry_chain.py 输出中提取 JSON');
  const chain = JSON.parse(m[0]);
  const exportId = chain.export_id;
  const caseName = chain.case_name;

  // 2) 打开管理页，先查看最终成功态（已有重试后成功）
  await page.goto(`${BASE}/admin`, { waitUntil:'networkidle' });
  await page.waitForTimeout(1200);
  await page.click('text=报告管理');
  await page.waitForTimeout(2200);

  const found = await page.evaluate(({ exportId, caseName }) => {
    const items = Array.from(document.querySelectorAll('.record-item'));
    const target = items.find(el => el.innerText.includes(exportId) || el.innerText.includes(caseName));
    return {
      found: !!target,
      text: target ? target.innerText : '',
      hasReportSuccess: target ? target.innerText.includes('报告飞书✅') : false,
      hasExportSuccess: target ? target.innerText.includes('记录飞书✅') : false,
      hasRetryButton: target ? target.innerText.includes('重传飞书') : false,
    };
  }, { exportId, caseName });

  const shot = path.join(OUT, `admin_feishu_retry_visual_${stamp}.png`);
  await page.screenshot({ path: shot, fullPage: true });

  const result = {
    exportId,
    caseName,
    found,
    screenshot: shot,
    ok: found.found && found.hasReportSuccess && found.hasExportSuccess && found.hasRetryButton
  };

  const jsonPath = path.join(OUT, `admin_feishu_retry_visual_${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(result, null, 2), 'utf8');
  console.log(JSON.stringify({ ...result, jsonPath }, null, 2));
  await browser.close();
  if(!result.ok) process.exit(1);
})();
