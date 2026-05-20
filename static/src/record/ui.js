// ui.js - 70 functions
// Auto-extracted from record.js

// XSS escape helper
function escHtml(str){
    if(!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function handleAdminEntry(event){
    if(event) event.preventDefault();
    if(!currentUserProfile){
        fetch('/api/user').then(r=>r.json()).then(function(d){
            currentUserProfile = d || null;
            handleAdminEntry();
        }).catch(function(){
            showToast('无权限使用后台','error');
        });
        return false;
    }
    const perms = (currentUserProfile && currentUserProfile.permissions) || [];
    const allowed = perms.includes('*') || perms.includes('admin.access');
    if(allowed){
        window.location.href='/admin';
        return false;
    }
    showToast('无权限使用后台','error');
    return false;
}

function getCurrentWeekNumber(){
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 1);
    const diff = Math.floor((now - start) / 86400000);
    return String(Math.ceil((diff + start.getDay() + 1) / 7));
}

function sanitizeReportWeekInput(){
    const weekEl = document.getElementById('reportWeekInput');
    if(!weekEl) return '';
    let raw = String(weekEl.value || '').replace(/\D/g, '');
    if(!raw){
        weekEl.value = '';
        return '';
    }
    let num = parseInt(raw, 10);
    if(Number.isNaN(num)){
        weekEl.value = '';
        return '';
    }
    if(num < 1) num = 1;
    if(num > 53) num = 53;
    weekEl.value = String(num);
    return weekEl.value;
}

function initReportNumberDisplays(){
    const yearEl = document.getElementById('reportYearDisplay');
    const weekEl = document.getElementById('reportWeekInput');
    if(yearEl) yearEl.textContent = new Date().getFullYear();
    if(weekEl && !String(weekEl.value || '').trim()){
        weekEl.value = getCurrentWeekNumber();
    }
    sanitizeReportWeekInput();
}

function updateReportNumber(){
    const year=document.getElementById('reportYearDisplay').textContent||new Date().getFullYear();
    const week=sanitizeReportWeekInput()||'';
    const suffix=(document.getElementById('reportNumberSuffix').value||'').trim();
    document.getElementById('reportNumber').value='PDJC-BG'+year+'-'+week+suffix;
}

function showResetDialog(){
    const overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML=`<div style="background:white;border-radius:12px;padding:24px;max-width:300px;width:85%;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
        <p style="font-size:16px;margin:0 0 20px;color:#333;">当前报告已生成。是否清空录入编辑页，开始新记录？</p>
        <div style="display:flex;gap:12px;">
            <button onclick="this.closest('div[style*=fixed]').remove();window._editingRecordId=window._lastEditedRecordId||'';" style="flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;background:#f5f5f5;font-size:15px;cursor:pointer;">保留当前内容</button>
            <button onclick="this.closest('div[style*=fixed]').remove();resetForm();" style="flex:1;padding:10px;border:none;border-radius:8px;background:#667eea;color:white;font-size:15px;cursor:pointer;">开始新记录</button>
        </div>
    </div>`;
    document.body.appendChild(overlay);
}

function hasMeaningfulEditingContent(){
    const projectName = (document.getElementById('projectName')?.value || '').trim();
    const clientName = (document.getElementById('clientName')?.value || '').trim();
    const detectionDate = (document.getElementById('detectionDate')?.value || '').trim();
    const roomCount = document.querySelectorAll('.room-card').length;
    return !!(projectName || clientName || detectionDate || roomCount > 0);
}

function showReturnToEditDialog(){
    const overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML=`<div style="background:white;border-radius:12px;padding:24px;max-width:360px;width:88%;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
        <p style="font-size:16px;line-height:1.6;margin:0 0 20px;color:#333;">当前录入编辑页仍保留上一条已暂存/已生成的数据。是否清空后开始新记录？</p>
        <div style="display:flex;gap:12px;">
            <button onclick="this.closest('div[style*=fixed]').remove();" style="flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;background:#f5f5f5;font-size:15px;cursor:pointer;">保留当前内容</button>
            <button onclick="this.closest('div[style*=fixed]').remove();resetForm();" style="flex:1;padding:10px;border:none;border-radius:8px;background:#667eea;color:white;font-size:15px;cursor:pointer;">开始新记录</button>
        </div>
    </div>`;
    document.body.appendChild(overlay);
}

function resetForm(){
    // 为新草稿生成新的固定ID
    window._editingRecordId='';
    window._localEditingTaskId='';
    window._sourceGeneratedRecordId='';
    window._isEditingGeneratedRecord=false;
    window._editCompleted=false;
    ensureEditingRecordId();
    _lastDraftFingerprint='';
    // 清空项目信息
    ['projectName','reportNumber','clientName','contactInfo','projectAddress','inspectionArea','detectionDate','weatherTemp','weatherHumidity','weatherPressure'].forEach(id=>{
        const el=document.getElementById(id);if(el)el.value='';
    });
    // 重置报告编号自定义部分
    document.getElementById('reportNumberSuffix').value='';
    initReportNumberDisplays();
    updateReportNumber();
    // 重置检测状态为静态
    document.querySelectorAll('input[name="detectionState"]').forEach(r=>{r.checked=r.value==='静态';});
    // 清空房间
    document.getElementById('roomsContainer').innerHTML='';
    roomCounter=0;
    // 重置领域选择
    document.querySelectorAll('.domain-btn').forEach(b=>b.classList.remove('active'));
    currentDomain=null;
    currentCriteriaIdx=null;
    currentDetectionType=null;
    _autoSaveDirty=false;
    // 更新摘要
    if(typeof updateProjectInfoSummary==='function') updateProjectInfoSummary();
}

function showTab(tab){
    const previousTab = window._currentTab || 'new';
    document.querySelectorAll('.tab-bar .tab-btn').forEach(a=>{
        a.classList.remove('active');
        if(a.getAttribute('onclick')?.includes("'"+tab+"'")) a.classList.add('active');
    });
    ['new','draft','history','mytasks'].forEach(t=>{const el=document.getElementById('tab-'+t);if(el)el.classList.toggle('hidden',t!==tab);});
    if(tab==='draft' || tab==='history') loadHistory();
    if(tab==='mytasks') loadMyTasks('active');
    if((previousTab === 'draft' || previousTab === 'history') && tab === 'new'){
        window._returningFromListTab = true;
    }
    const shouldPromptReturnToNew = (
        tab === 'new' &&
        window._returningFromListTab &&
        !window._suppressReturnToEditPrompt &&
        hasMeaningfulEditingContent() &&
        (window._hasSavedDraftOnce || window._editCompleted)
    );
    window._returningFromListTab = false;
    window._suppressReturnToEditPrompt = false;
    if(tab==='new' && window._editCompleted){
        // 编辑完成后切回新建,提示清空表单
        window._editCompleted = false;
        showResetDialog();
    }else if(shouldPromptReturnToNew){
        showReturnToEditDialog();
    }
    window._currentTab = tab;
    // 编辑/新建页面禁用下拉刷新,只在列表页启用
    pullRefreshDisabled = (tab === 'new');
}

function toggleCard(cardId, bodyId, arrowId, summaryId){
    const body = document.getElementById(bodyId);
    const arrow = document.getElementById(arrowId);
    if(body.style.display === 'none'){
        body.style.display = 'block';
        arrow.textContent = '▲';
    } else {
        body.style.display = 'none';
        arrow.textContent = '▼';
        updateCardSummary(cardId);
    }
}

function updateProjectInfoSummary(){
    const name = document.getElementById('projectName').value;
    const client = document.getElementById('clientName').value;
    const date = document.getElementById('detectionDate').value;
    const summary = document.getElementById('projectInfoSummary');
    const parts = [];
    if(name) parts.push(name);
    if(client) parts.push(client);
    if(date) parts.push(date);
    if(parts.length > 0){
        summary.textContent = `(${parts.join(' · ')})`;
    } else {
        summary.textContent = '';
    }
}

function updateCardSummary(cardId){
    if(cardId === 'basisCard'){
        const checked = document.querySelectorAll('input[name="basis"]:checked');
        const summary = document.getElementById('basisSummary');
        if(checked.length > 0){
            const codes = Array.from(checked).map(cb => cb.value.split(' ')[0]);
            summary.textContent = `(已选${checked.length}个:${codes.join('、')})`;
        } else {
            summary.textContent = '(未选择)';
        }
    } else if(cardId === 'judgementCard'){
        const checked = document.querySelectorAll('input[name="judgement"]:checked');
        const summary = document.getElementById('judgementSummary');
        const activeCode = window.activeJudgementStandard || '';
        if(checked.length > 0){
            summary.textContent = `(已选${checked.length}个,判定依据:${activeCode})`;
        } else {
            summary.textContent = '(未选择)';
        }
    }
}

function initCardCollapse(){
    // 监听checkbox变化,实时更新摘要
    document.addEventListener('change', function(e){
        if(e.target.name === 'basis') updateCardSummary('basisCard');
        if(e.target.name === 'judgement') updateCardSummary('judgementCard');
    });
}

function setActiveJudgement(code, name, event){
    event.preventDefault();
    event.stopPropagation();

    // 更新全局变量
    window.activeJudgementStandard = code;

    // 更新所有按钮状态
    document.querySelectorAll('.set-active-btn').forEach(btn=>{
        btn.classList.remove('active');
        btn.style.background = 'white';
        btn.style.color = '#ff9800';
        btn.textContent = '判定依据';
    });

    // 设置当前按钮为active
    event.target.classList.add('active');
    event.target.style.background = '#ff9800';
    event.target.style.color = 'white';
    event.target.textContent = '⭐ 判定依据';

    // 更新显示
    document.getElementById('activeJudgementInfo').style.display = 'block';
    document.getElementById('activeJudgementName').textContent = `${code} ${name}`;

    // 重新渲染所有房间的参数判定范围
    updateAllRoomsRanges(code);

    // 更新折叠摘要
    updateCardSummary('judgementCard');
}

function isAnimalBarrierContextIncomplete(cardOrRid){
    const card = typeof cardOrRid === 'string' ? document.querySelector(`[data-rid="${cardOrRid}"]`) : cardOrRid;
    if(!card) return false;
    const rid = card.dataset.rid || '';
    const detType = getRoomDetType(rid);
    if(!detType || detType.id !== 'animal_room') return false;
    const cleanClass = card.dataset.cleanClass || card.dataset.levelName || '';
    const barrierRoomClass = card.dataset.barrierRoomClass || '';
    const barrierAuxRoom = card.dataset.barrierAuxRoom || '';
    return (cleanClass === '屏障环境' && !barrierRoomClass) || (barrierRoomClass === '洁净辅房' && !barrierAuxRoom);
}

function moveJudgementPriority(rid, code, domain, dir){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    let priorityList = JSON.parse(card.dataset.judgementPriority || '[]');
    const idx = priorityList.indexOf(code);
    if(idx < 0) return;
    const newIdx = idx + dir;
    if(newIdx < 0 || newIdx >= priorityList.length) return;
    priorityList.splice(idx, 1);
    priorityList.splice(newIdx, 0, code);
    card.dataset.judgementPriority = JSON.stringify(priorityList);
    // 同步checkedList顺序
    let checkedList = JSON.parse(card.dataset.judgementChecked || '[]');
    checkedList = priorityList.filter(c => checkedList.includes(c));
    card.dataset.judgementChecked = JSON.stringify(checkedList);
    if((card.dataset.typeId || '') === 'pass_box'){
        card.dataset.passBoxJudgementSource = 'live';
    }
    renderRoomJudgementList(rid, domain);
    updateRoomRangesByPriority(rid);
}

function syncAnimalContextMarker(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card || (card.dataset.typeId || '') !== 'animal_room') return;
    const incomplete = isAnimalBarrierContextIncomplete(card);
    card.dataset.animalContextIncomplete = incomplete ? 'true' : 'false';
    if(incomplete){
        card.dataset.basisExpanded = 'false';
        card.dataset.judgementExpanded = 'false';
    } else {
        card.dataset.animalContextIncomplete = 'false';
    }
    updateRoomSummary(rid);
}

function syncPressurePairSummaryState(rid, pk='pressure'){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const summaryKey = `pressurePairSummary_${pk}`;
    const carrierKey = `pressurePairCarrier_${pk}`;
    const pb = card.querySelector(`.pb[data-pk="${pk}"]`);
    const summary = card.dataset[summaryKey] || '';
    const rows = pb ? Array.from(pb.querySelectorAll('[data-pressure-pair-row]')) : [];
    const hasLiveInputs = rows.some(row => {
        const refRoom = (row.querySelector(`[data-bsl-ref-room="${pk}"]`)?.value || '').trim();
        const vals = Array.from(row.querySelectorAll(`[data-dp="${pk}"] input`)).map(i => (i.value || '').trim()).filter(Boolean);
        return !!(refRoom || vals.length);
    });
    if((card.dataset.typeId || '') === 'bsl' && pk === 'pressure' && !pb && !summary){
        delete card.dataset[carrierKey];
        delete card.dataset[summaryKey];
        updateRoomSummary(rid);
        return;
    }
    if(!pb){
        delete card.dataset[carrierKey];
        delete card.dataset[summaryKey];
        updateRoomSummary(rid);
        return;
    }
    card.dataset[carrierKey] = 'true';
    if(!summary){
        if(!hasLiveInputs){
            delete card.dataset[summaryKey];
        }
        updateRoomSummary(rid);
        return;
    }
    const hepaResultText = (card.querySelector(`[data-res="hepa_leak"]`)?.textContent || '').trim();
    if((card.dataset.typeId || '') === 'pass_box' && (!hepaResultText || hepaResultText === '-')){
        delete card.dataset.hepaLeakSummary;
        delete card.dataset.hepaLeakSummarySource;
        delete card.dataset.hepaLeakSourceState;
    }
    updateRoomSummary(rid);
}

function syncElectronicsManualState(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card || (card.dataset.typeId || '') !== 'electronics_workshop') return;
    if(!card.querySelector('.pb[data-itype="numeric_range_manual"]') && (card.dataset.electronicsParamsReady || '') !== 'true'){
        card.dataset.electronicsManualRangeKeys = '[]';
        card.dataset.electronicsManualSource = '';
        updateRoomSummary(rid);
        return;
    }
    if((card.dataset.electronicsParamsReady || '') !== 'true' && card.querySelector('.pb[data-itype="numeric_range_manual"]')){
        card.dataset.electronicsParamsReady = 'true';
    }
    const savedKeys = JSON.parse(card.dataset.electronicsManualRangeKeys || '[]');
    const manualBlocks = Array.from(card.querySelectorAll('.pb[data-itype="numeric_range_manual"]'));
    card.dataset.electronicsParamsReady = manualBlocks.length > 0 ? 'true' : 'false';
    if(manualBlocks.length === 0){
        card.dataset.electronicsManualRangeKeys = '[]';
        card.dataset.electronicsManualSource = '';
        updateRoomSummary(rid);
        return;
    }
    const keys = manualBlocks.map(pb => pb.dataset.pk || '').filter(Boolean).filter(pk => {
        const manualRange = card.querySelector(`[data-manual-range="${pk}"]`)?.value || '';
        const manualMin = card.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
        const manualMax = card.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
        return !!(manualRange || manualMin || manualMax);
    });
    card.dataset.electronicsManualRangeKeys = JSON.stringify(keys);
    if(keys.length === 0){
        card.dataset.electronicsManualSource = savedKeys.length > 0 ? 'saved' : '';
        updateRoomSummary(rid);
        return;
    }
    const currentSource = card.dataset.electronicsManualSource || '';
    const hasLiveManualCarrier = keys.some(pk => {
        const manualRange = card.querySelector(`[data-manual-range="${pk}"]`)?.value || '';
        const manualMin = card.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
        const manualMax = card.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
        return !!(manualRange || manualMin || manualMax);
    });
    card.dataset.electronicsManualSource = hasLiveManualCarrier ? (currentSource === 'saved' ? 'saved' : 'live') : (currentSource === 'saved' ? 'saved' : '');
    updateRoomSummary(rid);
}

function isAnimalReadyMissing(card){
    return false;
}

function isCleanFunctionReadyMissing(card){
    return false;
}

function isOperatingReadyMissing(card){
    return false;
}

function hasAnimalReverseAnomaly(card){
    return false;
}

function hasCleanFunctionReverseAnomaly(card){
    return false;
}

function hasOperatingReverseAnomaly(card){
    return false;
}

function isAnimalChainClosed(card){
    return (card.dataset.typeId || '') === 'animal_room'
        && !isAnimalBarrierContextIncomplete(card)
        && ((((card.dataset.cleanClass || '') === '屏障环境') && !!(card.dataset.barrierRoomClass || ''))
            || (!!(card.dataset.cleanClass || '') && (card.dataset.cleanClass || '') !== '屏障环境'));
}

function isCleanFunctionChainClosed(card){
    return (card.dataset.typeId || '') === 'clean_function_room'
        && !!(card.dataset.cleanClass || '')
        && !!(card.dataset.cleanFunctionSubroom || '');
}

function isOperatingChainClosed(card){
    return (card.dataset.typeId || '') === 'operating_room'
        && !!(card.dataset.surgeryRoomType || '')
        && !isOperatingContextIncomplete(card);
}

function isAnimalAcceptanceState(card){
    return (card.dataset.typeId || '') === 'animal_room'
        && !!(card.dataset.cleanClass || '')
        && !isAnimalBarrierContextIncomplete(card);
}

function isCleanFunctionAcceptanceState(card){
    return isCleanFunctionChainClosed(card);
}

function isOperatingAcceptanceState(card){
    return isOperatingChainClosed(card);
}

function isOperatingContextIncomplete(cardOrRid){
    const card = typeof cardOrRid === 'string' ? document.querySelector(`[data-rid="${cardOrRid}"]`) : cardOrRid;
    if(!card) return false;
    if((card.dataset.typeId || '') !== 'operating_room') return false;
    const surgeryRoomType = card.dataset.surgeryRoomType || '';
    const surgeryAuxRoom = card.dataset.surgeryAuxRoom || '';
    const cleanClass = card.dataset.cleanClass || card.dataset.levelName || '';
    if(!surgeryRoomType) return true;
    if(surgeryRoomType === '洁净辅房'){
        return !surgeryAuxRoom || !cleanClass;
    }
    return !cleanClass;
}

function selEquipmentAlias(rid, aliasName){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    showToast(`设备入口“${aliasName}”已改为正式独立检测类型，请直接在“检测类型”中选择`, 'info');
}

function selBSL(rid, bsl){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return;
    // 找到生物安全等级的level-grid(通过父元素label文字定位)
    room.querySelectorAll('.level-grid').forEach(grid => {
        const label = grid.parentElement?.querySelector('label');
        if(label && label.textContent.includes('生物安全等级')){
            grid.querySelectorAll('.level-btn').forEach(b => {
                b.classList.remove('active');
                if(b.textContent.trim() === bsl) b.classList.add('active');
            });
        }
    });
    room.dataset.bsl = bsl;
    updateRoomSummary(rid);
}

function addPressurePair(rid, pk){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const container = room?.querySelector(`[data-bsl-pairs="${pk}"]`);
    if(!container) return;
    const index = container.querySelectorAll('[data-pressure-pair-row]').length + 1;
    container.insertAdjacentHTML('beforeend', renderPressurePairRow(rid, pk, index));
    calc_pressure_pairs(rid, pk);
}

function removePressurePair(btn, rid, pk){
    const row = btn.closest('[data-pressure-pair-row]');
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const container = room?.querySelector(`[data-bsl-pairs="${pk}"]`);
    if(!row || !container) return;
    if(container.querySelectorAll('[data-pressure-pair-row]').length <= 1){
        row.querySelectorAll('input').forEach(i=>i.value='');
        calc_pressure_pairs(rid, pk);
        return;
    }
    row.remove();
    container.querySelectorAll('[data-pressure-pair-row]').forEach((el, idx)=>{
        const label = el.querySelector('span');
        if(label) label.textContent = `相对房间${idx+1}:`;
    });
    calc_pressure_pairs(rid, pk);
}

function addPressureValuePt(btn, rid, pk){
    const dp = btn.closest(`[data-dp="${pk}"]`);
    if(!dp) return;
    const n = dp.querySelectorAll('input').length + 1;
    const inp = document.createElement('input');
    inp.type='number';
    inp.step='any';
    inp.placeholder=String(n);
    inp.oninput=function(){calc_pressure_pairs(rid,pk);};
    btn.before(inp);
}

function switchPressurePairType(rid, pk, btn, ptype){
    const row = btn.closest('[data-pressure-pair-row]');
    if(!row) return;
    row.querySelectorAll('[data-pair-ptype]').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const rangeInput = row.querySelector(`[data-pair-range="${pk}"]`);
    if(rangeInput && !rangeInput.value.trim()){
        const dbRange = getParamRange(rid, pk).range || '';
        rangeInput.value = dbRange || (ptype === 'positive' ? '≥10' : '-10~-15');
    }
    calc_pressure_pairs(rid, pk);
}

function switchPressureType(rid, pk, ptype, btn){
    const container = document.querySelector(`[data-dp-bsl="${pk}"][data-rid="${rid}"]`);
    if(!container) return;
    container.querySelectorAll('.level-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const rangeInput = container.querySelector(`[data-bsl-range="${pk}"]`);
    if(ptype === 'positive'){
        rangeInput.value = '≥10';
    } else {
        rangeInput.value = '-10~-15';
    }
    // 更新参数卡片上的判定范围显示
    updateBSLPressureRange(rid, pk, rangeInput.value);
}

function updateBSLPressureRange(rid, pk, rangeVal){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return;
    const pb = room.querySelector(`[data-pk="${pk}"]`);
    if(!pb) return;
    const rangeEl = pb.querySelector('.pb-range');
    if(rangeEl){
        const spans = rangeEl.querySelectorAll('span');
        for(let i = spans.length - 1; i >= 0; i--){
            const txt = (spans[i].textContent || '').trim();
            if(txt.startsWith('[') && txt.endsWith(']')) continue;
            if(txt.includes('判定范围')) continue;
            spans[i].textContent = rangeVal;
            break;
        }
    }
}

function handleManualRangeChange(rid, pk){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const minVal = room.querySelector(`[data-mr-min="${pk}"]`).value;
    const maxVal = room.querySelector(`[data-mr-max="${pk}"]`).value;
    const combined = (minVal !== '' && maxVal !== '') ? (minVal + '~' + maxVal) : (minVal + maxVal);
    updateManualNumericRange(rid, pk, combined);
}

function updateManualNumericRange(rid, pk, rangeVal){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return;
    const pb = room.querySelector(`[data-pk="${pk}"]`);
    if(!pb) return;
    const rangeValueEl = pb.querySelector('.pb-range .pb-range-value');
    if(rangeValueEl) rangeValueEl.textContent = rangeVal || '';
    if((room.dataset.typeId || '') === 'animal_room' && pk === 'animal_illumination'){
        const manualMin = pb.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
        const manualMax = pb.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
        const hasLiveManual = !!(manualMin || manualMax);
        const currentSource = room.dataset.animalIlluminationSource || '';
        room.dataset.animalIlluminationSource = hasLiveManual ? 'live' : (currentSource === 'saved' ? 'saved' : '');
    }
    calc_numeric(rid, pk);
    if((room.dataset.typeId || '') === 'electronics_workshop') syncElectronicsManualState(rid);
    updateRoomSummary(rid);
}

function addPt(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const dp=room.querySelector(`[data-dp="${pk}"]`);
    const btn=dp.querySelector('.add-pt');
    const n=dp.querySelectorAll('input').length+1;
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    const allowNegative = ['temperature','humidity'].includes(pk) || ['temperature','humidity'].includes(pb?.dataset.pk || '');
    const inp=document.createElement('input');
    inp.type='number'; inp.step='any'; if(!allowNegative) inp.min='0'; inp.placeholder=n;
    inp.oninput=function(){calc_numeric(rid,pk);};
    btn.before(inp);
}

function addVent(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const vents=room.querySelector(`[data-ac-vents="${pk}"]`);
    vents.insertAdjacentHTML('beforeend',`<div class="vent-grid" data-vent-row>
        <div class="vent-item"><label>面积(m2)</label><input type="number" step="any" data-va oninput="calc_airchange('${rid}','${pk}')"></div>
        <div class="vent-item"><label>风速(m/s)</label><input type="number" step="any" data-vs oninput="calc_airchange('${rid}','${pk}')"></div>
        <div class="vent-item"><label>风量(m3/h)</label><input type="number" step="any" data-vq readonly style="background:#f0f0f0;"></div>
    </div>`);
}

function addVolPt(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const dp=room.querySelector(`[data-dp-vol="${pk}"]`);
    const btn=dp.querySelector('.add-pt');
    const n=dp.querySelectorAll('input').length+1;
    const inp=document.createElement('input');
    inp.type='number'; inp.step='any'; inp.placeholder='风口'+n;
    inp.oninput=function(){calc_airchange_vol(rid,pk);};
    btn.before(inp);
}

function switchMethod(rid,pk,method,el){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    el.parentElement.querySelectorAll('.method-btn').forEach(b=>b.classList.remove('active'));
    el.classList.add('active');
    room.querySelector(`[data-ac-speed="${pk}"]`).classList.toggle('hidden',method!=='speed');
    room.querySelector(`[data-ac-volume="${pk}"]`).classList.toggle('hidden',method!=='volume');
    room.querySelector(`[data-pk="${pk}"]`).dataset.acMethod=method;
}

function getDisplayRangeText(pb){
    if(!pb) return '';
    const rangeEl = pb.querySelector('.pb-range');
    if(!rangeEl) return '';
    const spans = rangeEl.querySelectorAll('span');
    for(let i = spans.length - 1; i >= 0; i--){
        const txt = (spans[i].textContent || '').trim();
        if(!txt) continue;
        if(txt.startsWith('[') && txt.endsWith(']')) continue;
        if(txt.includes('判定范围')) continue;
        return txt;
    }
    return '';
}

function judgeRange(val,range){
    if(!range||range==='/')return true;
    // 支持全角和半角波浪号
    if(range.includes('~')||range.includes('～')){
        const parts=range.replace(/[^\d.~～\-]/g,'').split(/[~～]/);
        const a=parseFloat(parts[0]),b=parseFloat(parts[1]);
        const min=Math.min(a,b),max=Math.max(a,b);
        return val>=min&&val<=max;
    }
    if(range.includes('≥')){return val>=parseFloat(range.replace(/[^0-9.\-]/g,''));}
    if(range.includes('≤')){return val<=parseFloat(range.replace(/[^0-9.\-]/g,''));}
    return true;
}

function validate(){
    const d=collectData();

    // 基本信息校验
    if(!d.project_name){showToast('请填写项目名称','error');return null;}
    if(!d.client_name){showToast('请填写委托单位','error');return null;}
    if(!d.detection_date){showToast('请选择检测日期','error');return null;}
    if(!d.domain){showToast('请选择检测领域','error');return null;}
    if(!d.detection_type){showToast('请在房间中选择检测类型','error');return null;}

    // 检测依据和判定标准校验
    if(!d.basis || d.basis.length === 0){showToast('请至少选择一个检测依据','error');return null;}
    if(!d.judgement || d.judgement.length === 0){showToast('请至少选择一个判定标准','error');return null;}

    // 房间校验
    if(d.rooms.length===0){showToast('请至少添加一个房间','error');return null;}

    for(let i = 0; i < d.rooms.length; i++){
        const r = d.rooms[i];
        const roomLabel = r.name || `房间${i+1}`;
        const animalContextByData = r.type_id === 'animal_room' && ((r.level_name === '屏障环境' && !r.barrier_room_class) || (r.barrier_room_class === '洁净辅房' && !r.barrier_aux_room));
        const card = document.querySelector(`[data-rid="${r.id}"]`);
        if(r.type_id === 'animal_room' && Boolean(r.animal_context_incomplete) !== Boolean(animalContextByData)){
            showToast(`${roomLabel}:动物房上下文状态与保存标记不一致,请重新确认屏障环境选择链`,'error');
            return null;
        }
        if((r.hepa_leak_summary || '') && !(r.params?.hepa_leak?.result || '')){
            showToast(`${roomLabel}:检漏摘要存在,但检漏结果已为空,请先清场后再保存`,'error');
            return null;
        }
        if((r.type_id === 'animal_room') && (r.animal_illumination_source || '') === 'live' && !((r.params?.animal_illumination?.manualMin || '') || (r.params?.animal_illumination?.manualMax || ''))){
            showToast(`${roomLabel}:动物照度实时来源态存在,但当前无手动范围,请先清场后再保存`,'error');
            return null;
        }
        if((r.type_id === 'animal_room') && (r.animal_illumination_source || '') && !((r.params?.animal_illumination?.manualMin || '') || (r.params?.animal_illumination?.manualMax || '') || (r.animal_illumination_source === 'saved'))){
            showToast(`${roomLabel}:动物照度来源态存在,但当前无手动范围且非回填态,请先清场后再保存`,'error');
            return null;
        }
        if(r.type_id === 'pass_box' && !(Array.isArray(r.pass_box_judgement_active) && r.pass_box_judgement_active.length > 0) && (r.pass_box_result_state || '')){
            showToast(`${roomLabel}:传递窗结果已存在,但判定链为空,请重新确认`,'error');
            return null;
        }
        if(r.type_id === 'pass_box' && !(r.pass_box_result_state || '') && Array.isArray(r.pass_box_judgement_active) && r.pass_box_judgement_active.length > 0){
            showToast(`${roomLabel}:传递窗判定链已存在,但结果态为空,请重新确认`,'error');
            return null;
        }
        if(!(r.pressure_pair_summary || '')){
            if(card){
                delete card.dataset.legacyPressurePairSummarySource_pressure;
                delete card.dataset.pressurePairCarrier_pressure;
            }
        }
        if(r.type_id === 'pass_box' && (r.business_domain_hint || '') !== 'pharma'){
            showToast(`${roomLabel}:传递窗业务归属必须固定为制药领域`,'error');
            return null;
        }
        if(r.type_id === 'laminar_hood' && (r.business_domain_hint || '') !== 'pharma'){
            showToast(`${roomLabel}:层流罩业务归属必须固定为制药领域`,'error');
            return null;
        }
        if(r.type_id === 'pass_box' && Array.isArray(r.pass_box_judgement_active) && Array.isArray(r.judgement_active)){
            const a = JSON.stringify(r.pass_box_judgement_active);
            const b = JSON.stringify(r.judgement_active);
            if(a !== b){
                showToast(`${roomLabel}:传递窗专属判定链与当前有效判定链不一致`,'error');
                return null;
            }
        }
        if(r.type_id === 'laminar_hood' && ((r.pass_box_result_state || '') || (Array.isArray(r.pass_box_judgement_active) && r.pass_box_judgement_active.length > 0))){
            showToast(`${roomLabel}:层流罩不得保留传递窗专属结果/判定链残留`,'error');
            return null;
        }
        if(r.type_id === 'laminar_hood' && ((r.business_domain_hint || '') !== 'pharma')){
            showToast(`${roomLabel}:层流罩业务归属必须固定为制药领域`,'error');
            return null;
        }
        if(r.type_id === 'laminar_hood' && !Array.isArray(r.basis)){
            showToast(`${roomLabel}:层流罩检测依据数据结构异常`,'error');
            return null;
        }
        if(r.type_id === 'laminar_hood' && !Array.isArray(r.judgement)){
            showToast(`${roomLabel}:层流罩判定标准数据结构异常`,'error');
            return null;
        }
        if(r.type_id === 'laminar_hood'){
            const card = document.querySelector(`[data-rid="${r.id}"]`);
            if(card && (card.dataset.businessDomainHint || '') !== 'pharma'){
                showToast(`${roomLabel}:层流罩当前页面业务归属状态未正确恢复到制药领域`,'error');
                return null;
            }
        }
        if(r.type_id === 'pass_box'){
            const passBoxCard = document.querySelector(`[data-rid="${r.id}"]`);
            const livePbCount = passBoxCard?.querySelectorAll('.pb').length || 0;
            const liveHasParams = livePbCount > 0;
            const fallbackPbCount = passBoxCard ? Array.from(passBoxCard.querySelectorAll('[data-pk]')).filter(el => {
                const pk = el.dataset.pk || '';
                return pk && pk !== 'basis' && pk !== 'judgement';
            }).length : 0;
            const effectiveHasParams = liveHasParams || fallbackPbCount > 0 || Object.keys(r.params || {}).length > 0;
            const liveResultState = liveHasParams ? getPassBoxResultState(passBoxCard) : (r.pass_box_result_state || '');
            const liveJudgementActive = liveHasParams ? JSON.parse(passBoxCard?.dataset.passBoxJudgementActive || '[]') : (Array.isArray(r.pass_box_judgement_active) ? r.pass_box_judgement_active : []);
            if(!effectiveHasParams && ((r.pass_box_result_state || '') || (Array.isArray(r.pass_box_judgement_active) && r.pass_box_judgement_active.length > 0))){
                showToast(`${roomLabel}:传递窗参数区未建立时不得保留结果/判定链状态`,'error');
                return null;
            }
            if((r.pass_box_result_state || '') && liveResultState && (r.pass_box_result_state || '') !== liveResultState){
                showToast(`${roomLabel}:传递窗结果状态与当前结果块不一致`,'error');
                return null;
            }
            if(Array.isArray(r.pass_box_judgement_active) && r.pass_box_judgement_active.length > 0 && liveJudgementActive.length > 0){
                if(JSON.stringify((r.pass_box_judgement_active || []).slice()) !== JSON.stringify(liveJudgementActive.slice())){
                    showToast(`${roomLabel}:传递窗专属判定链与当前页面判定链不一致`,'error');
                    return null;
                }
            }
        }
        if(r.type_id === 'electronics_workshop'){
            const card = document.querySelector(`[data-rid="${r.id}"]`);
            const manualBlocks = Array.from(card?.querySelectorAll('.pb[data-itype="numeric_range_manual"]') || []);
            const liveManualKeys = manualBlocks.map(pb => pb.dataset.pk || '').filter(Boolean).filter(pk => {
                const manualRange = card?.querySelector(`[data-manual-range="${pk}"]`)?.value || '';
                const manualMin = card?.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
                const manualMax = card?.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
                return !!(manualRange || manualMin || manualMax);
            });
            if(Array.isArray(r.electronics_manual_range_keys) && r.electronics_manual_range_keys.length > 0){
                for(const pk of r.electronics_manual_range_keys){
                    const manualRange = card?.querySelector(`[data-manual-range="${pk}"]`)?.value || '';
                    const manualMin = card?.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
                    const manualMax = card?.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
                    if(!(manualRange || manualMin || manualMax)){
                        showToast(`${roomLabel}:${pk} 已标记为手动优先,但当前页面未保留手动范围`,'error');
                        return null;
                    }
                }
            }
            if(Array.isArray(r.electronics_manual_range_keys) && r.electronics_manual_range_keys.length > 0 && liveManualKeys.length > 0){
                if(JSON.stringify((r.electronics_manual_range_keys || []).slice().sort()) !== JSON.stringify(liveManualKeys.slice().sort())){
                    showToast(`${roomLabel}:电子行业手动键集合与当前页面不一致`,'error');
                    return null;
                }
            }
        }

        if(r.type_id === 'animal_room'){
            if(Boolean(r.animal_context_incomplete) && Boolean(r.basis_expanded || false)){
                showToast(`${roomLabel}:动物房上下文未完成,检测依据面板不得保持展开态`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && Boolean(r.judgement_expanded || false)){
                showToast(`${roomLabel}:动物房上下文未完成,判定标准面板不得保持展开态`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && (r.hepa_leak_summary || '')){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留检漏摘要`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && (r.pressure_pair_summary || '')){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留压差摘要`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && (r.pass_box_result_state || '')){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留结果状态残留`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && Array.isArray(r.electronics_manual_range_keys) && r.electronics_manual_range_keys.length > 0){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留手动优先键残留`,'error');
                return null;
            }
        }

        if(r.type_id === 'animal_room'){
            const liveAnimalIncomplete = card ? isAnimalBarrierContextIncomplete(card) : false;
            if(Boolean(r.animal_context_incomplete) !== Boolean(liveAnimalIncomplete)){
                showToast(`${roomLabel}:动物房上下文保存标记与当前页面状态不一致`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && Object.keys(r.params||{}).length > 0 && !(r.barrier_room_class || '')){
                showToast(`${roomLabel}:动物房上下文未完成且尚未选定房间类别,不得保留参数链`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && (r.barrier_room_class || '') === '洁净辅房' && !(r.barrier_aux_room || '') && Object.keys(r.params||{}).length > 0){
                showToast(`${roomLabel}:动物房洁净辅房上下文未完成,不得保留参数链`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && Boolean(r.basis_expanded || false)){
                showToast(`${roomLabel}:动物房上下文未完成,检测依据面板不得保持展开态`,'error');
                return null;
            }
            if(Boolean(r.animal_context_incomplete) && Boolean(r.judgement_expanded || false)){
                showToast(`${roomLabel}:动物房上下文未完成,判定标准面板不得保持展开态`,'error');
                return null;
            }
            if((r.clean_class || '') === '屏障环境' && !(r.barrier_room_class || '') && ((card?.dataset.barrierRoomClass || '') || (card?.dataset.barrierAuxRoom || ''))){
                showToast(`${roomLabel}:动物房屏障环境节点未定,但房间数据集仍残留屏障子节点`,'error');
                return null;
            }
            if((r.clean_class || '') === '屏障环境' && (r.barrier_room_class || '') !== '洁净辅房' && (card?.dataset.barrierAuxRoom || '')){
                showToast(`${roomLabel}:动物房当前不是洁净辅房,但房间数据集仍残留洁净辅房名称`,'error');
                return null;
            }
            if((r.type_id === 'animal_room') && Boolean(r.animal_context_incomplete) && (r.hepa_leak_summary || '')){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留高效过滤器检漏摘要`,'error');
                return null;
            }
            if((r.type_id === 'animal_room') && Boolean(r.animal_context_incomplete) && (r.pressure_pair_summary || '')){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留压差摘要`,'error');
                return null;
            }
            if((r.type_id === 'animal_room') && Boolean(r.animal_context_incomplete) && (r.pass_box_result_state || '')){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留结果状态残留`,'error');
                return null;
            }
            if((r.type_id === 'animal_room') && Boolean(r.animal_context_incomplete) && Array.isArray(r.electronics_manual_range_keys) && r.electronics_manual_range_keys.length > 0){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留手动优先键残留`,'error');
                return null;
            }
            if((r.type_id === 'animal_room') && Boolean(r.animal_context_incomplete) && Array.isArray(r.pass_box_judgement_active) && r.pass_box_judgement_active.length > 0){
                showToast(`${roomLabel}:动物房上下文未完成,不得保留传递窗激活判定链残留`,'error');
                return null;
            }
        }

        // 房间基本信息
        if(!r.name){showToast(`${roomLabel}:请填写房间名称`,'error');return null;}
        if(r.type_id === 'bsl' && !r.bsl){showToast(`${roomLabel}:请选择生物安全等级`,'error');return null;}
        if(!r.level_name){
            if(r.type_id === 'pass_box' || r.type_id === 'laminar_hood'){
                const levelOptions = (() => {
                    const card = document.querySelector(`[data-rid="${r.id}"]`);
                    return Array.from(card?.querySelectorAll('.room-clean-options .level-btn') || []).map(btn => (btn.textContent || '').trim()).filter(Boolean);
                })();
                if(levelOptions.length === 1){
                    r.level_name = levelOptions[0];
                    r.clean_class = r.clean_class || levelOptions[0];
                    if(card){
                        card.dataset.levelName = levelOptions[0];
                        card.dataset.cleanClass = card.dataset.cleanClass || levelOptions[0];
                    }
                }
            }
            // bsc/clean_bench/ivc 无洁净等级概念，自动填默认值
            if(['bsc','clean_bench','ivc'].includes(r.type_id)){
                r.level_name = r.level_name || '无等级要求';
                r.clean_class = r.clean_class || '无等级要求';
            }
        }
        if(!r.level_name && !['bsc','clean_bench','ivc'].includes(r.type_id)){showToast(`${roomLabel}:请选择${r.type_id==='animal_room'?'环境选择':'洁净等级'}`,'error');return null;}
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && !r.barrier_room_class){showToast(`${roomLabel}:屏障环境必须选择房间类别`,'error');return null;}
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && r.barrier_room_class === '洁净辅房' && !r.barrier_aux_room){showToast(`${roomLabel}:洁净辅房必须选择辅房名称`,'error');return null;}

        // 房间尺寸(如果有参数需要计算换气次数,则必填)
        const hasAirchange = Object.keys(r.params).some(k => r.params[k].type && r.params[k].type.includes('airchange'));
        if(hasAirchange){
            if(!r.length || !r.width || !r.height){
                showToast(`${roomLabel}:需要计算换气次数,请填写房间尺寸(长×宽×高)`,'error');
                return null;
            }
            // 尺寸合理性检查
            const l = parseFloat(r.length), w = parseFloat(r.width), h = parseFloat(r.height);
            if(isNaN(l) || isNaN(w) || isNaN(h) || l <= 0 || w <= 0 || h <= 0){
                showToast(`${roomLabel}:房间尺寸必须为正数`,'error');
                return null;
            }
            if(l > 100 || w > 100 || h > 10){
                showToast(`${roomLabel}:房间尺寸异常(长/宽>100m 或 高>10m),请检查`,'warning');
            }
        }

        // animal_room: 业务上下文未闭合时,不允许带着已录参数进入正式保存
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && !r.barrier_room_class && Object.keys(r.params||{}).length > 0){
            showToast(`${roomLabel}:屏障环境房间类别未完成,不能保留已录参数`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && !r.barrier_room_class && ((r.basis||[]).length > 0 || (r.judgement||[]).length > 0)){
            showToast(`${roomLabel}:屏障环境房间类别未完成,不能保留检测依据或判定标准链`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && r.barrier_room_class === '洁净辅房' && !r.barrier_aux_room && Object.keys(r.params||{}).length > 0){
            showToast(`${roomLabel}:洁净辅房名称未完成,不能保留已录参数`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && r.barrier_room_class === '洁净辅房' && !r.barrier_aux_room && ((r.basis||[]).length > 0 || (r.judgement||[]).length > 0)){
            showToast(`${roomLabel}:洁净辅房名称未完成,不能保留检测依据或判定标准链`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && !(r.clean_function_subroom || '')){
            showToast(`${roomLabel}:洁净功能用房子房间未选择`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && (r.clean_function_subroom || '') && !(r.clean_class || '')){
            showToast(`${roomLabel}:洁净功能用房洁净等级未选择`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && (r.clean_function_subroom || '') && ((r.basis||[]).length > 0 || (r.judgement||[]).length > 0) && !(r.clean_class || '')){
            showToast(`${roomLabel}:洁净功能用房洁净等级未完成,不得保留依据或判定链`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && !(r.clean_function_subroom || '') && (Object.keys(r.params||{}).length > 0 || (r.basis||[]).length > 0 || (r.judgement||[]).length > 0 || (r.active_judgement||[]).length > 0)){
            showToast(`${roomLabel}:洁净功能用房子房间未完成,不得保留参数/依据/判定链`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && (r.clean_function_subroom || '') && !(r.clean_class || '') && ((r.active_judgement||[]).length > 0 || Object.keys(r.params||{}).length > 0)){
            showToast(`${roomLabel}:洁净功能用房洁净等级未完成,不得保留激活判定或参数链`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && (r.clean_function_subroom || '') && !(r.clean_class || '') && (Boolean(r.basis_expanded) || Boolean(r.judgement_expanded))){
            showToast(`${roomLabel}:洁净功能用房洁净等级未完成,不得保留展开态`,'error');
            return null;
        }
        if(r.type_id === 'clean_function_room' && (r.clean_function_subroom || '') && !(r.clean_class || '') && ((r.basis||[]).length > 0 || (r.judgement_checked||[]).length > 0 || (r.judgement_active||[]).length > 0 || (r.active_judgement||[]).length > 0)){
            showToast(`${roomLabel}:洁净功能用房回填后仍残留依据/判定链,需先完成洁净等级`,'error');
            return null;
        }
        if(r.type_id === 'operating_room' && !(r.surgery_room_type || '')){
            showToast(`${roomLabel}:手术室房间类型未选择`,'error');
            return null;
        }
        if(r.type_id === 'operating_room' && (r.surgery_room_type || '') && !(r.clean_class || '')){
            showToast(`${roomLabel}:手术室洁净等级未选择`,'error');
            return null;
        }
        if(r.type_id === 'operating_room' && Boolean(r.clean_class) && !(r.surgery_room_type || '')){
            showToast(`${roomLabel}:手术室链路异常,洁净等级已存在但房间类型为空`,'error');
            return null;
        }
        if(r.type_id === 'operating_room' && (r.surgery_room_type || '') && !(r.clean_class || '') && ((r.basis||[]).length > 0 || (r.judgement||[]).length > 0 || (r.active_judgement||[]).length > 0)){
            showToast(`${roomLabel}:手术室洁净等级未完成,不得保留依据/判定链`,'error');
            return null;
        }
        if(r.type_id === 'operating_room' && (r.surgery_room_type || '') && !(r.clean_class || '') && (Object.keys(r.params||{}).length > 0 || Boolean(r.basis_expanded) || Boolean(r.judgement_expanded))){
            showToast(`${roomLabel}:手术室洁净等级未完成,不得保留参数区或展开态`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && Boolean(r.clean_class) && r.clean_class === '屏障环境' && !(r.barrier_room_class || '')){
            showToast(`${roomLabel}:动物房链路异常,屏障环境已存在但房间类别为空`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && Boolean(r.clean_class) && !(r.animal_context_incomplete) && !(r.barrier_room_class || '') && (r.clean_class === '屏障环境')){
            showToast(`${roomLabel}:动物房链路异常,环境已存在但房间类别为空`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && Boolean(r.clean_class) && !(r.animal_context_incomplete) && (r.clean_class === '屏障环境') && !(r.barrier_room_class || '')){
            showToast(`${roomLabel}:动物房链路异常,环境已存在但房间类别为空`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && !r.barrier_room_class && ((r.active_judgement||[]).length > 0)){
            showToast(`${roomLabel}:屏障环境房间类别未完成,不能保留激活判定链`,'error');
            return null;
        }
        if(r.type_id === 'animal_room' && r.level_name === '屏障环境' && r.barrier_room_class === '洁净辅房' && !r.barrier_aux_room && ((r.active_judgement||[]).length > 0)){
            showToast(`${roomLabel}:洁净辅房名称未完成,不能保留激活判定链`,'error');
            return null;
        }

        // 说明:房间参数不纳入"关键参数检查",不因为未录入房间参数而拦截生成。
        // 当前关键参数只看:项目信息、检测领域、房间名称。

        // 数值合理性检查(可选,警告级别)
        for(const [pk, pdata] of Object.entries(r.params)){
            if(pdata.type === 'hepa_leak_multi' && Array.isArray(pdata.objects)){
                const unnamed = pdata.objects.find(item => item && item.value !== '' && !(item.name||'').trim());
                if(unnamed){
                    showToast(`${roomLabel} ${pk}:高效过滤器检漏已录入检测值时,必须填写检测对象名称`,'error');
                    return null;
                }
                if((pdata.standard||'') && pdata.standard !== 'GB 50591-2010'){
                    showToast(`${roomLabel} ${pk}:高效过滤器检漏判定标准必须统一为 GB 50591-2010`,'error');
                    return null;
                }
                if((pdata.range||'') && pdata.range !== '≤0.01'){
                    showToast(`${roomLabel} ${pk}:高效过滤器检漏判定范围应统一为 ≤0.01`,'error');
                    return null;
                }
            }
            if(pdata.type === 'numeric' && pdata.values){
                for(const v of pdata.values){
                    const num = parseFloat(v);
                    if(isNaN(num)){
                        showToast(`${roomLabel} ${pk}:数值无效`,'error');
                        return null;
                    }
                    // 温度合理性
                    if(pk === 'temperature' && (num < -20 || num > 50)){
                        showToast(`${roomLabel} 温度:${num}°C 超出合理范围(-20~50°C)`,'warning');
                    }
                    // 湿度合理性
                    if(pk === 'humidity' && (num < 0 || num > 100)){
                        showToast(`${roomLabel} 湿度:${num}% 超出合理范围(0~100%)`,'error');
                        return null;
                    }
                    // 压差合理性
                    if(pk === 'pressure' && (num < -50 || num > 50)){
                        showToast(`${roomLabel} 静压差:${num}Pa 超出合理范围(-50~50Pa)`,'warning');
                    }
                }
            }
        }
    }

    return d;
}

function openDB(){
    return new Promise((resolve,reject)=>{
        const req=indexedDB.open(DB_NAME,DB_VERSION);
        req.onupgradeneeded=e=>{
            const db=e.target.result;
            if(!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME,{keyPath:'_localId',autoIncrement:true});
        };
        req.onsuccess=e=>resolve(e.target.result);
        req.onerror=e=>reject(e.target.error);
    });
}

function buildOfflineTask(data, action='save_draft', options={}){
    const clean=JSON.parse(JSON.stringify(data||{}));
    const isAuto = options.auto === true;
    if(window._sourceGeneratedRecordId && !clean.source_generated_record_id){
        clean.source_generated_record_id = window._sourceGeneratedRecordId;
    }
    if(window._localEditingTaskId && !clean._localId){
        clean._localId = window._localEditingTaskId;
    }
    if(window._editingRecordId && !clean.record_id){
        clean.record_id = window._editingRecordId;
    }
    clean._savedAt=new Date().toISOString();
    clean._queueAction=action;
    clean._draftKind = isAuto ? 'auto' : 'manual';
    clean._queueStatus='pending';
    clean._queueError='';
    clean._lastAttemptAt='';
    return clean;
}

function normalizeQueueError(errorText, action){
    const text=String(errorText||'').trim();
    if(!text){
        if(action==='submit_and_export') return '导出失败,请重试';
        if(action==='submit_and_generate') return '生成失败,请重试';
        return '同步失败,请重试';
    }
    if(text.includes('Failed to fetch') || text.includes('NetworkError') || text.includes('网络异常')) return '网络异常,等待恢复后重试';
    if(text.includes('服务器错误(502)')) return '服务暂时不可用,请稍后重试';
    if(text.includes('服务器错误(500)')) return '服务器处理失败,请稍后重试';
    if(text.includes('服务器错误(401)') || text.includes('未登录')) return '登录已失效,请重新登录后重试';
    if(text.includes('服务器错误(403)')) return '当前账号无权限执行此操作';
    if(text.includes('服务器错误(404)')) return '目标记录不存在或接口不可用';
    if(text.includes('没有房间数据')) return '缺少房间数据,无法生成记录';
    if(text.includes('请至少添加一个房间')) return '请先补充房间信息';
    if(text.includes('请填写项目名称')) return '项目名称未填写';
    if(text.includes('请填写委托单位')) return '委托单位未填写';
    if(text.includes('请选择检测日期')) return '检测日期未填写';
    if(text.includes('请选择检测领域')) return '检测领域未选择';
    if(text.includes('请在房间中选择检测类型')) return '检测类型未选择';
    if(text.includes('请至少选择一个检测依据')) return '检测依据未选择';
    if(text.includes('请至少选择一个判定标准')) return '判定标准未选择';
    if(text.includes('timeout') || text.includes('timed out')) return '处理超时,请重试';
    if(action==='submit_and_export' && (text.includes('飞书') || text.includes('upload'))) return '文件已生成,但上传失败';
    return text.length>30 ? text.slice(0,30)+'...' : text;
}

function getQueueStatusMeta(record){
    const action=record?._queueAction || 'save_draft';
    const status=record?._queueStatus || 'pending';
    if(status==='processing') return {label:'同步中', color:'#2196f3'};
    if(status==='failed'){
        if(action==='submit_and_export') return {label:'导出失败', color:'#e53935'};
        if(action==='submit_and_generate') return {label:'生成失败', color:'#e53935'};
        return {label:'同步失败', color:'#e53935'};
    }
    if(status==='done') return {label:'已完成', color:'#4caf50'};
    if(action==='submit_and_export') return {label:'导出中', color:'#ff9800'};
    if(action==='submit_and_generate') return {label:'生成中', color:'#ff9800'};
    if(action==='submit_only') return {label:'待提交', color:'#ff9800'};
    return {label:'待同步', color:'#ff9800'};
}

function getSyncEndpoint(action, record){
    if(action==='submit_and_export') return '/api/submit_and_export';
    if(action==='submit_and_generate') return '/api/submit_and_generate';
    return '/api/save';
}

function getSyncSuccessText(action, count){
    if(action==='submit_and_export') return `✅ 已同步并导出${count}条离线记录`;
    if(action==='submit_and_generate') return `✅ 已同步并生成${count}条离线记录`;
    return `✅ 已同步${count}条离线记录`;
}

function updateOnlineStatus(){
    isOnline=navigator.onLine;
    const badge=document.getElementById('syncBadge');
    if(badge) badge.style.display=isOnline?'none':'inline-block';
    if(isOnline) syncPendingRecords();
}

function ensureEditingRecordId(){
    if(window._editingRecordId) return window._editingRecordId;
    window._editingRecordId = 'D' + Date.now() + '_' + Math.random().toString(16).slice(2,10);
    return window._editingRecordId;
}

function fuzzyKeywordsMatch(fields, keyword){
    const kw=(keyword||'').trim().toLowerCase();
    if(!kw) return true;
    const text=(fields||[]).join(' ').toLowerCase();
    const parts=kw.split(/\s+/).filter(Boolean);
    return parts.every(part=>text.includes(part));
}

function previewFile(filename){
    var overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10001';
    overlay.innerHTML='<div style="background:#fff;border-radius:8px;padding:24px;width:92%;max-width:1200px;max-height:90vh;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;flex-direction:column"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid #f0f0f0;flex-shrink:0"><h3 style="margin:0">加载中...</h3><div style="display:flex;gap:8px"><a id="pv-dl" style="display:none;padding:6px 14px;background:#1890ff;color:white;border-radius:4px;font-size:13px;text-decoration:none" target="_blank">下载</a><button onclick="this.closest(\'.pv-overlay\').remove()" style="padding:6px 14px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:13px">关闭</button></div></div><div id="pv-body" style="border:1px solid #d9d9d9;border-radius:4px;padding:40px 60px;background:#fff;flex:1;overflow-y:auto;font-family:SimSun,serif;font-size:14px;line-height:1.8;color:#000"><p style="text-align:center;color:#999">加载中...</p></div></div>';
    overlay.className='pv-overlay';
    overlay.addEventListener('click',function(e){if(e.target===overlay)overlay.remove();});
    document.body.appendChild(overlay);
    fetch('/api/preview/'+encodeURIComponent(filename),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){
        if(!d.success){overlay.querySelector('#pv-body').innerHTML='<p style="text-align:center;color:#ff4d4f">预览失败: '+(d.error||'未知错误')+'</p>';return;}
        overlay.querySelector('h3').textContent=filename+' ('+((d.file_size||0)/1024).toFixed(1)+' KB)';
        var dl=overlay.querySelector('#pv-dl');dl.href='/download/'+encodeURIComponent(filename);dl.style.display='inline-block';
        overlay.querySelector('#pv-body').innerHTML='<style>.pv-c table{border-collapse:collapse;width:100%;margin:16px 0}.pv-c td,.pv-c th{border:1px solid #000;padding:8px;text-align:center}.pv-c p{margin:8px 0}</style><div class="pv-c">'+d.html+'</div>';
    }).catch(function(e){
        overlay.querySelector('#pv-body').innerHTML='<p style="text-align:center;color:#ff4d4f">网络错误: '+e.message+'</p>';
    });
}

function buildStatusText(status){
    const text = String(status || '未生成');
    const done = text.includes('已生成') || text.includes('已完成');
    const voided = text.includes('已作废');
    const color = voided ? '#c62828' : (done ? '#2e7d32' : '#c62828');
    return `<span style="color:${color};font-weight:600;">${text}</span>`;
}

function openFileWithWPS(filename){
    fetch('/admin/api/open_file/'+encodeURIComponent(filename), {method:'POST', credentials:'same-origin'})
      .then(function(r){ return r.json().then(function(d){ return {ok:r.ok, status:r.status, data:d}; }); })
      .then(function(res){
        var d = res.data || {};
        if(d && d.success){
          showToast((d.message || '已用 WPS 打开文件'), 'success');
          return;
        }
        if(res.status === 409){
          showToast((d.error || '当前主机不支持本机打开，改为浏览器下载'), 'info');
          window.location.href = '/download/' + encodeURIComponent(filename);
          return;
        }
        showToast((d && d.error) || '打开失败', 'error');
      })
      .catch(function(){ showToast('打开失败', 'error'); });
}

function openFeishuFile(feishuUrl){
    var fileToken = '';
    var m = feishuUrl.match(/\/drive\/file\/([A-Za-z0-9]+)/);
    if(m) fileToken = m[1];
    if(!fileToken){ m = feishuUrl.match(/\/(docx|sheets)\/([A-Za-z0-9]+)/); if(m) fileToken = m[2]; }
    if(!fileToken){ showToast('无法从链接提取飞书文件 token', 'error'); return; }
    showToast('正在从飞书下载...', 'info');
    fetch('/admin/api/download_feishu_file?file_token=' + encodeURIComponent(fileToken), {credentials:'same-origin'})
      .then(function(resp){
        if(!resp.ok) throw new Error('HTTP ' + resp.status);
        var cd = resp.headers.get('Content-Disposition') || '';
        var fname = 'feishu_file';
        var fm = cd.match(/filename=([^;]+)/);
        if(fm) fname = fm[1].replace(/"/g,'').trim();
        var ct = resp.headers.get('Content-Type') || 'application/octet-stream';
        return resp.blob().then(function(blob){ return {blob:blob, fname:fname, ct:ct}; });
      })
      .then(function(r){
        // 直接 blob 下载（所有设备统一行为）
        var url = URL.createObjectURL(r.blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = r.fname;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(function(){ URL.revokeObjectURL(url); document.body.removeChild(a); }, 5000);
        showToast('文件已下载: ' + r.fname, 'success');
      })
      .catch(function(e){ showToast('飞书文件下载失败: ' + e.message, 'error'); });
}

function buildRecordItem(r){
    let actionButtons='';
    const hasReport = !!(r.report_info?.feishu_url || r.report_info?.filename);
    const hasExport = !!(r.export_info?.feishu_url || r.export_info?.filename);
    const statusMeta = r._queueAction ? getQueueStatusMeta(r) : null;
    // 第二层隔离：非本人草稿可看不可编辑（仅限暂存记录，报告记录不受限）
    const isOwnRecord = !r.inspector || r.inspector === currentUser;
    const isDraft = isDraftRecord(r);
    if(hasReport || hasExport){
        if(r.report_info?.feishu_url){
            actionButtons+=`<button onclick="event.stopPropagation();openFeishuFile('${r.report_info.feishu_url}')" class="record-action-btn report-btn">📄 查看检测报告</button>`;
        }else if(r.report_info?.filename){
            actionButtons+=`<button onclick="event.stopPropagation();openFileWithWPS('${r.report_info.filename}')" class="record-action-btn report-btn">📄 查看检测报告</button>`;
        }
        if(r.export_info?.feishu_url){
            actionButtons+=`<button onclick="event.stopPropagation();openFeishuFile('${r.export_info.feishu_url}')" class="record-action-btn export-btn">📋 查看原始记录</button>`;
        }else if(r.export_info?.filename){
            actionButtons+=`<button onclick="event.stopPropagation();openFileWithWPS('${r.export_info.filename}')" class="record-action-btn export-btn">📋 查看原始记录</button>`;
        }
        if(hasReport || hasExport){
            actionButtons+= r.voided
                ? `<button onclick="event.stopPropagation();" disabled class="record-action-btn void-btn disabled">⛔ 已作废</button>`
                : `<button onclick="event.stopPropagation();voidReportRecord('${r.record_id}')" class="record-action-btn void-btn">⛔ 作废</button>`;
        }
    }
    let badges='';
    const draftTypeMeta = getDraftTypeMeta(r);
    if(draftTypeMeta && isDraftRecord(r)){
        badges+=`<span class="badge" style="margin-left:4px;background:${draftTypeMeta.color};color:white;" title="${draftTypeMeta.hint}">${draftTypeMeta.label}</span>`;
    }
    if(statusMeta){
        badges+=`<span class="badge" style="margin-left:4px;background:${statusMeta.color};color:white;" title="${r._queueError||statusMeta.label}">${statusMeta.label}</span>`;
    }
    if(r._queueAction){
        actionButtons += `
            <button onclick="event.stopPropagation();retryLocalTask('${r.record_id}')" class="record-action-btn retry-btn">重试</button>
            <button onclick="event.stopPropagation();abandonLocalTask('${r.record_id}')" class="record-action-btn delete-btn">删除</button>`;
    }
    // 本人草稿加“转让”按钮
    if(isDraft && isOwnRecord && r.inspector){
        actionButtons += `<button onclick="event.stopPropagation();transferDraft('${r.record_id}')" class="record-action-btn" style="background:#ff9800;color:white;">🔄 转让</button>`;
    }

    const rooms = Array.isArray(r.rooms) ? r.rooms : [];
    const roomSummary = rooms.length > 0
        ? rooms.slice(0,3).map(room => escHtml(buildRoomHierarchySummary(room))).join('；') + (rooms.length > 3 ? ` 等${rooms.length}项` : '')
        : escHtml(r.detection_type_name || r.detection_type || '未识别对象');

    const savedAt = r.save_time ? r.save_time.replace('T',' ').substring(0,16) : (r.detection_date || '');
    const reportStatus = r.voided ? '已作废' : (statusMeta?.label || (hasReport ? '已生成' : '未生成'));
    const recordStatus = r.voided ? '已作废' : (statusMeta?.label || (hasExport ? '已生成' : '未生成'));
    const currentStatus = (hasReport || hasExport)
        ? `<div class="record-status-row"><span class="record-status-chip">检测报告：${buildStatusText(reportStatus)}</span><span class="record-status-chip">原始记录：${buildStatusText(recordStatus)}</span></div>`
        : `<div class="record-status-row"><span class="record-status-chip">当前状态：${buildStatusText(statusMeta?.label || '草稿')}</span></div>`;
    const timeInspectorLine = [`生成时间：${escHtml(savedAt)}`, `检测员：${escHtml(r.inspector) || '-'}`].join(' / ');
    const clientLine = r.client_name ? `委托单位：${escHtml(r.client_name)}` : '';
    const headerLine = [escHtml(r.project_name)||'未命名项目', escHtml(r.report_number)||''].filter(Boolean).join(' / ');
    const voidReasonLine = r.voided && r.void_reason ? `<div class="record-extra record-error">作废理由：${escHtml(r.void_reason)}</div>` : '';
    const errorLine = r._queueError ? `<div class="record-extra record-error">${escHtml(r._queueError)}</div>` : '';

    const autoDraftHint = (draftTypeMeta && draftTypeMeta.label === '自动保存')
        ? `<div class="record-extra" style="color:#999;">${draftTypeMeta.hint}</div>`
        : '';

    // 第二层隔离：仅暂存记录限制非本人编辑
    const editDisabled = isDraft && !isOwnRecord;
    const onclickAttr = editDisabled
        ? `onclick="event.stopPropagation();showToast('这是其他检测员的记录，不能编辑','error')"`
        : `onclick="loadRecordForEdit('${r.record_id}')"`;
    const disabledStyle = editDisabled ? 'opacity:0.7;cursor:not-allowed;' : '';
    if(editDisabled){
        badges+=`<span class="badge" style="margin-left:4px;background:#9e9e9e;color:white;">只读</span>`;
    }

    return `<li class="record-item" ${onclickAttr} style="${disabledStyle}"><div class="record-info" style="flex:1;min-width:0;"><div class="title">${headerLine} ${badges}</div><div class="record-extra">${roomSummary}</div><div class="record-meta-line">${timeInspectorLine}</div><div class="record-meta-line">${currentStatus}</div><div class="record-extra">${clientLine}</div>${autoDraftHint}${voidReasonLine}${errorLine}</div><div class="record-actions">${actionButtons ? `<div class="record-actions-row">${actionButtons}</div>` : ''}</div></li>`;
}

function isReportRecord(r){
    const hasReport = !!(r.report_info?.feishu_url || r.report_info?.filename);
    const hasExport = !!(r.export_info?.feishu_url || r.export_info?.filename);
    const hasAnyOutput = hasReport || hasExport;
    const queuedForReport = !!(r._queueAction === 'submit_and_export' || r._queueAction === 'submit_and_generate');
    return hasAnyOutput || queuedForReport;
}

function normalizeLocalTaskRecord(task){
    const normalized = {
        ...task,
        record_id: task.record_id || ('LOCAL_'+task._localId),
        project_name: task.project_name || '',
        client_name: task.client_name || '',
        report_number: task.report_number || '',
        domain_name: task.domain_name || task.domain || '',
        level_name: task.level_name || '',
        detection_date: task.detection_date || '',
        inspector: task.inspector_name || task.inspector || currentUser || '本地',
        status: 'draft',
        save_time: task._savedAt || task.save_time || '',
        draft_kind: task._draftKind || 'manual'
    };
    normalized._hasStrongVisibleContent = !!(
        (normalized.project_name && String(normalized.project_name).trim()) ||
        (normalized.client_name && String(normalized.client_name).trim()) ||
        (normalized.detection_date && String(normalized.detection_date).trim()) ||
        (normalized.report_number && String(normalized.report_number).trim())
    );
    return normalized;
}

function loadHistory(){
    Promise.all([
        fetch('/api/list').then(r=>r.json()).catch(()=>({records:[]})),
        getPendingRecords().catch(()=>[])
    ]).then(([data,localPending])=>{
        const remoteRecords=data.records||[];
        const localRecords=(localPending||[])
            .map(normalizeLocalTaskRecord)
            .filter(r=>r._hasStrongVisibleContent);
        allHistoryRecords=[...localRecords,...remoteRecords];
        renderDraftRecords();
        renderHistoryRecords();
        window.scrollTo({top:0,behavior:'instant'});
        document.body.scrollTop=0;
        document.documentElement.scrollTop=0;
    }).catch(()=>{
        document.getElementById('draftRecordsList').innerHTML='<li style="text-align:center;color:#999;padding:30px;">加载失败</li>';
        document.getElementById('recordsList').innerHTML='<li style="text-align:center;color:#999;padding:30px;">加载失败</li>';
    });
}

function normalizeEditableRecordData(d, fallbackId=''){
    const record = {...(d||{})};
    record.record_id = record.record_id || fallbackId || '';
    record.project_name = record.project_name || '';
    record.report_number = record.report_number || '';
    record.client_name = record.client_name || '';
    record.contact_info = record.contact_info || '';
    record.project_address = record.project_address || '';
    record.inspection_area = record.inspection_area || '';
    record.detection_date = record.detection_date || '';
    record.detection_state = record.detection_state || '静态';
    record.domain = record.domain || record.domain_id || '';
    record.domain_name = record.domain_name || '';
    record.weather = record.weather || {temperature:'', humidity:'', pressure:''};
    record.rooms = Array.isArray(record.rooms) ? record.rooms.map(room => ({
        ...room,
        surgery_room_type: normalizeOperatingRoomTypeValue(room?.surgery_room_type || room?.context?.surgery_room_type || ''),
        surgery_aux_room: normalizeOperatingAuxRoomValue(room?.surgery_aux_room || room?.context?.surgery_aux_room || ''),
        surgery_aux_clean_class: normalizeOperatingAuxCleanClassValue(room?.surgery_aux_clean_class || room?.context?.surgery_aux_clean_class || ''),
        clean_function_subroom: room?.clean_function_subroom || room?.context?.clean_function_subroom || '',
        barrier_room_class: room?.barrier_room_class || room?.context?.barrier_room_class || '',
        barrier_aux_room: room?.barrier_aux_room || room?.context?.barrier_aux_room || '',
        animal_environment: room?.animal_environment || room?.context?.animal_environment || '',
        bsl: room?.bsl || room?.context?.bsl_level || '',
        bsl_level: room?.bsl_level || room?.context?.bsl_level || '',
        negative_pressure_mode: room?.negative_pressure_mode || room?.context?.negative_pressure_mode || '',
        iso_level: room?.iso_level || room?.context?.iso_level || '',
        food_grade: room?.food_grade || room?.context?.food_grade || '',
        gmp_grade: room?.gmp_grade || room?.context?.gmp_grade || '',
        basis: Array.isArray(room?.basis) ? room.basis : [],
        basis_dataset: Array.isArray(room?.basis_dataset) ? room.basis_dataset : [],
        basis_expanded: room?.basis_expanded === true || room?.basis_expanded === 'true',
        barrier_room_class: room?.barrier_room_class || '',
        barrier_aux_room: room?.barrier_aux_room || '',
        bsl: room?.bsl || '',
        business_domain_hint: ((room?.type_id === 'pass_box' || room?.type_id === 'laminar_hood')
            ? ((room?.business_domain_hint || '') || 'pharma')
            : (room?.business_domain_hint || '')),
        electronics_manual_range_keys: Array.isArray(room?.electronics_manual_range_keys) ? room.electronics_manual_range_keys : [],
        hepa_leak_summary: room?.hepa_leak_summary || '',
        animal_context_incomplete: room?.animal_context_incomplete === true || room?.animal_context_incomplete === 'true',
        animal_illumination_source: room?.animal_illumination_source || '',
        judgement: Array.isArray(room?.judgement) ? room.judgement : [],
        judgement_priority: Array.isArray(room?.judgement_priority) ? room.judgement_priority : [],
        judgement_checked: Array.isArray(room?.judgement_checked) ? room.judgement_checked : [],
        judgement_active: Array.isArray(room?.judgement_active) ? room.judgement_active : [],
        summary: {
            result_state: room?.summary?.result_state || room?.result_state || '',
            input_result_state: room?.summary?.input_result_state || room?.input_result_state || '',
            judgement_engine: room?.summary?.judgement_engine || room?.judgement_engine || '',
            judgement_reason: room?.summary?.judgement_reason || room?.judgement_reason || '',
            judgement_overridden: typeof room?.summary?.judgement_overridden === 'boolean'
                ? room.summary.judgement_overridden
                : (typeof room?.judgement_overridden === 'boolean' ? room.judgement_overridden : null),
            abnormal_items: Array.isArray(room?.summary?.abnormal_items)
                ? room.summary.abnormal_items
                : (Array.isArray(room?.abnormal_items) ? room.abnormal_items : []),
            judgement_active: Array.isArray(room?.summary?.judgement_active) ? room.summary.judgement_active : (Array.isArray(room?.judgement_active) ? room.judgement_active : []),
            basis_primary: room?.summary?.basis_primary || '',
            judgement_primary: room?.summary?.judgement_primary || ''
        },
        pass_box_judgement_active: Array.isArray(room?.pass_box_judgement_active) ? room.pass_box_judgement_active : [],
        pass_box_result_state: room?.pass_box_result_state || '',
        judgement_expanded: room?.judgement_expanded === true || room?.judgement_expanded === 'true',
        clean_function_subroom: room?.clean_function_subroom || '',
        params: normalizeEditableRoomParams(room?.params)
    })) : [];
    record.basis = Array.isArray(record.basis) ? record.basis : [];
    record.judgement = Array.isArray(record.judgement) ? record.judgement : [];
    record.report_info = record.report_info || null;
    record.export_info = record.export_info || null;
    return record;
}

function showToast(msg,type){const t=document.getElementById('toast');t.textContent=msg;t.className='toast '+(type||'');t.style.display='block';setTimeout(()=>t.style.display='none',2500);}

function showExportLoading(text){
    var existing = document.getElementById('export-loading-overlay');
    if(existing) existing.remove();
    var div = document.createElement('div');
    div.id = 'export-loading-overlay';
    div.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;z-index:9999';
    div.innerHTML = '<div style="background:#fff;border-radius:8px;padding:32px 48px;text-align:center;box-shadow:0 4px 16px rgba(0,0,0,0.2)"><div style="width:40px;height:40px;border:4px solid #f0f0f0;border-top-color:#1890ff;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 16px"></div><div style="font-size:15px;color:#333">'+(text||'处理中...')+'</div><div style="font-size:12px;color:#999;margin-top:8px">请勿关闭页面</div></div>';
    document.body.appendChild(div);
}

function addPt_bc(rid,pk){const room=document.querySelector(`[data-rid="${rid}"]`);const dp=room.querySelector(`[data-dp="${pk}"]`);const btn=dp.querySelector('.add-pt');const n=dp.querySelectorAll('input').length+1;const inp=document.createElement('input');inp.type='number';inp.step='1';inp.min='0';inp.placeholder=n;inp.oninput=function(){calc_bacteria_control(rid,pk);};btn.before(inp);}
function addPt_sc(rid,pk){const room=document.querySelector(`[data-rid="${rid}"]`);const dp=room.querySelector(`[data-dp="${pk}"]`);const btn=dp.querySelector('.add-pt');const n=dp.querySelectorAll('input').length+1;const inp=document.createElement('input');inp.type='number';inp.step='1';inp.min='0';inp.placeholder=n;inp.oninput=function(){calc_settling_control(rid,pk);};btn.before(inp);}
function addPt_fc(rid,pk){const room=document.querySelector(`[data-rid="${rid}"]`);const dp=room.querySelector(`[data-dp="${pk}"]`);const btn=dp.querySelector('.add-pt');const n=dp.querySelectorAll('input').length+1;const inp=document.createElement('input');inp.type='number';inp.step='1';inp.min='0';inp.placeholder=n;inp.oninput=function(){calc_floating_control(rid,pk);};btn.before(inp);}
function addPt_bzc(rid,pk,zone){const room=document.querySelector(`[data-rid="${rid}"]`);const dp=room.querySelector(`[data-dp="${pk}${zone}"]`);const btn=dp.querySelector('.add-pt');const n=dp.querySelectorAll('input').length+1;const inp=document.createElement('input');inp.type='number';inp.step='1';inp.min='0';inp.placeholder=n;inp.oninput=function(){calc_bacteria_zone_control(rid,pk);};btn.before(inp);}
function calc_bacteria_control(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    let range = getParamRange(rid,pk).range || '';
    const inputs=room.querySelectorAll(`[data-dp="${pk}"] input`);
    const vals=Array.from(inputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    const blank=parseFloat(room.querySelector(`[data-bc-blank="${pk}"]`)?.value);
    const neg=parseFloat(room.querySelector(`[data-bc-neg="${pk}"]`)?.value);
    
    let parts=[];
    let allPass=true;
    
    if(vals.length>0){
        const avg=vals.reduce((a,b)=>a+b,0)/vals.length;
        const pass = judgeRange(avg, range);
        if(!pass)allPass=false;
        parts.push(`平均值:${avg.toFixed(1)}${pass?'✅':'❌'}`);
    }
    
    if(!isNaN(blank)){
        const pass=blank===0;
        if(!pass)allPass=false;
        parts.push(`空白对照:${blank}${pass?'✅':'❌'}`);
    }
    
    if(!isNaN(neg)){
        const pass=neg===0;
        if(!pass)allPass=false;
        parts.push(`阴性对照:${neg}${pass?'✅':'❌'}`);
    }
    
    if(parts.length>0)setRes(rid,pk,parts.join(' | '),allPass);
    else {
        setRes(rid,pk,'-','');
    }
}

function loadMyTasks(filter){
  filter = filter || 'active';
  _myTasksFilter = filter;
  // 更新按钮高亮
  ['active','completed','all'].forEach(function(f){
    var btn = document.getElementById('mytask-btn-' + f);
    if(btn) btn.style.fontWeight = (f === filter) ? 'bold' : 'normal';
  });
  var box = document.getElementById('mytasks-list');
  if(!box) return;
  box.innerHTML = '<div style="text-align:center;color:#999;padding:30px;">加载中...</div>';
  var url = '/api/my_tasks';
  if(filter === 'completed') url += '?status=completed';
  else if(filter === 'all') url += '?status=all';
  fetch(url)
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(!d.success) throw new Error(d.error || '加载失败');
      renderMyTasks(d.items || []);
    })
    .catch(function(err){
      console.error(err);
      box.innerHTML = '<div style="text-align:center;color:#cf1322;padding:30px;">加载失败</div>';
    });
}

function doTaskAction(taskId, action){
  var confirmMsg = {accept:'确认接单？', start:'确认开始执行？', complete:'确认完成任务？'}[action] || '确认？';
  if(!confirm(confirmMsg)) return;
  fetch('/api/project_tasks/' + taskId + '/' + action, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: '{}'
  })
    .then(function(r){ return r.json().then(function(d){ return {ok:r.ok, data:d}; }); })
    .then(function(res){
      if(!res.ok || !res.data.success) throw new Error(res.data.error || '操作失败');
      loadMyTasks(_myTasksFilter);
      if(typeof pollTaskCount === 'function') pollTaskCount();
    })
    .catch(function(err){
      console.error(err);
      alert(err.message || '操作失败');
    });
}

function prefillFromTask(taskId){
  fetch('/api/project_tasks/' + taskId + '/prefill')
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(!d.success) throw new Error(d.error || '获取项目信息失败');
      var p = d.prefill || {};
      // 切到录入 tab
      showTab('new');
      // 填入项目基础信息
      var map = {
        'projectName': p.project_name || '',
        'clientName': p.client_name || '',
        'projectAddress': p.project_address || '',
        'contactInfo': (p.contact_name && p.contact_phone) ? (p.contact_name + ' ' + p.contact_phone) : (p.contact_name || p.contact_phone || ''),
        'detectionDate': p.expected_detection_date || '',
        'inspectionArea': p.detection_domain || ''
      };
      for(var id in map){
        var el = document.getElementById(id);
        if(el && map[id]){
          el.value = map[id];
          // 触发 input/change 事件让其他逻辑感知到
          el.dispatchEvent(new Event('input', {bubbles:true}));
          el.dispatchEvent(new Event('change', {bubbles:true}));
        }
      }
      // 记住任务来源
      window._currentTaskId = taskId;
      window._currentProjectId = d.project_id;
      // 展开项目信息卡片（如果折叠了）
      var body = document.getElementById('projectInfoBody');
      if(body && body.style.display === 'none'){
        var card = document.getElementById('projectInfoCard');
        if(card) card.click();
      }
      // 提示
      if(typeof showToast === 'function') showToast('已从任务自动填入项目信息');
    })
    .catch(function(err){
      console.error(err);
      alert(err.message || '获取项目信息失败');
    });
}


// Export all functions
export {
    escHtml,
    handleAdminEntry,
    updateReportNumber,
    showResetDialog,
    hasMeaningfulEditingContent,
    showReturnToEditDialog,
    resetForm,
    showTab,
    toggleCard,
    updateProjectInfoSummary,
    updateCardSummary,
    initCardCollapse,
    setActiveJudgement,
    isAnimalBarrierContextIncomplete,
    moveJudgementPriority,
    syncAnimalContextMarker,
    syncPressurePairSummaryState,
    syncElectronicsManualState,
    isAnimalReadyMissing,
    isCleanFunctionReadyMissing,
    isOperatingReadyMissing,
    hasAnimalReverseAnomaly,
    hasCleanFunctionReverseAnomaly,
    hasOperatingReverseAnomaly,
    isAnimalChainClosed,
    isCleanFunctionChainClosed,
    isOperatingChainClosed,
    isAnimalAcceptanceState,
    isCleanFunctionAcceptanceState,
    isOperatingAcceptanceState,
    isOperatingContextIncomplete,
    selEquipmentAlias,
    selBSL,
    addPressurePair,
    removePressurePair,
    addPressureValuePt,
    switchPressurePairType,
    switchPressureType,
    updateBSLPressureRange,
    handleManualRangeChange,
    updateManualNumericRange,
    addPt,
    addVent,
    addVolPt,
    switchMethod,
    getDisplayRangeText,
    judgeRange,
    validate,
    openDB,
    buildOfflineTask,
    normalizeQueueError,
    getQueueStatusMeta,
    getSyncEndpoint,
    getSyncSuccessText,
    updateOnlineStatus,
    ensureEditingRecordId,
    fuzzyKeywordsMatch,
    previewFile,
    buildStatusText,
    openFileWithWPS,
    openFeishuFile,
    buildRecordItem,
    isReportRecord,
    normalizeLocalTaskRecord,
    loadHistory,
    normalizeEditableRecordData,
    showToast,
    addPt_bc,
    loadMyTasks,
    doTaskAction,
    prefillFromTask
};
