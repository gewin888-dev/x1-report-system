#!/usr/bin/env node
const fs = require('fs');

const path = '/Users/fuwuqi/检测报告生成系统_X1/static/record.js';
const text = fs.readFileSync(path, 'utf8');

const checks = [
  ['collectData input_result_state', /input_result_state:\s*card\.dataset\.inputResultState\s*\|\|\s*''/],
  ['collectData judgement_engine', /judgement_engine:\s*card\.dataset\.judgementEngine\s*\|\|\s*''/],
  ['collectData judgement_reason', /judgement_reason:\s*card\.dataset\.judgementReason\s*\|\|\s*''/],
  ['collectData judgement_overridden', /judgement_overridden:\s*card\.dataset\.judgementOverridden === 'true' \? true : \(card\.dataset\.judgementOverridden === 'false' \? false : null\)/],
  ['collectData abnormal_items', /abnormal_items:\s*JSON\.parse\(card\.dataset\.abnormalItems \|\| '\[\]'\)/],
  ['normalize input_result_state', /input_result_state:\s*room\?\.summary\?\.input_result_state\s*\|\|\s*room\?\.input_result_state\s*\|\|\s*''/],
  ['normalize judgement_engine', /judgement_engine:\s*room\?\.summary\?\.judgement_engine\s*\|\|\s*room\?\.judgement_engine\s*\|\|\s*''/],
  ['normalize judgement_reason', /judgement_reason:\s*room\?\.summary\?\.judgement_reason\s*\|\|\s*room\?\.judgement_reason\s*\|\|\s*''/],
  ['normalize abnormal_items', /abnormal_items:\s*Array\.isArray\(room\?\.summary\?\.abnormal_items\)/],
  ['normalize judgement_overridden', /judgement_overridden:\s*typeof room\?\.summary\?\.judgement_overridden === 'boolean'/],
  ['load dataset inputResultState', /card\.dataset\.inputResultState = room\.summary\.input_result_state \|\| ''/],
  ['load dataset judgementEngine', /card\.dataset\.judgementEngine = room\.summary\.judgement_engine \|\| ''/],
  ['load dataset judgementReason', /card\.dataset\.judgementReason = room\.summary\.judgement_reason \|\| ''/],
  ['load dataset abnormalItems', /card\.dataset\.abnormalItems = JSON\.stringify\(Array\.isArray\(room\.summary\.abnormal_items\) \? room\.summary\.abnormal_items : \[\]\)/],
  ['load dataset judgementOverridden', /if\(typeof room\.summary\.judgement_overridden === 'boolean'\) card\.dataset\.judgementOverridden = room\.summary\.judgement_overridden \? 'true' : 'false'/]
];

const results = checks.map(([name, re]) => ({ name, ok: re.test(text) }));
const ok = results.every(r => r.ok);
console.log(JSON.stringify({ ok, results }, null, 2));
process.exit(ok ? 0 : 1);
