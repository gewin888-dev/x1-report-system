// export.js - 7 functions
// Auto-extracted from record.js

function isGeneratedRecordData(d){
    const hasReport = !!(d?.report_info?.feishu_url || d?.report_info?.filename);
    const hasExport = !!(d?.export_info?.feishu_url || d?.export_info?.filename);
    return hasReport && hasExport;
}

function doSave(data){
    try{
        if(window._sourceGeneratedRecordId){
            data.source_generated_record_id = window._sourceGeneratedRecordId;
        }
        const body=JSON.stringify(data);
        return fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:body}).then(r=>{
            if(!r.ok){return r.json().catch(()=>({success:false,error:'服务器错误('+r.status+')'}));}
            return r.json();
        }).catch(e=>({success:false,error:'请求失败: '+e.message}));
    }catch(e){
        return Promise.resolve({success:false,error:'数据序列化失败: '+e.message});
    }
}

function submitRecord(){
    if(submitting)return;
    const d=validate();if(!d)return;d.status='submitted';
    submitting=true;
    if(!isOnline){
        saveToLocal(d,'submit_only').then(()=>{submitting=false;showToast('📱 已保存到本地,联网后自动上传','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{submitting=false;showToast('保存失败','error');});
        return;
    }
    doSave(d).then(async r=>{submitting=false;if(r.success){_autoSaveDirty=false;window._editCompleted=true;window._lastEditedRecordId=window._editingRecordId;await clearActiveLocalDrafts(window._editingRecordId);showToast('提交成功!','success');setTimeout(()=>document.querySelectorAll('.tab-bar .tab-btn')[1].click(),1000);}else showToast('失败:'+r.error,'error');}).catch(()=>{
        saveToLocal(d,'submit_only').then(()=>{submitting=false;showToast('📱 网络异常,已保存到本地,联网后自动上传','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{submitting=false;showToast('保存失败','error');});
    });
}

function submitAndGenerate(){
    if(submitting)return;
    const d=validate();if(!d)return;d.status='submitted';d.generate_report=true;
    submitting=true;
    if(!isOnline){
        saveToLocal(d,'submit_and_generate').then(()=>{submitting=false;showToast('📱 已保存到本地,联网后自动上传并生成报告','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{submitting=false;showToast('保存失败','error');});
        return;
    }
    showExportLoading('正在生成报告，请稍候...');
    doSave(d).then(async r=>{
        submitting=false;
        hideExportLoading();
        if(r.success){
            let msg='✅ 提交成功';
            if(r.report){msg+=',报告已生成:'+r.report.filename;if(r.report.feishu?.success)msg+='\n📁 已上传飞书';}
            if(r.report_error)msg+='\n⚠️ '+r.report_error;
            await clearActiveLocalDrafts(window._editingRecordId);
            showToast(msg.replace(/\n/g,' | '),'success');
            window._editCompleted=true;window._lastEditedRecordId=window._editingRecordId;
            setTimeout(()=>document.querySelectorAll('.tab-bar .tab-btn')[1].click(),1000);
        }else{
            showToast('导出失败: '+(r.error||'未知错误'),'error');
        }
    }).catch(()=>{
        hideExportLoading();
        saveToLocal(d,'submit_and_generate').then(()=>{submitting=false;showToast('📱 网络异常,已保存到本地,联网后自动上传','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{submitting=false;showToast('保存失败','error');});
    });
}

function submitAndExport(){
    if(submitting)return;
    const d=validate();if(!d)return;d.status='submitted';
    submitting=true;
    if(!isOnline){
        if(window._sourceGeneratedRecordId){
            d.source_generated_record_id = window._sourceGeneratedRecordId;
        }
        saveToLocal(d,'submit_and_export').then(()=>{submitting=false;showToast('📱 已保存到本地,联网后自动生成记录并导出报告','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{submitting=false;showToast('保存失败','error');});
        return;
    }
    showExportLoading('正在生成记录并导出报告，请稍候...');
    if(window._sourceGeneratedRecordId){
        d.source_generated_record_id = window._sourceGeneratedRecordId;
    }
    fetch('/api/submit_and_export',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(d)}).then(r=>r.json()).then(async r=>{
        submitting=false;
        hideExportLoading();
        if(r.success){
            if(r.record_id) window._editingRecordId=r.record_id;
            if(r.final_record_id) window._editingRecordId=r.final_record_id;
            window._sourceGeneratedRecordId='';
            window._isEditingGeneratedRecord=false;
            let msg='✅ 生成成功';
            if(r.export?.feishu?.success) msg+='\n📋 原始记录已上传飞书';
            if(r.report?.feishu?.success) msg+='\n📄 检测报告已上传飞书';
            if(r.report) msg+='\n报告:'+r.report.filename;
            if(r.report_error) msg+='\n⚠️ 报告生成失败:'+r.report_error;
            await clearActiveLocalDrafts(window._editingRecordId);
            showToast(msg.replace(/\n/g,' | '),'success');
            window._editCompleted=true;window._lastEditedRecordId=window._editingRecordId;
            showSubmitVerifyPanel(r);
            setTimeout(()=>showTab('history'),800);
        }else{
            showToast('导出失败: '+(r.error||'未知错误'),'error');
        }
    }).catch(e=>{
        submitting=false;
        hideExportLoading();
        saveToLocal(d,'submit_and_export').then(()=>{showToast('📱 网络异常,已保存到本地,联网后自动生成记录并导出报告','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{showToast('保存失败','error');});
    });
}

function showSubmitVerifyPanel(payload){
    var overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.38);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;z-index:10002;padding:24px';
    var report = payload && payload.report || {};
    var exportInfo = payload && payload.export || {};
    var reportFile = report.filename || '';
    var exportFile = exportInfo.filename || '';
    var reportFeishu = !!(report.feishu && report.feishu.success);
    var exportFeishu = !!(exportInfo.feishu && exportInfo.feishu.success);
    var reportPreview = !!(report.feishu_url || reportFile);
    var exportPreview = !!(exportInfo.feishu_url || exportFile);
    function cardHtml(title, icon, ok, previewOk, fileName, kind){
        var tone = ok ? '#16a34a' : '#ea580c';
        var bg = ok ? '#f0fdf4' : '#fff7ed';
        var status = ok ? '已落入飞书' : (fileName ? '仅本地生成，未确认飞书' : '未生成');
        var previewText = previewOk ? '可核验内容完整性' : '暂无可核验文件';
        return '<div style="border:1px solid #e5e7eb;border-radius:14px;padding:16px;background:#fff;box-shadow:0 4px 14px rgba(15,23,42,.05)">'
            + '<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px">'
            + '<div><div style="font-size:16px;font-weight:700;color:#111827">'+icon+' '+title+'</div><div style="margin-top:6px;display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;background:'+bg+';color:'+tone+';font-size:12px;font-weight:700">'+status+'</div></div>'
            + '<div style="font-size:12px;color:#6b7280">'+previewText+'</div>'
            + '</div>'
            + '<div style="font-size:13px;color:#374151;line-height:1.7">'
            + '<div><span style="color:#6b7280">飞书核验：</span>'+(ok?'✅ 已确认上传成功':'⚠️ 需继续确认')+'</div>'
            + '<div><span style="color:#6b7280">文件内容：</span>'+(fileName?fileName:'未生成本地文件名')+'</div>'
            + '</div>'
            + '<div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap">'
            + (previewOk?'<button data-kind="'+kind+'" class="sv-preview-btn" style="padding:9px 14px;border:none;border-radius:10px;background:#2563eb;color:#fff;font-weight:600;cursor:pointer">核验预览</button>':'')
            + '</div>'
            + '</div>';
    }
    overlay.innerHTML = '<div style="background:#f8fafc;border-radius:18px;width:min(820px,96vw);max-height:90vh;overflow:auto;padding:22px 22px 18px;box-shadow:0 18px 60px rgba(15,23,42,.22)">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:16px">'
        + '<div><div style="font-size:20px;font-weight:800;color:#0f172a">提交结果核验</div><div style="margin-top:6px;font-size:13px;color:#475569">重点确认两件事：<b>是否成功落入飞书</b>、<b>内容是否完整可核验</b>。</div></div>'
        + '<button id="sv-close" style="border:1px solid #d1d5db;background:#fff;border-radius:10px;padding:8px 14px;cursor:pointer;color:#374151">关闭</button>'
        + '</div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">'
        + cardHtml('检测报告','📄',reportFeishu,reportPreview,reportFile,'report')
        + cardHtml('原始记录','📋',exportFeishu,exportPreview,exportFile,'export')
        + '</div>'
        + '<div style="margin-top:16px;padding:12px 14px;border-radius:12px;background:#eff6ff;color:#1e3a8a;font-size:13px;line-height:1.7">'
        + '说明：员工端以飞书落库核验为主；若飞书未确认但本地仍有文件，可先做内容自检，再回头补查上传链路。'
        + '</div>'
        + '</div>';
    document.body.appendChild(overlay);
    function close(){ overlay.remove(); }
    overlay.querySelector('#sv-close').onclick = close;
    overlay.addEventListener('click', function(e){ if(e.target===overlay) close(); });
    overlay.querySelectorAll('.sv-preview-btn').forEach(function(btn){
        btn.onclick = function(){
            var kind = btn.getAttribute('data-kind');
            if(kind === 'report'){
                if(report.feishu_url){ window.open(report.feishu_url, '_blank'); return; }
                if(reportFile){ previewFile(reportFile); return; }
                showToast('暂无可核验的检测报告', 'info');
                return;
            }
            if(exportInfo.feishu_url){ window.open(exportInfo.feishu_url, '_blank'); return; }
            if(exportFile){ previewFile(exportFile); return; }
            showToast('暂无可核验的原始记录', 'info');
        };
    });
}

function exportRecordExcel(){
    if(submitting)return;
    const d=collectData();
    if(!d.rooms||d.rooms.length===0){showToast('请先添加房间信息','error');return;}
    submitting=true;
    showToast('正在保存并导出原始记录...','success');
    d.status='submitted';
    doSave(d).then(saveRes=>{
        if(saveRes.success){
            _autoSaveDirty=false;
            if(saveRes.record_id) d.record_id=saveRes.record_id;
        }
        return fetch('/record/api/export_excel',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(d)}).then(r=>r.json());
    }).then(r=>{
        submitting=false;
        if(r.success){
            showToast('✅ 原始记录已保存并导出','success');
            window._editCompleted=true;window._lastEditedRecordId=window._editingRecordId;
            showSubmitVerifyPanel(r);
            loadHistory();
        }else{showToast('导出失败: '+r.error,'error');}
    }).catch(e=>{submitting=false;showToast('网络错误: '+e.message,'error');});
}

function hideExportLoading(){
    var div = document.getElementById('export-loading-overlay');
    if(div) div.remove();
}


// Export all functions
export {
    isGeneratedRecordData,
    doSave,
    submitRecord,
    submitAndGenerate,
    submitAndExport,
    exportRecordExcel,
    hideExportLoading
};
