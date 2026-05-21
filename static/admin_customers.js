/* ============================================================
 * admin_customers.js — 客户管理面板（美化版 v2）
 * ============================================================ */

var customerPanelInited = false;
var customerListData = [];
var customerSearchTimer = null;
var customerCurrentPage = 1;
var customerPageSize = 20;
var customerTotalPages = 1;
var customerTotal = 0;
var customerKeyword = '';

/* ========== 工具函数 ========== */
function _money(v) {
  var n = parseFloat(v) || 0;
  if (!n) return '-';
  return '¥' + n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}
function _safeHtml(s) { return typeof escapeHtml === 'function' ? escapeHtml(s) : String(s || ''); }

/* ========== 1. 初始化 ========== */
function initCustomersPanel() {
  if (!customerPanelInited) customerPanelInited = true;
  loadCustomerList();
}

/* ========== 2. 加载列表 ========== */
function loadCustomerList(page) {
  if (typeof page === 'number' && page > 0) customerCurrentPage = page;
  var params = new URLSearchParams();
  params.set('page', String(customerCurrentPage));
  params.set('page_size', String(customerPageSize));
  if (customerKeyword) params.set('keyword', customerKeyword);

  fetch('/admin/api/customer_management/list?' + params.toString())
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '加载失败');
      customerListData = d.items || [];
      customerCurrentPage = d.page || 1;
      customerPageSize = d.page_size || 20;
      customerTotalPages = d.total_pages || 1;
      customerTotal = d.total || 0;
      renderCustomerSummary(d.summary || {});
      renderCustomerList(customerListData);
      renderCustomerPagination();
    })
    .catch(function(err) {
      console.error(err);
      var box = document.getElementById('customer-list-container');
      if (box) box.innerHTML = '<div style="padding:60px;text-align:center;color:#94a3b8;font-size:14px;">加载客户列表失败</div>';
      var pager = document.getElementById('customer-pagination');
      if (pager) pager.innerHTML = '';
    });
}

/* ========== 3. 汇总卡片 ========== */
function renderCustomerSummary(s) {
  var ids = { 'cs-total': s.total, 'cs-with-projects': s.with_projects, 'cs-pending-feedback': s.pending_feedback, 'cs-receivable': s.receivable_clients };
  for (var k in ids) {
    var el = document.getElementById(k);
    if (el) el.textContent = ids[k] || 0;
  }
}

/* ========== 4. 渲染客户列表 ========== */
function renderCustomerList(items) {
  var box = document.getElementById('customer-list-container');
  if (!box) return;
  if (!items || !items.length) {
    box.innerHTML = '<div style="padding:60px;text-align:center;color:#94a3b8;font-size:14px;">暂无客户数据</div>';
    return;
  }

  // 表头
  var html = '<table style="width:100%;border-collapse:separate;border-spacing:0 2px;"><colgroup><col style="width:32%"><col style="width:7%"><col style="width:11%"><col style="width:11%"><col style="width:11%"><col style="width:8%"><col style="width:10%"><col style="width:5%"></colgroup>'
    + '<thead><tr style="font-size:12px;color:#94a3b8;font-weight:500;"><td style="padding:0 12px;">客户</td><td style="text-align:center;">项目数</td><td style="text-align:right;padding-right:8px;">合同总额</td><td style="text-align:right;padding-right:8px;">已收款</td><td style="text-align:right;padding-right:8px;">应收款</td><td style="text-align:center;">消息</td><td style="text-align:center;">账号</td><td></td></tr></thead><tbody>';

  items.forEach(function(c) {
    var receivable = parseFloat(c.receivable) || 0;
    var recvColor = receivable > 0 ? '#dc2626' : '#16a34a';
    var recvWeight = receivable > 0 ? '700' : '400';

    // 标签
    var tags = '';
    if (c.domains) {
      var darr = typeof c.domains === 'string' ? c.domains.split(',').filter(function(s){return s.trim();}) : c.domains;
      darr.slice(0, 3).forEach(function(d) {
        tags += '<span style="display:inline-block;background:#eff6ff;color:#3b82f6;border-radius:4px;padding:1px 6px;font-size:11px;margin-right:3px;line-height:18px;">' + _safeHtml(d.trim()) + '</span>';
      });
      if (darr.length > 3) tags += '<span style="color:#94a3b8;font-size:11px;">+' + (darr.length - 3) + '</span>';
    }

    // 状态指示
        html += '<tr onclick="showCustomerDetail(\'' + _safeHtml(c.client_name).replace(/'/g, "\\'") + '\')"'
      + ' style="background:#fff;cursor:pointer;transition:all .15s;"'
      + ' onmouseenter="this.style.background=\'#f8fafc\'"'
      + ' onmouseleave="this.style.background=\'#fff\'">'

      // 客户信息列（单行紧凑）
      + '<td style="padding:8px 12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
      + '<span style="font-size:13px;font-weight:600;color:#0f172a;">' + _safeHtml(c.client_name) + '</span>'
      + (c.contact_name ? '<span style="color:#64748b;font-size:11px;margin-left:8px;">' + _safeHtml(c.contact_name) + '</span>' : '')
      + (c.contact_phone ? '<span style="color:#94a3b8;font-size:11px;font-family:monospace;margin-left:4px;">' + _safeHtml(c.contact_phone) + '</span>' : '')
      + ' ' + tags
      + '</td>'
      + '<td style="text-align:center;font-size:13px;font-weight:600;color:#334155;padding:8px 4px;">' + (c.project_count || 0) + '</td>'
      // 合同总额
      + '<td style="text-align:right;font-size:12px;color:#334155;padding:8px 8px;">' + _money(c.total_contract) + '</td>'
      // 已收款
      + '<td style="text-align:right;font-size:12px;color:#16a34a;padding:8px 8px;">' + _money(c.total_paid) + '</td>'
      // 应收款
      + '<td style="text-align:right;font-size:12px;font-weight:' + recvWeight + ';color:' + recvColor + ';padding:8px 8px;">' + _money(c.receivable) + '</td>'
      // 消息
      + '<td style="text-align:center;padding:8px 4px;">' + ((c.feedback_count||0)>0 ? '<span style="background:#fffbeb;color:#d97706;border:1px solid #fde68a;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:600;">💬'+c.feedback_count+'</span>' : '<span style="color:#cbd5e1;">—</span>') + '</td>'
      // 账号
      + '<td style="text-align:center;padding:8px 4px;">' + (c.has_account ? '<span style="background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:600;">✅ 已开通</span>' : '<span style="color:#cbd5e1;">—</span>') + '</td>'
      + '<td style="text-align:center;vertical-align:middle;"><button onclick="event.stopPropagation();deleteCustomer(\x27' + _safeHtml(c.client_name).replace(/'/g, "\\'") + '\x27)" style="padding:3px 8px;font-size:11px;color:#94a3b8;border:1px solid #e2e8f0;border-radius:6px;background:#fff;cursor:pointer;transition:all .15s;" onmouseenter="this.style.color=\x27#dc2626\x27;this.style.borderColor=\x27#fca5a5\x27" onmouseleave="this.style.color=\x27#94a3b8\x27;this.style.borderColor=\x27#e2e8f0\x27">删除</button></div>'

      + '</td></tr>';
  });

  html += '</tbody></table>';
  box.innerHTML = html;
}

function renderCustomerPagination() {
  var box = document.getElementById('customer-pagination');
  if (!box) return;
  if (customerTotal <= 0) { box.innerHTML = ''; return; }

  var start = (customerCurrentPage - 1) * customerPageSize + 1;
  var end = Math.min(customerCurrentPage * customerPageSize, customerTotal);

  var html = '';
  html += '<div style="font-size:13px;color:#64748b;">共 <strong style="color:#0f172a;">' + customerTotal + '</strong> 条，当前显示 ' + start + '-' + end + '</div>';
  html += '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">';
  html += '<select onchange="changeCustomerPageSize(this.value)" style="height:34px;border:1px solid #d9d9d9;border-radius:8px;padding:0 8px;background:#fff;">'
    + '<option value="20"' + (customerPageSize===20?' selected':'') + '>20/页</option>'
    + '<option value="50"' + (customerPageSize===50?' selected':'') + '>50/页</option>'
    + '<option value="100"' + (customerPageSize===100?' selected':'') + '>100/页</option>'
    + '</select>';
  html += '<button class="btn" ' + (customerCurrentPage<=1?'disabled style="opacity:.45;cursor:not-allowed;"':'onclick="loadCustomerList(' + (customerCurrentPage-1) + ')"') + '>上一页</button>';
  html += '<span style="font-size:13px;color:#334155;min-width:88px;text-align:center;">第 ' + customerCurrentPage + ' / ' + customerTotalPages + ' 页</span>';
  html += '<button class="btn" ' + (customerCurrentPage>=customerTotalPages?'disabled style="opacity:.45;cursor:not-allowed;"':'onclick="loadCustomerList(' + (customerCurrentPage+1) + ')"') + '>下一页</button>';
  html += '</div>';
  box.innerHTML = html;
}

function changeCustomerPageSize(v) {
  var n = parseInt(v, 10) || 20;
  customerPageSize = Math.max(1, Math.min(100, n));
  customerCurrentPage = 1;
  loadCustomerList(1);
}

/* ========== 5. 搜索（服务端） ========== */
function filterCustomerList() {
  clearTimeout(customerSearchTimer);
  customerSearchTimer = setTimeout(function() {
    customerKeyword = (document.getElementById('customer-search')?.value || '').trim();
    customerCurrentPage = 1;
    loadCustomerList(1);
  }, 300);
}

/* ========== 6. 客户详情 ========== */
function showCustomerDetail(clientName) {
  document.getElementById('customer-list-view').style.display = 'none';
  document.getElementById('customer-detail-view').style.display = '';
  var box = document.getElementById('customer-detail-content');
  box.innerHTML = '<div style="text-align:center;padding:60px;color:#94a3b8;">加载中...</div>';

  fetch('/admin/api/customer_management/detail?client_name=' + encodeURIComponent(clientName))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '加载失败');
      renderCustomerDetail(d);
    })
    .catch(function(err) {
      console.error(err);
      box.innerHTML = '<div style="text-align:center;padding:60px;color:#dc2626;">加载失败: ' + _safeHtml(err.message) + '</div>';
    });
}

function renderCustomerDetail(data) {
  var p = data.profile || {};
  var projects = data.projects || [];
  var urgeLogs = data.urge_logs || [];
  var feedbacks = data.feedbacks || [];
  var reports = data.reports || [];
  var account = data.account || {};
  var box = document.getElementById('customer-detail-content');

  var h = '';

  /* --- 头部信息卡 --- */
  var acctBadge = account && account.user_id
    ? '<span style="background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;border-radius:999px;padding:3px 10px;font-size:12px;">✅ 已开通 · ' + _safeHtml(account.user_id) + '</span>'
    : '<span style="background:#f8fafc;color:#94a3b8;border:1px solid #e2e8f0;border-radius:999px;padding:3px 10px;font-size:12px;">未开通账号</span>';

  h += '<div style="background:linear-gradient(135deg,#1e40af 0%,#3b82f6 100%);border-radius:14px;padding:24px 28px;margin-bottom:16px;color:#fff;">'
    + '<input type="hidden" id="customer-profile-version" value="' + _safeHtml(p.version || 1) + '">' 
    + '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">'
    + '<div>'
    + '<div style="font-size:22px;font-weight:800;margin-bottom:6px;">' + _safeHtml(p.client_name || '') + '</div>'
    + '<div style="display:flex;gap:20px;font-size:13px;opacity:0.9;">'
    + '<span>📞 ' + _safeHtml(p.recipient_name || '-') + ' · ' + _safeHtml(p.recipient_phone || '-') + '</span>'
    + '<span>📍 ' + _safeHtml(p.recipient_address || '-') + '</span>'
    + '</div></div>'
    + '<div>' + acctBadge + '</div>'
    + '</div>'
    + '<div style="display:flex;gap:32px;margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.2);font-size:14px;">'
    + '<div><div style="opacity:0.7;font-size:12px;margin-bottom:2px;">项目总数</div><div style="font-weight:700;font-size:18px;">' + projects.length + '</div></div>'
    + '<div><div style="opacity:0.7;font-size:12px;margin-bottom:2px;">合同总额</div><div style="font-weight:700;font-size:18px;">' + _money(projects.reduce(function(s,pr){return s+(parseFloat(pr.contract_amount)||0);},0)) + '</div></div>'
    + '<div><div style="opacity:0.7;font-size:12px;margin-bottom:2px;">催单次数</div><div style="font-weight:700;font-size:18px;">' + urgeLogs.length + '</div></div>'
    + '<div><div style="opacity:0.7;font-size:12px;margin-bottom:2px;">反馈次数</div><div style="font-weight:700;font-size:18px;">' + feedbacks.length + '</div></div>'
    + '</div></div>';
  h += '<div id="customer-profile-meta" style="margin:-6px 0 12px 0;font-size:12px;color:#64748b;">最后更新：' + _safeHtml(p.updated_by || '-') + ' · ' + _safeHtml((p.updated_at || '').slice(0,16) || '-') + '</div>';

  /* --- 开票/收件信息（默认折叠） --- */
  h += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">';
  // 开票
  h += '<details style="background:#fff;border-radius:12px;border:1px solid #f1f5f9;">'
    + '<summary style="padding:16px 24px;cursor:pointer;font-size:15px;font-weight:700;color:#0f172a;display:flex;align-items:center;gap:6px;list-style:none;">'
    + '<span style="transition:transform .2s;display:inline-block;font-size:12px;color:#94a3b8;margin-right:4px;" class="fold-arrow">▶</span>🧾 开票信息'
    + '</summary>'
    + '<div style="padding:0 24px 20px;">'
    + '<div style="display:flex;gap:6px;margin-bottom:12px;justify-content:flex-end;">'
    + '<button class="btn btn-sm" onclick="toggleCustomerProfileEdit(true)" id="customer-profile-edit-btn" style="font-size:12px;">编辑</button>'
    + '<button class="btn btn-sm" onclick="saveCustomerProfile(\'' + _safeHtml(p.client_name||'').replace(/'/g,"\\'") + '\')" id="customer-profile-save-btn" style="display:none;background:#1677ff;color:#fff;font-size:12px;">保存</button>'
    + '<button class="btn btn-sm" onclick="toggleCustomerProfileEdit(false)" id="customer-profile-cancel-btn" style="display:none;font-size:12px;">取消</button>'
    + '</div>'
    + '<div id="customer-profile-form">'
    + _pField('invoice_company', '公司全称', p.invoice_company)
    + _pField('invoice_tax_no', '税号', p.invoice_tax_no)
    + _pField('invoice_address_phone', '地址电话', p.invoice_address_phone)
    + _pField('invoice_bank', '开户行', p.invoice_bank)
    + _pField('invoice_bank_account', '银行账号', p.invoice_bank_account)
    + '</div></div></details>';
  // 收件
  h += '<details style="background:#fff;border-radius:12px;border:1px solid #f1f5f9;">'
    + '<summary style="padding:16px 24px;cursor:pointer;font-size:15px;font-weight:700;color:#0f172a;display:flex;align-items:center;gap:6px;list-style:none;">'
    + '<span style="transition:transform .2s;display:inline-block;font-size:12px;color:#94a3b8;margin-right:4px;" class="fold-arrow">▶</span>📦 收件信息'
    + '</summary>'
    + '<div style="padding:0 24px 20px;">'
    + '<div style="display:flex;gap:6px;margin-bottom:12px;justify-content:flex-end;">'
    + '<button class="btn btn-sm" onclick="toggleCustomerRecvEdit(true)" id="customer-recv-edit-btn" style="font-size:12px;">编辑</button>'
    + '<button class="btn btn-sm" onclick="saveCustomerRecv(\'' + _safeHtml(p.client_name||'').replace(/'/g,"\\'") + '\')" id="customer-recv-save-btn" style="display:none;background:#1677ff;color:#fff;font-size:12px;">保存</button>'
    + '<button class="btn btn-sm" onclick="toggleCustomerRecvEdit(false)" id="customer-recv-cancel-btn" style="display:none;font-size:12px;">取消</button>'
    + '</div>'
    + '<div id="customer-profile-form-recv">'
    + _rField('recipient_name', '收件人', p.recipient_name)
    + _rField('recipient_phone', '电话', p.recipient_phone)
    + _rField('recipient_address', '地址', p.recipient_address)
    + '</div></div></details>';
  h += '</div>';

  /* --- 项目列表 --- */
  h += '<div style="background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:16px;border:1px solid #f1f5f9;">'
    + '<div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;">📂 关联项目 <span style="color:#94a3b8;font-weight:400;font-size:13px;">(' + projects.length + ')</span></div>';
  if (projects.length) {
    h += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">'
      + '<thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">'
      + '<th style="text-align:left;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">项目编号</th>'
      + '<th style="text-align:left;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">项目名称</th>'
      + '<th style="text-align:center;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">检测阶段</th>'
      + '<th style="text-align:center;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">报告状态</th>'
      + '<th style="text-align:right;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">合同额</th>'
      + '<th style="text-align:right;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">应收</th>'
      + '<th style="text-align:center;padding:10px 8px;color:#64748b;font-weight:600;font-size:12px;">催单</th>'
      + '</tr></thead><tbody>';
    projects.forEach(function(pr, i) {
      var ca = parseFloat(pr.contract_amount) || 0;
      var pa = parseFloat(pr.paid_amount) || 0;
      var recv = ca - pa;
      var recvStyle = recv > 0 ? 'color:#dc2626;font-weight:600;' : 'color:#16a34a;';
      var bgColor = i % 2 === 0 ? '#fff' : '#f8fafc';

      var stageBadge = _stageBadge(pr.inspection_stage || '');
      var reportBadge = _reportBadge(pr.report_status || '');
      var urgeMark = pr.has_urge ? '<span style="color:#dc2626;cursor:pointer;" title="点击清除催单" onclick="event.stopPropagation();clearUrge(' + pr.id + ',\'' + _safeHtml(pr.client_name||p.client_name||'').replace(/'/g,"\\'") + '\', this)">🔔 有催单</span>' : '<span style="color:#cbd5e1;">—</span>';

      h += '<tr style="border-bottom:1px solid #f1f5f9;background:' + bgColor + ';">'
        + '<td style="padding:10px 8px;color:#3b82f6;font-weight:500;white-space:nowrap;">' + _safeHtml(pr.project_no || '-') + '</td>'
        + '<td style="padding:10px 8px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + _safeHtml(pr.project_name || '-') + '</td>'
        + '<td style="padding:10px 8px;text-align:center;">' + stageBadge + '</td>'
        + '<td style="padding:10px 8px;text-align:center;">' + reportBadge + '</td>'
        + '<td style="padding:10px 8px;text-align:right;">' + _money(ca) + '</td>'
        + '<td style="padding:10px 8px;text-align:right;' + recvStyle + '">' + _money(recv) + '</td>'
        + '<td style="padding:10px 8px;text-align:center;font-size:12px;">' + urgeMark + '</td>'
        + '</tr>';
    });
    h += '</tbody></table></div>';
  } else {
    h += '<div style="padding:30px;text-align:center;color:#94a3b8;">暂无项目</div>';
  }
  h += '</div>';

  /* --- 反馈记录 --- */
  if (feedbacks.length) {
    h += '<div style="background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:16px;border:1px solid #f1f5f9;">'
      + '<div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;">💬 反馈记录 <span style="color:#94a3b8;font-weight:400;font-size:13px;">(' + feedbacks.length + ')</span></div>';
    feedbacks.forEach(function(fb) {
      var statusColor = fb.status === '待处理' ? '#dc2626' : '#16a34a';
      var attachments = Array.isArray(fb.attachments) ? fb.attachments : [];
      var attachmentHtml = attachments.length
        ? '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">' + attachments.map(function(att) {
            return '<a href="' + _safeHtml(att.download_url || '#') + '" target="_blank" rel="noopener noreferrer" style="font-size:12px;padding:4px 8px;border:1px solid #dbeafe;border-radius:999px;background:#eff6ff;color:#1d4ed8;text-decoration:none;">📎 ' + _safeHtml(att.original_name || '附件') + '</a>';
          }).join('') + '</div>'
        : '';
      h += '<div style="padding:12px 16px;border-radius:8px;border:1px solid #f1f5f9;margin-bottom:8px;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<span style="font-weight:600;font-size:13px;">' + _safeHtml(fb.project_name || '-') + '</span>'
        + '<span style="font-size:11px;color:' + statusColor + ';font-weight:600;">' + _safeHtml(fb.status || '') + '</span>'
        + '</div>'
        + '<div style="font-size:13px;color:#334155;margin-bottom:4px;">' + _safeHtml(fb.content || '') + '</div>'
        + '<div style="font-size:11px;color:#94a3b8;">' + _safeHtml(fb.created_at || '') + '</div>'
        + attachmentHtml;
      if (fb.reply) {
        h += '<div style="margin-top:8px;padding:8px 12px;background:#f0fdf4;border-radius:6px;font-size:12px;color:#16a34a;">↩️ ' + _safeHtml(fb.reply) + '</div>';
      } else if (fb.status === '待处理') {
        h += '<div style="margin-top:8px;">'
          + '<input type="hidden" id="fb-version-' + fb.id + '" value="' + _safeHtml(fb.version || 1) + '">'
          + '<input type="text" id="fb-reply-' + fb.id + '" placeholder="输入回复..." style="padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;width:70%;margin-right:6px;">'
          + '<button class="btn btn-sm" onclick="replyFeedback(' + fb.id + ',\'' + _safeHtml(p.client_name||'').replace(/'/g,"\\'") + '\', this)" style="background:#1677ff;color:#fff;font-size:12px;">回复</button>'
          + '</div>';
      }
      h += '</div>';
    });
    h += '</div>';
  }

  /* --- 催单记录 --- */
  if (urgeLogs.length) {
    h += '<div style="background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:16px;border:1px solid #f1f5f9;">'
      + '<div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;">⚡ 催单记录 <span style="color:#94a3b8;font-weight:400;font-size:13px;">(' + urgeLogs.length + ')</span></div>';
    urgeLogs.forEach(function(u) {
      h += '<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f8fafc;font-size:13px;">'
        + '<span style="color:#94a3b8;font-size:12px;white-space:nowrap;">' + _safeHtml((u.created_at||'').slice(0,16)) + '</span>'
        + '<span style="color:#334155;">' + _safeHtml(u.project_name || '-') + '</span>'
        + (u.remark ? '<span style="color:#64748b;font-size:12px;">— ' + _safeHtml(u.remark) + '</span>' : '')
        + '</div>';
    });
    h += '</div>';
  }

  /* --- 导出报告 --- */
  if (reports.length) {
    h += '<div style="background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:16px;border:1px solid #f1f5f9;">'
      + '<div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:14px;">📄 导出报告 <span style="color:#94a3b8;font-weight:400;font-size:13px;">(' + reports.length + ')</span></div>';
    reports.forEach(function(r) {
      h += '<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f8fafc;font-size:13px;">'
        + '<span style="color:#3b82f6;font-weight:500;">' + _safeHtml(r.report_no || '-') + '</span>'
        + '<span style="color:#334155;">' + _safeHtml(r.project_name || '') + '</span>'
        + '<span style="color:#94a3b8;font-size:12px;margin-left:auto;">' + _safeHtml((r.export_time||'').slice(0,16)) + '</span>'
        + (r.feishu_url ? '<a href="' + _safeHtml(r.feishu_url) + '" target="_blank" style="color:#3b82f6;font-size:12px;text-decoration:none;">查看</a>' : '')
        + '</div>';
    });
    h += '</div>';
  }

  box.innerHTML = h;
}

/* --- 表单字段 --- */
function _pField(name, label, value) {
  return '<div style="margin-bottom:10px;">'
    + '<label style="display:block;font-size:11px;color:#94a3b8;margin-bottom:2px;">' + label + '</label>'
    + '<input type="text" data-profile-field="' + name + '" value="' + _safeHtml(value || '') + '" disabled '
    + 'style="width:100%;padding:7px 10px;border:1px solid #e2e8f0;border-radius:6px;font-size:13px;color:#334155;background:#f8fafc;box-sizing:border-box;transition:all .15s;">'
    + '</div>';
}

function _rField(name, label, value) {
  return '<div style="margin-bottom:10px;">'
    + '<label style="display:block;font-size:11px;color:#94a3b8;margin-bottom:2px;">' + label + '</label>'
    + '<input type="text" data-recv-field="' + name + '" value="' + _safeHtml(value || '') + '" disabled '
    + 'style="width:100%;padding:7px 10px;border:1px solid #e2e8f0;border-radius:6px;font-size:13px;color:#334155;background:#f8fafc;box-sizing:border-box;transition:all .15s;">'
    + '</div>';
}

/* --- 状态徽章 --- */
function _stageBadge(stage) {
  var map = {
    '待检测': { bg: '#fef3c7', c: '#d97706', b: '#fde68a' },
    '检测中': { bg: '#dbeafe', c: '#2563eb', b: '#bfdbfe' },
    '已完成': { bg: '#dcfce7', c: '#16a34a', b: '#bbf7d0' }
  };
  var s = map[stage] || { bg: '#f1f5f9', c: '#64748b', b: '#e2e8f0' };
  return '<span style="display:inline-block;background:' + s.bg + ';color:' + s.c + ';border:1px solid ' + s.b + ';border-radius:999px;padding:2px 10px;font-size:11px;font-weight:600;white-space:nowrap;">' + _safeHtml(stage || '-') + '</span>';
}

function _reportBadge(status) {
  var map = {
    '未出具': { bg: '#f1f5f9', c: '#64748b', b: '#e2e8f0' },
    '已出具': { bg: '#dbeafe', c: '#2563eb', b: '#bfdbfe' },
    '待客户确认': { bg: '#fef3c7', c: '#d97706', b: '#fde68a' },
    '客户已确认': { bg: '#dcfce7', c: '#16a34a', b: '#bbf7d0' }
  };
  var s = map[status] || { bg: '#f1f5f9', c: '#64748b', b: '#e2e8f0' };
  return '<span style="display:inline-block;background:' + s.bg + ';color:' + s.c + ';border:1px solid ' + s.b + ';border-radius:999px;padding:2px 10px;font-size:11px;font-weight:600;white-space:nowrap;">' + _safeHtml(status || '-') + '</span>';
}

/* ========== 7. 编辑/保存 profile ========== */
function toggleCustomerProfileEdit(editing) {
  var fields = document.querySelectorAll('[data-profile-field]');
  fields.forEach(function(f) {
    f.disabled = !editing;
    f.style.background = editing ? '#fff' : '#f8fafc';
    f.style.borderColor = editing ? '#3b82f6' : '#e2e8f0';
  });
  var editBtn = document.getElementById('customer-profile-edit-btn');
  var saveBtn = document.getElementById('customer-profile-save-btn');
  var cancelBtn = document.getElementById('customer-profile-cancel-btn');
  if (editBtn) editBtn.style.display = editing ? 'none' : '';
  if (saveBtn) saveBtn.style.display = editing ? '' : 'none';
  if (cancelBtn) cancelBtn.style.display = editing ? '' : 'none';
}

function saveCustomerProfile(clientName) {
  var payload = { client_name: clientName };
  var verEl = document.getElementById('customer-profile-version');
  if(verEl && verEl.value) payload.version = Number(verEl.value) || 1;
  document.querySelectorAll('[data-profile-field]').forEach(function(f) {
    payload[f.getAttribute('data-profile-field')] = f.value;
  });
  var btn = document.getElementById('customer-profile-save-btn');
  var oldText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '保存中...'; }
  fetch('/admin/api/customer_management/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function(r) { return r.json().then(function(d){ return {ok:r.ok, status:r.status, data:d}; }); })
    .then(function(res) {
      var d = res.data || {};
      if (!res.ok || !d.success) {
        if(res.status === 409 || d.code === 'version_conflict'){
          throw new Error(d.error || '客户资料已被其他人修改，请刷新后重试');
        }
        throw new Error(d.error || '保存失败');
      }
      if (typeof showToast === 'function') showToast('保存成功', 'success');
      toggleCustomerProfileEdit(false);
      showCustomerDetail(clientName);
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '保存失败', 'error');
      showCustomerDetail(clientName);
    }).finally(function(){ if(btn){ btn.disabled = false; btn.textContent = oldText || '保存'; } });
}

/* ========== 7b. 收件信息编辑/保存 ========== */
function toggleCustomerRecvEdit(editing) {
  var fields = document.querySelectorAll('[data-recv-field]');
  fields.forEach(function(f) {
    f.disabled = !editing;
    f.style.background = editing ? '#fff' : '#f8fafc';
    f.style.borderColor = editing ? '#3b82f6' : '#e2e8f0';
  });
  var editBtn = document.getElementById('customer-recv-edit-btn');
  var saveBtn = document.getElementById('customer-recv-save-btn');
  var cancelBtn = document.getElementById('customer-recv-cancel-btn');
  if (editBtn) editBtn.style.display = editing ? 'none' : '';
  if (saveBtn) saveBtn.style.display = editing ? '' : 'none';
  if (cancelBtn) cancelBtn.style.display = editing ? '' : 'none';
}

function saveCustomerRecv(clientName) {
  var payload = { client_name: clientName };
  var verEl = document.getElementById('customer-profile-version');
  if(verEl && verEl.value) payload.version = Number(verEl.value) || 1;
  document.querySelectorAll('[data-recv-field]').forEach(function(f) {
    payload[f.getAttribute('data-recv-field')] = f.value;
  });
  var btn = document.getElementById('customer-recv-save-btn');
  var oldText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '保存中...'; }
  fetch('/admin/api/customer_management/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function(r) { return r.json().then(function(d){ return {ok:r.ok, status:r.status, data:d}; }); })
    .then(function(res) {
      var d = res.data || {};
      if (!res.ok || !d.success) {
        if(res.status === 409 || d.code === 'version_conflict'){
          throw new Error(d.error || '客户资料已被其他人修改，请刷新后重试');
        }
        throw new Error(d.error || '保存失败');
      }
      if (typeof showToast === 'function') showToast('收件信息已保存', 'success');
      toggleCustomerRecvEdit(false);
      showCustomerDetail(clientName);
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '保存失败', 'error');
      showCustomerDetail(clientName);
    }).finally(function(){ if(btn){ btn.disabled = false; btn.textContent = oldText || '保存'; } });
}

/* ========== 8. 清除催单 ========== */
function clearUrge(projectId, clientName, btnEl) {
  if (!confirm('确认清除该项目的催单标记？')) return;
  var btn = btnEl || null;
  var oldText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '清除中...'; }
  fetch('/admin/api/customer_management/clear_urge/' + projectId, { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '操作失败');
      if (typeof showToast === 'function') showToast('催单标记已清除', 'success');
      showCustomerDetail(clientName);
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '操作失败', 'error');
    }).finally(function(){ if(btn){ btn.disabled = false; btn.textContent = oldText || '🔔 有催单'; } });
}

/* ========== 9. 回复反馈 ========== */
function replyFeedback(fbId, clientName, btnEl) {
  var input = document.getElementById('fb-reply-' + fbId);
  var verEl = document.getElementById('fb-version-' + fbId);
  var reply = input ? input.value.trim() : '';
  if (!reply) { if (typeof showToast === 'function') showToast('请输入回复内容', 'error'); return; }
  var payload = { reply: reply, status: '已处理' };
  if(verEl && verEl.value) payload.version = Number(verEl.value) || 1;
  var btn = btnEl || null;
  var oldText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '回复中...'; }
  fetch('/admin/api/customer_management/feedback/' + fbId + '/reply', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function(r) { return r.json().then(function(d){ return {ok:r.ok, status:r.status, data:d}; }); })
    .then(function(res) {
      var d = res.data || {};
      if (!res.ok || !d.success) {
        if(res.status === 409 || d.code === 'version_conflict'){
          throw new Error(d.error || '反馈已被其他人处理，请刷新后重试');
        }
        throw new Error(d.error || '回复失败');
      }
      if (typeof showToast === 'function') showToast('已回复', 'success');
      showCustomerDetail(clientName);
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '回复失败', 'error');
      showCustomerDetail(clientName);
    }).finally(function(){ if(btn){ btn.disabled = false; btn.textContent = oldText || '回复'; } });
}

/* ========== 10. 返回列表 ========== */
function backToCustomerList() {
  document.getElementById('customer-detail-view').style.display = 'none';
  document.getElementById('customer-list-view').style.display = '';
  loadCustomerList();
}

/* ========== 11. 新增客户 ========== */
function openCustomerCreateModal() {
  var existing = document.getElementById('customer-create-modal');
  if (existing) existing.remove();

  var modal = document.createElement('div');
  modal.id = 'customer-create-modal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,0.4);display:flex;align-items:center;justify-content:center;z-index:10000;backdrop-filter:blur(2px);';
  modal.innerHTML = '<div style="background:#fff;border-radius:16px;padding:28px 32px;width:480px;max-width:92vw;box-shadow:0 20px 60px rgba(0,0,0,0.15);max-height:90vh;overflow-y:auto;">'
    + '<div style="font-size:17px;font-weight:700;color:#0f172a;margin-bottom:20px;">➕ 新增客户</div>'
    + '<div style="font-size:12px;color:#64748b;margin-bottom:16px;padding:8px 12px;background:#f8fafc;border-radius:8px;">创建客户主数据，可选同时创建登录账号</div>'
    + _createField('new-customer-name', '客户名称（公司）', '公司/单位全称', true)
    + '<div style="display:flex;gap:12px;">'
    + '<div style="flex:1;">' + _createField('new-customer-contact', '联系人', '姓名', false) + '</div>'
    + '<div style="flex:1;">' + _createField('new-customer-phone', '联系电话', '手机号', false) + '</div>'
    + '</div>'
    + '<div style="border-top:1px dashed #e2e8f0;margin:16px 0;padding-top:16px;">'
    + '<div style="font-size:13px;font-weight:600;color:#334155;margin-bottom:12px;">🔐 登录账号（选填）</div>'
    + '<div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">填写后客户可直接登录客户端查看项目进度</div>'
    + '<div style="display:flex;gap:12px;">'
    + '<div style="flex:1;">' + _createField('new-customer-username', '用户名', '字母数字下划线，3-20位', false) + '</div>'
    + '<div style="flex:1;">' + _createField('new-customer-password', '初始密码', '至少6位', false) + '</div>'
    + '</div></div>'
    + '<div style="display:flex;justify-content:flex-end;gap:10px;margin-top:20px;">'
    + '<button class="btn btn-sm" onclick="closeCustomerCreateModal()" style="padding:8px 20px;">取消</button>'
    + '<button class="btn btn-sm" onclick="submitCustomerCreate()" style="padding:8px 20px;background:#2563eb;color:#fff;border:none;">创建</button>'
    + '</div></div>';
  document.body.appendChild(modal);
  modal.addEventListener('click', function(e) { if (e.target === modal) closeCustomerCreateModal(); });
  setTimeout(function() { var el = document.getElementById('new-customer-name'); if (el) el.focus(); }, 100);
}

function _createField(id, label, placeholder, required) {
  return '<div style="margin-bottom:14px;">'
    + '<label style="display:block;font-size:12px;color:#64748b;margin-bottom:4px;font-weight:500;">' + label + (required ? ' <span style="color:#dc2626;">*</span>' : '') + '</label>'
    + '<input id="' + id + '" type="text" placeholder="' + placeholder + '" style="width:100%;padding:9px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;box-sizing:border-box;transition:border-color .15s;" onfocus="this.style.borderColor=\'#3b82f6\'" onblur="this.style.borderColor=\'#e2e8f0\'">'
    + '</div>';
}

function closeCustomerCreateModal() {
  var m = document.getElementById('customer-create-modal');
  if (m) m.remove();
}

function submitCustomerCreate() {
  var name = (document.getElementById('new-customer-name')?.value || '').trim();
  var contact = (document.getElementById('new-customer-contact')?.value || '').trim();
  var phone = (document.getElementById('new-customer-phone')?.value || '').trim();
  var username = (document.getElementById('new-customer-username')?.value || '').trim();
  var password = (document.getElementById('new-customer-password')?.value || '').trim();
  if (!name) { if (typeof showToast === 'function') showToast('客户名称不能为空', 'error'); return; }

  var payload = { client_name: name, contact_name: contact, contact_phone: phone };
  if (username) payload.username = username;
  if (password) payload.password = password;
  var btn = document.querySelector('#customer-create-modal button[onclick="submitCustomerCreate()"]');
  var oldText = btn ? btn.textContent : '';
  if(btn && btn.disabled) return;
  if(btn){ btn.disabled = true; btn.textContent = '创建中...'; }
  fetch('/admin/api/customer_management/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '创建失败');
      if (typeof showToast === 'function') showToast(d.message || '客户创建成功', 'success');
      closeCustomerCreateModal();
      loadCustomerList();
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '创建失败', 'error');
    }).finally(function(){ if(btn){ btn.disabled = false; btn.textContent = oldText || '创建'; } });
}

/* ========== 12. 删除客户 ========== */
function deleteCustomer(clientName) {
  fetch('/admin/api/customer_management/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_name: clientName, inspect_only: true })
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '获取删除影响失败');
      var impact = d.impact || {};
      var msg = '确认删除客户「' + clientName + '」？\n\n'
        + '关联项目：' + (impact.project_count || 0) + ' 个\n'
        + '客户反馈：' + (impact.feedback_count || 0) + ' 条\n'
        + '客户账号：' + (impact.account_count || 0) + ' 个\n\n'
        + '删除后会移除客户资料、催单记录、反馈记录；若强制删除且有关联项目，则只解除项目客户绑定。';
      if (!confirm(msg)) return;
      _doDeleteCustomer(clientName, false);
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '删除前检查失败', 'error');
      else alert(err.message || '删除前检查失败');
    });
}

function _doDeleteCustomer(clientName, force) {
  var btns = [...document.querySelectorAll('button[onclick*="deleteCustomer(\\x27' + clientName.replace(/'/g, "\\'") + '\\x27)"]')];
  btns.forEach(function(btn){ btn.disabled = true; btn.dataset.oldText = btn.textContent; btn.textContent = '删除中...'; });
  fetch('/admin/api/customer_management/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_name: clientName, force: force })
  })
    .then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); })
    .then(function(res) {
      if (res.data.success) {
        if (typeof showToast === 'function') showToast(res.data.message || '客户已删除', 'success');
        var detailView = document.getElementById('customer-detail-view');
        if (detailView && detailView.style.display !== 'none') backToCustomerList();
        else loadCustomerList();
        return;
      }
      if (res.data.has_projects) {
        var cnt = res.data.project_count || 0;
        if (confirm('该客户关联 ' + cnt + ' 个项目。\n\n强制删除将解除项目关联（项目不会被删除，仅清空客户字段）。\n\n确认强制删除？')) {
          _doDeleteCustomer(clientName, true);
        }
        return;
      }
      throw new Error(res.data.error || '删除失败');
    })
    .catch(function(err) {
      if (typeof showToast === 'function') showToast(err.message || '删除失败', 'error');
      else alert(err.message || '删除失败');
    }).finally(function(){ btns.forEach(function(btn){ btn.disabled = false; btn.textContent = btn.dataset.oldText || '删除'; }); });
}
