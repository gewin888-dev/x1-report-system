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
            if(r.export?.download_url){window.open(r.export.download_url,'_blank');}
            setTimeout(()=>showTab('history'),300);
        }else{
            showToast('导出失败: '+(r.error||'未知错误'),'error');
        }
    }).catch(e=>{
        submitting=false;
        hideExportLoading();
        saveToLocal(d,'submit_and_export').then(()=>{showToast('📱 网络异常,已保存到本地,联网后自动生成记录并导出报告','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>{showToast('保存失败','error');});
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
            if(r.download_url){window.open(r.download_url,'_blank');}
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
