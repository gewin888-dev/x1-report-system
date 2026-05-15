/* ============================================================
 * admin_customers.js — 客户管理面板
 * ============================================================ */

var customerPanelInited = false;
var customerListData = [];
var customerSearchTimer = null;

/* ---------- 1. 初始化 ---------- */
function initCustomersPanel() {
  if (!customerPanelInited) {
    customerPanelInited = true;
  }
  loadCustomerList();
}

/* ---------- 2. 加载客户列表 ---------- */
function loadCustomerList() {
  fetch('/admin/api/customer_management/list')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '加载失败');
      customerListData = d.items || [];
      renderCustomerSummary(d.summary || {});
      renderCustomerList(customerListData);
    })
    .catch(function(err) {
      console.error(err);
      var box = document.getElementById('customer-list-container');
      if (box) box.innerHTML = '<div class="empty">加载客户列表失败</div>';
    });
}

/* ---------- 3. 汇总卡片 ---------- */
function renderCustomerSummary(summary) {
  var el;
  el = document.getElementById('cs-total');
  if (el) el.textContent = summary.total || 0;
  el = document.getElementById('cs-with-projects');
  if (el) el.textContent = summary.with_projects || 0;
  el = document.getElementById('cs-pending-urge');
  if (el) el.textContent = summary.pending_urge || 0;
  el = document.getElementById('cs-pending-feedback');
  if (el) el.textContent = summary.pending_feedback || 0;
  el = document.getElementById('cs-receivable');
  if (el) el.textContent = summary.receivable_clients || 0;
}

/* ---------- 4. 渲染客户列表 ---------- */
function renderCustomerList(items) {
  var container = document.getElementById('customer-list-container');
  if (!container) return;
  if (!items || !items.length) {
    container.innerHTML = '<div class="empty" style="padding:40px;text-align:center;color:#999;">暂无客户数据</div>';
    return;
  }
  var html = '';
  items.forEach(function(item) {
    var receivableStyle = (parseFloat(item.receivable) || 0) > 0 ? 'color:#cf1322;font-weight:600;' : 'color:#389e0d;';
    var urgeBadge = (item.urge_count || 0) > 0
      ? '<span style="background:#fff1f0;color:#cf1322;border:1px solid #ffa39e;border-radius:999px;padding:1px 7px;font-size:11px;margin-left:4px;">🔔' + item.urge_count + '</span>'
      : '';
    var feedbackBadge = (item.feedback_count || 0) > 0
      ? '<span style="background:#fff7e6;color:#d46b08;border:1px solid #ffd591;border-radius:999px;padding:1px 7px;font-size:11px;margin-left:4px;">💬' + item.feedback_count + '</span>'
      : '';
    var accountTag = item.has_account
      ? '<span style="background:#f6ffed;color:#389e0d;border:1px solid #b7eb8f;border-radius:999px;padding:1px 7px;font-size:11px;">✅ 已开通</span>'
      : '<span style="background:#fafafa;color:#999;border:1px solid #d9d9d9;border-radius:999px;padding:1px 7px;font-size:11px;">未开通</span>';
    var domains = '';
    if (item.domains) {
      var darr = typeof item.domains === 'string' ? item.domains.split(',').filter(function(s){return s.trim();}) : item.domains;
      domains = darr.map(function(d) {
        return '<span style="background:#e6f4ff;color:#0958d9;border-radius:4px;padding:1px 6px;font-size:11px;margin-right:4px;">' + escapeHtml(d.trim()) + '</span>';
      }).join('');
    }
    var money = function(v) { var n = parseFloat(v) || 0; return n ? '¥' + n.toLocaleString('zh-CN', {minimumFractionDigits: 0, maximumFractionDigits: 2}) : '-'; };

    html += '<div class="customer-card" onclick="showCustomerDetail(\'' + escapeHtml(item.client_name).replace(/'/g, "\\'") + '\')" style="'
      + 'background:#fff;border-radius:10px;padding:14px 20px;margin-bottom:8px;cursor:pointer;'
      + 'border:1px solid #f0f0f0;transition:background 0.15s;"'
      + ' onmouseenter="this.style.background=\'#f0f7ff\'" onmouseleave="this.style.background=\'#fff\'">'
      + '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">'
      + '<div style="display:flex;align-items:center;gap:12px;flex:1;min-width:0;">'
      + '<span style="font-size:15px;font-weight:600;">🏢 ' + escapeHtml(item.client_name) + '</span>'
      + '<span style="color:#666;font-size:13px;">' + escapeHtml(item.contact_name || '-') + '</span>'
      + '<span style="color:#888;font-size:12px;font-family:monospace;">' + escapeHtml(item.contact_phone || '') + '</span>'
      + '</div>'
      + '<div style="display:flex;align-items:center;gap:12px;font-size:13px;">'
      + '<span>项目 <b>' + (item.project_count || 0) + '</b></span>'
      + '<span>合同 <b>' + money(item.total_contract) + '</b></span>'
      + '<span style="' + receivableStyle + '">应收 ' + money(item.receivable) + '</span>'
      + '</div>'
      + '</div>'
      + '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:6px;flex-wrap:wrap;gap:4px;">'
      + '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
      + domains
      + '<span style="color:#aaa;font-size:12px;margin-left:8px;">最近项目 ' + escapeHtml(item.last_project_date || '-') + '</span>'
      + '</div>'
      + '<div style="display:flex;align-items:center;gap:6px;">'
      + urgeBadge + feedbackBadge + ' ' + accountTag
      + '</div>'
      + '</div>'
      + '</div>';
  });
  container.innerHTML = html;
}

/* ---------- 5. 搜索过滤 ---------- */
function filterCustomerList() {
  clearTimeout(customerSearchTimer);
  customerSearchTimer = setTimeout(function() {
    var keyword = (document.getElementById('customer-search')?.value || '').trim().toLowerCase();
    if (!keyword) {
      renderCustomerList(customerListData);
      return;
    }
    var filtered = customerListData.filter(function(item) {
      var name = (item.client_name || '').toLowerCase();
      var contact = (item.contact_name || '').toLowerCase();
      var phone = (item.contact_phone || '').toLowerCase();
      return name.indexOf(keyword) >= 0 || contact.indexOf(keyword) >= 0 || phone.indexOf(keyword) >= 0;
    });
    renderCustomerList(filtered);
  }, 200);
}

/* ---------- 6. 客户详情 ---------- */
function showCustomerDetail(clientName) {
  document.getElementById('customer-list-view').style.display = 'none';
  document.getElementById('customer-detail-view').style.display = '';
  var contentEl = document.getElementById('customer-detail-content');
  contentEl.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">加载中...</div>';

  fetch('/admin/api/customer_management/detail?client_name=' + encodeURIComponent(clientName))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '加载失败');
      renderCustomerDetail(d);
    })
    .catch(function(err) {
      console.error(err);
      contentEl.innerHTML = '<div style="text-align:center;padding:40px;color:#cf1322;">加载详情失败: ' + escapeHtml(err.message) + '</div>';
    });
}

function renderCustomerDetail(data) {
  var profile = data.profile || {};
  var projects = data.projects || [];
  var urgeLogs = data.urge_logs || [];
  var feedbacks = data.feedbacks || [];
  var reports = data.reports || [];
  var account = data.account || {};
  var contentEl = document.getElementById('customer-detail-content');

  var html = '';

  // 4a: 头部信息卡
  var accountStatus = account && account.user_id
    ? '<span style="color:#389e0d;">✅ 已开通</span>'
    : '<span style="color:#999;">未开通</span>';
  var lastDate = '';
  if (projects.length) {
    var dates = projects.map(function(p) { return p.last_project_date || p.updated_at || ''; }).filter(Boolean).sort();
    lastDate = dates.length ? dates[dates.length - 1].slice(0, 10) : '-';
  }

  html += '<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
    + '<div style="font-size:18px;font-weight:700;margin-bottom:8px;">🏢 ' + escapeHtml(profile.client_name || '') + '</div>'
    + '<div style="display:flex;gap:24px;flex-wrap:wrap;font-size:13px;color:#555;">'
    + '<span>联系人: <b>' + escapeHtml(profile.recipient_name || '-') + '</b></span>'
    + '<span>电话: <b>' + escapeHtml(profile.recipient_phone || '-') + '</b></span>'
    + '<span>账号: ' + accountStatus + '</span>'
    + '<span>最近项目: ' + escapeHtml(lastDate || '-') + '</span>'
    + '</div></div>';

  // 4b: 基础信息（可编辑）
  var selfMaintained = profile.updated_at
    ? '<span style="color:#389e0d;font-size:12px;margin-left:8px;">客户自维护 ✅</span>'
    : '';

  html += '<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
    + '<div style="font-size:16px;font-weight:700;margin-bottom:12px;">📋 基础信息' + selfMaintained + '</div>'
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;" id="customer-profile-form">'
    // 左栏 - 开票信息
    + '<div>'
    + '<div style="font-size:14px;font-weight:600;margin-bottom:8px;color:#333;">开票信息</div>'
    + _profileField('invoice_company', '公司名称', profile.invoice_company)
    + _profileField('invoice_tax_no', '税号', profile.invoice_tax_no)
    + _profileField('invoice_address_phone', '地址电话', profile.invoice_address_phone)
    + _profileField('invoice_bank', '开户行', profile.invoice_bank)
    + _profileField('invoice_bank_account', '银行账号', profile.invoice_bank_account)
    + '</div>'
    // 右栏 - 收件信息
    + '<div>'
    + '<div style="font-size:14px;font-weight:600;margin-bottom:8px;color:#333;">收件信息</div>'
    + _profileField('recipient_name', '收件人', profile.recipient_name)
    + _profileField('recipient_phone', '电话', profile.recipient_phone)
    + _profileField('recipient_address', '地址', profile.recipient_address)
    + '</div>'
    + '</div>'
    + '<div style="margin-top:12px;text-align:right;">'
    + '<button class="btn btn-sm" id="customer-profile-edit-btn" onclick="toggleCustomerProfileEdit(true)" style="margin-right:8px;">编辑</button>'
    + '<button class="btn btn-sm" id="customer-profile-save-btn" onclick="saveCustomerProfile(\'' + escapeHtml(profile.client_name || '').replace(/'/g, "\\'") + '\')" style="display:none;background:#1677ff;color:#fff;">保存</button>'
    + '<button class="btn btn-sm" id="customer-profile-cancel-btn" onclick="toggleCustomerProfileEdit(false)" style="display:none;">取消</button>'
    + '</div>'
    + '</div>';

  // 4c: 项目列表
  html += '<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
    + '<div style="font-size:16px;font-weight:700;margin-bottom:12px;">📂 关联项目</div>';
  if (projects.length) {
    html += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">'
      + '<thead><tr style="border-bottom:1px solid #f0f0f0;">'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">项目编号</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">项目名称</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">检测领域</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">检测阶段</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">报告状态</th>'
      + '<th style="text-align:right;padding:8px 6px;color:#666;font-weight:500;">合同额</th>'
      + '<th style="text-align:right;padding:8px 6px;color:#666;font-weight:500;">已收</th>'
      + '<th style="text-align:right;padding:8px 6px;color:#666;font-weight:500;">应收</th>'
      + '<th style="text-align:center;padding:8px 6px;color:#666;font-weight:500;">催单</th>'
      + '<th style="text-align:center;padding:8px 6px;color:#666;font-weight:500;">来源</th>'
      + '</tr></thead><tbody>';
    projects.forEach(function(p) {
      var ca = parseFloat(p.contract_amount) || 0;
      var pa = parseFloat(p.paid_amount) || 0;
      var ra = ca - pa;
      var raStyle = ra > 0 ? 'color:#cf1322;' : 'color:#389e0d;';
      var fmtAmt = function(v) { var n = parseFloat(v) || 0; return n ? '¥' + n.toLocaleString('zh-CN', {minimumFractionDigits: 0, maximumFractionDigits: 2}) : '-'; };
      var urgeCell = p.has_urge
        ? '<span style="cursor:pointer;font-size:16px;" title="点击清除催单" onclick="event.stopPropagation();clearCustomerUrge(' + (p.id) + ',\'' + escapeHtml(profile.client_name || '').replace(/'/g, "\\'") + '\')">🔔</span>'
        : '';
      var sourceCell = p.source === '客户需求'
        ? '<span style="background:#e6f4ff;color:#0958d9;border-radius:999px;padding:1px 7px;font-size:11px;">客户需求</span>'
        : '';
      html += '<tr style="border-bottom:1px solid #f5f5f5;transition:background 0.1s;" onmouseenter="this.style.background=\'#fafafa\'" onmouseleave="this.style.background=\'\'">'
        + '<td style="padding:8px 6px;font-family:monospace;font-size:12px;color:#0958d9;">' + escapeHtml(p.project_no || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + escapeHtml(p.project_name || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + escapeHtml(p.detection_domain || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + escapeHtml(p.inspection_stage || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + escapeHtml(p.report_status || '-') + '</td>'
        + '<td style="padding:8px 6px;text-align:right;font-family:monospace;">' + fmtAmt(ca) + '</td>'
        + '<td style="padding:8px 6px;text-align:right;font-family:monospace;color:#389e0d;">' + fmtAmt(pa) + '</td>'
        + '<td style="padding:8px 6px;text-align:right;font-family:monospace;' + raStyle + '">' + fmtAmt(ra) + '</td>'
        + '<td style="padding:8px 6px;text-align:center;">' + urgeCell + '</td>'
        + '<td style="padding:8px 6px;text-align:center;">' + sourceCell + '</td>'
        + '</tr>';
    });
    html += '</tbody></table></div>';
  } else {
    html += '<div style="color:#999;padding:12px 0;">暂无关联项目</div>';
  }
  html += '</div>';

  // 4d: 催单记录
  html += '<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
    + '<div style="font-size:16px;font-weight:700;margin-bottom:12px;">🔔 催单记录</div>';
  if (urgeLogs.length) {
    html += '<div style="border-left:2px solid #d9d9d9;padding-left:16px;">';
    urgeLogs.forEach(function(log) {
      html += '<div style="position:relative;margin-bottom:12px;padding-left:12px;">'
        + '<div style="position:absolute;left:-22px;top:4px;width:8px;height:8px;border-radius:50%;background:#1677ff;"></div>'
        + '<div style="font-size:13px;color:#333;">' + escapeHtml(log.urge_type === 'report' ? '催报告' : log.urge_type === 'invoice' ? '催发票' : '催单') + '</div>'
        + '<div style="font-size:11px;color:#aaa;margin-top:2px;">' + escapeHtml(log.created_at || '') + '</div>'
        + '</div>';
    });
    html += '</div>';
  } else {
    html += '<div style="color:#999;padding:4px 0;font-size:13px;">暂无催单记录</div>';
  }
  html += '</div>';

  // 4e: 反馈记录
  html += '<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
    + '<div style="font-size:16px;font-weight:700;margin-bottom:12px;">💬 反馈记录</div>';
  if (feedbacks.length) {
    feedbacks.forEach(function(fb) {
      var borderColor = fb.status === '未处理' ? '#fa8c16' : '#f0f0f0';
      html += '<div style="border:1px solid ' + borderColor + ';border-radius:8px;padding:14px;margin-bottom:10px;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        + '<span style="background:#e6f4ff;color:#0958d9;border-radius:999px;padding:1px 7px;font-size:11px;">' + escapeHtml(fb.feedback_type || '反馈') + '</span>'
        + '<span style="font-weight:600;font-size:14px;">' + escapeHtml(fb.title || '') + '</span>'
        + '<span style="margin-left:auto;font-size:11px;color:#aaa;">' + escapeHtml(fb.created_at || '') + '</span>'
        + '<span style="font-size:11px;padding:1px 6px;border-radius:999px;' + (fb.status === '未处理' ? 'background:#fff7e6;color:#d46b08;' : 'background:#f6ffed;color:#389e0d;') + '">' + escapeHtml(fb.status || '') + '</span>'
        + '</div>'
        + '<div style="font-size:13px;color:#444;margin-bottom:8px;">' + escapeHtml(fb.content || '') + '</div>';
      if (fb.reply) {
        html += '<div style="background:#f6ffed;border-radius:6px;padding:8px 12px;font-size:12px;color:#333;"><b>回复:</b> ' + escapeHtml(fb.reply) + '</div>';
      }
      html += '<div style="margin-top:8px;" id="feedback-reply-area-' + fb.id + '">'
        + '<button class="btn btn-sm" onclick="toggleFeedbackReply(' + fb.id + ')" style="font-size:12px;">回复</button>'
        + '<div id="feedback-reply-box-' + fb.id + '" style="display:none;margin-top:8px;">'
        + '<textarea id="feedback-reply-text-' + fb.id + '" style="width:100%;height:60px;border:1px solid #d9d9d9;border-radius:6px;padding:8px;font-size:13px;resize:vertical;" placeholder="输入回复内容..."></textarea>'
        + '<div style="margin-top:6px;display:flex;align-items:center;gap:8px;">'
        + '<select id="feedback-reply-status-' + fb.id + '" style="border:1px solid #d9d9d9;border-radius:6px;padding:4px 8px;font-size:12px;">'
        + '<option value="已处理">已处理</option><option value="处理中">处理中</option><option value="未处理">未处理</option></select>'
        + '<button class="btn btn-sm" onclick="submitFeedbackReply(' + fb.id + ',\'' + escapeHtml(profile.client_name || '').replace(/'/g, "\\'") + '\')" style="background:#1677ff;color:#fff;font-size:12px;">提交</button>'
        + '</div></div></div>';
      html += '</div>';
    });
  } else {
    html += '<div style="color:#999;padding:4px 0;font-size:13px;">暂无反馈记录</div>';
  }
  html += '</div>';

  // 4f: 报告记录
  html += '<div style="background:#fff;border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
    + '<div style="font-size:16px;font-weight:700;margin-bottom:12px;">📄 报告记录</div>';
  if (reports.length) {
    html += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;">'
      + '<thead><tr style="border-bottom:1px solid #f0f0f0;">'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">项目名称</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">检测类型</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">报告编号</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">导出时间</th>'
      + '<th style="text-align:left;padding:8px 6px;color:#666;font-weight:500;">预览</th>'
      + '</tr></thead><tbody>';
    reports.forEach(function(rpt) {
      var previewLink = rpt.feishu_url
        ? '<a href="' + escapeHtml(rpt.feishu_url) + '" target="_blank" style="color:#1677ff;text-decoration:none;">查看</a>'
        : '-';
      html += '<tr style="border-bottom:1px solid #f5f5f5;transition:background 0.1s;" onmouseenter="this.style.background=\'#fafafa\'" onmouseleave="this.style.background=\'\'">'
        + '<td style="padding:8px 6px;">' + escapeHtml(rpt.project_name || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + escapeHtml(rpt.detection_type || '-') + '</td>'
        + '<td style="padding:8px 6px;font-family:monospace;">' + escapeHtml(rpt.report_no || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + escapeHtml((rpt.export_time || '').replace('T', ' ').slice(0, 16) || '-') + '</td>'
        + '<td style="padding:8px 6px;">' + previewLink + '</td>'
        + '</tr>';
    });
    html += '</tbody></table></div>';
  } else {
    html += '<div style="color:#999;padding:4px 0;font-size:13px;">暂无报告记录</div>';
  }
  html += '</div>';

  contentEl.innerHTML = html;
}

/* ---------- 辅助：表单字段渲染 ---------- */
function _profileField(name, label, value) {
  return '<div style="margin-bottom:8px;">'
    + '<label style="display:block;font-size:12px;color:#888;margin-bottom:2px;">' + escapeHtml(label) + '</label>'
    + '<input type="text" data-profile-field="' + name + '" value="' + escapeHtml(value || '') + '" disabled '
    + 'style="width:100%;padding:6px 10px;border:1px solid #f0f0f0;border-radius:6px;font-size:13px;background:#fafafa;color:#444;box-sizing:border-box;transition:all 0.15s;" />'
    + '</div>';
}

/* ---------- 7. 编辑/保存客户档案 ---------- */
function toggleCustomerProfileEdit(editing) {
  var fields = document.querySelectorAll('#customer-profile-form input[data-profile-field]');
  fields.forEach(function(el) {
    el.disabled = !editing;
    el.style.background = editing ? '#fff' : '#fafafa';
    el.style.borderColor = editing ? '#d9d9d9' : '#f0f0f0';
  });
  var editBtn = document.getElementById('customer-profile-edit-btn');
  var saveBtn = document.getElementById('customer-profile-save-btn');
  var cancelBtn = document.getElementById('customer-profile-cancel-btn');
  if (editBtn) editBtn.style.display = editing ? 'none' : '';
  if (saveBtn) saveBtn.style.display = editing ? '' : 'none';
  if (cancelBtn) cancelBtn.style.display = editing ? '' : 'none';
}

function saveCustomerProfile(clientName) {
  var fields = document.querySelectorAll('#customer-profile-form input[data-profile-field]');
  var payload = { client_name: clientName };
  fields.forEach(function(el) {
    payload[el.getAttribute('data-profile-field')] = el.value || '';
  });
  fetch('/admin/api/customer_management/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '保存失败');
      showToast('保存成功', 'success');
      toggleCustomerProfileEdit(false);
    })
    .catch(function(err) {
      console.error(err);
      showToast(err.message || '保存失败', 'error');
    });
}

/* ---------- 8. 清除催单 ---------- */
function clearCustomerUrge(projectId, clientName) {
  if (!confirm('确认清除该项目的催单标记？')) return;
  fetch('/admin/api/customer_management/clear_urge/' + projectId, { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '操作失败');
      showToast('催单已清除', 'success');
      showCustomerDetail(clientName);
    })
    .catch(function(err) {
      console.error(err);
      showToast(err.message || '操作失败', 'error');
    });
}

/* ---------- 9. 反馈回复 ---------- */
function toggleFeedbackReply(fbId) {
  var box = document.getElementById('feedback-reply-box-' + fbId);
  if (box) {
    box.style.display = box.style.display === 'none' ? '' : 'none';
  }
}

function submitFeedbackReply(fbId, clientName) {
  var text = document.getElementById('feedback-reply-text-' + fbId)?.value || '';
  var status = document.getElementById('feedback-reply-status-' + fbId)?.value || '已处理';
  if (!text.trim()) {
    showToast('请输入回复内容', 'error');
    return;
  }
  fetch('/admin/api/customer_management/feedback/' + fbId + '/reply', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reply: text, status: status })
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '提交失败');
      showToast('回复已提交', 'success');
      showCustomerDetail(clientName);
    })
    .catch(function(err) {
      console.error(err);
      showToast(err.message || '提交失败', 'error');
    });
}

/* ---------- 10. 返回列表 ---------- */
function backToCustomerList() {
  document.getElementById('customer-detail-view').style.display = 'none';
  document.getElementById('customer-list-view').style.display = '';
  loadCustomerList();
}

/* ---------- 11. 新增客户 ---------- */
function openCustomerCreateModal() {
  // 创建 modal
  var existing = document.getElementById('customer-create-modal');
  if (existing) existing.remove();

  var modal = document.createElement('div');
  modal.id = 'customer-create-modal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:10000;';
  modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:28px 32px;width:420px;max-width:90vw;box-shadow:0 8px 32px rgba(0,0,0,0.15);">'
    + '<div style="font-size:16px;font-weight:700;margin-bottom:16px;">➕ 新增客户</div>'
    + '<div style="margin-bottom:12px;">'
    + '<label style="display:block;font-size:12px;color:#666;margin-bottom:4px;">客户名称 <span style="color:#cf1322;">*</span></label>'
    + '<input id="new-customer-name" type="text" style="width:100%;padding:8px 12px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;box-sizing:border-box;" placeholder="公司/单位名称" />'
    + '</div>'
    + '<div style="margin-bottom:12px;">'
    + '<label style="display:block;font-size:12px;color:#666;margin-bottom:4px;">联系人</label>'
    + '<input id="new-customer-contact" type="text" style="width:100%;padding:8px 12px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;box-sizing:border-box;" placeholder="收件人姓名" />'
    + '</div>'
    + '<div style="margin-bottom:12px;">'
    + '<label style="display:block;font-size:12px;color:#666;margin-bottom:4px;">电话</label>'
    + '<input id="new-customer-phone" type="text" style="width:100%;padding:8px 12px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;box-sizing:border-box;" placeholder="联系电话" />'
    + '</div>'
    + '<div style="margin-bottom:16px;">'
    + '<label style="display:block;font-size:12px;color:#666;margin-bottom:4px;">地址</label>'
    + '<input id="new-customer-address" type="text" style="width:100%;padding:8px 12px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;box-sizing:border-box;" placeholder="收件地址" />'
    + '</div>'
    + '<div style="display:flex;justify-content:flex-end;gap:8px;">'
    + '<button class="btn btn-sm" onclick="closeCustomerCreateModal()">取消</button>'
    + '<button class="btn btn-sm" onclick="submitCustomerCreate()" style="background:#1677ff;color:#fff;">创建</button>'
    + '</div>'
    + '</div>';
  document.body.appendChild(modal);
  // 点击蒙层关闭
  modal.addEventListener('click', function(e) {
    if (e.target === modal) closeCustomerCreateModal();
  });
  // 自动聚焦
  setTimeout(function() { document.getElementById('new-customer-name')?.focus(); }, 100);
}

function closeCustomerCreateModal() {
  var modal = document.getElementById('customer-create-modal');
  if (modal) modal.remove();
}

function submitCustomerCreate() {
  var name = (document.getElementById('new-customer-name')?.value || '').trim();
  var contact = (document.getElementById('new-customer-contact')?.value || '').trim();
  var phone = (document.getElementById('new-customer-phone')?.value || '').trim();
  var address = (document.getElementById('new-customer-address')?.value || '').trim();

  if (!name) {
    showToast('客户名称不能为空', 'error');
    return;
  }

  fetch('/admin/api/customer_management/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_name: name,
      recipient_name: contact,
      recipient_phone: phone,
      recipient_address: address
    })
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.success) throw new Error(d.error || '创建失败');
      showToast('客户创建成功', 'success');
      closeCustomerCreateModal();
      loadCustomerList();
    })
    .catch(function(err) {
      console.error(err);
      showToast(err.message || '创建失败', 'error');
    });
}
