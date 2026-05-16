// restore.js - 6 functions
// Auto-extracted from record.js

function getRestoreFlow(typeId){
    return RESTORE_FLOW_REGISTRY[typeId] || { mode: 'flat-default' };
}

function buildDraftFingerprint(d){
    const clone = JSON.parse(JSON.stringify(d||{}));
    delete clone.timestamp;
    delete clone.save_time;
    delete clone.report_info;
    delete clone.export_info;
    return JSON.stringify(clone);
}

function saveDraft(){
    const d=collectData();d.status='draft'; d._draft_kind='manual';
    const fingerprint = buildDraftFingerprint(d);
    const isForkFromGenerated = !!window._sourceGeneratedRecordId;
    if(!isOnline){
        saveToLocal(d,'save_draft').then(()=>{_autoSaveDirty=false;_lastDraftFingerprint=fingerprint;window._hasSavedDraftOnce = true;showToast(isForkFromGenerated?'📱 已另存为新草稿，后续继续覆盖此草稿':'📱 已保存到本地','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>showToast('保存失败','error'));
        return;
    }
    doSave(d).then(r=>{if(r.success){_autoSaveDirty=false;_lastDraftFingerprint=fingerprint;if(r.record_id) window._editingRecordId=r.record_id;window._hasSavedDraftOnce = true;showToast(isForkFromGenerated?'已另存为新草稿，后续继续覆盖此草稿':'已暂存','success');setTimeout(()=>showTab('draft'),300);}else showToast('暂存失败','error');}).catch(()=>{
        saveToLocal(d,'save_draft').then(()=>{_autoSaveDirty=false;_lastDraftFingerprint=fingerprint;window._hasSavedDraftOnce = true;showToast(isForkFromGenerated?'📱 网络异常，已另存为新草稿，后续继续覆盖此草稿':'📱 网络异常,已保存到本地','success');updatePendingCount();setTimeout(()=>showTab('draft'),300);}).catch(()=>showToast('保存失败','error'));
    });
}

function getDraftTypeMeta(r){
    const action = r?._queueAction || 'save_draft';
    const status = r?._queueStatus || '';
    const kind = (r?.draft_kind || r?._draftKind || 'manual');
    if(action !== 'save_draft'){
        if(status === 'failed') return {label:'同步失败', color:'#e53935', hint:(r?._queueError || '离线任务同步失败')};
        return {label:'待同步', color:'#ff9800', hint:'等待联网后自动同步'};
    }
    if(kind === 'auto') return {label:'自动保存', color:'#9e9e9e', hint:'7天后自动清理'};
    return {label:'手动暂存', color:'#1976d2', hint:'用户主动暂存'};
}

function isDraftRecord(r){
    const hasReport = !!(r.report_info?.feishu_url || r.report_info?.filename);
    const hasExport = !!(r.export_info?.feishu_url || r.export_info?.filename);
    const hasAnyOutput = hasReport || hasExport;
    const hasStrongVisibleContent = !!(
        (r.project_name && String(r.project_name).trim()) ||
        (r.client_name && String(r.client_name).trim()) ||
        (r.detection_date && String(r.detection_date).trim()) ||
        (r.report_number && String(r.report_number).trim())
    );
    return !hasAnyOutput && hasStrongVisibleContent;
}

function compareDraftPriority(a, b){
    // 失败任务和排队中任务置顶，其余统一按时间倒序（最新在前）
    const score = (r)=>{
        const action = r?._queueAction || 'save_draft';
        const status = r?._queueStatus || '';
        if(action !== 'save_draft' && status === 'failed') return 2;
        if(action !== 'save_draft') return 1;
        return 0;
    };
    const diff = score(b) - score(a);
    if(diff !== 0) return diff;
    return String(b.save_time || b.updated_at || b.created_at || '').localeCompare(String(a.save_time || a.updated_at || a.created_at || ''));
}


// Export all functions
export {
    getRestoreFlow,
    buildDraftFingerprint,
    saveDraft,
    getDraftTypeMeta,
    isDraftRecord,
    compareDraftPriority
};
