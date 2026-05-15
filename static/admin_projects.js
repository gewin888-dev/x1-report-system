const PROJECT_STAGE_OPTIONS = ['商机跟进','已报价','待签约','已签约','进场准备','检测中','报告编制中','待交付','已交付','已完成','暂停','终止'];
const CONTRACT_STATUS_OPTIONS = ['未签','合同审批中','已签未归档','已签已归档','无合同','异常'];
const INSPECTION_STAGE_OPTIONS = ['未安排','已排期','待进场','检测中','检测完成','补测中','检测异常','已结束'];
const REPORT_STATUS_OPTIONS = ['未开始','编制中','审核中','待修改','待出具','已出具','待客户确认','客户已确认','已发送客户'];
const INVOICE_STATUS_OPTIONS = ['未开票','待开票','部分开票','已开票','无需开票'];
const PAYMENT_STATUS_OPTIONS = ['未回款','部分回款','已回款','逾期未回款','无需回款'];
let projectPanelInited = false;
let projectSearchTimer = null;
function fillSelectOptions(elId, options, placeholder=''){ const el=document.getElementById(elId); if(!el) return; const first=placeholder?`<option value="">${placeholder}</option>`:''; el.innerHTML=first+options.map(x=>`<option value="${x}">${x}</option>`).join(''); }
function initProjectFilters(){ fillSelectOptions('project-contract-status', CONTRACT_STATUS_OPTIONS, '全部合同情况'); fillSelectOptions('project-inspection-stage', INSPECTION_STAGE_OPTIONS, '全部检测阶段'); fillSelectOptions('project-report-status', REPORT_STATUS_OPTIONS, '全部报告状态'); fillSelectOptions('project-invoice-status', INVOICE_STATUS_OPTIONS, '全部开票情况'); fillSelectOptions('project-payment-status', PAYMENT_STATUS_OPTIONS, '全部收款情况'); fillSelectOptions('project-contract-status-form', CONTRACT_STATUS_OPTIONS); fillSelectOptions('project-inspection-stage-form', INSPECTION_STAGE_OPTIONS); fillSelectOptions('project-report-status-form', REPORT_STATUS_OPTIONS); fillSelectOptions('project-invoice-status-form', INVOICE_STATUS_OPTIONS); fillSelectOptions('project-payment-status-form', PAYMENT_STATUS_OPTIONS); }
function initProjectPanel(){ if(!projectPanelInited){ initProjectFilters(); loadClientNameDatalist(); projectPanelInited=true; } loadProjectSummary(); loadProjects(1); }
var _clientInfoCache={};
function loadClientNameDatalist(){ fetch('/admin/api/customer_management/list').then(r=>r.json()).then(d=>{ if(!d.success) return; const dl=document.getElementById('client-name-datalist'); if(!dl) return; _clientInfoCache={}; dl.innerHTML=d.items.map(c=>{ _clientInfoCache[c.client_name]={contact_name:c.contact_name||'',contact_phone:c.contact_phone||'',address:c.contact_address||''}; return '<option value="'+escapeHtml(c.client_name)+'">'; }).join(''); }).catch(()=>{}); }
function onClientNameSelect(){ var val=(document.getElementById('project-client-name')||{}).value||''; var info=_clientInfoCache[val]; if(!info) return; var isNew=!document.getElementById('project-id').value; var cn=document.getElementById('project-contact-name'); var cp=document.getElementById('project-contact-phone'); var addr=document.getElementById('project-address'); if(cn&&(isNew||!cn.value)&&info.contact_name) cn.value=info.contact_name; if(cp&&(isNew||!cp.value)&&info.contact_phone) cp.value=info.contact_phone; if(addr&&(isNew||!addr.value)&&info.address) addr.value=info.address; }
function debounceProjectSearch(){ clearTimeout(projectSearchTimer); projectSearchTimer=setTimeout(()=>loadProjects(1),250); }
function formatMoney(v){ const n=Number(v||0); return '¥ ' + n.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2}); }
// escapeHtml defined in admin.html globally

function getProjectTagClass(type, value){
  const v = String(value || '');
  if(['已完成','已签已归档','已回款','已开票','已出具','已发送客户','客户已确认'].includes(v)) return 'green';
  if(['检测中','编制中','待开票','部分回款','待出具','审核中','已签约','已报价','待客户确认'].includes(v)) return 'blue';
  if(['待签约','合同审批中','未开票','未回款','已排期','待进场','待修改'].includes(v)) return 'orange';
  if(['终止','异常','检测异常','逾期未回款','未签'].includes(v)) return 'red';
  return 'default';
}

function renderProjectTag(type, value){
  const cls = getProjectTagClass(type, value);
  const palette = {
    green: 'background:#f6ffed;color:#389e0d;border:1px solid #b7eb8f;',
    blue: 'background:#e6f4ff;color:#0958d9;border:1px solid #91caff;',
    orange: 'background:#fff7e6;color:#d46b08;border:1px solid #ffd591;',
    red: 'background:#fff1f0;color:#cf1322;border:1px solid #ffa39e;',
    default: 'background:#fafafa;color:#666;border:1px solid #d9d9d9;'
  };
  return `<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:12px;white-space:nowrap;${palette[cls]}">${escapeHtml(value || '-')}</span>`;
}

function renderProjectSummary(summary){ const box=document.getElementById('project-summary-cards'); if(!box) return; const ra=Math.round(((summary.contract_total_amount||0)-(summary.paid_total_amount||0))*100)/100; box.innerHTML=`<div class="stat-cards" style="grid-template-columns:repeat(8,minmax(0,1fr));gap:10px;"><div class="stat-card blue"><div class="label">项目总数</div><div class="value">${summary.total_projects||0}</div></div><div class="stat-card orange"><div class="label">检测中</div><div class="value">${summary.inspecting_projects||0}</div></div><div class="stat-card purple"><div class="label">待出报告</div><div class="value">${summary.pending_reports||0}</div></div><div class="stat-card blue"><div class="label">待开票</div><div class="value">${summary.pending_invoices||0}</div></div><div class="stat-card orange"><div class="label">待回款</div><div class="value">${summary.pending_payments||0}</div></div><div class="stat-card green"><div class="label">合同总额</div><div class="value">${formatMoney(summary.contract_total_amount||0)}</div></div><div class="stat-card" style="border-left:4px solid #cf1322;"><div class="label">应收款</div><div class="value" style="color:${ra>0?'#cf1322':'#389e0d'};">${formatMoney(ra)}</div></div><div class="stat-card"><div class="label">已完成</div><div class="value">${summary.completed_projects||0}</div></div></div>`; }
function loadProjectSummary(){ fetch('/admin/api/business_projects/summary').then(r=>r.json()).then(d=>{ if(!d.success) throw new Error(d.error||'加载失败'); renderProjectSummary(d.summary||{}); }).catch(console.error); }
function loadProjects(page=1){ const params=new URLSearchParams(); params.set('page',page); params.set('page_size',20); const m=[['keyword','project-search'],['contract_status','project-contract-status'],['inspection_stage','project-inspection-stage'],['report_status','project-report-status'],['invoice_status','project-invoice-status'],['payment_status','project-payment-status'],['owner','project-owner']]; m.forEach(([k,id])=>{ const v=document.getElementById(id)?.value||''; if(v) params.set(k,v); }); fetch('/admin/api/business_projects?'+params.toString()).then(r=>r.json()).then(d=>{ if(!d.success) throw new Error(d.error||'加载失败'); renderProjectTable(d); }).catch(err=>{ console.error(err); const box=document.getElementById('project-list'); if(box) box.innerHTML='<div class="empty">加载失败</div>'; }); }
function _classifyProject(x){ const ca=parseFloat(x.contract_amount)||0; const pa=parseFloat(x.paid_amount)||0; const ra=ca-pa; const ins=x.inspection_stage||''; const rpt=x.report_status||''; const inv=x.invoice_status||''; const done_ins=(ins==='检测完成'||ins==='已结束'); const done_rpt=(rpt==='已出具'||rpt==='已发送客户'||rpt==='客户已确认'); const done_inv=(inv==='已开票'||inv==='无需开票'); const done_work=done_ins && done_rpt && done_inv; if(done_work && ra<=0) return 'done'; if(done_work && ra>0) return 'receivable'; return 'active'; }
function renderProjectTable(data){ const items=data.items||[]; const box=document.getElementById('project-list'); if(!box) return; if(!items.length){ box.innerHTML='<div class="empty">暂无项目</div>'; renderProjectPagination(0,1,20); return; } const sm=data.summary||{}; const fmtAmt=function(v){v=parseFloat(v)||0;return v?v.toLocaleString('zh-CN',{minimumFractionDigits:0,maximumFractionDigits:2}):'-';}; const groups={'active':[],'receivable':[],'done':[]}; items.forEach(x=>groups[_classifyProject(x)].push(x)); const groupMeta=[['active','🟢 进行中','#e6f7ff',false],['receivable','🟡 待收款','#fff7e6',false],['done','✅ 已完结','#f6ffed',true]]; const renderRow=function(x){const ca=parseFloat(x.contract_amount)||0;const pa=parseFloat(x.paid_amount)||0;const ra=ca-pa;return `<tr><td style="font-family:monospace;font-size:12px;color:#0958d9;">${escapeHtml(x.project_no||'-')}</td><td>${escapeHtml(x.project_name)}${x.has_urge?'<span title="\u5ba2\u6237\u50ac\u5355" style="color:#f5222d;margin-left:4px;">\ud83d\udd14</span>':''}</td><td>${escapeHtml(x.client_name)}</td><td>${renderProjectTag('contract_status',x.contract_status)}</td><td style="text-align:right;font-family:monospace;">${ca?fmtAmt(ca):'-'}</td><td>${renderProjectTag('inspection_stage',x.inspection_stage)}</td><td>${renderProjectTag('report_status',x.report_status)}</td><td>${renderProjectTag('invoice_status',x.invoice_status)}</td><td style="text-align:right;font-family:monospace;color:#389e0d;">${pa?fmtAmt(pa):'-'}</td><td style="text-align:right;font-family:monospace;color:${ra>0?'#cf1322':'#389e0d'};">${ca?fmtAmt(ra):'-'}</td><td>${escapeHtml(x.owner||'-')}</td><td>${escapeHtml((x.updated_at||'').replace('T',' ').slice(0,16)||'-')}</td><td><button class="btn btn-sm" onclick="showProjectModal(${x.id},'view')">查看</button> <button class="btn btn-sm" onclick="showProjectModal(${x.id},'edit')">编辑</button> <button class="btn btn-sm btn-danger" onclick="deleteProject(${x.id})">删除</button></td></tr>`;}; let tbody=''; groupMeta.forEach(([key,label,bg,collapsed])=>{ const arr=groups[key]; if(!arr.length) return; const gid='proj-group-'+key; const arrow=collapsed?'▶':'▼'; tbody+=`<tr class="proj-group-header" style="cursor:pointer;background:${bg};" onclick="toggleProjectGroup('${gid}',this)"><td colspan="13" style="font-weight:600;font-size:13px;padding:8px 12px;border:none;"><span class="proj-group-arrow">${arrow}</span> ${label}（${arr.length}）</td></tr>`; const display=collapsed?'none':''; arr.forEach(x=>{ tbody+=renderRow(x).replace('<tr','<tr class="'+gid+'" style="display:'+display+'"'); }); }); box.innerHTML=`<table><colgroup><col style='width:8%'><col style='width:11%'><col style='width:9%'><col style='width:7%'><col style='width:8%'><col style='width:7%'><col style='width:7%'><col style='width:7%'><col style='width:7%'><col style='width:7%'><col style='width:5%'><col style='width:8%'><col style='width:9%'></colgroup><thead><tr><th>项目编号</th><th>项目名称</th><th>客户/委托单位</th><th>合同情况</th><th>合同金额</th><th>检测阶段</th><th>报告状态</th><th>开票情况</th><th>已收款</th><th>应收款</th><th>负责人</th><th>更新时间</th><th>操作</th></tr></thead><tbody>${tbody}</tbody><tfoot><tr style="background:#f5f5f5;font-weight:600;"><td colspan="4" style="text-align:right;">合计</td><td style="text-align:right;font-family:monospace;">${fmtAmt(sm.contract_amount)}</td><td colspan="3"></td><td style="text-align:right;font-family:monospace;color:#389e0d;">${fmtAmt(sm.paid_amount)}</td><td style="text-align:right;font-family:monospace;color:${(sm.receivable_amount||0)>0?'#cf1322':'#389e0d'};">${fmtAmt(sm.receivable_amount)}</td><td colspan="3"></td></tr></tfoot></table>`; renderProjectPagination(data.total||0, data.page||1, data.page_size||20); }
function toggleProjectGroup(gid,headerEl){ const rows=document.querySelectorAll('tr.'+gid); if(!rows.length) return; const show=rows[0].style.display==='none'; rows.forEach(r=>r.style.display=show?'':'none'); const arrow=headerEl.querySelector('.proj-group-arrow'); if(arrow) arrow.textContent=show?'▼':'▶'; }
function renderProjectPagination(total,page,pageSize){ const box=document.getElementById('project-pagination'); if(!box) return; const totalPages=Math.max(1,Math.ceil(total/pageSize)); box.innerHTML=`<div class="pagination"><span class="page-info">共 ${total} 条 / 第 ${page} / ${totalPages} 页</span><button ${page<=1?'disabled':''} onclick="loadProjects(${page-1})">上一页</button><button ${page>=totalPages?'disabled':''} onclick="loadProjects(${page+1})">下一页</button></div>`; }
function resetProjectForm(){ ['project-id','project-name','project-client-name','project-address','project-contact-name','project-contact-phone','project-detection-domain','project-detection-type','project-expected-date','project-desc','project-contract-status-form','project-contract-amount','project-paid-amount','project-inspection-stage-form','project-report-status-form','project-invoice-status-form','project-payment-status-form','project-owner-form','project-remarks'].forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; }); }
function fillProjectForm(x){ document.getElementById('project-id').value=x.id||''; document.getElementById('project-name').value=x.project_name||''; document.getElementById('project-client-name').value=x.client_name||''; document.getElementById('project-address').value=x.project_address||''; document.getElementById('project-contact-name').value=x.contact_name||''; document.getElementById('project-contact-phone').value=x.contact_phone||''; document.getElementById('project-detection-domain').value=x.detection_domain||''; document.getElementById('project-detection-type').value=x.detection_type||''; document.getElementById('project-expected-date').value=x.expected_detection_date||''; document.getElementById('project-desc').value=x.project_desc||''; document.getElementById('project-contract-status-form').value=x.contract_status||''; document.getElementById('project-contract-amount').value=x.contract_amount||''; var paidEl=document.getElementById('project-paid-amount'); if(paidEl) paidEl.value=x.paid_amount||''; document.getElementById('project-inspection-stage-form').value=x.inspection_stage||''; document.getElementById('project-report-status-form').value=x.report_status||''; document.getElementById('project-invoice-status-form').value=x.invoice_status||''; document.getElementById('project-payment-status-form').value=x.payment_status||''; document.getElementById('project-owner-form').value=x.owner||''; document.getElementById('project-remarks').value=x.remarks||''; }
function setProjectFieldReadonlyStyle(id, readonly){
  const el = document.getElementById(id);
  if(!el) return;
  el.disabled = readonly;
  if(readonly){
    el.style.background = '#fafafa';
    el.style.color = '#444';
    el.style.borderColor = '#f0f0f0';
    el.style.boxShadow = 'none';
  }else{
    el.style.background = '#fff';
    el.style.color = '#222';
    el.style.borderColor = '#d9d9d9';
    el.style.boxShadow = '';
  }
}

function setProjectFormMode(mode){
  const readonly = mode === 'view';
  document.getElementById('project-modal-mode').value = mode;
  ['project-name','project-client-name','project-address','project-contact-name','project-contact-phone','project-detection-domain','project-detection-type','project-expected-date','project-desc','project-contract-amount','project-paid-amount','project-owner-form','project-remarks'].forEach(id=>setProjectFieldReadonlyStyle(id, readonly));
  ['project-contract-status-form','project-inspection-stage-form','project-report-status-form','project-invoice-status-form','project-payment-status-form'].forEach(id=>setProjectFieldReadonlyStyle(id, readonly));
  const saveBtn=document.getElementById('project-save-btn');
  const closeBtn=document.getElementById('project-close-btn');
  const topEditBtn=document.getElementById('project-top-edit-btn');
  const topCloseBtn=document.getElementById('project-top-close-btn');
  const cancelBtn=document.getElementById('project-cancel-btn');
  const assignBtn=document.getElementById('project-assign-btn');
  const reportBtn=document.getElementById('project-report-btn');
  const subtitle=document.getElementById('project-modal-subtitle');
  if(saveBtn){ saveBtn.style.display = readonly ? 'none' : ''; saveBtn.textContent = '保存项目'; }
  if(cancelBtn){ cancelBtn.style.display = readonly ? 'none' : ''; }
  if(closeBtn){ closeBtn.style.display = readonly ? '' : 'none'; closeBtn.textContent = '关闭信息卡'; }
  if(topEditBtn){ topEditBtn.style.display = readonly ? '' : 'none'; topEditBtn.onclick = switchProjectModalToEdit; }
  if(topCloseBtn){ topCloseBtn.style.display = readonly ? '' : 'none'; }
  if(assignBtn){ assignBtn.style.display = readonly ? '' : 'none'; assignBtn.title = '预留：后续用于将当前项目派给检测员'; assignBtn.disabled = true; assignBtn.style.opacity = readonly ? '0.7' : '0'; }
  if(reportBtn){ reportBtn.style.display = readonly ? '' : 'none'; reportBtn.title = '预留：后续用于查看当前项目的关联报告'; reportBtn.disabled = true; reportBtn.style.opacity = readonly ? '0.7' : '0'; }
  if(subtitle) subtitle.textContent = readonly ? '查看项目完整档案；后续检测员派单、客户进度查询与历史报告关联均以此为基础。' : '维护项目基础信息与推进状态，后续检测员派单、客户进度查询与历史报告关联均以此为基础。';
}

function showProjectModal(id=null, mode='edit'){ const modal=document.getElementById('project-modal'); const title=document.getElementById('project-modal-title'); if(!modal) return; resetProjectForm(); if(id){ title.textContent = mode === 'view' ? '项目信息卡' : '编辑项目'; fetch('/admin/api/business_projects/'+id).then(r=>r.json()).then(d=>{ if(!d.success) throw new Error(d.error||'加载项目失败'); fillProjectForm(d.item||{}); setProjectFormMode(mode); modal.classList.add('show'); loadProjectTasks(id); loadProjectReports(id); }).catch(err=>{ console.error(err); alert(err.message||'加载项目失败'); }); } else { title.textContent='新增项目'; setProjectFormMode('edit'); renderTaskListEmpty(); modal.classList.add('show'); } }
function closeProjectModal(){ document.getElementById('project-modal')?.classList.remove('show'); }
function switchProjectModalToEdit(){
  const id = document.getElementById('project-id')?.value || '';
  if(!id) return;
  showProjectModal(id, 'edit');
}
function collectProjectFormData(){ return { project_name:document.getElementById('project-name')?.value||'', client_name:document.getElementById('project-client-name')?.value||'', project_address:document.getElementById('project-address')?.value||'', contact_name:document.getElementById('project-contact-name')?.value||'', contact_phone:document.getElementById('project-contact-phone')?.value||'', detection_domain:document.getElementById('project-detection-domain')?.value||'', detection_type:document.getElementById('project-detection-type')?.value||'', expected_detection_date:document.getElementById('project-expected-date')?.value||'', project_desc:document.getElementById('project-desc')?.value||'', contract_status:document.getElementById('project-contract-status-form')?.value||'', contract_amount:document.getElementById('project-contract-amount')?.value||0, paid_amount:document.getElementById('project-paid-amount')?.value||0, inspection_stage:document.getElementById('project-inspection-stage-form')?.value||'', report_status:document.getElementById('project-report-status-form')?.value||'', invoice_status:document.getElementById('project-invoice-status-form')?.value||'', payment_status:document.getElementById('project-payment-status-form')?.value||'', owner:document.getElementById('project-owner-form')?.value||'', remarks:document.getElementById('project-remarks')?.value||'' }; }
function saveProject(){ const id=document.getElementById('project-id')?.value||''; const payload=collectProjectFormData(); if(!payload.project_name.trim()){ alert('项目名称不能为空'); return; } const isEdit=!!id; fetch(isEdit?('/admin/api/business_projects/'+id):'/admin/api/business_projects',{ method:isEdit?'PUT':'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) }).then(r=>r.json().then(d=>({ok:r.ok,data:d}))).then(({ok,data})=>{ if(!ok||!data.success) throw new Error(data.error||'保存失败'); closeProjectModal(); loadProjectSummary(); loadProjects(1); }).catch(err=>{ console.error(err); alert(err.message||'保存失败'); }); }
function deleteProject(id){ if(!confirm('确认删除该项目吗？')) return; fetch('/admin/api/business_projects/'+id,{method:'DELETE'}).then(r=>r.json().then(d=>({ok:r.ok,data:d}))).then(({ok,data})=>{ if(!ok||!data.success) throw new Error(data.error||'删除失败'); loadProjectSummary(); loadProjects(1); }).catch(err=>{ console.error(err); alert(err.message||'删除失败'); }); }

/* ============================================================
 * 派单链 V1 — 前端任务管理
 * ============================================================ */

const TASK_STATUS_PALETTE = {
  '待指派': 'background:#fafafa;color:#666;border:1px solid #d9d9d9;',
  '已指派': 'background:#e6f4ff;color:#0958d9;border:1px solid #91caff;',
  '已接单': 'background:#e6f4ff;color:#0958d9;border:1px solid #91caff;',
  '执行中': 'background:#fff7e6;color:#d46b08;border:1px solid #ffd591;',
  '已完成': 'background:#f6ffed;color:#389e0d;border:1px solid #b7eb8f;',
  '已取消': 'background:#fff1f0;color:#cf1322;border:1px solid #ffa39e;',
};

function renderTaskStatusTag(label){
  const style = TASK_STATUS_PALETTE[label] || TASK_STATUS_PALETTE['待指派'];
  return `<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:12px;white-space:nowrap;${style}">${escapeHtml(label||'-')}</span>`;
}

function renderTaskListEmpty(){
  const box = document.getElementById('project-task-list');
  if(box) box.innerHTML = '<div style="color:#999;padding:8px 0;">新项目保存后可发起派单</div>';
}

function loadProjectTasks(projectId){
  const box = document.getElementById('project-task-list');
  if(!box) return;
  box.innerHTML = '<div style="color:#999;padding:8px 0;">加载中...</div>';
  fetch('/admin/api/business_projects/' + projectId + '/tasks')
    .then(r => r.json())
    .then(d => {
      if(!d.success) throw new Error(d.error || '加载任务失败');
      renderProjectTaskList(d.items || [], projectId);
    })
    .catch(err => {
      console.error(err);
      box.innerHTML = '<div style="color:#cf1322;padding:8px 0;">加载任务失败</div>';
    });
}

function renderProjectTaskList(items, projectId){
  const box = document.getElementById('project-task-list');
  if(!box) return;
  if(!items.length){
    box.innerHTML = '<div style="color:#999;padding:8px 0;">暂无任务，点击“发起派单”创建第一个检测任务</div>';
    return;
  }
  let html = '';
  items.forEach(t => {
    const canCancel = t.task_status !== 'completed' && t.task_status !== 'cancelled';
    html += `<div style="padding:10px 12px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:8px;background:#fff;">`;
    html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">`;
    html += `<div style="font-weight:600;color:#111827;font-size:13px;">${escapeHtml(t.task_name)}</div>`;
    html += renderTaskStatusTag(t.task_status_label);
    html += `</div>`;
    html += `<div style="display:grid;grid-template-columns:80px 1fr 80px 1fr;gap:4px 8px;font-size:12px;color:#374151;">`;
    html += `<div style="color:#6b7280;">任务类型</div><div>${escapeHtml(t.task_type_label)}</div>`;
    html += `<div style="color:#6b7280;">检测员</div><div>${escapeHtml(t.assigned_to_name || t.assigned_to || '未指派')}</div>`;
    html += `<div style="color:#6b7280;">指派时间</div><div>${escapeHtml((t.assigned_at||'').replace('T',' ').slice(0,16) || '—')}</div>`;
    html += `<div style="color:#6b7280;">预计日期</div><div>${escapeHtml(t.expected_execute_date || '—')}</div>`;
    if(t.started_at){ html += `<div style="color:#6b7280;">开始时间</div><div>${escapeHtml(t.started_at.replace('T',' ').slice(0,16))}</div>`; }
    if(t.completed_at){ html += `<div style="color:#6b7280;">完成时间</div><div>${escapeHtml(t.completed_at.replace('T',' ').slice(0,16))}</div>`; }
    if(t.remarks){ html += `<div style="color:#6b7280;">备注</div><div style="grid-column:span 3;">${escapeHtml(t.remarks)}</div>`; }
    html += `</div>`;
    if(canCancel){
      html += `<div style="margin-top:6px;text-align:right;"><button class="btn btn-sm" style="color:#cf1322;border-color:#ffa39e;" onclick="cancelProjectTask(${t.id}, ${projectId})">取消任务</button></div>`;
    }
    html += `</div>`;
  });
  box.innerHTML = html;
}

function showDispatchDialog(){
  const projectId = document.getElementById('project-id')?.value || '';
  if(!projectId){ alert('请先保存项目'); return; }
  // 加载检测员列表
  const sel = document.getElementById('dispatch-inspector');
  if(sel){
    sel.innerHTML = '<option value="">— 暂不指派，创建待派单任务 —</option>';
    fetch('/admin/api/inspectors').then(r=>r.json()).then(d=>{
      if(d.success && d.items){
        d.items.forEach(u=>{
          const roleLabel = u.role==='inspector' ? '检测员' : '主管';
          sel.innerHTML += `<option value="${u.user_id}">${u.display_name}（${roleLabel}）</option>`;
        });
      }
    }).catch(()=>{});
  }
  // 重置表单
  const typeEl = document.getElementById('dispatch-task-type'); if(typeEl) typeEl.value = 'inspection';
  const dateEl = document.getElementById('dispatch-expected-date'); if(dateEl) dateEl.value = '';
  const rmkEl = document.getElementById('dispatch-remarks'); if(rmkEl) rmkEl.value = '';
  // 显示弹窗
  const modal = document.getElementById('dispatch-modal');
  if(modal) modal.style.display = 'flex';
}

function closeDispatchDialog(){
  const modal = document.getElementById('dispatch-modal');
  if(modal) modal.style.display = 'none';
}

function submitDispatch(){
  const projectId = document.getElementById('project-id')?.value || '';
  if(!projectId){ alert('项目不存在'); return; }
  const assignee = document.getElementById('dispatch-inspector')?.value || '';
  const taskType = document.getElementById('dispatch-task-type')?.value || 'inspection';
  const expectedDate = document.getElementById('dispatch-expected-date')?.value || '';
  const remarks = document.getElementById('dispatch-remarks')?.value || '';
  const payload = {
    project_id: parseInt(projectId),
    task_type: taskType,
  };
  if(assignee) payload.assigned_to = assignee;
  if(expectedDate) payload.expected_execute_date = expectedDate;
  if(remarks.trim()) payload.remarks = remarks.trim();
  fetch('/admin/api/project_tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  })
    .then(r => r.json().then(d => ({ok: r.ok, data: d})))
    .then(({ok, data}) => {
      if(!ok || !data.success) throw new Error(data.error || '创建任务失败');
      closeDispatchDialog();
      loadProjectTasks(projectId);
      loadProjectSummary();
    })
    .catch(err => {
      console.error(err);
      alert(err.message || '创建任务失败');
    });
}

function cancelProjectTask(taskId, projectId){
  if(!confirm('确认取消该任务？')) return;
  const reason = prompt('取消原因（可留空）') || '';
  fetch('/admin/api/project_tasks/' + taskId + '/cancel', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({remarks: reason.trim() || undefined})
  })
    .then(r => r.json().then(d => ({ok: r.ok, data: d})))
    .then(({ok, data}) => {
      if(!ok || !data.success) throw new Error(data.error || '取消失败');
      loadProjectTasks(projectId);
      loadProjectSummary();
    })
    .catch(err => {
      console.error(err);
      alert(err.message || '取消失败');
    });
}

function loadProjectReports(projectId){
  var box = document.getElementById('project-report-list');
  var countEl = document.getElementById('project-report-count');
  if(!box) return;
  box.innerHTML = '<div style="color:#999;">加载中…</div>';
  fetch('/admin/api/business_projects/' + projectId + '/reports')
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(!d.success){ box.innerHTML='<div style="color:#999;">加载失败</div>'; return; }
      var items = d.items || [];
      if(countEl) countEl.textContent = items.length ? ('共 ' + items.length + ' 份') : '';
      if(!items.length){ box.innerHTML='<div style="color:#999;">暂无关联报告</div>'; return; }
      box.innerHTML = items.map(function(r){
        var statusDots = '';
        if(r.has_report_file) statusDots += '<span title="检测报告" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#389e0d;margin-right:4px;"></span>';
        if(r.has_export_file) statusDots += '<span title="原始记录" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#0958d9;margin-right:4px;"></span>';
        return '<div style="padding:8px 10px;border:1px solid #f0f0f0;border-radius:8px;margin-bottom:6px;background:#fafafa;">'
          + '<div style="display:flex;justify-content:space-between;align-items:center;">'
          + '<div>'
          + '<span style="font-family:monospace;color:#0958d9;font-weight:600;">' + escapeHtml(r.report_number || '-') + '</span>'
          + ' <span style="color:#8c8c8c;font-size:11px;">' + escapeHtml(r.detection_type || '') + '</span>'
          + '</div>'
          + '<div style="font-size:11px;color:#8c8c8c;">' + escapeHtml((r.saved_at||'').replace('T',' ').slice(0,16)) + '</div>'
          + '</div>'
          + '<div style="margin-top:4px;display:flex;align-items:center;gap:6px;">'
          + statusDots
          + '<span style="font-size:11px;color:#666;">' + escapeHtml(r.export_id) + '</span>'
          + (r.report_path ? ' <a href="/admin/api/download_file?path=' + encodeURIComponent(r.report_path) + '" target="_blank" style="font-size:11px;color:#0958d9;text-decoration:none;">📄报告</a>' : '')
          + (r.export_path ? ' <a href="/admin/api/download_file?path=' + encodeURIComponent(r.export_path) + '" target="_blank" style="font-size:11px;color:#0958d9;text-decoration:none;">📊原始记录</a>' : '')
          + '</div>'
          + '</div>';
      }).join('');
    })
    .catch(function(err){ console.error(err); box.innerHTML='<div style="color:#f5222d;">加载失败</div>'; });
}
