/* customer.js — X1 客户中心前端交互 */
(function () {
  'use strict';

  /* ========== 工具函数 ========== */

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showToast(msg, type) {
    var existing = document.querySelector('.x1-toast');
    if (existing) existing.remove();
    var el = document.createElement('div');
    el.className = 'x1-toast';
    el.textContent = msg;
    Object.assign(el.style, {
      position: 'fixed', top: '24px', left: '50%', transform: 'translateX(-50%)',
      padding: '10px 28px', borderRadius: '6px', fontSize: '14px', fontWeight: '500',
      color: '#fff', zIndex: '9999', boxShadow: '0 4px 12px rgba(0,0,0,.15)',
      transition: 'opacity .3s',
      background: type === 'error' ? '#f5222d' : '#52c41a'
    });
    document.body.appendChild(el);
    setTimeout(function () { el.style.opacity = '0'; }, 2600);
    setTimeout(function () { el.remove(); }, 3000);
  }

  /* ========== 进度条 ========== */

  var STEPS = ['待审核', '已排期', '检测中', '报告编制中', '待客户确认', '客户已确认', '已出报告'];

  function getStepIndex(project) {
    // 根据 report_status / inspection_stage 推断当前步骤
    var rs = (project.report_status || '').trim();
    var is_ = (project.inspection_stage || '').trim();

    // 第7步: 已出报告（最终状态，签字盖章版已交付）
    if (rs === '已出报告' || rs === '已出具' || rs === '已发送客户') return 6;
    // 第6步: 客户已确认
    if (rs === '客户已确认') return 5;
    // 第5步: 待客户确认
    if (rs === '待客户确认') return 4;
    // 第4步: 报告编制中
    if (rs === '报告编制中' || rs === '编制中' || rs === '审核中' || rs === '待修改' || rs === '待出具') return 3;
    // 第3步: 检测中
    if (is_ === '检测中' || is_ === '补测中' || is_ === '检测完成') return 2;
    // 第2步: 已派单
    if (is_ === '已派单' || is_ === '已排期' || is_ === '待进场') return 1;
    // 第1步: 待审核
    return 0;
  }

  function renderProgressBar(project) {
    var current = getStepIndex(project);
    var html = '<div class="step-progress">';
    STEPS.forEach(function (label, i) {
      var cls = i < current ? 'done' : (i === current ? 'current' : '');
      html += '<div class="step-item ' + cls + '"><span class="dot">' + (i + 1) + '</span>' + escapeHtml(label) + '</div>';
      if (i < STEPS.length - 1) {
        html += '<div class="step-line' + (i < current ? ' done' : '') + '"></div>';
      }
    });
    html += '</div>';
    return html;
  }

  /* ========== API 通用 ========== */

  // 透传 as_client 参数（admin 预览模式）
  var _asClient = (new URLSearchParams(window.location.search)).get('as_client') || '';

  function api(method, url, body) {
    if (_asClient) {
      var sep = url.indexOf('?') === -1 ? '?' : '&';
      url += sep + 'as_client=' + encodeURIComponent(_asClient);
    }
    var opts = { method: method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
    if (body) opts.body = JSON.stringify(body);
    return fetch(url, opts).then(function (r) {
      if (!r.ok) return r.json().catch(function () { return {}; }).then(function (d) { throw d; });
      return r.json().catch(function () { return {}; });
    });
  }

  /* ========== 初始化 ========== */

  function init() {
    api('GET', '/api/user').then(function (u) {
      var name = u.client_name || u.display_name || u.real_name || u.username || '';
      document.getElementById('customer-welcome').textContent = '欢迎回来，' + name;
      document.getElementById('header-username').textContent = name;
    }).catch(function () {});

    loadProfile();
    bindTabSwitch();
    bindProfileButtons();
    bindModals();
    bindLogout();
    checkFirstVisitGuide();
  }

  /* ========== 新客户引导 ========== */
  function checkFirstVisitGuide() {
    if (localStorage.getItem('x1_customer_guided')) return;
    // 检查是否有项目，没有则显示引导
    api('GET', '/customer/api/projects').then(function (d) {
      var list = d.items || d.list || [];
      if (list.length === 0) showWelcomeGuide();
    }).catch(function () {});
  }

  function showWelcomeGuide() {
    var overlay = document.createElement('div');
    overlay.id = 'welcome-guide-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.innerHTML = '<div style="background:#fff;border-radius:16px;padding:32px 24px;max-width:420px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.3);">' +
      '<div style="font-size:48px;margin-bottom:16px;">👋</div>' +
      '<h2 style="font-size:20px;color:#1a1a2e;margin-bottom:12px;">欢迎使用普迪检测客户服务平台</h2>' +
      '<p style="font-size:14px;color:#64748b;line-height:1.8;margin-bottom:24px;">' +
      '您可以在这里：<br>' +
      '🚀 <b>提交检测项目</b> — 在线下单<br>' +
      '📊 <b>跟踪项目进度</b> — 实时查看状态<br>' +
      '📄 <b>预览/下载报告</b> — 报告出具后即可查看<br>' +
      '🔔 <b>消息通知</b> — 进度更新自动推送</p>' +
      '<button onclick="dismissGuide()" style="padding:12px 32px;background:linear-gradient(135deg,#1677ff,#4096ff);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;">开始使用</button>' +
      '</div>';
    document.body.appendChild(overlay);
  }

  window.dismissGuide = function () {
    localStorage.setItem('x1_customer_guided', '1');
    var el = document.getElementById('welcome-guide-overlay');
    if (el) el.remove();
  };

  /* ========== Tab 切换（补充加载逻辑） ========== */

  var tabLoaded = { 'tab-profile': true };

  function bindTabSwitch() {
    document.querySelectorAll('.tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tabId = btn.getAttribute('data-tab');
        if (tabId === 'tab-profile' && !tabLoaded['tab-profile']) { loadProfile(); tabLoaded['tab-profile'] = true; }
        if (tabId === 'tab-history' && !tabLoaded['tab-history']) { loadHistory(); tabLoaded['tab-history'] = true; }
        if (tabId === 'tab-projects') { loadProjects(); }
        if (tabId === 'tab-feedback') { loadFeedback(); }
        if (tabId === 'tab-notifications' && typeof loadCustNotifications === 'function') { loadCustNotifications(); }
      });
    });
  }

  /* ========== 基础信息 ========== */

  var invoiceFields = ['invoice-company', 'invoice-taxno', 'invoice-addr-phone', 'invoice-bank', 'invoice-bankaccount'];
  var shipFields = ['ship-name', 'ship-phone', 'ship-address'];
  var fieldKeyMap = {
    'invoice-company': 'invoice_company', 'invoice-taxno': 'invoice_tax_no',
    'invoice-addr-phone': 'invoice_address_phone', 'invoice-bank': 'invoice_bank',
    'invoice-bankaccount': 'invoice_bank_account',
    'ship-name': 'recipient_name', 'ship-phone': 'recipient_phone', 'ship-address': 'recipient_address'
  };

  function loadProfile() {
    api('GET', '/customer/api/profile').then(function (d) {
      var pdata = d.data || d || {};
      Object.keys(fieldKeyMap).forEach(function (elId) {
        var el = document.getElementById(elId);
        if (el) el.value = pdata[fieldKeyMap[elId]] || '';
      });
    }).catch(function () {});
  }

  function setFieldsEditable(fields, editable) {
    fields.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.readOnly = !editable;
    });
  }

  function collectFields(fields) {
    var data = {};
    fields.forEach(function (id) {
      data[fieldKeyMap[id]] = (document.getElementById(id) || {}).value || '';
    });
    return data;
  }

  function bindProfileButtons() {
    // 工商开票
    var btnIE = document.getElementById('btn-invoice-edit');
    var btnIS = document.getElementById('btn-invoice-save');
    btnIE && btnIE.addEventListener('click', function () {
      setFieldsEditable(invoiceFields, true);
      btnIE.style.display = 'none';
      btnIS.style.display = '';
    });
    btnIS && btnIS.addEventListener('click', function () {
      var data = collectFields(invoiceFields);
      api('PUT', '/customer/api/profile', data).then(function () {
        setFieldsEditable(invoiceFields, false);
        btnIS.style.display = 'none';
        btnIE.style.display = '';
        showToast('开票信息已保存');
      }).catch(function () { showToast('保存失败，请重试', 'error'); });
    });

    // 收件信息
    var btnSE = document.getElementById('btn-ship-edit');
    var btnSS = document.getElementById('btn-ship-save');
    btnSE && btnSE.addEventListener('click', function () {
      setFieldsEditable(shipFields, true);
      btnSE.style.display = 'none';
      btnSS.style.display = '';
    });
    btnSS && btnSS.addEventListener('click', function () {
      var data = collectFields(shipFields);
      api('PUT', '/customer/api/profile', data).then(function () {
        setFieldsEditable(shipFields, false);
        btnSS.style.display = 'none';
        btnSE.style.display = '';
        showToast('收件信息已保存');
      }).catch(function () { showToast('保存失败，请重试', 'error'); });
    });
  }

  /* ========== 历史记录 ========== */

  function loadHistory() {
    api('GET', '/customer/api/history').then(function (d) {
      var list = d.items || d.list || d.data || [];
      if (!Array.isArray(list)) list = [];
      var tbody = document.getElementById('history-list');
      var empty = document.getElementById('history-empty');
      if (!list.length) {
        tbody.innerHTML = '';
        empty.style.display = '';
        return;
      }
      empty.style.display = 'none';
      tbody.innerHTML = list.map(function (r) {
        var status = r.status || '已完成';
        var statusCls = (status === '已出报告' || status === '已出具' || status === '已完成') ? 'background:#f6ffed;color:#389e0d;'
          : (status === '客户已确认') ? 'background:#f6ffed;color:#52c41a;'
          : 'background:#e6f7ff;color:#1677ff;';
        var previewBtn = '';
        if (r.can_preview_pdf && r.project_id) {
          previewBtn = '<button class="btn btn-preview btn-sm" style="font-size:12px;padding:3px 10px;" onclick="previewReport(' + r.project_id + ')">🔍 查看报告</button>';
        } else if (r.feishu_url) {
          previewBtn = '<a href="' + escapeHtml(r.feishu_url) + '" target="_blank" class="btn btn-primary btn-sm" style="font-size:12px;padding:3px 10px;">预览</a>';
        }
        var downloadBtn = '';
        if (r.feishu_export_url) {
          downloadBtn = '<a href="' + escapeHtml(r.feishu_export_url) + '" target="_blank" class="btn btn-default btn-sm" style="font-size:12px;padding:3px 10px;">下载</a>';
        } else if (r.project_id) {
          downloadBtn = '<button class="btn btn-default btn-sm" style="font-size:12px;padding:3px 10px;" onclick="downloadReport(' + r.project_id + ')">⬇️ 下载</button>';
        }
        return '<tr>'
          + '<td>' + escapeHtml(r.project_name) + '</td>'
          + '<td>' + escapeHtml(r.detection_type || r.detection_object || '') + '</td>'
          + '<td>' + escapeHtml(r.detection_date || r.export_time || '') + '</td>'
          + '<td><span style="display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:500;' + statusCls + '">' + escapeHtml(status) + '</span></td>'
          + '<td style="white-space:nowrap;">' + previewBtn + ' ' + downloadBtn + '</td>'
          + '</tr>';
      }).join('');
    }).catch(function () {});
  }

  /* ========== 检测项目 ========== */

  var _allProjects = [];

  function loadProjects() {
    api('GET', '/customer/api/projects').then(function (d) {
      var list = d.items || d.list || d.data || [];
      if (!Array.isArray(list)) list = [];
      _allProjects = list;
      var container = document.getElementById('customer-projects-list');
      var empty = document.getElementById('projects-empty');
      if (!list.length) {
        container.innerHTML = '';
        empty.style.display = '';
        return;
      }
      empty.style.display = 'none';
      container.innerHTML = list.map(function (p) {
        var rptStatus = (p.report_status || '').trim();
        var inspStage = (p.inspection_stage || '').trim();
        var projectStatusText = '待审核';
        var statusColor = 'background:#fff7e6;color:#fa8c16;';

        if (rptStatus === '已出报告' || rptStatus === '已出具' || rptStatus === '已发送客户') {
          projectStatusText = '已出报告';
          statusColor = 'background:#f6ffed;color:#52c41a;';
        } else if (rptStatus === '客户已确认') {
          projectStatusText = '客户已确认';
          statusColor = 'background:#f6ffed;color:#52c41a;';
        } else if (rptStatus === '待客户确认') {
          projectStatusText = '待客户确认';
          statusColor = 'background:#e6f7ff;color:#1677ff;';
        } else if (rptStatus === '报告编制中' || rptStatus === '编制中' || rptStatus === '审核中' || rptStatus === '待修改' || rptStatus === '待出具') {
          projectStatusText = '报告编制中';
          statusColor = 'background:#e6f7ff;color:#1677ff;';
        } else if (inspStage === '检测中' || inspStage === '补测中' || inspStage === '检测完成') {
          projectStatusText = '检测中';
          statusColor = 'background:#e6f7ff;color:#1677ff;';
        } else if (inspStage === '已派单' || inspStage === '已排期' || inspStage === '待进场') {
          projectStatusText = '已排期';
          statusColor = 'background:#fff7e6;color:#fa8c16;';
        }
        // === 催单按钮（冷却期内灰色） ===
        var coolingReport = p.urge_cooling_report;
        var coolingInvoice = p.urge_cooling_invoice;
        var urgeBtns = '';
        if (coolingReport) {
          urgeBtns += '<button class="btn btn-sm btn-disabled" disabled>📄 催报告（处理中）</button>';
        } else {
          urgeBtns += '<button class="btn btn-primary btn-sm" onclick="urgeProject(' + p.id + ',\'report\')">📄 催报告</button>';
        }
        if (coolingInvoice) {
          urgeBtns += '<button class="btn btn-sm btn-disabled" disabled>🧾 催发票（处理中）</button>';
        } else {
          urgeBtns += ' <button class="btn btn-warn btn-sm" onclick="urgeProject(' + p.id + ',\'invoice\')">🧾 催发票</button>';
        }

        // === 报告操作按钮（状态驱动高亮/灰色） ===
        var canPreview = (rptStatus === '待客户确认' || rptStatus === '客户已确认' || rptStatus === '已出报告' || rptStatus === '已出具' || rptStatus === '已发送客户');
        var canFeedback = (rptStatus === '待客户确认');
        var canConfirm = (rptStatus === '待客户确认');
        var reportBtns = '';
        if (canPreview) {
          reportBtns += '<button class="btn btn-sm btn-preview" onclick="previewReport(' + p.id + ')">🔍 预览</button>';
          reportBtns += '<button class="btn btn-sm" onclick="downloadReport(' + p.id + ')" style="background:#f0f5ff;color:#1677ff;border:1px solid #91caff;">⬇️ 下载</button>';
        } else {
          reportBtns += '<button class="btn btn-sm btn-disabled" disabled>🔍 预览</button>';
          reportBtns += '<button class="btn btn-sm btn-disabled" disabled>⬇️ 下载</button>';
        }
        if (canFeedback) {
          reportBtns += '<button class="btn btn-sm btn-feedback" onclick="openReportFeedback(' + p.id + ')">✍️ 反馈</button>';
        } else {
          reportBtns += '<button class="btn btn-sm btn-disabled" disabled>✍️ 反馈</button>';
        }
        if (canConfirm) {
          reportBtns += '<button class="btn btn-sm btn-confirm" onclick="openConfirmReport(' + p.id + ')">✅ 确认</button>';
        } else {
          reportBtns += '<button class="btn btn-sm btn-disabled" disabled>✅ 确认</button>';
        }
        var projectFeedbackHtml = '';
        if ((p.feedback_count || 0) > 0) {
          var latest = p.latest_feedback || {};
          var latestTitle = latest.title || '已提交反馈';
          var latestDesc = latest.content || '';
          projectFeedbackHtml = '<div style="margin-top:12px;padding:10px 12px;border-radius:10px;background:#f8fbff;border:1px solid #dbeafe;">'
            + '<div style="display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:4px;">'
            + '<span style="font-size:12px;font-weight:700;color:#1d4ed8;">💬 项目反馈 ' + (p.feedback_count || 0) + ' 条</span>'
            + (p.feedback_has_attachments ? '<span style="font-size:11px;color:#0f766e;">含附件</span>' : '')
            + '</div>'
            + '<div style="font-size:12px;color:#334155;font-weight:600;">' + escapeHtml(latestTitle) + '</div>'
            + (latestDesc ? '<div style="font-size:12px;color:#64748b;margin-top:4px;line-height:1.5;">' + escapeHtml(latestDesc).slice(0, 120) + '</div>' : '')
            + '</div>';
        }

        return '<div class="project-card">'
          + '<div class="project-card-header">'
          + '<span class="project-name">' + escapeHtml(p.project_name || '') + '</span>'
          + '<span class="project-status" style="' + statusColor + '">' + escapeHtml(projectStatusText) + '</span>'
          + '</div>'
          + '<div class="project-meta">'
          + '<span>客户：' + escapeHtml(p.client_name || '') + '</span>'
          + '<span>检测类型：' + escapeHtml(p.detection_type || '') + '</span>'
          + (p.expected_detection_date ? '<span>检测日期：' + escapeHtml(p.expected_detection_date) + '</span>' : '')
          + (p.project_address ? '<span>项目地址：' + escapeHtml(p.project_address) + '</span>' : '')
          + (p.contact_name ? '<span>联系人：' + escapeHtml(p.contact_name) + (p.contact_phone ? ' ' + escapeHtml(p.contact_phone) : '') + '</span>' : '')
          + '<span>下单日期：' + escapeHtml((p.created_at || '').slice(0, 10)) + '</span>'
          + '</div>'
          + renderProgressBar(p)
          + projectFeedbackHtml
          + '<div class="project-card-actions">'
          + '<div class="action-group">' + urgeBtns + '</div>'
          + '<div class="action-group">' + reportBtns + '</div>'
          + '</div>'
          + '</div>';
      }).join('');
    }).catch(function () {});
  }

  /* ========== 下单弹窗 ========== */

  function openOrderModal() {
    document.getElementById('order-modal').classList.add('show');
  }
  function closeOrderModal() {
    document.getElementById('order-modal').classList.remove('show');
    // 清空表单
    ['order-project-name', 'order-object-type', 'order-address', 'order-contact', 'order-phone', 'order-date', 'order-remark']
      .forEach(function (id) { var el = document.getElementById(id); if (el) el.value = ''; });
  }
  function submitOrder() {
    var data = {
      project_name: (document.getElementById('order-project-name') || {}).value || '',
      detection_type: (document.getElementById('order-object-type') || {}).value || '',
      project_address: (document.getElementById('order-address') || {}).value || '',
      contact_name: (document.getElementById('order-contact') || {}).value || '',
      contact_phone: (document.getElementById('order-phone') || {}).value || '',
      expected_detection_date: (document.getElementById('order-date') || {}).value || '',
      project_desc: (document.getElementById('order-remark') || {}).value || ''
    };
    if (!data.project_name) { showToast('请填写项目名称', 'error'); return; }
    api('POST', '/customer/api/projects', data).then(function () {
      closeOrderModal();
      loadProjects();
      showToast('订单提交成功');
    }).catch(function () { showToast('提交失败，请重试', 'error'); });
  }

  /* ========== 催单 ========== */

  window.urgeProject = function (projectId, type) {
    api('POST', '/customer/api/projects/' + projectId + '/urge', { type: type })
      .then(function (d) {
        showToast(d.message || '催单已提交', 'success');
        loadProjects();
      })
      .catch(function (e) {
        if (e && e.message && e.message.indexOf('4小时') !== -1) {
          showToast('正在处理您的请求，请4小时后再试', 'info');
        } else {
          showToast('催单失败，请重试', 'error');
        }
        loadProjects(); // 刷新按钮状态
      });
  };

  /* ========== 报告反馈 & 确认 ========== */

  /* --- 预览报告 --- */
  var _currentReportProjectId = null;

  window.downloadReport = function (projectId) {
    var qs = _asClient ? '?as_client=' + encodeURIComponent(_asClient) : '';
    window.open('/customer/api/projects/' + projectId + '/download_report' + qs, '_blank');
  };

  window.previewReport = function (projectId) {
    var qs = _asClient ? '?as_client=' + encodeURIComponent(_asClient) : '';
    // 先用 HEAD 请求检查 PDF 是否存在
    fetch('/customer/api/projects/' + projectId + '/preview_pdf' + qs, { method: 'HEAD', credentials: 'same-origin' })
      .then(function (r) {
        if (r.ok) {
          window.open('/customer/api/projects/' + projectId + '/preview_pdf' + qs, '_blank');
        } else {
          showToast('报告正在生成中，请稍后再试', 'info');
        }
      })
      .catch(function () { showToast('无法连接服务器，请检查网络', 'error'); });
  };

  /* --- 报告反馈弹窗（多条问题） --- */
  var _rfItemCount = 0;

  window.addFeedbackItem = function () {
    _rfItemCount++;
    var n = _rfItemCount;
    var list = document.getElementById('rf-items-list');
    var div = document.createElement('div');
    div.className = 'rf-item';
    div.id = 'rf-item-' + n;
    div.innerHTML = '<div class="rf-item-header">'
      + '<span class="rf-num">' + n + '</span>'
      + '<select data-role="rf-type">'
      + '<option value="数据有误">数据有误</option>'
      + '<option value="格式问题">格式问题</option>'
      + '<option value="信息缺失">信息缺失</option>'
      + '<option value="其他">其他</option>'
      + '</select>'
      + '</div>'
      + '<textarea data-role="rf-desc" rows="2" placeholder="请描述具体问题，如：第X页第X行数据与实际不符"></textarea>'
      + (n > 1 ? '<button type="button" class="rf-item-remove" onclick="removeFeedbackItem(' + n + ')">&times;</button>' : '');
    list.appendChild(div);
  };

  window.removeFeedbackItem = function (n) {
    var el = document.getElementById('rf-item-' + n);
    if (el) el.remove();
    // 重新编号
    var items = document.querySelectorAll('#rf-items-list .rf-item');
    items.forEach(function (item, i) {
      var num = item.querySelector('.rf-num');
      if (num) num.textContent = i + 1;
    });
  };

  window.openReportFeedback = function (projectId) {
    _currentReportProjectId = projectId;
    _rfItemCount = 0;
    document.getElementById('rf-items-list').innerHTML = '';
    document.getElementById('rf-contact').value = '';
    var rfFiles = document.getElementById('rf-attachments');
    if (rfFiles) rfFiles.value = '';
    addFeedbackItem(); // 默认一条
    document.getElementById('report-feedback-modal').classList.add('show');
  };

  window.closeReportFeedbackModal = function () {
    document.getElementById('report-feedback-modal').classList.remove('show');
    _currentReportProjectId = null;
  };

  window.submitReportFeedback = function () {
    var items = document.querySelectorAll('#rf-items-list .rf-item');
    var problems = [];
    var hasEmpty = false;
    items.forEach(function (item, i) {
      var type = (item.querySelector('[data-role="rf-type"]').value || '');
      var desc = (item.querySelector('[data-role="rf-desc"]').value || '').trim();
      if (!desc) { hasEmpty = true; return; }
      problems.push('问题' + (i + 1) + '【' + type + '】' + desc);
    });
    if (hasEmpty || problems.length === 0) {
      showToast('每条问题的描述不能为空', 'error');
      return;
    }
    var contact = (document.getElementById('rf-contact').value || '').trim();
    var fullContent = problems.join('\n') + (contact ? '\n联系方式：' + contact : '');
    var formData = new FormData();
    formData.append('content', fullContent);
    var rfFiles = ((document.getElementById('rf-attachments') || {}).files || []);
    Array.prototype.forEach.call(rfFiles, function (file) {
      formData.append('attachments', file);
    });
    fetch('/customer/api/projects/' + _currentReportProjectId + '/report_feedback', {
      method: 'POST',
      credentials: 'same-origin',
      body: formData
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok || !d.success) throw new Error(d.message || d.error || '提交失败');
        return d;
      });
    }).then(function (d) {
      closeReportFeedbackModal();
      showToast(d.message || '反馈已提交（共' + problems.length + '条），我们将尽快处理', 'success');
      loadProjects();
    }).catch(function (e) { showToast(e.message || '提交失败，请重试', 'error'); });
  };

  /* --- 确认报告弹窗 --- */
  window.openConfirmReport = function (projectId) {
    _currentReportProjectId = projectId;
    document.getElementById('cr-remark').value = '';
    document.getElementById('cr-agree').checked = false;
    document.getElementById('cr-submit-btn').disabled = true;
    document.getElementById('confirm-report-modal').classList.add('show');
  };

  window.closeConfirmReportModal = function () {
    document.getElementById('confirm-report-modal').classList.remove('show');
    _currentReportProjectId = null;
  };

  // 勾选协议后才能提交
  document.addEventListener('DOMContentLoaded', function () {
    var cb = document.getElementById('cr-agree');
    if (cb) {
      cb.addEventListener('change', function () {
        document.getElementById('cr-submit-btn').disabled = !cb.checked;
      });
    }
  });

  window.submitConfirmReport = function () {
    if (!document.getElementById('cr-agree').checked) {
      showToast('请先勾选确认协议', 'error');
      return;
    }
    var remark = (document.getElementById('cr-remark').value || '').trim();
    api('POST', '/customer/api/projects/' + _currentReportProjectId + '/confirm_report', { remark: remark })
      .then(function (d) {
        closeConfirmReportModal();
        showToast(d.message || '报告已确认，将安排打印出具正式报告', 'success');
        loadProjects();
      })
      .catch(function (e) { showToast(e.message || '确认失败，请重试', 'error'); });
  };

  /* ========== 投诉建议 ========== */

  function loadFeedback() {
    api('GET', '/customer/api/feedback').then(function (d) {
      var list = d.items || d.list || d.data || [];
      if (!Array.isArray(list)) list = [];
      var container = document.getElementById('feedback-list');
      var empty = document.getElementById('feedback-empty');
      if (!list.length) {
        container.innerHTML = '';
        empty.style.display = '';
        return;
      }
      empty.style.display = 'none';
      container.innerHTML = list.map(function (f) {
        var typeCls = f.feedback_type === '投诉' ? 'complaint' : (f.feedback_type === '建议' ? 'suggestion' : 'other');
        var typeLabel = f.feedback_type || '其他';
        var statusLabel = f.status || '';
        var projectHtml = f.project_name
          ? '<div style="font-size:12px;color:#1677ff;margin-bottom:4px;">关联项目：' + escapeHtml(f.project_name) + '</div>'
          : '';
        var attachments = Array.isArray(f.attachments) ? f.attachments : [];
        var attachmentHtml = attachments.length
          ? '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">' + attachments.map(function (att) {
              return '<a href="' + escapeHtml(att.download_url || '#') + '" target="_blank" rel="noopener noreferrer" style="font-size:12px;padding:4px 8px;border:1px solid #dbeafe;border-radius:999px;background:#eff6ff;color:#1d4ed8;text-decoration:none;">📎 ' + escapeHtml(att.original_name || '附件') + '</a>';
            }).join('') + '</div>'
          : '';
        var replyHtml = f.reply
          ? '<div style="margin-top:8px;padding:10px 14px;background:#f7f9fc;border-radius:6px;font-size:13px;color:#555;"><b>回复：</b>' + escapeHtml(f.reply) + '</div>'
          : '';
        return '<div class="feedback-item">'
          + '<div class="feedback-item-header">'
          + '<span class="fb-title">' + escapeHtml(f.title || '') + '</span>'
          + '<span class="feedback-type-tag ' + typeCls + '">' + typeLabel + '</span>'
          + '</div>'
          + projectHtml
          + '<div class="feedback-desc">' + escapeHtml(f.content || '') + '</div>'
          + '<div class="feedback-meta">' + escapeHtml(f.created_at || '') + (statusLabel ? ' · <span style="color:' + (statusLabel === '已处理' ? '#52c41a' : '#aaa') + ';">' + escapeHtml(statusLabel) + '</span>' : '') + '</div>'
          + attachmentHtml
          + replyHtml
          + '</div>';
      }).join('');
    }).catch(function () {});
  }

  window.openFeedbackModal = function () {
    var select = document.getElementById('feedback-project');
    if (select) {
      select.innerHTML = '<option value="">请选择项目</option>';
      (_allProjects || []).forEach(function (p) {
        var label = (p.project_no ? (p.project_no + ' · ') : '') + (p.project_name || ('项目#' + p.id));
        select.innerHTML += '<option value="' + p.id + '">' + escapeHtml(label) + '</option>';
      });
    }
    var modal = document.getElementById('feedback-modal');
    if (modal) modal.classList.add('show');
  };
  window.closeFeedbackModal = function () {
    document.getElementById('feedback-modal').classList.remove('show');
    ['feedback-project', 'feedback-type', 'feedback-title', 'feedback-detail', 'feedback-contact']
      .forEach(function (id) { var el = document.getElementById(id); if (el) el.value = ''; });
    var fileEl = document.getElementById('feedback-attachments');
    if (fileEl) fileEl.value = '';
  };
  window.submitFeedback = function () {
    var projectId = ((document.getElementById('feedback-project') || {}).value || '').trim();
    var feedbackType = ((document.getElementById('feedback-type') || {}).value || '').trim();
    var title = ((document.getElementById('feedback-title') || {}).value || '').trim();
    var content = ((document.getElementById('feedback-detail') || {}).value || '').trim();
    var contact = ((document.getElementById('feedback-contact') || {}).value || '').trim();
    if (!projectId || !feedbackType || !title || !content) { showToast('请选择项目，并填写反馈类型、标题和详细描述', 'error'); return; }
    var formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('feedback_type', feedbackType);
    formData.append('title', title);
    formData.append('content', content);
    formData.append('contact', contact);
    var files = ((document.getElementById('feedback-attachments') || {}).files || []);
    Array.prototype.forEach.call(files, function (file) {
      formData.append('attachments', file);
    });
    fetch('/customer/api/feedback', {
      method: 'POST',
      credentials: 'same-origin',
      body: formData
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok || !d.success) throw new Error(d.message || d.error || '提交失败');
        return d;
      });
    }).then(function () {
      closeFeedbackModal();
      loadFeedback();
      loadProjects();
      showToast('反馈提交成功');
    }).catch(function (e) { showToast(e.message || '提交失败，请重试', 'error'); });
  };

  /* ========== 弹窗绑定 ========== */

  function bindModals() {
    // 下单弹窗
    var btnNew = document.getElementById('btn-new-order');
    btnNew && btnNew.addEventListener('click', openOrderModal);
    document.getElementById('order-modal-close').addEventListener('click', closeOrderModal);
    document.getElementById('order-cancel').addEventListener('click', closeOrderModal);
    document.getElementById('order-submit').addEventListener('click', submitOrder);
    // 点遮罩关闭
    document.getElementById('order-modal').addEventListener('click', function (e) {
      if (e.target === this) closeOrderModal();
    });

    // 反馈弹窗
    var btnFb = document.getElementById('btn-new-feedback');
    btnFb && btnFb.addEventListener('click', openFeedbackModal);
    document.getElementById('feedback-modal-close').addEventListener('click', closeFeedbackModal);
    document.getElementById('feedback-cancel').addEventListener('click', closeFeedbackModal);
    document.getElementById('feedback-submit').addEventListener('click', submitFeedback);
    document.getElementById('feedback-modal').addEventListener('click', function (e) {
      if (e.target === this) closeFeedbackModal();
    });
  }

  /* ========== 退出登录 ========== */

  function bindLogout() {
    var btn = document.getElementById('btn-logout');
    btn && btn.addEventListener('click', function () {
      api('POST', '/logout').then(function () {
        window.location.href = '/customer/login';
      }).catch(function () {
        window.location.href = '/customer/login';
      });
    });
  }

  /* ========== 脉冲动画样式注入 ========== */

  (function injectPulse() {
    var style = document.createElement('style');
    style.textContent =
      '@keyframes x1pulse{0%,100%{box-shadow:0 0 0 0 rgba(22,119,255,.35);}50%{box-shadow:0 0 0 6px rgba(22,119,255,0);}}' +
      '.step-item.current .dot{animation:x1pulse 1.8s ease-in-out infinite;}';
    document.head.appendChild(style);
  })();

  /* ========== 启动 ========== */

  document.addEventListener('DOMContentLoaded', function(){
    init();
    if(typeof pollCustNotifCount === 'function'){ pollCustNotifCount(); setInterval(pollCustNotifCount, 60000); }
  });
})();
