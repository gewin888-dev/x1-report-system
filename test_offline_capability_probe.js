#!/usr/bin/env node
/*
X1 断网能力静态探测
目标：先确认前端具备离线保存、本地任务队列、断网提示、恢复入口等代码骨架
*/
const fs = require('fs');
const path = '/Users/fuwuqi/检测报告生成系统_X1/static/record.js';
const text = fs.readFileSync(path, 'utf8');

const checks = [
  ['has isOnline gate', /if\(!isOnline\)/],
  ['has saveToLocal', /function saveToLocal\(/],
  ['has buildOfflineTask', /function buildOfflineTask\(/],
  ['has getLocalTaskByRecordId', /getLocalTaskByRecordId\(/],
  ['has local draft fallback toast', /已保存到本地/],
  ['has network exception fallback toast', /网络异常,已保存到本地/],
  ['has draft tab rendering', /draftRecordsList/],
  ['has local queue action save_draft', /save_draft/],
  ['has local queue action submit_only', /submit_only/],
  ['has local queue action submit_and_generate', /submit_and_generate/],
  ['has local queue action submit_and_export', /submit_and_export/],
  ['has load local task path', /String\(id\)\.startsWith\('LOCAL_'/],
];

const results = checks.map(([name, re]) => ({ name, ok: re.test(text) }));
const ok = results.every(r => r.ok);
console.log(JSON.stringify({ ok, results }, null, 2));
process.exit(ok ? 0 : 1);
