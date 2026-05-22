// 检测报告生成系统 - 主逻辑

let currentDomain=null, currentCriteriaIdx=null, currentUser='', currentUserProfile=null, roomCounter=0;

// 下拉刷新功能(已禁用,使用浏览器原生刷新)
let pullRefreshDisabled = false;

document.addEventListener('DOMContentLoaded', function(){
    window._hasSavedDraftOnce = false;
    window._returningFromListTab = false;
    window._suppressReturnToEditPrompt = false;
    ensureEditingRecordId();
    document.getElementById('detectionDate').value=new Date().toISOString().split('T')[0];
    // 报告编号:年份自动更新，周默认固定为当前值但后续不自动滚动
    initReportNumberDisplays();
    updateReportNumber();
    fetch('/api/user').then(r=>r.json()).then(d=>{currentUser=d.username; currentUserProfile=d||null; document.getElementById('currentUser').textContent=d.display_name||d.username;}).catch(()=>{currentUser='离线'; currentUserProfile=null;});
    renderDomainGrid();

    // 检查URL参数,如果有 ?edit= 则自动加载记录
    const urlParams = new URLSearchParams(window.location.search);
    const editId = urlParams.get('edit');
    if(editId){
        setTimeout(()=>{ loadRecordForEdit(editId); }, 500);
    }
});

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

function renderDomainGrid(){
    const grid = document.getElementById('domainGrid');
    if(!grid) return;
    const domains = Array.isArray(SYSTEM_DB?.domains) ? SYSTEM_DB.domains : [];
    if(!domains.length){
        grid.innerHTML = '<div style="padding:12px;color:#999;">检测领域加载中...</div>';
        return;
    }
    const top = domains.filter(d=>['hospital','electronics'].includes(d.id));
    const rest = domains.filter(d=>!['hospital','electronics'].includes(d.id));
    grid.innerHTML = `<div class="domain-grid-row domain-grid-row-2">${top.map(d=>`<div class="domain-btn" onclick="selectDomain('${d.id}',this)">${d.icon} ${d.name}</div>`).join('')}</div><div class="domain-grid-row domain-grid-row-3">${rest.map(d=>`<div class="domain-btn" onclick="selectDomain('${d.id}',this)">${d.icon} ${d.name}</div>`).join('')}</div>`;
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

// 报告编号:PDJC-BG年份-周份+用户自定义
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

let currentDetectionType = null;

function selectDomain(id,el){
    // 如果已有房间数据,切换领域前确认
    const existingRooms = document.querySelectorAll('.room-card');
    if(existingRooms.length > 0 && currentDomain && currentDomain !== id){
        if(!confirm('切换领域将清空已录入的房间数据,是否继续?')){
            return;
        }
        document.getElementById('roomsContainer').innerHTML = '';
        roomCounter = 0;
    }

    document.querySelectorAll('.domain-btn').forEach(b=>b.classList.remove('active'));
    el.classList.add('active');
    currentDomain=id;
    currentDetectionType=null;

    // 按 X3.3 原设计：隐藏全局检测类型、检测依据、判定标准，直接进入房间级录入
    document.getElementById('detectionTypeCard').classList.add('hidden');
    document.getElementById('basisCard').classList.add('hidden');
    document.getElementById('judgementCard').classList.add('hidden');

    // 直接显示房间区域
    document.getElementById('roomsCard').classList.remove('hidden');
}


// 设置判定依据标准
// 折叠/展开卡片
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

// 项目信息摘要更新
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

// 更新折叠后的摘要显示
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

// 初始化时自动展开,选好后可折叠
function initCardCollapse(){
    // 监听checkbox变化,实时更新摘要
    document.addEventListener('change', function(e){
        if(e.target.name === 'basis') updateCardSummary('basisCard');
        if(e.target.name === 'judgement') updateCardSummary('judgementCard');
    });
}
initCardCollapse();

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

// 根据新的判定标准更新所有房间的判定范围
function updateAllRoomsRanges(standardCode){
    // 已废弃：旧的全局范围覆盖链会污染按房间/子房间的实际判定范围。
    // 统一改由 updateRoomRangesByPriority(rid) 按房间上下文实时渲染。
    return;
}

function getRoomLevels(){
    if(!currentDetectionType) return [];
    // 如果有levelParams,返回levelParams的值数组
    if(currentDetectionType.levelParams){
        return Object.keys(currentDetectionType.levelParams).map(k=>({
            name: k,
            params: currentDetectionType.levelParams[k]
        }));
    }
    // 否则返回默认params
    if(currentDetectionType.params){
        return [{ name: 'default', params: currentDetectionType.params }];
    }
    return [];
}

function addRoom(){
    if(!currentDomain){
        showToast('请先选择检测领域','error');
        return;
    }

    roomCounter++;
    const rid='r'+roomCounter;

    // 获取当前领域的检测类型列表
    let types = SYSTEM_DB.detectionTypes[currentDomain] || [];
    // 收口原则：
    // 1) 传递窗、层流罩都改为各自领域下独立正式入口
    // 2) hospital_clean_corridor 不升级为正式检测类型入口
    if(currentDomain === 'hospital') types = types.filter(t => t.id !== 'hospital_clean_corridor');
    const typeBtnsHtml = types.map(t => `<div class="level-btn" onclick="selRoomType('${rid}','${t.id}')">${t.name}</div>`).join('');

    document.getElementById('roomsContainer').insertAdjacentHTML('beforeend',
    `<div class="room-card" data-rid="${rid}" data-domain="${currentDomain}">
        <div class="room-summary" onclick="toggleRoom('${rid}')">
            <span>📦 <strong class="room-summary-name">未命名房间</strong> <button type="button" class="room-inline-toggle" onclick="event.stopPropagation();toggleRoom('${rid}')">展开 ▼</button> <span class="remove-room remove-room-inline" onclick="event.stopPropagation();this.closest('.room-card').remove()">✕</span> <span class="room-summary-level" style="color:#888;font-size:12px;"></span></span>
            <span></span>
        </div>
        <div class="room-body">
        <div class="room-header">
            <div class="room-header-main">
                <div class="room-name-row">
                    <input type="text" class="rname room-name-input" placeholder="请输入房间/设备名称" oninput="updateRoomSummary('${rid}')">
                    <button type="button" class="room-inline-toggle room-inline-toggle-open" onclick="toggleRoom('${rid}')">折叠 ▲</button>
                    <span class="remove-room remove-room-inline" onclick="this.closest('.room-card').remove()">✕</span>
                </div>
                <div class="room-size-block" data-room-size-block style="display:none;">
                    <div class="room-size-title">请输入房间/设备尺寸：</div>
                    <div class="room-dimensions compact-room-dimensions" data-room-dimensions>
                        <input type="text" inputmode="decimal" pattern="[0-9]*[.]?[0-9]*" placeholder="长(m)" data-dim="length" oninput="handleRoomDimensionChange('${rid}')">
                        <input type="text" inputmode="decimal" pattern="[0-9]*[.]?[0-9]*" placeholder="宽(m)" data-dim="width" oninput="handleRoomDimensionChange('${rid}')">
                        <input type="text" inputmode="decimal" pattern="[0-9]*[.]?[0-9]*" placeholder="高(m)" data-dim="height" oninput="handleRoomDimensionChange('${rid}')">
                    </div>
                </div>
            </div>
            <div class="room-header-actions"></div>
        </div>
        <div class="room-type-row"><label class="room-type-label">检测类型:</label><div class="level-grid">${typeBtnsHtml}</div></div>
        <div class="room-surgery-type-options" style="margin:8px 0;"></div>
        <div class="room-surgery-aux-options" style="margin:8px 0;"></div>
        <div class="room-clean-options" style="margin:8px 0;"></div>
        <div class="room-barrier-room-class-options" style="margin:8px 0;"></div>
        <div class="room-barrier-aux-options" style="margin:8px 0;"></div>
        <div class="room-bsl-options" style="margin:8px 0;"></div>
        <div class="room-basis" style="margin:8px 0;background:#fff;border-radius:6px;border:1px solid #e0e0e0;overflow:hidden;display:none;">
            <div style="padding:8px 12px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;" onclick="toggleRoomBasis('${rid}')">
                <span style="font-size:13px;font-weight:500;color:#555;">📚 检测依据 <span class="rb-summary" style="font-size:12px;color:#888;font-weight:normal;"></span></span>
                <span class="rb-arrow" style="font-size:12px;color:#999;">▼</span>
            </div>
            <div class="rb-body" style="display:none;padding:0 12px 8px;"></div>
        </div>
        <div class="room-judgement" style="margin:8px 0;background:#fff;border-radius:6px;border:1px solid #e0e0e0;overflow:hidden;display:none;">
            <div style="padding:8px 12px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;" onclick="toggleRoomJudgement('${rid}')">
                <span style="font-size:13px;font-weight:500;color:#555;">⚖️ 判定标准 <span class="rj-summary" style="font-size:12px;color:#888;font-weight:normal;"></span></span>
                <span class="rj-arrow" style="font-size:12px;color:#999;">▼</span>
            </div>
            <div class="rj-body" style="display:none;padding:0 12px 8px;"></div>
        </div>
        <div class="rparams-top"></div>
        <div class="rparams"></div>
        </div>
    </div>`);

    // 折叠之前的房间
    document.querySelectorAll('.room-card').forEach(card=>{
        if(card.dataset.rid !== rid && !card.classList.contains('collapsed')){
            card.classList.add('collapsed');
            updateRoomSummary(card.dataset.rid);
        }
    });

    // 滚动到"房间/设备 检测数据录入"标题
    setTimeout(()=>{
        const title = document.getElementById('roomSectionTitle');
        const y = title.getBoundingClientRect().top + window.pageYOffset - 10;
        window.scrollTo({top: y, behavior: 'smooth'});
    }, 100);
}

function renderParamsForRoom(rid, detectionType){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    let effectiveDetectionType = detectionType || getRoomDetType(rid);
    if(room && effectiveDetectionType && effectiveDetectionType.id === 'operating_room' && room.dataset.surgeryRoomType === '洁净辅房' && room.dataset.surgeryAuxRoom && room.dataset.surgeryAuxCleanClass){
        const auxCleanClass = room.dataset.surgeryAuxCleanClass || '';
        const auxCleanMap = {
            'I级(局部5级其他6级)': { particleInput: 'particle_zone', particle_op: '≥0.5μm≤3520, ≥5μm≤29', particle_surr: '≥0.5μm≤35200, ≥5μm≤293', bacteriaInput: 'bacteria_zone_control', bacteria_op: '≤0.2', bacteria_surr: '≤0.4' },
            'Ⅰ级（局部5级其他6级）': { particleInput: 'particle_zone', particle_op: '≥0.5μm≤3520, ≥5μm≤29', particle_surr: '≥0.5μm≤35200, ≥5μm≤293', bacteriaInput: 'bacteria_zone_control', bacteria_op: '≤0.2', bacteria_surr: '≤0.4' },
            'II级(7级)': { particle: '≥0.5μm≤352000, ≥5μm≤2930', particleInput: 'particle_4', bacteria: '≤1.5', bacteriaInput: 'bacteria_control' },
            'Ⅱ级（7级）': { particle: '≥0.5μm≤352000, ≥5μm≤2930', particleInput: 'particle_4', bacteria: '≤1.5', bacteriaInput: 'bacteria_control' },
            'III级(8级)': { particle: '≥0.5μm≤3520000, ≥5μm≤29300', particleInput: 'particle_4', bacteria: '≤4', bacteriaInput: 'bacteria_control' },
            'Ⅲ级（8级）': { particle: '≥0.5μm≤3520000, ≥5μm≤29300', particleInput: 'particle_4', bacteria: '≤4', bacteriaInput: 'bacteria_control' },
            'IV级(8.5级)': { particle: '3520000>0.5μm≤11120000, 29300>5μm≤92500', particleInput: 'particle_4', bacteria: '≤6', bacteriaInput: 'bacteria_control' },
            'Ⅳ级（8.5级）': { particle: '3520000>0.5μm≤11120000, 29300>5μm≤92500', particleInput: 'particle_4', bacteria: '≤6', bacteriaInput: 'bacteria_control' }
        };
        const cleanOverride = auxCleanMap[auxCleanClass] || {};
        effectiveDetectionType = {
            ...effectiveDetectionType,
            params: (effectiveDetectionType.params || []).map(p => {
                if(p.key === 'particle'){
                    if(cleanOverride.particle_op){
                        return { ...p, inputType: cleanOverride.particleInput, range_op: cleanOverride.particle_op, range_surr: cleanOverride.particle_surr, range: '', zone_label_op: '局部', zone_label_surr: '其他区域' };
                    }
                    if(cleanOverride.particle){
                        return { ...p, inputType: cleanOverride.particleInput || 'particle_4', range: cleanOverride.particle, range_op: '', range_surr: '' };
                    }
                }
                if(p.key === 'bacteria'){
                    if(cleanOverride.bacteria_op){
                        return { ...p, inputType: cleanOverride.bacteriaInput || 'bacteria_zone_control', range_op: cleanOverride.bacteria_op, range_surr: cleanOverride.bacteria_surr, range: '', zone_label_op: '局部', zone_label_surr: '其他区域' };
                    }
                    if(cleanOverride.bacteria){
                        return { ...p, inputType: cleanOverride.bacteriaInput || 'bacteria_control', range: cleanOverride.bacteria, range_op: '', range_surr: '' };
                    }
                }
                return p;
            })
        };
    }
    if(room && effectiveDetectionType && effectiveDetectionType.id === 'operating_room' && room.dataset.surgeryRoomType === '眼科手术室' && room.dataset.cleanClass === 'Ⅳ级（十万级）' && Array.isArray(effectiveDetectionType.params)){
        effectiveDetectionType = {
            ...effectiveDetectionType,
            params: effectiveDetectionType.params.map(p => {
                if(p.key === 'particle') return { ...p, inputType: 'particle_4', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500', range_op: '', range_surr: '' };
                if(p.key === 'bacteria') return { ...p, inputType: 'bacteria_control' };
                return p;
            })
        };
    }
    if(room && effectiveDetectionType && effectiveDetectionType.id === 'operating_room' && room.dataset.surgeryRoomType === '手术室' && room.dataset.cleanClass === 'Ⅳ级（十万级）' && Array.isArray(effectiveDetectionType.params)){
        effectiveDetectionType = {
            ...effectiveDetectionType,
            params: effectiveDetectionType.params.map(p => {
                if(p.key === 'particle') return { ...p, inputType: 'particle_4', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500', range_op: '', range_surr: '' };
                if(p.key === 'bacteria') return { ...p, inputType: 'bacteria_control' };
                return p;
            })
        };
    }
    if(room && effectiveDetectionType && effectiveDetectionType.id === 'operating_room' && room.dataset.surgeryRoomType === '眼科手术室' && ['Ⅱ级（千级）','Ⅲ级（万级）','Ⅳ级（十万级）'].includes(room.dataset.cleanClass || '') && Array.isArray(effectiveDetectionType.params)){
        const filteredParams = effectiveDetectionType.params.filter(p => p.key !== 'wind_speed' && p.key !== 'wind_uniformity' && p.key !== 'particle_door');
        let params = filteredParams;
        const hasAirchange = params.some(p => p.key === 'airchange');
        if(!hasAirchange){
            const src = SYSTEM_DB.detectionTypes?.hospital?.find(t => t.id === 'operating_room')?.eyeLevelParams?.[room.dataset.cleanClass || ''] || [];
            const airchangeParam = src.find(p => p.key === 'airchange');
            if(airchangeParam){
                const insertAt = Math.max(0, params.findIndex(p => p.key === 'pressure'));
                params = [...params];
                params.splice(insertAt, 0, { ...airchangeParam });
            }
        }
        effectiveDetectionType = { ...effectiveDetectionType, params };
    }
    if(room && effectiveDetectionType && effectiveDetectionType.id === 'operating_room' && room.dataset.surgeryRoomType === '手术室' && ['Ⅱ级（千级）','Ⅲ级（万级）','Ⅳ级（十万级）'].includes(room.dataset.cleanClass || '') && Array.isArray(effectiveDetectionType.params)){
        const filteredParams = effectiveDetectionType.params.filter(p => p.key !== 'wind_speed' && p.key !== 'wind_uniformity' && p.key !== 'particle_door');
        let params = filteredParams;
        const hasAirchange = params.some(p => p.key === 'airchange');
        if(!hasAirchange){
            const src = SYSTEM_DB.detectionTypes?.hospital?.find(t => t.id === 'operating_room')?.levelParams?.[room.dataset.cleanClass || ''] || [];
            const airchangeParam = src.find(p => p.key === 'airchange');
            if(airchangeParam){
                const insertAt = Math.max(0, params.findIndex(p => p.key === 'pressure'));
                params = [...params];
                params.splice(insertAt, 0, { ...airchangeParam });
            }
        }
        effectiveDetectionType = { ...effectiveDetectionType, params };
    }
    if(room && effectiveDetectionType && (effectiveDetectionType.id === 'pass_box' || effectiveDetectionType.id === 'laminar_hood') && !room.dataset.businessDomainHint){
        room.dataset.businessDomainHint = 'pharma';
    }
    if(room && effectiveDetectionType && effectiveDetectionType.id === 'animal_room' && isAnimalBarrierContextIncomplete(room)){
        const box = room.querySelector('.rparams');
        const topDimsBlock = room.querySelector('[data-room-size-block]');
        if(topDimsBlock) topDimsBlock.style.display = 'none';
        const cleanClass = room.dataset.cleanClass || room.dataset.levelName || '';
        const barrierRoomClass = room.dataset.barrierRoomClass || '';
        if(box){
            if(cleanClass === '屏障环境' && !barrierRoomClass){
                box.innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择房间类别</p>';
            } else if(barrierRoomClass === '洁净辅房' && !room.dataset.barrierAuxRoom){
                box.innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择洁净辅房名称</p>';
            } else {
                box.innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 当前屏障环境上下文未完成</p>';
            }
        }
        return;
    }
    const defaultJudgement = effectiveDetectionType?.defaultJudgement || [];
    const stdLabel = defaultJudgement.length > 0 ? defaultJudgement[0] : '';
    const actualDetType = effectiveDetectionType;
    const animalCleanClass = room?.dataset.cleanClass || '';
    const animalBarrierRoomClass = room?.dataset.barrierRoomClass || '';
    const isAnimalSpecialTarget = actualDetType?.id === 'animal_room' && ['普通环境','屏障环境','隔离环境'].includes(animalCleanClass);
    const shouldSkipAnimalInlineRange = isAnimalSpecialTarget && !((animalCleanClass === '屏障环境' && (animalBarrierRoomClass === '主房间' || animalBarrierRoomClass === '洁净辅房')) || animalCleanClass === '隔离环境');
    const selfRendersRangeTypes = ['numeric','airchange','airchange_speed_only','particle_4','particle_4_051','particle_4_8','settling_control','floating_control','noise_corrected','wind_uniformity','illumination_uniformity','hepa_leak_multi','bacteria_control','bacteria_zone_control','bacteria_zone'];

    let h = '';
    (effectiveDetectionType.params||[]).forEach(p=>{
        h+=`<div class="pb" data-pk="${p.key}" data-itype="${p.inputType}" ${p.sourceKey?`data-sourcekey="${p.sourceKey}"`:''}>`;
        h+=`<div class="pb-head"><div><div class="pb-name">${p.name}</div>`;
        if(p.inputType!=='pressure_bsl'){
            const isManualRange = p.inputType === 'numeric_range_manual';
            const skipInlineRange = shouldSkipAnimalInlineRange && ['humidity','work_illumination','cage_airspeed'].includes(p.key);
            const mapped = getParamRange(rid, p.key);
            const mappedRange = mapped?.range || '';
            const mappedUnit = mapped?.unit || p.unit || '';
            const mappedStd = mapped?.standard || '';
            const isZoneRangeType = ['particle_zone','bacteria_zone','bacteria_zone_control'].includes(p.inputType);
            const isSelfRangeType = selfRendersRangeTypes.includes(p.inputType);
            const isAnimalRangeDuplicateTarget = shouldSkipAnimalInlineRange && ['humidity','work_illumination','cage_airspeed'].includes(p.key);
            const shouldRenderOuterRange = !isManualRange && !skipInlineRange && !isSelfRangeType && !isZoneRangeType;
            if(shouldRenderOuterRange) {
                const finalRange = mappedRange || '';
                const finalStd = mappedStd || stdLabel;
                if(finalRange){
                    h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;">
                        <span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span>
                        <span style="color:#2e7d32;">${finalRange} ${mappedUnit}</span>${finalStd ? ` <span style="color:#999;font-size:11px;margin-left:4px;">[${finalStd}]</span>` : ''}
                        </div>`;
                }
            }
            if(skipInlineRange && !isAnimalRangeDuplicateTarget){
                if(mappedRange){
                    h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;">
                    <span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span>
                    <span style="color:#2e7d32;">${mappedRange} ${mappedUnit}</span>${mappedStd ? ` <span style="color:#999;font-size:11px;margin-left:4px;">[${mappedStd}]</span>` : ''}
                    </div>`;
                }
            }
            const finalRangeOp = mapped?.range_op || '';
            const finalRangeSurr = mapped?.range_surr || '';
            if(finalRangeOp && !isZoneRangeType) {
                h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;">
                    <span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span>
                    ${p.zone_label_op||'手术区'}:<span style="color:#2e7d32;">${finalRangeOp}</span> |
                    ${p.zone_label_surr||'周边区'}:<span style="color:#2e7d32;">${finalRangeSurr}</span>${mappedStd || stdLabel ? ` <span style="color:#999;font-size:11px;margin-left:4px;">[${mappedStd || stdLabel}]</span>` : ''}
                    </div>`;
            }
            if(p.calc&&p.calc!=='/') h+=`<div class="pb-calc">计算:${p.calc}</div>`;
        }
        h+=`</div></div>`;
        h+=renderInput(rid,p);
        if(p.inputType!=='pressure_bsl' && p.inputType!=='hepa_leak_multi'){
            h+=`<div class="cr"><span>结果:</span><span class="cv" data-res="${p.key}">-</span></div>`;
        }
        h+=`</div>`;
    });
    room.querySelector('.rparams').innerHTML = h;
    const topDimsBlock = room.querySelector('[data-room-size-block]');
    const paramsTop = room.querySelector('.rparams-top');
    if(topDimsBlock && paramsTop){
        if(topDimsBlock.parentElement !== paramsTop){
            paramsTop.appendChild(topDimsBlock);
        }
        topDimsBlock.style.display = h ? 'block' : 'none';
    }
    bindRoomParamAutoCalc(rid);
    if(detectionType && detectionType.id === 'pass_box'){
        room.dataset.passBoxParamsReady = h ? 'true' : 'false';
        updateRoomSummary(rid);
    }
    if(detectionType && detectionType.id === 'electronics_workshop'){
        const hasManualControls = room.querySelectorAll('.pb[data-itype="numeric_range_manual"]').length > 0;
        room.dataset.electronicsParamsReady = hasManualControls ? 'true' : 'false';
        if(!hasManualControls){
            room.dataset.electronicsManualRangeKeys = '[]';
            room.dataset.electronicsManualSource = '';
        }
        updateRoomSummary(rid);
    }
}

function bindRoomParamAutoCalc(rid){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return;
    room.querySelectorAll('.pb').forEach(pb=>{
        const pk = pb.dataset.pk;
        const itype = pb.dataset.itype || '';
        if(!pk) return;
        const trigger = () => {
            if(itype === 'numeric' || itype === 'numeric_range_manual') return calc_numeric(rid, pk);
            if(itype === 'airchange') return calc_airchange(rid, pk);
            if(itype === 'particle_zone') return calc_pzone(rid, pk);
            if(itype === 'particle_4') return calc_p4(rid, pk);
            if(itype === 'particle_4_051') return calc_p4_051(rid, pk);
            if(itype === 'particle_4_8') return calc_p4_8(rid, pk);
            if(itype === 'bacteria_zone') return calc_bzone(rid, pk);
            if(itype === 'settling') return calc_settling(rid, pk);
            if(itype === 'floating') return calc_floating(rid, pk);
            if(itype === 'bacteria_control') return calc_bacteria_control(rid, pk);
            if(itype === 'bacteria_zone_control') return calc_bacteria_zone_control(rid, pk);
            if(itype === 'settling_control') return calc_settling_control(rid, pk);
            if(itype === 'floating_control') return calc_floating_control(rid, pk);
            if(itype === 'noise_corrected') return calc_noise(rid, pk);
        };
        pb.querySelectorAll('input').forEach(input=>{
            if(input.dataset.boundAutoCalc === 'true') return;
            input.dataset.boundAutoCalc = 'true';
            input.addEventListener('input', trigger);
            input.addEventListener('change', trigger);
        });
    });
}


function renderRoomBasis(rid, domain, detType){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const standards = SYSTEM_DB.basis[domain] || [];
    const saved = JSON.parse(card.dataset.basisChecked || '[]');
    const defaults = saved.length > 0 ? saved : (detType.defaultBasis || []);

    let h = '';
    standards.forEach(s => {
        const checked = defaults.includes(s.code);
        h += `<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #f0f0f0;">
            <input type="checkbox" data-rb-code="${s.code}" ${checked?'checked':''} onchange="updateRoomBasisSummary('${rid}')">
            <span style="font-size:12px;"><span style="color:#1976d2;font-weight:500;">${s.code}</span> ${s.name}</span>
        </div>`;
    });

    card.querySelector('.rb-body').innerHTML = h;
    updateRoomBasisSummary(rid);
}

function toggleRoomBasis(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const body = card.querySelector('.rb-body');
    const arrow = card.querySelector('.rb-arrow');
    if(body.style.display === 'none'){
        body.style.display = 'block';
        arrow.textContent = '▲';
        card.dataset.basisExpanded = 'true';
    } else {
        body.style.display = 'none';
        arrow.textContent = '▼';
        card.dataset.basisExpanded = 'false';
    }
    updateRoomBasisSummary(rid);
}

function updateRoomBasisSummary(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const checked = card.querySelectorAll('[data-rb-code]:checked');
    const summary = card.querySelector('.rb-summary');
    if(checked.length > 0){
        const codes = Array.from(checked).map(c => c.dataset.rbCode);
        card.dataset.basisChecked = JSON.stringify(codes);
        card.dataset.basisPrimary = codes[0] || '';
        summary.textContent = '(' + codes.join('、') + ')';
    } else {
        card.dataset.basisChecked = '[]';
        card.dataset.basisPrimary = '';
        summary.textContent = '';
    }
    updateRoomSummary(rid);
}

function selRoomType(rid, typeId){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const domain = card.dataset.domain;
    const types = SYSTEM_DB.detectionTypes[domain] || [];
    const detType = types.find(t => t.id === typeId);
    if(!detType) return;

    // 同领域同检测类型限制：已有房间选了检测类型时，新房间必须选同一类型
    const existingTypeId = Array.from(document.querySelectorAll('.room-card')).find(c => c.dataset.rid !== rid && c.dataset.typeId)?.dataset?.typeId || '';
    if(existingTypeId && existingTypeId !== typeId){
        const existingTypeName = Array.from(document.querySelectorAll('.room-card')).find(c => c.dataset.rid !== rid && c.dataset.typeId)?.dataset?.typeName || existingTypeId;
        showToast(`同一项目内只能添加相同检测类型的房间（当前已有：${existingTypeName}）`, 'error');
        return;
    }

    // 高亮选中的检测类型按钮
    card.querySelectorAll('.level-grid')[0]?.querySelectorAll('.level-btn').forEach(b => {
        b.classList.remove('active');
        if(b.getAttribute('onclick')?.includes("'"+typeId+"'")) b.classList.add('active');
    });

    const topDims = card.querySelector('[data-room-dimensions]');
    const topDimsBlock = card.querySelector('[data-room-size-block]');
    if(topDims && topDimsBlock){
        topDims.style.display = 'flex';
        topDimsBlock.style.display = 'none';
    }

    // 存储房间的检测类型
    card.dataset.typeId = typeId;
    card.dataset.typeName = detType.name;
    card.dataset.businessDomainHint = (typeId === 'pass_box' || typeId === 'laminar_hood') ? 'pharma' : '';
    delete card.dataset.equipmentAlias;
    delete card.dataset.bsl;
    delete card.dataset.cleanFunctionSubroom;
    delete card.dataset.surgeryRoomType;
    delete card.dataset.surgeryAuxRoom;
    delete card.dataset.surgeryAuxCleanClass;
    delete card.dataset.barrierRoomClass;
    delete card.dataset.barrierAuxRoom;
    delete card.dataset.cleanClass;
    delete card.dataset.levelName;
    delete card.dataset.levelIdx;
    delete card.dataset.animalContextIncomplete;
    card.dataset.basisChecked = '[]';
    card.dataset.basisPrimary = '';
    card.dataset.judgementPriority = '[]';
    card.dataset.judgementChecked = '[]';
    card.dataset.judgementActive = '[]';
    card.dataset.passBoxJudgementActive = '[]';
    card.dataset.passBoxJudgementSource = '';
    card.dataset.passBoxParamsReady = 'false';
    card.dataset.passBoxResultState = '';
    card.dataset.electronicsManualSource = '';
    card.dataset.electronicsParamsReady = 'false';
    delete card.dataset.legacyPressurePairSummarySource_pressure;
    delete card.dataset.pressurePairCarrier_pressure;
    card.dataset.basisExpanded = 'false';
    card.dataset.judgementExpanded = 'false';
    delete card.dataset.hepaLeakSummary;
    card.dataset.electronicsManualRangeKeys = '[]';

    card.querySelector('.room-surgery-type-options').innerHTML = '';
    card.querySelector('.room-surgery-aux-options').innerHTML = '';
    card.querySelector('.room-barrier-room-class-options').innerHTML = '';
    card.querySelector('.room-barrier-aux-options').innerHTML = '';

    // 渲染洁净等级选项
    const cleanOptions = (Array.isArray(detType.cleanClassOptions) && detType.cleanClassOptions.length > 0)
        ? detType.cleanClassOptions
        : ((['pass_box', 'laminar_hood', 'bsc', 'clean_bench', 'ivc'].includes(typeId)) ? [] : (SYSTEM_DB.cleanClassOptions[domain] || []));
    const cleanLabel = detType.cleanClassLabel || '洁净等级';
    const isBslCleanClass = typeId === 'bsl' && cleanOptions.length === 5;
    const cleanGridClass = isBslCleanClass ? 'single-line-level-grid' : (cleanOptions.length === 4 ? 'single-line-level-grid single-line-level-grid-4' : 'level-grid');
    const cleanHtml = cleanOptions.length > 0
        ? `<label style="font-size:13px;font-weight:500;color:#555;display:block;margin-bottom:6px;">${cleanLabel}:</label><div class="${cleanGridClass}">${cleanOptions.map(opt => `<div class="level-btn" onclick="selCleanClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`
        : '';
    card.querySelector('.room-clean-options').innerHTML = cleanHtml;

    const barrierRoomClassHtml = (detType.id === 'animal_room' && Array.isArray(detType.barrierRoomClassOptions) && (card.dataset.cleanClass || '') === '屏障环境')
        ? `<label style="font-size:13px;font-weight:500;color:#555;">${detType.barrierRoomClassLabel || '房间类别'}:</label><div class="level-grid">${detType.barrierRoomClassOptions.map(opt => `<div class="level-btn" onclick="selBarrierRoomClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`
        : '';
    card.querySelector('.room-barrier-room-class-options').innerHTML = barrierRoomClassHtml;
    card.querySelector('.room-barrier-aux-options').innerHTML = '';
    delete card.dataset.barrierRoomClass;
    delete card.dataset.barrierAuxRoom;

    // 手术室房间类型选项
    if(detType.id === 'operating_room' && Array.isArray(detType.surgeryRoomTypeOptions)){
        const stLabel = detType.surgeryRoomTypeLabel || '房间类型';
        card.querySelector('.room-surgery-type-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">${stLabel}:</label><div class="level-grid">${detType.surgeryRoomTypeOptions.map(opt => `<div class="level-btn" onclick="selSurgeryRoomType('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
        // operating_room 选房间类型后再显示等级,初始隐藏等级
        card.querySelector('.room-clean-options').innerHTML = '';
    } else if(detType.id === 'clean_function_room' && Array.isArray(detType.subroomOptions)) {
        const subLabel = detType.subroomLabel || '子房间类型';
        card.querySelector('.room-surgery-type-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">${subLabel}:</label><div class="level-grid">${detType.subroomOptions.map(opt => `<div class="level-btn" onclick="selCleanFunctionSubroom('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
        card.querySelector('.room-clean-options').innerHTML = '';
    } else if(Array.isArray(detType.equipmentOptions) && detType.equipmentOptions.length > 0) {
        const equipLabel = detType.equipmentLabel || '设备类型';
        card.querySelector('.room-surgery-type-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">${equipLabel}:</label><div class="level-grid">${detType.equipmentOptions.map(opt => `<div class="level-btn" onclick="selEquipmentAlias('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
    } else {
        card.querySelector('.room-surgery-type-options').innerHTML = '';
    }
    delete card.dataset.surgeryRoomType;
    delete card.dataset.cleanFunctionSubroom;

    // 手术室辅房选项初始化
    card.querySelector('.room-surgery-aux-options').innerHTML = '';
    delete card.dataset.surgeryAuxRoom;
    delete card.dataset.surgeryAuxCleanClass;

    // 渲染BSL等级选项(仅生物安全领域,但排除动物房)
    const bslOptions = detType.bslClassOptions !== undefined ? detType.bslClassOptions : ((SYSTEM_DB.bslOptions && SYSTEM_DB.bslOptions[domain] && detType.id !== 'animal_room') ? SYSTEM_DB.bslOptions[domain] : []);
    const bslHtml = bslOptions.length > 0
        ? `<label style="font-size:13px;font-weight:500;color:#555;display:block;margin-bottom:6px;">生物安全等级:</label><div class="level-grid single-line-level-grid single-line-level-grid-4">${bslOptions.map(opt => `<div class="level-btn" onclick="selBSL('${rid}','${opt}')">${opt}</div>`).join('')}</div>`
        : '';
    card.querySelector('.room-bsl-options').innerHTML = bslHtml;

    // 如果只有一个等级选项(如"无等级要求"),自动选中
    if(cleanOptions.length === 1){
        card.dataset.cleanClass = cleanOptions[0];
        card.dataset.levelName = cleanOptions[0];
        card.dataset.levelIdx = 0;
        setTimeout(()=>{
            const btn = card.querySelector('.room-clean-options .level-btn');
            if(btn) btn.classList.add('active');
        }, 0);
    }

    // 渲染检测依据
    card.querySelector('.room-basis').style.display = '';
    renderRoomBasis(rid, domain, detType);

    // 渲染判定标准
    card.querySelector('.room-judgement').style.display = '';
    renderRoomJudgementForType(rid, domain, detType);

    // 先把默认依据同步到数据集，避免首次选级时 basisChecked 仍为空
    updateRoomBasisSummary(rid);

    // 不立即渲染参数,等待选择洁净等级或房间类型
    const topDimsBlockInit = card.querySelector('[data-room-size-block]');
    if(topDimsBlockInit) topDimsBlockInit.style.display = 'none';
    if(detType.id === 'operating_room'){
        card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择房间类型和洁净等级</p>';
    } else if(typeId === 'bsl' && bslOptions.length > 0){
        if(detType.params){
            renderParamsForRoom(rid, detType);
        } else {
            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择生物安全等级</p>';
        }
    } else if(cleanOptions.length > 1){
        card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择洁净等级</p>';
    } else if(cleanOptions.length === 1){
        // 只有一个等级选项,自动渲染参数
        if(detType.levelParams && detType.levelParams[cleanOptions[0]]){
            const levelParams = detType.levelParams[cleanOptions[0]];
            const tempType = { ...detType, params: levelParams };
            renderParamsForRoom(rid, tempType);
        } else if(detType.params){
            renderParamsForRoom(rid, detType);
        }
    } else if(['pass_box', 'laminar_hood', 'bsc', 'clean_bench', 'ivc'].includes(detType.id) && detType.params){
        // 设备类对象无等级,直接渲染参数区
        renderParamsForRoom(rid, detType);
    } else if(bslOptions.length > 0){
        card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择生物安全等级</p>';
    } else {
        // 没有等级选项,直接渲染参数
        if(detType.params){
            renderParamsForRoom(rid, detType);
        } else {
            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 该检测类型暂无参数配置</p>';
        }
    }

    if((detType.id === 'pass_box' || detType.id === 'laminar_hood') && !card.dataset.businessDomainHint){
        card.dataset.businessDomainHint = 'pharma';
    }
    updateRoomSummary(rid);
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

function syncAnimalRoomContextSummary(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const detType = getRoomDetType(rid);
    if(!detType || detType.id !== 'animal_room') return;
    const cleanClass = card.dataset.cleanClass || card.dataset.levelName || '';
    const barrierRoomClass = card.dataset.barrierRoomClass || '';
    if(cleanClass !== '屏障环境'){
        delete card.dataset.barrierRoomClass;
        delete card.dataset.barrierAuxRoom;
    }
    if((card.dataset.barrierRoomClass || '') !== '洁净辅房'){
        delete card.dataset.barrierAuxRoom;
    }
    const contextIncomplete = isAnimalBarrierContextIncomplete(card);
    if(contextIncomplete){
        card.dataset.animalContextIncomplete = 'true';
        card.dataset.basisExpanded = 'false';
        card.dataset.judgementExpanded = 'false';
        card.dataset.basisChecked = '[]';
        card.dataset.basisPrimary = '';
        card.dataset.judgementPriority = '[]';
        card.dataset.judgementChecked = '[]';
        card.dataset.judgementActive = '[]';
        card.dataset.basisExpanded = 'false';
        card.dataset.judgementExpanded = 'false';
        const rbSummary = card.querySelector('.rb-summary');
        const rjSummary = card.querySelector('.rj-summary');
        const rbArrow = card.querySelector('.rb-arrow');
        const rjArrow = card.querySelector('.rj-arrow');
        if(rbSummary) rbSummary.textContent = '';
        if(rjSummary) rjSummary.textContent = '';
        if(rbArrow) rbArrow.textContent = '▼';
        if(rjArrow) rjArrow.textContent = '▼';
        card.querySelectorAll('.pb .cv[data-res]').forEach(resEl => {
            resEl.textContent = '-';
            resEl.style.color = '';
            resEl.style.fontWeight = '';
        });
        card.querySelectorAll('.pb').forEach(pb => {
            const pk = pb.dataset.pk || '';
            const itype = pb.dataset.itype || '';
            const keepAnimalContextValue = ['numeric_range_manual'].includes(itype);
            if(pb.closest('[data-pk="pressure"]')) return;
            pb.querySelectorAll('input').forEach(input => {
                if(input.type === 'checkbox' || input.type === 'radio' || input.type === 'button' || input.type === 'submit') return;
                if(keepAnimalContextValue && (input.hasAttribute('data-manual-range') || input.hasAttribute('data-mr-min') || input.hasAttribute('data-mr-max'))) return;
                input.value = '';
            });
            pb.querySelectorAll('select').forEach(sel => sel.selectedIndex = 0);
            pb.querySelectorAll('textarea').forEach(ta => ta.value = '');
            if(pk){
                delete card.dataset[`pressurePairSummary_${pk}`];
            }
        });
        delete card.dataset.hepaLeakSummary;
        delete card.dataset.hepaLeakSummarySource;
        delete card.dataset.animalIlluminationSource;
        const rparams = card.querySelector('.rparams');
        if(rparams){
            if(cleanClass === '屏障环境' && !barrierRoomClass){
                rparams.innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择房间类别</p>';
            } else if(barrierRoomClass === '洁净辅房' && !card.dataset.barrierAuxRoom){
                rparams.innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择洁净辅房名称</p>';
            } else {
                rparams.innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 当前屏障环境上下文未完成</p>';
            }
        }
        card.querySelectorAll('.pb[data-itype="numeric_range_manual"]').forEach(pb => {
            const pk = pb.dataset.pk || '';
            if(!pk) return;
            const mrInput = pb.querySelector(`[data-manual-range="${pk}"]`);
            const preservedRange = mrInput ? mrInput.value : '';
            updateManualNumericRange(rid, pk, preservedRange);
            const firstInput = pb.querySelector(`[data-dp="${pk}"] input`);
            if(firstInput) firstInput.dispatchEvent(new Event('input',{bubbles:true}));
        });
    } else {
        card.dataset.animalContextIncomplete = 'false';
    }
    updateRoomSummary(rid);
}

function renderRoomJudgementForType(rid, domain, detType){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const standards = SYSTEM_DB.judgement[domain] || [];
    const savedPriority = JSON.parse(card.dataset.judgementPriority || '[]');
    const savedChecked = JSON.parse(card.dataset.judgementChecked || '[]');
    const defaults = savedChecked.length > 0 ? savedChecked : (detType.defaultJudgement || []);
    let priorityList = savedPriority.filter(code => standards.find(s => s.code === code));
    if(priorityList.length === 0){
        priorityList = defaults.filter(code => standards.find(s => s.code === code));
    }
    // 未在当前顺序中的标准追加到末尾
    standards.forEach(s => { if(!priorityList.includes(s.code)) priorityList.push(s.code); });
    const checkedList = priorityList.filter(code => defaults.includes(code));
    // GMP车间温湿度等页显取值依赖判定标准链，首次进入时先把默认判定同步进dataset
    card.dataset.judgementActive = JSON.stringify(checkedList);
    card.dataset.judgementPriority = JSON.stringify(priorityList);
    card.dataset.judgementChecked = JSON.stringify(checkedList);
    // 先把默认依据同步到数据集，避免首次选级时 basisChecked 仍为空
    updateRoomBasisSummary(rid);

    if((card.dataset.typeId || '') === 'pass_box'){
        const hasSavedJudgement = Array.isArray(savedChecked) && savedChecked.length > 0;
        card.dataset.passBoxJudgementSource = hasSavedJudgement ? 'saved' : '';
    }
    renderRoomJudgementList(rid, domain);
}

function renderRoomJudgementList(rid, domain){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const standards = SYSTEM_DB.judgement[domain] || [];
    const priorityList = JSON.parse(card.dataset.judgementPriority || '[]');
    const checkedList = JSON.parse(card.dataset.judgementChecked || '[]');
    const stdMap = {};
    standards.forEach(s => stdMap[s.code] = s);
    let h = '';
    priorityList.forEach((code, i) => {
        const s = stdMap[code];
        if(!s) return;
        const checked = checkedList.includes(code);
        const num = checked ? `<span style="display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;background:#1976d2;color:#fff;border-radius:50%;font-size:11px;font-weight:600;">${checkedList.indexOf(code)+1}</span>` : `<span style="display:inline-block;width:18px;height:18px;"></span>`;
        h += `<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #f0f0f0;">
            ${num}
            <input type="checkbox" data-rj-code="${code}" ${checked?'checked':''} onchange="toggleRoomJudgementCode('${rid}','${code}','${domain}')">
            <span style="font-size:12px;flex:1;"><span style="color:#1976d2;font-weight:500;">${code}</span> <span style="color:#666;">${s.name}</span></span>
            <button onclick="moveJudgementPriority('${rid}','${code}','${domain}',-1)" style="padding:1px 6px;font-size:12px;border:1px solid #ddd;border-radius:3px;background:#f5f5f5;cursor:pointer;${i===0?'opacity:0.3;pointer-events:none;':''}" title="上移">↑</button>
            <button onclick="moveJudgementPriority('${rid}','${code}','${domain}',1)" style="padding:1px 6px;font-size:12px;border:1px solid #ddd;border-radius:3px;background:#f5f5f5;cursor:pointer;${i===priorityList.length-1?'opacity:0.3;pointer-events:none;':''}" title="下移">↓</button>
        </div>`;
    });
    card.querySelector('.rj-body').innerHTML = h;
    updateRoomJudgementSummary(rid);
}

function toggleRoomJudgementCode(rid, code, domain){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    let checkedList = JSON.parse(card.dataset.judgementChecked || '[]');
    if(checkedList.includes(code)){
        checkedList = checkedList.filter(c => c !== code);
    } else {
        // 按优先级顺序插入
        const priorityList = JSON.parse(card.dataset.judgementPriority || '[]');
        const newChecked = priorityList.filter(c => checkedList.includes(c) || c === code);
        checkedList = newChecked;
    }
    card.dataset.judgementChecked = JSON.stringify(checkedList);
    if((card.dataset.typeId || '') === 'pass_box'){
        card.dataset.passBoxJudgementSource = 'live';
    }
    renderRoomJudgementList(rid, domain);
    updateRoomRangesByPriority(rid);
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

function toggleRoom(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    card.classList.toggle('collapsed');
    updateRoomSummary(rid);
}

function getPassBoxResultState(card){
    if(!card || (card.dataset.typeId || '') !== 'pass_box') return '';
    const savedState = card.dataset.passBoxResultState || '';
    const resultEls = Array.from(card.querySelectorAll('.pb .cv[data-res]'));
    if(resultEls.length === 0) return savedState;
    const values = resultEls.map(el => (el.textContent || '').trim()).filter(Boolean);
    if(values.length === 0) return savedState;
    const effective = values.filter(v => v !== '-');
    if(effective.length === 0) return savedState;
    const allPass = effective.every(v => v.includes('✅') || v === '合格');
    const anyFail = effective.some(v => v.includes('❌') || v === '不合格');
    if(allPass) return '合格';
    if(anyFail) return '不合格';
    return '待定';
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

function syncPassBoxResultState(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card || (card.dataset.typeId || '') !== 'pass_box') return;
    const livePbCount = card.querySelectorAll('.pb').length;
    if(livePbCount > 0){
        card.dataset.passBoxParamsReady = 'true';
    } else {
        delete card.dataset.passBoxParamsReady;
    }
    const passBoxHasParams = livePbCount > 0;
    if(!passBoxHasParams){
        card.dataset.passBoxJudgementActive = '[]';
        card.dataset.passBoxJudgementSource = '';
        card.dataset.passBoxResultState = '';
        delete card.dataset.hepaLeakSummary;
        delete card.dataset.hepaLeakSummarySource;
        delete card.dataset.hepaLeakSourceState;
        updateRoomSummary(rid);
        return;
    }
    card.dataset.passBoxResultState = getPassBoxResultState(card);
    const hepaResultText = (card.querySelector(`[data-res="hepa_leak"]`)?.textContent || '').trim();
    if(!hepaResultText || hepaResultText === '-'){
        delete card.dataset.hepaLeakSummary;
        delete card.dataset.hepaLeakSummarySource;
        delete card.dataset.hepaLeakSourceState;
    }
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

function updateRoomSummary(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const summaryToggleBtn = card.querySelector('.room-summary .room-inline-toggle');
    if(summaryToggleBtn) summaryToggleBtn.textContent = card.classList.contains('collapsed') ? '展开 ▼' : '折叠 ▲';
    const headerToggleBtn = card.querySelector('.room-body .room-inline-toggle');
    if(headerToggleBtn) headerToggleBtn.textContent = card.classList.contains('collapsed') ? '展开 ▼' : '折叠 ▲';
    const name = card.querySelector('.rname')?.value || '未命名房间';
    const typeName = card.dataset.typeName || '';
    const level = card.dataset.cleanClass || card.dataset.levelName || '';
    const cleanFunctionSubroom = card.dataset.cleanFunctionSubroom || '';
    const surgeryRoomType = card.dataset.surgeryRoomType || '';
    const surgeryAuxRoom = card.dataset.surgeryAuxRoom || '';
    const barrierRoomClass = card.dataset.barrierRoomClass || '';
    const barrierAuxRoom = card.dataset.barrierAuxRoom || '';
    const bsl = card.dataset.bsl || '';
    const savedAnimalContextIncomplete = card.dataset.animalContextIncomplete === 'true';
    const liveAnimalContextIncomplete = isAnimalBarrierContextIncomplete(card);
    const animalContextIncomplete = liveAnimalContextIncomplete || savedAnimalContextIncomplete;
    const pressurePairSummary = card.dataset.pressurePairSummary_pressure || '';
    const pressurePairCarrier = card.dataset.pressurePairCarrier_pressure === 'true';
    const hepaLeakSummary = card.dataset.hepaLeakSummary || '';
    const hepaLeakSummarySource = card.dataset.hepaLeakSummarySource || '';
    const hepaLeakSourceState = card.dataset.hepaLeakSourceState || '';
    const animalIlluminationSource = card.dataset.animalIlluminationSource || '';
    const bacteriaControlSource = card.dataset.resultSource_bacteria_control || '';
    const bacteriaZoneControlSource = card.dataset.resultSource_bacteria_zone_control || '';
    const settlingControlSource = card.dataset.resultSource_settling_control || '';
    const floatingControlSource = card.dataset.resultSource_floating_control || '';
    const windUniformitySource = card.dataset.resultSource_wind_uniformity || '';
    const illuminationUniformitySource = card.dataset.resultSource_illumination_uniformity || '';
    const basisChecked = JSON.parse(card.dataset.basisChecked || '[]');
    const basisPrimary = card.dataset.basisPrimary || basisChecked[0] || '';
    const judgementActive = JSON.parse(card.dataset.judgementActive || '[]');
    const activeJudgementCode = judgementActive[0] || '';
    const basisExpanded = card.dataset.basisExpanded === 'true';
    const judgementExpanded = card.dataset.judgementExpanded === 'true';
    const passBoxJudgementActive = JSON.parse(card.dataset.passBoxJudgementActive || '[]');
    card.querySelector('.room-summary-name').textContent = name;
    const parts = [];
    if(typeName) parts.push(typeName);
    if((card.dataset.typeId || '') === 'pass_box') parts.push('设备类:传递窗');
    if((card.dataset.typeId || '') === 'laminar_hood') parts.push('设备类:层流罩');
    if((card.dataset.businessDomainHint || '') === 'pharma' && (card.dataset.typeId || '') === 'pass_box') parts.push('归属:制药');
    if((card.dataset.businessDomainHint || '') === 'pharma' && (card.dataset.typeId || '') === 'laminar_hood') parts.push('归属:制药');
    const passBoxHasParams = (card.dataset.typeId || '') === 'pass_box' && card.querySelectorAll('.pb').length > 0;
    const passBoxResultState = passBoxHasParams ? getPassBoxResultState(card) : '';
    const passBoxResultEls = Array.from(card.querySelectorAll('.pb .cv[data-res]'));
    const passBoxUsingSavedFallback = (card.dataset.typeId || '') === 'pass_box' && passBoxHasParams && passBoxResultEls.length === 0 && !!(card.dataset.passBoxResultState || '');
    const electronicsManualRangeKeys = [];
    if((card.dataset.typeId || '') === 'electronics_workshop'){
        card.querySelectorAll('.pb[data-itype="numeric_range_manual"]').forEach(pb => {
            const pk = pb.dataset.pk || '';
            const manualRange = pb.querySelector(`[data-manual-range="${pk}"]`)?.value || '';
            const manualMin = pb.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
            const manualMax = pb.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
            if(manualRange || manualMin || manualMax) electronicsManualRangeKeys.push(pk);
        });
    }
    if((card.dataset.typeId || '') === 'pass_box' && passBoxJudgementActive.length > 0) parts.push('判定链:有效');
    if((card.dataset.typeId || '') === 'pass_box' && passBoxJudgementActive[0]) parts.push(`传递窗主判:${passBoxJudgementActive[0]}`);
    if((card.dataset.typeId || '') === 'pass_box' && (card.dataset.passBoxParamsReady || '') === 'true' && !passBoxHasParams) parts.push('参数区:回填');
    if((card.dataset.typeId || '') === 'pass_box' && !passBoxHasParams && (passBoxJudgementActive.length > 0 || passBoxResultState)) parts.push('参数区:回填');
    if(passBoxHasParams) parts.push('参数区:已建立');
    if((card.dataset.typeId || '') === 'pass_box' && passBoxResultState) parts.push(`结果:${passBoxResultState}`);
    if(passBoxUsingSavedFallback || (!passBoxResultEls.length && !!passBoxResultState)) parts.push('结果源:回填');
    if((card.dataset.typeId || '') === 'pass_box' && passBoxResultState && !passBoxHasParams) parts.push('结果待落参数区');
    const electronicsSavedManualKeys = JSON.parse(card.dataset.electronicsManualRangeKeys || '[]');
    const electronicsManualKeysForSummary = electronicsManualRangeKeys.length > 0 ? electronicsManualRangeKeys : electronicsSavedManualKeys;
    if((card.dataset.typeId || '') === 'electronics_workshop' && electronicsManualKeysForSummary.length > 0) parts.push(`手动优先:${electronicsManualKeysForSummary.join('/')}`);
    if(surgeryRoomType) parts.push(surgeryRoomType);
    if(surgeryAuxRoom) parts.push(surgeryAuxRoom);
    if(cleanFunctionSubroom) parts.push(`子房间:${cleanFunctionSubroom}`);
    if(barrierRoomClass) parts.push(`房间类:${barrierRoomClass}`);
    if(barrierAuxRoom) parts.push(`辅房:${barrierAuxRoom}`);
    if(bsl) parts.push(`BSL:${bsl}`);
    if(animalContextIncomplete) parts.push('屏障链:未完成');
    if((card.dataset.typeId || '') === 'animal_room' && savedAnimalContextIncomplete && !liveAnimalContextIncomplete) parts.push('屏障链:回填');
    if((card.dataset.typeId || '') === 'animal_room' && liveAnimalContextIncomplete) parts.push('屏障链:实时');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true') parts.push('依据判定:封锁');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && !((card.dataset.barrierRoomClass || '') || (card.dataset.barrierAuxRoom || ''))) parts.push('上下文节点:待选');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.cleanClass || '') === '屏障环境' && (card.dataset.barrierRoomClass || '') === '洁净辅房' && !(card.dataset.barrierAuxRoom || '')) parts.push('洁净辅房:待选');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && JSON.parse(card.dataset.judgementActive || '[]').length > 0) parts.push('激活判定残留');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && (card.dataset.hepaLeakSummary || '')) parts.push('高效检漏残留');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && (card.dataset.pressurePairSummary_pressure || '')) parts.push('压差摘要残留');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && (card.dataset.passBoxResultState || '')) parts.push('结果状态残留');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && JSON.parse(card.dataset.electronicsManualRangeKeys || '[]').length > 0) parts.push('手动键残留');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && JSON.parse(card.dataset.passBoxJudgementActive || '[]').length > 0) parts.push('传递窗判定残留');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '')) parts.push(`子房间:${card.dataset.cleanFunctionSubroom}`);
    if((card.dataset.typeId || '') === 'clean_function_room' && !(card.dataset.cleanFunctionSubroom || '')) parts.push('子房间:待选');
    if(isCleanFunctionChainClosed(card)) parts.push('子房间链:闭合');
    if(isCleanFunctionAcceptanceState(card)) parts.push('子房间链:验收态');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '')) parts.push(`房型:${card.dataset.surgeryRoomType}`);
    if((card.dataset.typeId || '') === 'operating_room' && !(card.dataset.surgeryRoomType || '')) parts.push('房型:待选');
    if(isOperatingChainClosed(card)) parts.push('房型链:闭合');
    if(isOperatingAcceptanceState(card)) parts.push('房型链:验收态');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.restoreStage || '')) parts.push(`恢复:${card.dataset.restoreStage}`);
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') === '洁净辅房' && !(card.dataset.surgeryAuxRoom || '')) parts.push('辅房名称:待选');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') === '洁净辅房' && (card.dataset.surgeryAuxRoom || '') && !(card.dataset.cleanClass || '')) parts.push('辅房等级:待选');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') && !(card.dataset.cleanClass || '') && (card.dataset.surgeryRoomType || '') !== '洁净辅房') parts.push('手术等级:待选');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') && !(card.dataset.cleanClass || '') && (basisChecked.length > 0 || judgementActive.length > 0)) parts.push('等级未定却有判定链');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') && !(card.dataset.cleanClass || '') && (activeJudgementCode || pressurePairSummary)) parts.push('等级未定却有激活链');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') && !(card.dataset.cleanClass || '') && card.querySelectorAll('.pb').length > 0) parts.push('等级未定却有参数区');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') && !(card.dataset.cleanClass || '') && ((card.dataset.basisExpanded || '') === 'true' || (card.dataset.judgementExpanded || '') === 'true')) parts.push('等级未定却有展开态');
    if((card.dataset.typeId || '') === 'operating_room' && (card.dataset.surgeryRoomType || '') && (card.dataset.cleanClass || '')) parts.push('手术室链:闭合');
    if(isOperatingAcceptanceState(card)) parts.push('手术室链:验收态');
    if(hasAnimalReverseAnomaly(card)) parts.push('动物房链:逆向异常');
    if(isAnimalAcceptanceState(card)) parts.push('动物房链:验收态');
    if(isAnimalReadyMissing(card)) parts.push('动物房链:ready缺失');
    if(isAnimalChainClosed(card)) parts.push('动物房链:闭合');
    
    if(hasCleanFunctionReverseAnomaly(card)) parts.push('洁净功能链:逆向异常');
    if(isCleanFunctionAcceptanceState(card)) parts.push('洁净功能链:验收态');
    if(isCleanFunctionReadyMissing(card)) parts.push('洁净功能链:ready缺失');
    if(isCleanFunctionChainClosed(card)) parts.push('洁净功能链:闭合');
    if(hasOperatingReverseAnomaly(card)) parts.push('手术室链:逆向异常');
    if(isOperatingAcceptanceState(card)) parts.push('手术室链:验收态');
    if(isOperatingReadyMissing(card)) parts.push('手术室链:ready缺失');
    if(isOperatingChainClosed(card)) parts.push('手术室链:闭合');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '') && !(card.dataset.cleanClass || '') && (basisChecked.length > 0 || judgementActive.length > 0 || activeJudgementCode)) parts.push('回填后待清理');
    if((card.dataset.typeId || '') === 'clean_function_room' && !(card.dataset.cleanFunctionSubroom || '') && (basisChecked.length > 0 || judgementActive.length > 0)) parts.push('子房间未定却有判定链');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '') && !(card.dataset.cleanClass || '') && (basisChecked.length > 0 || judgementActive.length > 0)) parts.push('等级未定却有判定链');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '') && !(card.dataset.cleanClass || '') && (activeJudgementCode || pressurePairSummary)) parts.push('等级未定却有激活链');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '') && !(card.dataset.cleanClass || '') && ((card.dataset.basisExpanded || '') === 'true' || (card.dataset.judgementExpanded || '') === 'true')) parts.push('等级未定却有展开态');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '') && !(card.dataset.cleanClass || '') && card.querySelectorAll('.pb').length > 0) parts.push('等级未定却有参数区');
    if((card.dataset.typeId || '') === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '') && !(card.dataset.cleanClass || '')) parts.push('洁净等级:待选');
    if((card.dataset.typeId || '') === 'animal_room' && (card.dataset.animalContextIncomplete || '') === 'true' && ((card.dataset.basisExpanded || '') === 'true' || (card.dataset.judgementExpanded || '') === 'true')) parts.push('展开态异常');
    if(pressurePairSummary) parts.push(`压差链:${pressurePairSummary}`);
    if((card.dataset.typeId || '') === 'bsl' && pressurePairCarrier && !card.querySelector('.pb[data-pk="pressure"]')) parts.push('压差参数区:回填');
    if((card.dataset.typeId || '') === 'bsl' && pressurePairCarrier) parts.push('压差参数区:已建立');
    if((card.dataset.typeId || '') === 'bsl' && pressurePairSummary && !pressurePairCarrier) parts.push('压差待落参数区');
    if((card.dataset.typeId || '') === 'animal_room' && animalIlluminationSource === 'live') parts.push('动物照度源:实时');
    if((card.dataset.typeId || '') === 'animal_room' && animalIlluminationSource === 'saved') parts.push('动物照度源:回填');
    if((card.dataset.typeId || '') === 'animal_room' && card.querySelector('[data-pk="animal_illumination"]') && !animalIlluminationSource && ['普通环境','隔离环境','屏障环境'].includes(level)) parts.push('动物照度源:标准');
    if(bacteriaControlSource === 'live') parts.push('细菌浓度态:实时');
    if(bacteriaControlSource === 'saved') parts.push('细菌浓度态:回填');
    if(bacteriaZoneControlSource === 'live') parts.push('分区细菌态:实时');
    if(bacteriaZoneControlSource === 'saved') parts.push('分区细菌态:回填');
    if(settlingControlSource === 'live') parts.push('沉降菌态:实时');
    if(settlingControlSource === 'saved') parts.push('沉降菌态:回填');
    if(floatingControlSource === 'live') parts.push('浮游菌态:实时');
    if(floatingControlSource === 'saved') parts.push('浮游菌态:回填');
    if(windUniformitySource === 'live') parts.push('风速不均匀度态:实时');
    if(windUniformitySource === 'saved') parts.push('风速不均匀度态:回填');
    if(illuminationUniformitySource === 'live') parts.push('照度均匀度态:实时');
    if(illuminationUniformitySource === 'saved') parts.push('照度均匀度态:回填');
    if(hepaLeakSummary) parts.push(`检漏:${hepaLeakSummary}`);
    if(hepaLeakSummary && hepaLeakSummarySource) parts.push(`检漏源:${hepaLeakSummarySource}`);
    if(hepaLeakSummary && hepaLeakSourceState === 'live') parts.push('检漏态:实时');
    if(hepaLeakSummary && hepaLeakSourceState === 'saved') parts.push('检漏态:回填');
    if(hepaLeakSummary && !hepaLeakSourceState) parts.push('检漏态:待核');
    if(!hepaLeakSummary && (hepaLeakSummarySource || hepaLeakSourceState)) parts.push('检漏链:异常残留');
    if(level) parts.push(level);
    if(basisChecked.length > 0) parts.push(`依据${basisChecked.length}`);
    if(basisPrimary) parts.push(`主依:${basisPrimary}`);
    if(judgementActive.length > 0) parts.push(`判定${judgementActive.length}`);
    if(activeJudgementCode) parts.push(`主判:${activeJudgementCode}`);
    const summaryResultState = card.dataset.resultState || '';
    const summaryInputResultState = card.dataset.inputResultState || '';
    const summaryJudgementReasonRaw = card.dataset.judgementReason || '';
    const summaryJudgementReason = summaryJudgementReasonRaw.length > 24
        ? summaryJudgementReasonRaw.slice(0, 24) + '…'
        : summaryJudgementReasonRaw;
    const summaryJudgementOverridden = card.dataset.judgementOverridden === 'true';
    const summaryAbnormalItems = JSON.parse(card.dataset.abnormalItems || '[]');
    const abnormalPreview = summaryAbnormalItems.slice(0, 2).map(item => {
        if(typeof item === 'string') return item;
        if(item && typeof item === 'object') return item.item_name || item.item || item.name || item.label || JSON.stringify(item);
        return '';
    }).filter(Boolean);
    if(summaryResultState) parts.push(`结果:${summaryResultState}`);
    if(summaryJudgementOverridden) parts.push(`判定覆盖:${summaryInputResultState || '是'}→${summaryResultState || '是'}`);
    if(summaryJudgementReason) parts.push(`原因:${summaryJudgementReason}`);
    if(summaryAbnormalItems.length > 0) parts.push(`异常项:${summaryAbnormalItems.length}条`);
    if(abnormalPreview.length > 0) parts.push(`异常预览:${abnormalPreview.join('、')}`);
    if(basisExpanded) parts.push('依据展开');
    if(judgementExpanded) parts.push('判定展开');
    card.querySelector('.room-summary-level').textContent = parts.length > 0 ? '(' + parts.join(' · ') + ')' : '';
}


function toggleRoomJudgement(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const body = card.querySelector('.rj-body');
    const arrow = card.querySelector('.rj-arrow');
    if(body.style.display === 'none'){
        body.style.display = 'block';
        arrow.textContent = '▲';
        card.dataset.judgementExpanded = 'true';
    } else {
        body.style.display = 'none';
        arrow.textContent = '▼';
        card.dataset.judgementExpanded = 'false';
    }
    updateRoomSummary(rid);
}

function updateRoomJudgementSummary(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    const summary = card.querySelector('.rj-summary');
    if(!summary) return;
    const priorityList = JSON.parse(card.dataset.judgementPriority || '[]');
    const checkedList = JSON.parse(card.dataset.judgementChecked || '[]');
    const activeStds = priorityList.filter(c => checkedList.includes(c));
    card.dataset.judgementActive = JSON.stringify(activeStds);
    if((card.dataset.typeId || '') === 'pass_box'){
        card.dataset.passBoxJudgementActive = JSON.stringify(activeStds);
    } else {
        card.dataset.passBoxJudgementActive = '[]';
        card.dataset.passBoxJudgementSource = '';
    }
    if(activeStds.length > 0){
        // 显示优先级序号+标准号
        const hasLiveJudgementCarrier = ((card.dataset.passBoxParamsReady || '') === 'true') && card.querySelectorAll('.pb').length > 0;
        const currentPassBoxJudgementSource = card.dataset.passBoxJudgementSource || '';
        if((card.dataset.typeId || '') === 'pass_box'){
            const passBoxJudgementActive = JSON.parse(card.dataset.passBoxJudgementActive || '[]');
            const hasSavedJudgementCarrier = Array.isArray(passBoxJudgementActive) && passBoxJudgementActive.length > 0 && !hasLiveJudgementCarrier;
            card.dataset.passBoxJudgementSource = hasLiveJudgementCarrier ? 'live' : (hasSavedJudgementCarrier && currentPassBoxJudgementSource === 'saved' ? 'saved' : '');
        }
        const names = activeStds.map((code, i) => `${['1','2','3','4','5','6','7','8'][i]||'·'}${code}`);
        summary.textContent = '(' + names.join('、') + ')';
    } else {
        summary.textContent = '';
    }
    updateRoomSummary(rid);
}

function switchRoomStar(rid, code){
    // 兼容旧调用:将code设为最高优先级并触发优先级更新
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    let priorityList = JSON.parse(card.dataset.judgementPriority || '[]');
    let checkedList = JSON.parse(card.dataset.judgementChecked || '[]');
    // 确保code已勾选
    if(!checkedList.includes(code)) checkedList.unshift(code);
    // 将code移到优先级第一位
    priorityList = [code, ...priorityList.filter(c => c !== code)];
    card.dataset.judgementPriority = JSON.stringify(priorityList);
    card.dataset.judgementChecked = JSON.stringify(checkedList);
    const domain = card.dataset.domain || currentDomain;
    renderRoomJudgementList(rid, domain);
    updateRoomRangesByPriority(rid);
}

function updateRoomRanges(rid, standardCode){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    if(((card.dataset.typeId || '') === 'pass_box' || (card.dataset.typeId || '') === 'laminar_hood') && !card.dataset.businessDomainHint) card.dataset.businessDomainHint = 'pharma';
    if(isAnimalBarrierContextIncomplete(card)) return;
    const detType = getRoomDetType(rid);
    if(!detType) return;
    const typeId = detType.id;
    const cleanClass = card.dataset.cleanClass || '';
    const barrierRoomClass = card.dataset.barrierRoomClass || '';
    const barrierAuxRoom = card.dataset.barrierAuxRoom || '';
    const surgeryAuxRoom = card.dataset.surgeryAuxRoom || '';
    const cleanFunctionSubroom = card.dataset.cleanFunctionSubroom || '';

    const ranges = SYSTEM_DB.standardRanges || {};
    const stdRanges = ranges[standardCode];
    if(!stdRanges || !stdRanges[typeId]) return;

    let rangeMap = null;
    if(typeId === 'animal_room' && cleanClass === '屏障环境' && barrierRoomClass === '洁净辅房' && barrierAuxRoom && stdRanges[typeId]['屏障环境洁净辅房'] && stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom]){
        rangeMap = stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom];
    } else if(typeId === 'clean_function_room' && cleanFunctionSubroom && stdRanges[typeId] && stdRanges[typeId][cleanFunctionSubroom]){
        rangeMap = stdRanges[typeId][cleanFunctionSubroom];
    } else if(typeId === 'operating_room'){
        rangeMap = stdRanges[typeId]?.[cleanClass] || {};
    } else if(typeId === 'clean_function_room' && !cleanFunctionSubroom){
        rangeMap = stdRanges[typeId]?.[cleanClass] || {};
    } else if(typeId === 'negative_pressure'){
        rangeMap = { ...(stdRanges[typeId]?._default || {}), ...(cleanClass && stdRanges[typeId]?.[cleanClass] ? stdRanges[typeId][cleanClass] : {}) };
        if(rangeMap.airchange && !rangeMap.airchange_polluted) rangeMap.airchange_polluted = rangeMap.airchange;
        if(rangeMap.pressure && !rangeMap.static_pressure_diff) rangeMap.static_pressure_diff = rangeMap.pressure;
    } else if(typeId === 'operating_room' && surgeryAuxRoom && stdRanges[typeId]['辅房'] && stdRanges[typeId]['辅房'][surgeryAuxRoom]){
        // 辅房:合并房间名称的基础范围 + 等级的洁净度/细菌范围
        const baseRange = stdRanges[typeId]['辅房'][surgeryAuxRoom];
        const auxCleanClass = card.dataset.surgeryAuxCleanClass || '';
        const levelRange = (auxCleanClass && stdRanges[typeId]['辅房等级'] && stdRanges[typeId]['辅房等级'][auxCleanClass]) ? stdRanges[typeId]['辅房等级'][auxCleanClass] : {};
        rangeMap = { ...baseRange, ...levelRange };
    } else if(typeId === 'operating_room' && card.dataset.surgeryRoomType === '眼科手术室' && cleanClass && stdRanges['eye_operating_room'] && stdRanges['eye_operating_room'][cleanClass]){
        rangeMap = { ...stdRanges['eye_operating_room'][cleanClass] };
        if(cleanClass === 'Ⅰ级（百级）') rangeMap.particle = { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' };
        if(cleanClass === 'Ⅱ级（千级）') rangeMap.particle = { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' };
        if(cleanClass === 'Ⅲ级（万级）') rangeMap.particle = { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' };
    } else if(typeId === 'animal_room' && cleanClass === '屏障环境' && barrierRoomClass === '洁净辅房' && barrierAuxRoom && stdRanges[typeId]['屏障环境洁净辅房'] && stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom]){
        rangeMap = stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom];
    } else if(typeId === 'animal_room' && cleanClass && stdRanges[typeId][cleanClass]){
        rangeMap = stdRanges[typeId][cleanClass];
    } else if(cleanClass && stdRanges[typeId][cleanClass]){
        rangeMap = stdRanges[typeId][cleanClass];
    } else if(stdRanges[typeId]['_default']) {
        rangeMap = stdRanges[typeId]['_default'];
    } else {
        const keys = Object.keys(stdRanges[typeId]);
        if(keys.length > 0) rangeMap = stdRanges[typeId][keys[0]];
    }
    if(!rangeMap) return;

    card.querySelectorAll('.pb').forEach(pb => {
        if(pb.dataset.pk === 'pressure') return;
        if(pb.querySelector('[data-manual-range]')) return;
        if(pb.dataset.pk === 'settling' || pb.dataset.pk === 'floating' || pb.dataset.pk === 'animal_illumination') return;
        if(pb.dataset.itype === 'settling_control' || pb.dataset.itype === 'floating_control' || pb.dataset.itype === 'numeric_range_manual') return;
        const rangeEl = pb.querySelector('.pb-range');
        if(rangeEl) rangeEl.remove();
    });

    // 动物房/医院洁净功能用房(细菌浓度沉降法)这类自渲染range的参数，需直接重渲染参数块保证前后台同步
    if(typeId === 'animal_room' || typeId === 'clean_function_room'){
        const currentDetType = getRoomDetType(rid);
        if(currentDetType){
            renderParamsForRoom(rid, currentDetType);
            return;
        }
    }

    Object.entries(rangeMap).forEach(([paramKey, rangeObj]) => {
        if(paramKey === 'pressure') return;
        const pb = card.querySelector(`[data-pk="${paramKey}"]`);
        if(!pb) return;

        if(pb.dataset.pk === 'settling' || pb.dataset.pk === 'floating' || pb.dataset.pk === 'animal_illumination') return;
        if(pb.dataset.itype === 'settling_control' || pb.dataset.itype === 'floating_control' || pb.dataset.itype === 'numeric_range_manual') return;

        const manualRangeInput = pb.querySelector(`[data-manual-range="${paramKey}"]`);
        if(manualRangeInput){
            const manualMin = pb.querySelector(`[data-mr-min="${paramKey}"]`)?.value || '';
            const manualMax = pb.querySelector(`[data-mr-max="${paramKey}"]`)?.value || '';
            const hasUserManual = manualMin !== '' || manualMax !== '';
            if(!hasUserManual && rangeObj.range) manualRangeInput.value = rangeObj.range;
            updateManualNumericRange(rid, paramKey, manualRangeInput.value || '');
            return;
        }

        let rangeHtml = `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;">`;
        rangeHtml += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span>`;
        if(rangeObj.range_op && rangeObj.range_surr){
            const isAuxRoom = card.dataset.surgeryRoomType === '洁净辅房';
            const lbl_op = isAuxRoom ? '局部' : '手术区';
            const lbl_surr = isAuxRoom ? '其他区域' : '周边区';
            rangeHtml += `${lbl_op}:<span style="color:#2e7d32;">${rangeObj.range_op}</span> | ${lbl_surr}:<span style="color:#2e7d32;">${rangeObj.range_surr}</span>`;
        } else if(rangeObj.range){
            rangeHtml += `<span style="color:#2e7d32;">${rangeObj.range}</span>`;
        }
        rangeHtml += `</div>`;

        const nameEl = pb.querySelector('.pb-name');
        if(nameEl) nameEl.insertAdjacentHTML('afterend', rangeHtml);
    });
}

// 按优先级顺序为每个参数选取第一个有range的标准,并显示来源标注
function updateRoomRangesByPriority(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    if(((card.dataset.typeId || '') === 'pass_box' || (card.dataset.typeId || '') === 'laminar_hood') && !card.dataset.businessDomainHint) card.dataset.businessDomainHint = 'pharma';
    if(isAnimalBarrierContextIncomplete(card)) return;
    const detType = getRoomDetType(rid);
    if(!detType) return;
    const typeId = detType.id;
    const cleanClass = card.dataset.cleanClass || '';
    const barrierRoomClass = card.dataset.barrierRoomClass || '';
    const barrierAuxRoom = card.dataset.barrierAuxRoom || '';
    const surgeryAuxRoom = card.dataset.surgeryAuxRoom || '';
    const cleanFunctionSubroom = card.dataset.cleanFunctionSubroom || '';
    const cleanFunctionStandardSubroom = card.dataset.cleanFunctionStandardSubroom || cleanFunctionSubroom;
    const priorityList = JSON.parse(card.dataset.judgementPriority || '[]');
    const checkedList = JSON.parse(card.dataset.judgementChecked || '[]');
    const activeStds = priorityList.filter(c => checkedList.includes(c));
    if(activeStds.length === 0) return;

    const ranges = SYSTEM_DB.standardRanges || {};

    function getRangeMap(standardCode){
        const stdRanges = ranges[standardCode];
        if(!stdRanges) return null;
        if(stdRanges['_universal']){
            const u = stdRanges['_universal'];
            if(cleanClass && u[cleanClass]) return u[cleanClass];
            if(u['_default']) return u['_default'];
            return null;
        }
        if(!stdRanges[typeId]) return null;
        if(typeId === 'animal_room'){
            if(cleanClass === '屏障环境' && barrierRoomClass === '洁净辅房' && barrierAuxRoom && stdRanges[typeId]['屏障环境洁净辅房'] && stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom]){
                return stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom];
            }
            if(cleanClass && stdRanges[typeId][cleanClass]){
                return stdRanges[typeId][cleanClass];
            }
            if(stdRanges[typeId]['_default']) return stdRanges[typeId]['_default'];
            return null;
        }
        if(typeId === 'clean_function_room' && cleanFunctionSubroom){
            const subroomAliasMap = { '通用洁净功能用房': cleanClass || 'Ⅲ级（万级）' };
            const subroomKey = cleanFunctionStandardSubroom || subroomAliasMap[cleanFunctionSubroom] || cleanFunctionSubroom;
            if(stdRanges[typeId] && stdRanges[typeId][subroomKey]){
                const subMap = { ...stdRanges[typeId][subroomKey] };
                const levelMap = cleanClass && stdRanges[typeId][cleanClass] ? stdRanges[typeId][cleanClass] : {};
                if(!subMap.airchange && levelMap.airchange) subMap.airchange = levelMap.airchange;
                if(!subMap.particle && levelMap.particle) subMap.particle = levelMap.particle;
                if(!subMap.settling && !subMap.bacteria && (levelMap.settling || levelMap.bacteria)) subMap.settling = levelMap.settling || levelMap.bacteria;
                if(!subMap.temperature && levelMap.temperature) subMap.temperature = levelMap.temperature;
                if(!subMap.humidity && levelMap.humidity) subMap.humidity = levelMap.humidity;
                if(!subMap.noise && levelMap.noise) subMap.noise = levelMap.noise;
                if(!subMap.illumination && (levelMap.illumination || levelMap.work_illumination)) subMap.illumination = levelMap.illumination || levelMap.work_illumination;
                return subMap;
            }
        } else if(typeId === 'operating_room' && surgeryAuxRoom && stdRanges[typeId]['辅房'] && stdRanges[typeId]['辅房'][surgeryAuxRoom]){
            const baseRange = stdRanges[typeId]['辅房'][surgeryAuxRoom];
            const auxCleanClass = card.dataset.surgeryAuxCleanClass || '';
            const levelRange = (auxCleanClass && stdRanges[typeId]['辅房等级'] && stdRanges[typeId]['辅房等级'][auxCleanClass]) ? stdRanges[typeId]['辅房等级'][auxCleanClass] : {};
            return { ...baseRange, ...levelRange };
        } else if(typeId === 'operating_room'){
            return stdRanges[typeId]?.[cleanClass] || {};
        } else if(typeId === 'clean_function_room' && !cleanFunctionSubroom){
            return stdRanges[typeId]?.[cleanClass] || {};
        } else if(typeId === 'negative_pressure'){
            const rangeMap = { ...(stdRanges[typeId]?._default || {}), ...(cleanClass && stdRanges[typeId]?.[cleanClass] ? stdRanges[typeId][cleanClass] : {}) };
            if(rangeMap.airchange && !rangeMap.airchange_polluted) rangeMap.airchange_polluted = rangeMap.airchange;
            if(rangeMap.pressure && !rangeMap.static_pressure_diff) rangeMap.static_pressure_diff = rangeMap.pressure;
            return rangeMap;
        } else if(typeId === 'operating_room' && surgeryAuxRoom && stdRanges[typeId]['辅房'] && stdRanges[typeId]['辅房'][surgeryAuxRoom]){
            const baseRange = stdRanges[typeId]['辅房'][surgeryAuxRoom];
            const auxCleanClass = card.dataset.surgeryAuxCleanClass || '';
            const levelRange = (auxCleanClass && stdRanges[typeId]['辅房等级'] && stdRanges[typeId]['辅房等级'][auxCleanClass]) ? stdRanges[typeId]['辅房等级'][auxCleanClass] : {};
            return { ...baseRange, ...levelRange };
        } else if(typeId === 'operating_room' && card.dataset.surgeryRoomType === '眼科手术室' && cleanClass && stdRanges['eye_operating_room'] && stdRanges['eye_operating_room'][cleanClass]){
            const eyeRangeMap = { ...stdRanges['eye_operating_room'][cleanClass] };
            if(cleanClass === 'Ⅰ级（百级）') eyeRangeMap.particle = { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' };
            if(cleanClass === 'Ⅱ级（千级）') eyeRangeMap.particle = { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' };
            if(cleanClass === 'Ⅲ级（万级）') eyeRangeMap.particle = { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' };
            if(cleanClass === 'Ⅳ级（十万级）') eyeRangeMap.particle = { range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' };
            return eyeRangeMap;
        } else if(typeId === 'animal_room' && cleanClass === '屏障环境' && barrierRoomClass === '洁净辅房' && barrierAuxRoom && stdRanges[typeId]['屏障环境洁净辅房'] && stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom]){
            return stdRanges[typeId]['屏障环境洁净辅房'][barrierAuxRoom];
        } else if(cleanClass && stdRanges[typeId][cleanClass]){
            return stdRanges[typeId][cleanClass];
        } else if(stdRanges[typeId]['_default']){
            return stdRanges[typeId]['_default'];
        } else {
            const keys = Object.keys(stdRanges[typeId]);
            return keys.length > 0 ? stdRanges[typeId][keys[0]] : null;
        }
    }

    card.querySelectorAll('.pb').forEach(pb => {
        if(pb.dataset.pk === 'pressure') return;
        if(pb.querySelector('[data-manual-range]')) return;
        if(pb.dataset.itype === 'pass_fail') return;
        if(pb.dataset.pk === 'settling' || pb.dataset.pk === 'floating' || pb.dataset.pk === 'animal_illumination') return;
        if(pb.dataset.itype === 'hepa_leak_multi') return;
        if(['particle_zone','particle_4','particle_4_051','particle_4_8','numeric','airchange','settling_control','floating_control','bacteria_control','bacteria_zone_control','bacteria_zone','noise_corrected','wind_uniformity','illumination_uniformity'].includes(pb.dataset.itype || '')) return;
        const rangeEl = pb.querySelector('.pb-range');
        if(rangeEl) rangeEl.remove();
    });

    const paramResult = {};
    activeStds.forEach(standardCode => {
        const rangeMap = getRangeMap(standardCode);
        if(!rangeMap) return;
        Object.entries(rangeMap).forEach(([paramKey, rangeObj]) => {
            if(paramKey === 'pressure') return;
            const normalizedParamKey = typeId === 'negative_pressure'
                ? ({ airchange: 'airchange_polluted', pressure: 'static_pressure_diff' }[paramKey] || paramKey)
                : paramKey;
            if(rangeObj.range || rangeObj.range_op) {
                paramResult[normalizedParamKey] = { rangeObj, sourceCode: standardCode };
            }
        });
    });

    Object.entries(paramResult).forEach(([paramKey, { rangeObj, sourceCode }]) => {
        let pb = card.querySelector(`[data-pk="${paramKey}"]`);
        if(!pb && typeId === 'clean_function_room' && paramKey === 'settling') pb = card.querySelector('[data-pk="bacteria"]');
        if(!pb && typeId === 'negative_pressure' && paramKey === 'surface_bacteria') pb = card.querySelector('[data-pk="surface_bacteria"]');
        if(!pb && typeId === 'negative_pressure' && paramKey === 'bacteria') pb = card.querySelector('[data-pk="bacteria"]');
        if(!pb) return;

        if(['hepa_leak_multi','particle_zone','particle_4','particle_4_051','particle_4_8','numeric','airchange','settling_control','floating_control','bacteria_control','bacteria_zone_control','bacteria_zone','noise_corrected','wind_uniformity','illumination_uniformity','pass_fail'].includes(pb.dataset.itype || '')) return;

        const manualMinInput = pb.querySelector(`[data-mr-min="${paramKey}"]`);
        const manualMaxInput = pb.querySelector(`[data-mr-max="${paramKey}"]`);
        if(manualMinInput || manualMaxInput){
            const manualMin = manualMinInput?.value || '';
            const manualMax = manualMaxInput?.value || '';
            const hasUserManual = manualMin !== '' || manualMax !== '';
            const defaultRange = rangeObj.range || '';
            const rangeText = hasUserManual ? ((manualMin !== '' && manualMax !== '') ? `${manualMin}~${manualMax}` : `${manualMin}${manualMax}`) : defaultRange;
            let rangeBox = pb.querySelector('.pb-range');
            if(!rangeBox){
                const headContainer = pb.querySelector('.pb-head > div');
                if(headContainer){
                    const stdLabel = sourceCode ? `[${sourceCode}]` : '';
                    const rangeHtml = `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;"><span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span><span class="pb-range-value" style="color:#2e7d32;">${rangeText || ''}</span>${stdLabel ? ` <span class="pb-range-std" style="color:#999;font-size:11px;margin-left:4px;">${stdLabel}</span>` : ''}</div>`;
                    const calcEl = pb.querySelector('.pb-calc');
                    if(calcEl) calcEl.insertAdjacentHTML('beforebegin', rangeHtml);
                    else headContainer.insertAdjacentHTML('beforeend', rangeHtml);
                }
            }
            updateManualNumericRange(rid, paramKey, rangeText);
            const stdEl = pb.querySelector('.pb-range .pb-range-std');
            if(stdEl) stdEl.textContent = sourceCode ? `[${sourceCode}]` : '';
            return;
        }

        const stdLabel = sourceCode;
        const displayRange = rangeObj.range || '';
        const displayUnit = rangeObj.unit || '';
        let rangeHtml = `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;">`;
        rangeHtml += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span>`;
        if(rangeObj.range_op && rangeObj.range_surr){
            const isAuxRoom = card.dataset.surgeryRoomType === '洁净辅房';
            const lbl_op = isAuxRoom ? '局部' : '手术区';
            const lbl_surr = isAuxRoom ? '其他区域' : '周边区';
            rangeHtml += `${lbl_op}:<span style="color:#2e7d32;">${rangeObj.range_op}</span> | ${lbl_surr}:<span style="color:#2e7d32;">${rangeObj.range_surr}</span>`;
        } else if(displayRange){
            rangeHtml += `<span style="color:#2e7d32;">${displayRange}${displayUnit ? ' ' + displayUnit : ''}</span>`;
        }
        rangeHtml += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        rangeHtml += `</div>`;

        const nameEl = pb.querySelector('.pb-name');
        if(nameEl) nameEl.insertAdjacentHTML('afterend', rangeHtml);
    });
}

// 获取房间的检测类型对象
function getRoomDetType(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return null;
    const domain = card.dataset.domain || currentDomain;
    const typeId = card.dataset.typeId;
    if(!typeId || !domain) return currentDetectionType;
    const types = SYSTEM_DB.detectionTypes[domain] || [];
    const baseType = types.find(t => t.id === typeId) || currentDetectionType;
    if(typeId === 'clean_function_room' && (card.dataset.cleanFunctionSubroom || '')){
        const subroom = card.dataset.cleanFunctionSubroom;
        const cloned = JSON.parse(JSON.stringify(baseType));
        if(cloned && Array.isArray(cloned.params)){
            cloned.params = cloned.params.map(p => {
                if(p.key === 'particle'){
                    const rangeObj = SYSTEM_DB.standardRanges?.['GB 50333-2013']?.clean_function_room?.[(subroom === '通用洁净功能用房' ? 'Ⅲ级（万级）' : subroom)]?.particle
                        || SYSTEM_DB.standardRanges?.['GB 50333-2013']?.clean_function_room?.[card.dataset.cleanClass || '']?.particle
                        || null;
                    return { ...p, inputType: 'particle_4', range: rangeObj?.range || p.range || '', unit: rangeObj?.unit || p.unit || '' };
                }
                if(p.key === 'bacteria'){
                    const rangeObj = SYSTEM_DB.standardRanges?.['GB 50333-2013']?.clean_function_room?.[(subroom === '通用洁净功能用房' ? 'Ⅲ级（万级）' : subroom)]?.bacteria
                        || SYSTEM_DB.standardRanges?.['GB 50333-2013']?.clean_function_room?.[(subroom === '通用洁净功能用房' ? 'Ⅲ级（万级）' : subroom)]?.settling
                        || null;
                    return { ...p, key: 'settling', inputType: 'settling_control', range: rangeObj?.range || p.range || '', unit: rangeObj?.unit || p.unit || '' };
                }
                return p;
            });
        }
        cloned.name = `${baseType.name}-${subroom}`;
        return cloned;
    }
    if(typeId === 'operating_room' && card.dataset.surgeryRoomType === '眼科手术室'){
        const cloned = JSON.parse(JSON.stringify(baseType));
        const cleanClass = card.dataset.cleanClass || card.dataset.levelName || '';
        if(cloned?.eyeLevelParams && cloned.eyeLevelParams[cleanClass]){
            let params = cloned.eyeLevelParams[cleanClass];
            if(Array.isArray(params)){
                params = params.map(p => {
                    if(p.key !== 'particle') return p;
                    if(cleanClass === 'Ⅰ级（百级）') return { ...p, inputType: 'particle_zone', range: '', range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' };
                    if(cleanClass === 'Ⅱ级（千级）') return { ...p, inputType: 'particle_zone', range: '', range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' };
                    if(cleanClass === 'Ⅲ级（万级）') return { ...p, inputType: 'particle_zone', range: '', range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' };
                    if(cleanClass === 'Ⅳ级（十万级）') return { ...p, inputType: 'particle_4', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500', range_op: '', range_surr: '' };
                    return p;
                });
            }
            cloned.params = params;
            cloned.name = `${baseType.name}-${card.dataset.surgeryRoomType}`;
            return cloned;
        }
    }
    if(typeId === 'operating_room' && card.dataset.surgeryRoomType === '洁净辅房' && card.dataset.surgeryAuxRoom){
        const cloned = JSON.parse(JSON.stringify(baseType));
        const roomName = card.dataset.surgeryAuxRoom || '';
        const auxCleanClass = card.dataset.surgeryAuxCleanClass || '';
        const baseParams = cloned?.surgeryAuxRoomParams?.[roomName] || [];
        const auxCleanMap = {
            'I级(局部5级其他6级)': { particleInput: 'particle_zone', particle_op: '≥0.5μm≤3520, ≥5μm≤29', particle_surr: '≥0.5μm≤35200, ≥5μm≤293', bacteriaInput: 'bacteria_zone_control', bacteria_op: '≤0.2', bacteria_surr: '≤0.4' },
            'Ⅰ级（局部5级其他6级）': { particleInput: 'particle_zone', particle_op: '≥0.5μm≤3520, ≥5μm≤29', particle_surr: '≥0.5μm≤35200, ≥5μm≤293', bacteriaInput: 'bacteria_zone_control', bacteria_op: '≤0.2', bacteria_surr: '≤0.4' },
            'II级(7级)': { particle: '≥0.5μm≤352000, ≥5μm≤2930', particleInput: 'particle_4', bacteria: '≤1.5', bacteriaInput: 'bacteria_control' },
            'Ⅱ级（7级）': { particle: '≥0.5μm≤352000, ≥5μm≤2930', particleInput: 'particle_4', bacteria: '≤1.5', bacteriaInput: 'bacteria_control' },
            'III级(8级)': { particle: '≥0.5μm≤3520000, ≥5μm≤29300', particleInput: 'particle_4', bacteria: '≤4', bacteriaInput: 'bacteria_control' },
            'Ⅲ级（8级）': { particle: '≥0.5μm≤3520000, ≥5μm≤29300', particleInput: 'particle_4', bacteria: '≤4', bacteriaInput: 'bacteria_control' },
            'IV级(8.5级)': { particle: '3520000>0.5μm≤11120000, 29300>5μm≤92500', particleInput: 'particle_4', bacteria: '≤6', bacteriaInput: 'bacteria_control' },
            'Ⅳ级（8.5级）': { particle: '3520000>0.5μm≤11120000, 29300>5μm≤92500', particleInput: 'particle_4', bacteria: '≤6', bacteriaInput: 'bacteria_control' }
        };
        const cleanOverride = auxCleanMap[auxCleanClass] || {};
        const isLevel1 = auxCleanClass === 'I级(局部5级其他6级)' || auxCleanClass === 'Ⅰ级（局部5级其他6级）';
        if(Array.isArray(baseParams) && baseParams.length){
            cloned.params = baseParams.map(p => {
                if(p.key === 'airchange' && isLevel1) return { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20～0.25' };
                if(p.key === 'particle' && isLevel1 && cleanOverride.particle_op) return { ...p, inputType: cleanOverride.particleInput, range_op: cleanOverride.particle_op, range_surr: cleanOverride.particle_surr, range: '', zone_label_op: '局部', zone_label_surr: '其他区域' };
                if(p.key === 'bacteria' && isLevel1 && cleanOverride.bacteria_op) return { ...p, inputType: cleanOverride.bacteriaInput, range_op: cleanOverride.bacteria_op, range_surr: cleanOverride.bacteria_surr, range: '', zone_label_op: '局部', zone_label_surr: '其他区域' };
                if(p.key === 'particle' && cleanOverride.particle) return { ...p, range: cleanOverride.particle, inputType: cleanOverride.particleInput || p.inputType };
                if(p.key === 'bacteria' && cleanOverride.bacteria) return { ...p, range: cleanOverride.bacteria, inputType: cleanOverride.bacteriaInput || p.inputType };
                return p;
            });
            cloned.name = `${baseType.name}-${roomName}`;
            return cloned;
        }
    }
    // 动物房屏障环境/隔离环境：主房间直接使用 levelParams，洁净辅房使用 barrierAuxParams
    if(typeId === 'animal_room'){
        const cloned = JSON.parse(JSON.stringify(baseType));
        const cleanClass = card.dataset.cleanClass || card.dataset.levelName || '';
        const barrierRoomClass = card.dataset.barrierRoomClass || '';
        const barrierAuxRoom = card.dataset.barrierAuxRoom || '';
        if(cleanClass === '屏障环境' && barrierRoomClass === '洁净辅房' && barrierAuxRoom && cloned?.barrierAuxParams?.[barrierAuxRoom]){
            cloned.params = cloned.barrierAuxParams[barrierAuxRoom];
            cloned.name = `${baseType.name}-${barrierAuxRoom}`;
            return cloned;
        }
        if(cloned?.levelParams && cloned.levelParams[cleanClass]){
            cloned.params = cloned.levelParams[cleanClass];
            cloned.name = `${baseType.name}-${cleanClass}`;
            return cloned;
        }
    }
    return baseType;
}



function normalizeOperatingRoomTypeValue(v){
    const val = String(v || '').trim();
    if(!val) return '';
    if(val === '辅房') return '洁净辅房';
    return val;
}

function normalizeOperatingAuxRoomValue(v){
    const val = String(v || '').trim();
    if(!val) return '';
    const map = {
        '刷手间': '刷手间',
        '无菌敷料间': '无菌敷料间',
        '器械室': '器械室',
        '麻醉恢复室': '恢复室'
    };
    return map[val] || val;
}

function normalizeOperatingAuxCleanClassValue(v){
    const val = String(v || '').trim();
    if(!val) return '';
    const map = {
        'Ⅱ级辅房': 'Ⅱ级（7级）',
        'Ⅲ级辅房': 'Ⅲ级（8级）',
        'Ⅳ级辅房': 'Ⅳ级（8.5级）',
        'I级辅房': 'Ⅰ级（局部5级其他6级)',
        'Ⅰ级辅房': 'Ⅰ级（局部5级其他6级）'
    };
    return map[val] || val;
}

const RESTORE_FLOW_REGISTRY = {
    operating_room: { mode: 'nested-3' },
    animal_room: { mode: 'nested-3' },
    clean_function_room: { mode: 'nested-2' },
    bsl: { mode: 'context-single' },
    negative_pressure: { mode: 'context-single' },
    electronics_workshop: { mode: 'context-single' },
    food_workshop: { mode: 'context-single' },
    gmp_workshop: { mode: 'context-single' },
    veterinary_gmp_workshop: { mode: 'context-single' },
    pass_box: { mode: 'flat-default' },
    laminar_hood: { mode: 'flat-default' },
    bsc: { mode: 'flat-default' },
    clean_bench: { mode: 'flat-default' },
    ivc: { mode: 'flat-default' }
};

function normalizeFoodGradeValue(val){
    const raw = String(val || '').trim();
    if(!raw) return '';
    const aliasMap = {
        'Ⅰ级': 'Ⅰ级（百级）',
        'Ⅱ级': 'Ⅱ级（万级）',
        'Ⅲ级': 'Ⅲ级（十万级）',
        'Ⅳ级': 'Ⅳ级（三十万级）'
    };
    return aliasMap[raw] || raw;
}

function getRestoreFlow(typeId){
    return RESTORE_FLOW_REGISTRY[typeId] || { mode: 'flat-default' };
}

function applyFlatCleanClassRestore(rid, room, card){
    const isLevelFreeDevice = ['bsc', 'clean_bench', 'ivc'].includes(room.type_id);
    if((!room.clean_class && !isLevelFreeDevice) || room.type_id === 'operating_room') return;
    const normalizedCleanClass = room.type_id === 'food_workshop'
        ? normalizeFoodGradeValue(room.clean_class)
        : (room.clean_class || room.level_name || (isLevelFreeDevice ? '无等级要求' : ''));
    const cleanBtns = card.querySelectorAll('.room-clean-options .level-btn');
    let matched = false;
    cleanBtns.forEach(btn=>{
        if(btn.textContent.trim() === normalizedCleanClass){
            btn.classList.add('active');
            card.dataset.cleanClass = normalizedCleanClass;
            card.dataset.levelName = normalizedCleanClass;
            matched = true;
        }
    });
    if(!matched){
        cleanBtns.forEach(btn=>{
            if(btn.textContent.includes(normalizedCleanClass) || normalizedCleanClass.includes(btn.textContent.trim())){
                btn.classList.add('active');
                card.dataset.cleanClass = normalizedCleanClass;
                card.dataset.levelName = normalizedCleanClass;
                matched = true;
            }
        });
    }
    if(!matched && (room.type_id === 'pass_box' || room.type_id === 'laminar_hood' || isLevelFreeDevice) && normalizedCleanClass){
        card.dataset.cleanClass = normalizedCleanClass;
        card.dataset.levelName = normalizedCleanClass;
        matched = true;
    }
    if(matched){
        const detType = getRoomDetType(rid);
        if(detType && Array.isArray(detType.params) && detType.params.length > 0){
            const prevType = currentDetectionType;
            currentDetectionType = detType;
            renderParamsForRoom(rid, detType);
            currentDetectionType = prevType;
            return;
        }
        if(detType && detType.levelParams && detType.levelParams[normalizedCleanClass]){
            const levelParams = detType.levelParams[normalizedCleanClass];
            const tempType = { ...detType, params: levelParams }; 
            const prevType = currentDetectionType;
            currentDetectionType = detType;
            renderParamsForRoom(rid, tempType);
            currentDetectionType = prevType;
        }
    }
}


function waitForRoomRestore(conditionFn, onReady, options={}){
    const retries = Number.isFinite(options.retries) ? options.retries : 12;
    const delay = Number.isFinite(options.delay) ? options.delay : 40;
    let count = 0;
    const tick = ()=>{
        let ok = false;
        try{ ok = !!conditionFn(); }catch(e){ ok = false; }
        if(ok){ onReady(); return; }
        count += 1;
        if(count >= retries){ onReady(); return; }
        setTimeout(tick, delay);
    };
    tick();
}

function isRoomParamRestoreReady(card, room){
    if(!card || !room) return false;
    const typeId = room.type_id || card.dataset.typeId || '';
    const paramsBox = card.querySelector('.rparams');
    const hasInputs = !!(paramsBox && paramsBox.querySelector('input, select, textarea'));
    if(typeId === 'operating_room'){
        const surgeryRoomType = card.dataset.surgeryRoomType || room.surgery_room_type || '';
        if(!surgeryRoomType) return false;
        if(surgeryRoomType === '洁净辅房' || surgeryRoomType === '辅房'){
            const auxRoom = card.dataset.surgeryAuxRoom || room.surgery_aux_room || '';
            const auxClean = card.dataset.surgeryAuxCleanClass || room.surgery_aux_clean_class || '';
            return !!auxRoom && !!auxClean && hasInputs;
        }
        return !!(card.dataset.cleanClass || room.clean_class || '') && hasInputs;
    }
    if(typeId === 'clean_function_room'){
        return !!(card.dataset.cleanFunctionSubroom || room.clean_function_subroom || '') && !!(card.dataset.cleanClass || room.clean_class || '') && hasInputs;
    }
    if(typeId === 'animal_room'){
        const cleanClass = card.dataset.cleanClass || room.clean_class || '';
        if(cleanClass === '屏障环境'){
            const barrierRoomClass = card.dataset.barrierRoomClass || room.barrier_room_class || '';
            if(!barrierRoomClass) return false;
            if(barrierRoomClass === '洁净辅房'){
                return !!(card.dataset.barrierAuxRoom || room.barrier_aux_room || '') && hasInputs;
            }
        }
        return !!cleanClass && hasInputs;
    }
    return hasInputs;
}

function restoreRoomDatasets(rid, room, card){
    if(Array.isArray(room.basis_dataset)) card.dataset.basisChecked = JSON.stringify(room.basis_dataset);
    card.dataset.basisPrimary = (Array.isArray(room.basis_dataset) && room.basis_dataset.length > 0) ? room.basis_dataset[0] : '';
    if(room.barrier_room_class) card.dataset.barrierRoomClass = room.barrier_room_class;
    if(room.barrier_aux_room) card.dataset.barrierAuxRoom = room.barrier_aux_room;
    if(room.bsl) card.dataset.bsl = room.bsl;
    if(room.business_domain_hint && (room.type_id === 'pass_box' || room.type_id === 'laminar_hood')) card.dataset.businessDomainHint = room.business_domain_hint;
    else if(room.type_id === 'pass_box' || room.type_id === 'laminar_hood') card.dataset.businessDomainHint = 'pharma';
    else delete card.dataset.businessDomainHint;
    if(Array.isArray(room.electronics_manual_range_keys)){
        card.dataset.electronicsManualRangeKeys = JSON.stringify(room.electronics_manual_range_keys);
        card.dataset.electronicsManualSource = room.electronics_manual_range_keys.length > 0 ? 'saved' : '';
    }
    if(room.hepa_leak_summary) card.dataset.hepaLeakSummary = room.hepa_leak_summary;
    else delete card.dataset.hepaLeakSummary;
    if(room.hepa_leak_summary && (room.params?.hepa_leak?.result || '')) card.dataset.hepaLeakSummarySource = 'saved';
    else delete card.dataset.hepaLeakSummarySource;
    if(room.hepa_leak_summary && (room.params?.hepa_leak?.result || '') && !card.dataset.hepaLeakSourceState) card.dataset.hepaLeakSourceState = 'saved';
    else delete card.dataset.hepaLeakSourceState;
    if(room.animal_illumination_source && ((room.params?.animal_illumination?.manualMin || '') || (room.params?.animal_illumination?.manualMax || '') || room.animal_illumination_source === 'saved')) card.dataset.animalIlluminationSource = room.animal_illumination_source;
    else delete card.dataset.animalIlluminationSource;
    delete card.dataset.resultSource_bacteria_control;
    delete card.dataset.resultSource_bacteria_zone_control;
    delete card.dataset.resultSource_settling_control;
    delete card.dataset.resultSource_floating_control;
    delete card.dataset.resultSource_wind_uniformity;
    delete card.dataset.resultSource_illumination_uniformity;
    delete card.dataset.legacyPressurePairSummarySource_pressure;
    delete card.dataset.pressurePairCarrier_pressure;
    card.dataset.animalContextIncomplete = room.animal_context_incomplete ? 'true' : 'false';
    if(Array.isArray(room.judgement_priority)) card.dataset.judgementPriority = JSON.stringify(room.judgement_priority);
    if(Array.isArray(room.judgement_checked)) card.dataset.judgementChecked = JSON.stringify(room.judgement_checked);
    if(Array.isArray(room.judgement_active)) card.dataset.judgementActive = JSON.stringify(room.judgement_active);
    if(room.summary && typeof room.summary === 'object'){
        card.dataset.resultState = room.summary.result_state || '';
        card.dataset.inputResultState = room.summary.input_result_state || '';
        card.dataset.judgementEngine = room.summary.judgement_engine || '';
        card.dataset.judgementReason = room.summary.judgement_reason || '';
        card.dataset.abnormalItems = JSON.stringify(Array.isArray(room.summary.abnormal_items) ? room.summary.abnormal_items : []);
        if(typeof room.summary.judgement_overridden === 'boolean') card.dataset.judgementOverridden = room.summary.judgement_overridden ? 'true' : 'false';
        else delete card.dataset.judgementOverridden;
    } else {
        delete card.dataset.resultState;
        delete card.dataset.inputResultState;
        delete card.dataset.judgementEngine;
        delete card.dataset.judgementReason;
        delete card.dataset.abnormalItems;
        delete card.dataset.judgementOverridden;
    }
    card.dataset.passBoxJudgementActive = (room.type_id === 'pass_box' && Array.isArray(room.pass_box_judgement_active)) ? JSON.stringify(room.pass_box_judgement_active) : '[]';
    const restoredPassBoxParamsReady = room.type_id === 'pass_box' && ((room.params && Object.keys(room.params||{}).length > 0) || !!card.querySelector('.pb'));
    const restoredPassBoxJudgementActive = (room.type_id === 'pass_box' && Array.isArray(room.pass_box_judgement_active)) ? room.pass_box_judgement_active : [];
    const restoredPassBoxResultState = room.type_id === 'pass_box' ? (room.pass_box_result_state || '') : '';
    card.dataset.passBoxParamsReady = restoredPassBoxParamsReady ? 'true' : 'false';
    card.dataset.passBoxJudgementSource = restoredPassBoxParamsReady && restoredPassBoxJudgementActive.length > 0 ? 'saved' : '';
    card.dataset.passBoxResultState = restoredPassBoxParamsReady ? restoredPassBoxResultState : '';
    if(!restoredPassBoxParamsReady){
        card.dataset.passBoxJudgementActive = '[]';
        card.dataset.passBoxResultState = '';
    }
}

function restoreRoomExpandedStates(card, room){
    if(room.basis_expanded === true || room.basis_expanded === 'true'){
        const rbBody = card.querySelector('.rb-body');
        const rbArrow = card.querySelector('.rb-arrow');
        if(rbBody) rbBody.style.display = 'block';
        if(rbArrow) rbArrow.textContent = '▲';
        card.dataset.basisExpanded = 'true';
    }
    if(room.judgement_expanded === true || room.judgement_expanded === 'true'){
        const rjBody = card.querySelector('.rj-body');
        const rjArrow = card.querySelector('.rj-arrow');
        if(rjBody) rjBody.style.display = 'block';
        if(rjArrow) rjArrow.textContent = '▲';
        card.dataset.judgementExpanded = 'true';
    }
}

function restoreNestedRoomContext(rid, room, card){
    const flow = getRestoreFlow(room.type_id);
    const cleanFunctionSubroom = room.clean_function_subroom || room?.context?.clean_function_subroom || '';
    if(room.type_id === 'clean_function_room' && cleanFunctionSubroom){
        const preservedCleanClass = room.clean_class || room.level_name || '';
        card.dataset.restoreBranch = 'clean_function_room';
        card.dataset.restoringCleanFunctionContext = 'true';
        card.dataset.cleanFunctionRestoreSubroom = cleanFunctionSubroom;
        if(cleanFunctionSubroom) card.dataset.cleanFunctionSubroom = cleanFunctionSubroom;
        if(preservedCleanClass){
            card.dataset.cleanClass = preservedCleanClass;
            card.dataset.levelName = preservedCleanClass;
            card.dataset.cleanFunctionRestoreCleanClass = preservedCleanClass;
        } else {
            delete card.dataset.cleanFunctionRestoreCleanClass;
        }
        selCleanFunctionSubroom(rid, cleanFunctionSubroom);
        if(preservedCleanClass){
            waitForRoomRestore(
                ()=>!!document.querySelector(`[data-rid="${rid}"] .room-clean-options .level-btn`),
                ()=>{
                    card.dataset.cleanClass = preservedCleanClass;
                    card.dataset.levelName = preservedCleanClass;
                    selCleanClass(rid, preservedCleanClass);
                    card.dataset.restoreStage = 'stage3_restored_clean_function_room';
                    delete card.dataset.restoringCleanFunctionContext;
                    updateRoomSummary(rid);
                }
            );
        }
        else {
            delete card.dataset.restoringCleanFunctionContext;
            card.dataset.basisChecked = '[]';
            card.dataset.judgementChecked = '[]';
            card.dataset.judgementActive = '[]';
            card.dataset.basisExpanded = 'false';
            card.dataset.judgementExpanded = 'false';
            card.dataset.activeJudgementCode = '';
            delete card.dataset.pressurePairSummary;
            delete card.dataset.legacyPressurePairSummarySource_pressure;
            delete card.dataset.pressurePairCarrier_pressure;
            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择洁净等级</p>';
        }
        return;
    }
    if(flow.mode === 'context-single'){
        applyFlatCleanClassRestore(rid, room, card);
        return;
    }
    if(flow.mode === 'flat-default'){
        applyFlatCleanClassRestore(rid, room, card);
        return;
    }
    const animalBarrierRoomClass = room.barrier_room_class || room?.context?.barrier_room_class || '';
    const animalBarrierAuxRoom = room.barrier_aux_room || room?.context?.barrier_aux_room || '';
    if(room.type_id === 'animal_room' && room.clean_class === '屏障环境'){
        card.dataset.animalRestoreBranch = 'entered';
        card.dataset.animalRestoreCleanClass = room.clean_class || '';
        card.dataset.animalRestoreBarrierRoomClass = animalBarrierRoomClass;
        card.dataset.animalRestoreBarrierAuxRoom = animalBarrierAuxRoom;
        card.dataset.restoringAnimalContext = 'true';
        card.dataset.cleanClass = room.clean_class || '';
        card.dataset.levelName = room.clean_class || '';
        if(animalBarrierRoomClass) card.dataset.barrierRoomClass = animalBarrierRoomClass;
        if(animalBarrierAuxRoom) card.dataset.barrierAuxRoom = animalBarrierAuxRoom;
        waitForRoomRestore(
            ()=>!!document.querySelector(`[data-rid="${rid}"] .room-clean-options`),
            ()=>{
                selCleanClass(rid, room.clean_class);
                if(animalBarrierRoomClass){
                    waitForRoomRestore(
                        ()=>!!document.querySelector(`[data-rid="${rid}"] .room-barrier-room-class-options .level-btn`),
                        ()=>{
                            selBarrierRoomClass(rid, animalBarrierRoomClass);
                            if(animalBarrierAuxRoom && animalBarrierRoomClass === '洁净辅房'){
                                waitForRoomRestore(
                                    ()=>!!document.querySelector(`[data-rid="${rid}"] .room-barrier-aux-options .level-btn`),
                                    ()=>{
                                        selBarrierAuxRoom(rid, animalBarrierAuxRoom);
                                        card.dataset.restoreStage = 'stage4_restored_animal_room';
                                        delete card.dataset.restoringAnimalContext;
                                        syncAnimalRoomContextSummary(rid);
                                        updateRoomSummary(rid);
                                    }
                                );
                            } else {
                                card.dataset.restoreStage = 'stage3_restored_animal_room';
                                delete card.dataset.restoringAnimalContext;
                                syncAnimalRoomContextSummary(rid);
                                updateRoomSummary(rid);
                            }
                        }
                    );
                } else {
                    card.dataset.restoreStage = 'stage2_restored_animal_room';
                    delete card.dataset.restoringAnimalContext;
                    syncAnimalRoomContextSummary(rid);
                    updateRoomSummary(rid);
                }
            }
        );
        return;
    }
    if(room.surgery_room_type && room.type_id === 'operating_room'){
        selSurgeryRoomType(rid, room.surgery_room_type);
        if(room.surgery_room_type === '洁净辅房'){
            if(room.surgery_aux_room){
                waitForRoomRestore(
                    ()=>!!document.querySelector(`[data-rid="${rid}"] .room-surgery-aux-options .level-btn`),
                    ()=>{
                        selSurgeryAuxRoom(rid, room.surgery_aux_room);
                        if(room.surgery_aux_clean_class){
                            waitForRoomRestore(
                                ()=>!!document.querySelector(`[data-rid="${rid}"] .room-clean-options .level-btn`),
                                ()=>{
                                    selSurgeryAuxCleanClass(rid, room.surgery_aux_clean_class);
                                    card.dataset.restoreStage = 'stage4_restored_operating_room';
                                    updateRoomSummary(rid);
                                }
                            );
                        } else {
                            card.dataset.restoreStage = 'stage3_restored_operating_room';
                            updateRoomSummary(rid);
                        }
                    }
                );
            }
        } else {
            if(room.clean_class){
                waitForRoomRestore(
                    ()=>!!document.querySelector(`[data-rid="${rid}"] .room-clean-options .level-btn`),
                    ()=>{
                        selCleanClass(rid, room.clean_class);
                        card.dataset.restoreStage = 'stage4_restored_operating_room';
                        updateRoomSummary(rid);
                    }
                );
            } else {
                card.dataset.basisChecked = '[]';
                card.dataset.judgementChecked = '[]';
                card.dataset.judgementActive = '[]';
                card.dataset.basisExpanded = 'false';
                card.dataset.judgementExpanded = 'false';
                card.dataset.activeJudgementCode = '';
                delete card.dataset.pressurePairSummary;
                delete card.dataset.legacyPressurePairSummarySource_pressure;
                delete card.dataset.pressurePairCarrier_pressure;
                card.dataset.hepaLeakSummary = '';
                card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择手术室洁净等级</p>';
                card.dataset.restoreStage = 'stage2_restored_operating_room';
                updateRoomSummary(rid);
            }
        }
        return;
    } else if(room.surgery_aux_room && room.type_id === 'operating_room'){
        selSurgeryAuxRoom(rid, room.surgery_aux_room);
        card.dataset.restoreStage = 'stage3_restored_operating_room';
        updateRoomSummary(rid);
    } else {
        applyFlatCleanClassRestore(rid, room, card);
    }
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


function selCleanClass(rid, cleanClass){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    const normalizedCleanClass = detType && detType.id === 'food_workshop' ? normalizeFoodGradeValue(cleanClass) : cleanClass;
    // 清除同组其他按钮的active状态(洁净等级是room-clean-options里的level-grid或single-line-level-grid)
    const cleanContainer = room.querySelector('.room-clean-options') || room;
    const cleanBtns = cleanContainer.querySelector('.level-grid, .single-line-level-grid');
    if(cleanBtns) {
        cleanBtns.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === normalizedCleanClass) b.classList.add('active');
        });
    }
    room.dataset.cleanClass = normalizedCleanClass;
    room.dataset.levelName = normalizedCleanClass;

    // 设置levelIdx
    if(detType && detType.levelParams){
        const keys = Object.keys(detType.levelParams);
        const levelIdx = keys.indexOf(normalizedCleanClass);
        room.dataset.levelIdx = levelIdx >= 0 ? levelIdx : 0;
    } else {
        room.dataset.levelIdx = 0;
    }

    cleanClass = normalizedCleanClass;

    if(detType && detType.id === 'animal_room'){
        const restoringAnimalContext = (room.dataset.restoreStage || '').includes('restored_animal_room') || room.dataset.restoringAnimalContext === 'true';
        const preservedBarrierRoomClass = room.dataset.barrierRoomClass || '';
        const preservedBarrierAuxRoom = room.dataset.barrierAuxRoom || '';
        room.dataset.basisChecked = '[]';
        room.dataset.basisPrimary = '';
        room.dataset.judgementPriority = '[]';
        room.dataset.judgementChecked = '[]';
        room.dataset.judgementActive = '[]';
        room.dataset.basisExpanded = 'false';
        room.dataset.judgementExpanded = 'false';
        if(cleanClass !== '屏障环境'){
            room.dataset.animalContextIncomplete = 'false';
            room.querySelector('.room-barrier-room-class-options').innerHTML = '';
            room.querySelector('.room-barrier-aux-options').innerHTML = '';
            delete room.dataset.barrierRoomClass;
            delete room.dataset.barrierAuxRoom;
            delete room.dataset.hepaLeakSummary;
            Array.from(room.querySelectorAll('.pb')).forEach(pb => {
                const pk = pb.dataset.pk || '';
                if(pk) delete room.dataset[`pressurePairSummary_${pk}`];
            });
        } else if(Array.isArray(detType.barrierRoomClassOptions)) {
            const label = detType.barrierRoomClassLabel || '房间类别';
            room.querySelector('.room-barrier-room-class-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">${label}:</label><div class="level-grid">${detType.barrierRoomClassOptions.map(opt => `<div class="level-btn" onclick="selBarrierRoomClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
            room.querySelector('.room-barrier-aux-options').innerHTML = '';
            if(!restoringAnimalContext){
                delete room.dataset.barrierRoomClass;
                delete room.dataset.barrierAuxRoom;
            } else {
                if(preservedBarrierRoomClass) room.dataset.barrierRoomClass = preservedBarrierRoomClass;
                if(preservedBarrierAuxRoom) room.dataset.barrierAuxRoom = preservedBarrierAuxRoom;
            }
        }
        renderRoomBasis(rid, room.dataset.domain || currentDomain, detType);
        renderRoomJudgementForType(rid, room.dataset.domain || currentDomain, detType);
        syncAnimalContextMarker(rid);
        syncAnimalRoomContextSummary(rid);
    }

    if(detType && detType.id === 'operating_room'){
        // operating_room 的辅房选择由 selSurgeryRoomType 控制,选等级时不再渲染辅房按钮
        // 不做任何操作
    } else {
        room.querySelector('.room-surgery-aux-options').innerHTML = '';
        delete room.dataset.surgeryAuxRoom;
    }

    if(detType && detType.id === 'clean_function_room' && room.dataset.cleanFunctionSubroom){
        const prevType = currentDetectionType;
        currentDetectionType = detType;
        renderParamsForRoom(rid, detType);
        currentDetectionType = prevType;
        updateRoomRangesByPriority(rid);
        room.querySelectorAll('.pb[data-itype="particle_4"]').forEach(pb => {
            const pk = pb.dataset.pk;
            if(pk) calc_p4(rid, pk);
        });
        room.querySelectorAll('.pb[data-itype="noise_corrected"]').forEach(pb => {
            const pk = pb.dataset.pk;
            if(pk) calc_noise(rid, pk);
        });
        updateRoomSummary(rid);
        return;
    }

    // 如果检测类型有levelParams,重新渲染参数
    if(detType && detType.id === 'operating_room' && room.dataset.surgeryRoomType === '眼科手术室' && detType.eyeLevelParams && detType.eyeLevelParams[normalizedCleanClass]){
        let levelParams = detType.eyeLevelParams[normalizedCleanClass];
        if(Array.isArray(levelParams) && ['Ⅰ级（百级）','Ⅱ级（千级）','Ⅲ级（万级）','Ⅳ级（十万级）'].includes(normalizedCleanClass)){
            levelParams = levelParams.map(p => {
                if(p.key !== 'particle') return p;
                if(cleanClass === 'Ⅰ级（百级）') return { ...p, inputType: 'particle_zone', range: '', range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' };
                if(cleanClass === 'Ⅱ级（千级）') return { ...p, inputType: 'particle_zone', range: '', range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' };
                if(cleanClass === 'Ⅲ级（万级）') return { ...p, inputType: 'particle_zone', range: '', range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' };
                if(cleanClass === 'Ⅳ级（十万级）') return { ...p, inputType: 'particle_4', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500', range_op: '', range_surr: '' };
                return p;
            });
        }
        const tempType = { ...detType, params: levelParams };
        if(cleanClass === 'Ⅳ级（十万级）' && Array.isArray(tempType.params)){
            tempType.params = tempType.params.map(p => {
                if(p.key === 'particle') return { ...p, inputType: 'particle_4', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500', range_op: '', range_surr: '' };
                if(p.key === 'bacteria') return { ...p, inputType: 'bacteria_control' };
                return p;
            });
        }
        const prevType = currentDetectionType;
        currentDetectionType = detType;
        renderParamsForRoom(rid, tempType);
        currentDetectionType = prevType;
    } else if(detType && detType.id === 'operating_room' && room.dataset.surgeryRoomType === '手术室' && detType.levelParams && detType.levelParams[normalizedCleanClass]){
        const levelParams = detType.levelParams[normalizedCleanClass];
        const tempType = { ...detType, params: levelParams };
        if(cleanClass === 'Ⅳ级（十万级）' && Array.isArray(tempType.params)){
            tempType.params = tempType.params.map(p => {
                if(p.key === 'particle') return { ...p, inputType: 'particle_4' };
                if(p.key === 'bacteria') return { ...p, inputType: 'bacteria_control' };
                return p;
            });
        }
        const prevType = currentDetectionType;
        currentDetectionType = detType;
        renderParamsForRoom(rid, tempType);
        currentDetectionType = prevType;
    } else if(detType && detType.levelParams && detType.levelParams[normalizedCleanClass]){
        const levelParams = detType.levelParams[normalizedCleanClass];
        const tempType = { ...detType, params: levelParams };
        const prevType = currentDetectionType;
        currentDetectionType = tempType;
        renderParamsForRoom(rid, tempType);
        currentDetectionType = prevType;
    }


    // 根据房间的判定标准优先级更新判定范围
    updateRoomRangesByPriority(rid);

    // 重新渲染后自动触发一次粒子项判定,确保切换环境后结果联动正确
    room.querySelectorAll('.pb[data-itype="particle_4"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="particle_4_051"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4_051(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="particle_4_8"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4_8(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="noise_corrected"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_noise(rid, pk);
    });

    updateRoomSummary(rid);
}

function selBarrierRoomClass(rid, roomClass){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    if(!room || !detType) return;
    const container = room.querySelector('.room-barrier-room-class-options .level-grid');
    if(container){
        container.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === roomClass) b.classList.add('active');
        });
    }
    room.dataset.barrierRoomClass = roomClass;
    room.dataset.animalContextIncomplete = 'false';
    if(detType && Array.isArray(detType.defaultJudgement) && detType.defaultJudgement.length > 0){
        room.dataset.judgementPriority = JSON.stringify(detType.defaultJudgement);
        room.dataset.judgementChecked = JSON.stringify(detType.defaultJudgement);
        room.dataset.judgementActive = JSON.stringify(detType.defaultJudgement);
    } else {
        room.dataset.judgementPriority = '[]';
        room.dataset.judgementChecked = '[]';
        room.dataset.judgementActive = '[]';
    }
    room.dataset.basisChecked = '[]';
    room.dataset.basisPrimary = '';
    room.dataset.basisExpanded = 'false';
    room.dataset.judgementExpanded = 'false';
    room.querySelector('.rb-summary') && (room.querySelector('.rb-summary').textContent = '');
    room.querySelector('.rj-summary') && (room.querySelector('.rj-summary').textContent = '');
    delete room.dataset.barrierAuxRoom;

    if(roomClass === '洁净辅房' && Array.isArray(detType.barrierAuxRoomOptions)){
        const label = detType.barrierAuxRoomLabel || '洁净辅房名称';
        room.querySelector('.room-barrier-aux-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">${label}:</label><div class="level-grid">${detType.barrierAuxRoomOptions.map(opt => `<div class="level-btn" onclick="selBarrierAuxRoom('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
        room.querySelector('.rb-body').innerHTML = '';
        room.querySelector('.rj-body').innerHTML = '';
        room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择洁净辅房名称</p>';
        room.querySelector('.rb-summary') && (room.querySelector('.rb-summary').textContent = '未完成');
        room.querySelector('.rj-summary') && (room.querySelector('.rj-summary').textContent = '未完成');
    } else {
        room.querySelector('.room-barrier-aux-options').innerHTML = '';
        const levelParams = detType.levelParams && detType.levelParams['屏障环境'] ? detType.levelParams['屏障环境'] : detType.params;
        const tempType = { ...detType, params: levelParams || [] };
        const prevType = currentDetectionType;
        currentDetectionType = tempType;
        renderParamsForRoom(rid, tempType);
        currentDetectionType = prevType;
        updateRoomRangesByPriority(rid);
        room.querySelectorAll('.pb[data-itype="particle_4"]').forEach(pb => {
            const pk = pb.dataset.pk;
            if(pk) calc_p4(rid, pk);
        });
    }
    renderRoomBasis(rid, room.dataset.domain || currentDomain, detType);
    renderRoomJudgementForType(rid, room.dataset.domain || currentDomain, detType);
    room.dataset.animalContextIncomplete = isAnimalBarrierContextIncomplete(room) ? 'true' : 'false';
    syncAnimalRoomContextSummary(rid);
    if(roomClass === '洁净辅房' && !room.dataset.barrierAuxRoom){
        renderRoomBasis(rid, room.dataset.domain || currentDomain, detType);
        renderRoomJudgementForType(rid, room.dataset.domain || currentDomain, detType);
    }
}

function selBarrierAuxRoom(rid, roomName){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    if(!room || !detType) return;
    room.dataset.animalContextIncomplete = 'false';
    const container = room.querySelector('.room-barrier-aux-options .level-grid');
    if(container){
        container.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === roomName) b.classList.add('active');
        });
    }
    room.dataset.barrierAuxRoom = roomName;
    room.dataset.basisChecked = '[]';
    room.dataset.basisPrimary = '';
    if(detType && Array.isArray(detType.defaultJudgement) && detType.defaultJudgement.length > 0){
        room.dataset.judgementPriority = JSON.stringify(detType.defaultJudgement);
        room.dataset.judgementChecked = JSON.stringify(detType.defaultJudgement);
        room.dataset.judgementActive = JSON.stringify(detType.defaultJudgement);
    } else {
        room.dataset.judgementPriority = '[]';
        room.dataset.judgementChecked = '[]';
        room.dataset.judgementActive = '[]';
    }
    room.dataset.basisExpanded = 'false';
    room.dataset.judgementExpanded = 'false';
    room.querySelector('.rb-summary') && (room.querySelector('.rb-summary').textContent = '');
    room.querySelector('.rj-summary') && (room.querySelector('.rj-summary').textContent = '');
    const auxParams = detType.barrierAuxParams && detType.barrierAuxParams[roomName] ? detType.barrierAuxParams[roomName] : [];
    const tempType = { ...detType, params: auxParams };
    const prevType = currentDetectionType;
    currentDetectionType = detType;
    renderParamsForRoom(rid, tempType);
    currentDetectionType = prevType;
    updateRoomRangesByPriority(rid);
    room.querySelectorAll('.pb[data-itype="particle_4"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="particle_4_8"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4_8(rid, pk);
    });
    renderRoomBasis(rid, room.dataset.domain || currentDomain, detType);
    renderRoomJudgementForType(rid, room.dataset.domain || currentDomain, detType);
    room.dataset.animalContextIncomplete = isAnimalBarrierContextIncomplete(room) ? 'true' : 'false';
    syncAnimalRoomContextSummary(rid);
}

function selSurgeryRoomType(rid, roomType){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    if(!room || !detType) return;
    // 高亮选中按钮
    const container = room.querySelector('.room-surgery-type-options .level-grid');
    if(container){
        container.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === roomType) b.classList.add('active');
        });
    }
    room.dataset.surgeryRoomType = roomType;
    room.dataset.restoreStage = 'stage2_surgery_room_type';
    // 清除之前的辅房选择
    room.querySelector('.room-surgery-aux-options').innerHTML = '';
    delete room.dataset.surgeryAuxRoom;
    delete room.dataset.surgeryAuxCleanClass;
    delete room.dataset.cleanClass;
    delete room.dataset.levelName;

    if(roomType === '手术室'){
        const opts = ['Ⅰ级（百级）', 'Ⅱ级（千级）', 'Ⅲ级（万级）', 'Ⅳ级（十万级）'];
        room.querySelector('.room-clean-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">洁净等级：</label><div class="level-grid">${opts.map(opt => `<div class="level-btn" onclick="selCleanClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
        room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择手术室洁净等级</p>';
    } else if(roomType === '眼科手术室'){
        const opts = ['Ⅰ级（百级）', 'Ⅱ级（千级）', 'Ⅲ级（万级）', 'Ⅳ级（十万级）'];
        room.querySelector('.room-clean-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">洁净等级：</label><div class="level-grid">${opts.map(opt => `<div class="level-btn" onclick="selCleanClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
        room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择眼科手术室洁净等级</p>';
    } else if(roomType === '洁净辅房' || roomType === '辅房'){
        room.querySelector('.room-clean-options').innerHTML = '';
        if(Array.isArray(detType.surgeryAuxRoomOptions)){
            const label = detType.surgeryAuxRoomLabel || '辅房名称';
            room.querySelector('.room-surgery-aux-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">${label}:</label><div class="level-grid">${detType.surgeryAuxRoomOptions.map(opt => `<div class="level-btn" onclick="selSurgeryAuxRoom('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
        }
        room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择辅房名称</p>';
    } else {
        room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择房间类型</p>';
    }
    requestAnimationFrame(() => updateRoomSummary(rid));
}


function cleanClassOrDefault(room, fallback){
    return room?.dataset?.cleanClass || fallback || 'Ⅲ级（万级）';
}

function selCleanFunctionSubroom(rid, subroom){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    if(!room || !detType) return;
    const restoringCleanFunction = room.dataset.restoringCleanFunctionContext === 'true';
    const preservedCleanClass = room.dataset.cleanClass || room.dataset.levelName || '';
    const container = room.querySelector('.room-surgery-type-options .level-grid');
    if(container){
        container.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === subroom) b.classList.add('active');
        });
    }
    room.dataset.cleanFunctionSubroom = subroom;
    const subroomStandardMap = {
        '通用洁净功能用房': cleanClassOrDefault(room, 'Ⅲ级（万级）'),
        'ICU病房': 'Ⅲ级（万级）',
        '消毒供应中心': 'Ⅲ级（万级）',
        '透析室': 'Ⅲ级（万级）'
    };
    room.dataset.cleanFunctionStandardSubroom = subroomStandardMap[subroom] || subroom;
    if(!restoringCleanFunction){
        delete room.dataset.cleanClass;
        delete room.dataset.levelName;
        delete room.dataset.levelIdx;
    } else {
        if(preservedCleanClass){
            room.dataset.cleanClass = preservedCleanClass;
            room.dataset.levelName = preservedCleanClass;
        }
    }
    delete room.dataset.pressurePairSummary_pressure;
    delete room.dataset.pressurePairCarrier_pressure;
    room.dataset.basisChecked = '[]';
    room.dataset.judgementActive = '[]';
    room.dataset.activeJudgementCode = '';
    room.dataset.pressurePairSummary = '';
    room.dataset.basisExpanded = 'false';
    room.dataset.judgementExpanded = 'false';
    room.dataset.basisChecked = '[]';
    room.dataset.basisPrimary = '';
    room.dataset.judgementPriority = '[]';
    room.dataset.judgementChecked = '[]';
    room.dataset.judgementActive = '[]';
    room.dataset.basisExpanded = 'false';
    room.dataset.judgementExpanded = 'false';
    const cleanOptions = (detType.cleanClassOptions || []).filter(opt => ['Ⅲ级（万级）', 'Ⅳ级（十万级）'].includes(opt));
    room.querySelector('.room-clean-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">洁净等级：</label><div class="level-grid">${cleanOptions.map(opt => `<div class="level-btn" onclick="selCleanClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
    renderRoomBasis(rid, room.dataset.domain || currentDomain, detType);
    renderRoomJudgementForType(rid, room.dataset.domain || currentDomain, detType);
    if(!restoringCleanFunction){
        room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择洁净等级</p>';
    }
    updateRoomSummary(rid);
}

function selSurgeryAuxRoom(rid, roomName){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    if(!room || !detType) return;
    const container = room.querySelector('.room-surgery-aux-options .level-grid');
    if(container){
        container.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === roomName) b.classList.add('active');
        });
    }
    room.dataset.surgeryAuxRoom = roomName;
    room.dataset.restoreStage = 'stage3_surgery_aux_room';
    delete room.dataset.surgeryAuxCleanClass;
    room.dataset.basisChecked = '[]';
    room.dataset.judgementActive = '[]';
    room.dataset.activeJudgementCode = '';
    delete room.dataset.pressurePairSummary;
    delete room.dataset.pressurePairSummary_pressure;
    delete room.dataset.pressurePairCarrier_pressure;
    room.dataset.basisExpanded = 'false';
    room.dataset.judgementExpanded = 'false';
    // 显示辅房等级选择
    const auxCleanOpts = detType.surgeryAuxCleanClassOptions || [];
    if(auxCleanOpts.length > 0){
        room.querySelector('.room-clean-options').innerHTML = `<label style="font-size:13px;font-weight:500;color:#555;">辅房等级:</label><div class="level-grid">${auxCleanOpts.map(opt => `<div class="level-btn" onclick="selSurgeryAuxCleanClass('${rid}','${opt}')">${opt}</div>`).join('')}</div>`;
    }
    // 清空参数区(等选等级后再渲染)
    room.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请先选择辅房等级</p>';
    updateRoomSummary(rid);
}

function selSurgeryAuxCleanClass(rid, auxCleanClass){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    if(!room || !detType) return;
    room.dataset.restoreStage = 'stage4_surgery_aux_clean_class';
    // 高亮选中按钮
    const container = room.querySelector('.room-clean-options .level-grid');
    if(container){
        container.querySelectorAll('.level-btn').forEach(b => {
            b.classList.remove('active');
            if(b.textContent.trim() === auxCleanClass) b.classList.add('active');
        });
    }
    room.dataset.surgeryAuxCleanClass = auxCleanClass;
    room.dataset.cleanClass = auxCleanClass;
    room.dataset.levelName = auxCleanClass;
    // 辅房等级→洁净度/细菌浓度映射(GB 50333-2013 表3.0.2-2)
    const auxCleanMap = {
        'I级(局部5级其他6级)': { particleInput: 'particle_zone', particle_op: '≥0.5μm≤3520, ≥5μm≤29', particle_surr: '≥0.5μm≤35200, ≥5μm≤293', bacteriaInput: 'bacteria_zone_control', bacteria_op: '≤0.2', bacteria_surr: '≤0.4' },
        'Ⅰ级（局部5级其他6级）': { particleInput: 'particle_zone', particle_op: '≥0.5μm≤3520, ≥5μm≤29', particle_surr: '≥0.5μm≤35200, ≥5μm≤293', bacteriaInput: 'bacteria_zone_control', bacteria_op: '≤0.2', bacteria_surr: '≤0.4' },
        'II级(7级)': { particle: '≥0.5μm≤352000, ≥5μm≤2930', particleInput: 'particle_4', bacteria: '≤1.5' },
        'Ⅱ级（7级）': { particle: '≥0.5μm≤352000, ≥5μm≤2930', particleInput: 'particle_4', bacteria: '≤1.5' },
        'III级(8级)': { particle: '≥0.5μm≤3520000, ≥5μm≤29300', particleInput: 'particle_4', bacteria: '≤4' },
        'Ⅲ级（8级）': { particle: '≥0.5μm≤3520000, ≥5μm≤29300', particleInput: 'particle_4', bacteria: '≤4' },
        'IV级(8.5级)': { particle: '3520000>0.5μm≤11120000, 29300>5μm≤92500', particleInput: 'particle_4', bacteria: '≤6' },
        'Ⅳ级（8.5级）': { particle: '3520000>0.5μm≤11120000, 29300>5μm≤92500', particleInput: 'particle_4', bacteria: '≤6' }
    };
    const cleanOverride = auxCleanMap[auxCleanClass] || {};
    // 用辅房参数渲染,动态覆盖洁净度和细菌浓度的range和inputType
    const roomName = room.dataset.surgeryAuxRoom || '';
    const baseParams = detType.surgeryAuxRoomParams && detType.surgeryAuxRoomParams[roomName] ? detType.surgeryAuxRoomParams[roomName] : [];
    const isLevel1 = auxCleanClass === 'I级(局部5级其他6级)';
    const auxParams = baseParams.map(p => {
        // I级:换气次数替换为截面风速(与I级手术室相同)
        if(p.key === 'airchange' && isLevel1) return { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20~0.25' };
        // I级:洁净度分局部/其他两区
        if(p.key === 'particle' && isLevel1 && cleanOverride.particle_op) return { ...p, inputType: cleanOverride.particleInput, range_op: cleanOverride.particle_op, range_surr: cleanOverride.particle_surr, range: '', zone_label_op: '局部', zone_label_surr: '其他区域' };
        // I级:细菌浓度分局部/其他两区
        if(p.key === 'bacteria' && isLevel1 && cleanOverride.bacteria_op) return { ...p, inputType: cleanOverride.bacteriaInput, range_op: cleanOverride.bacteria_op, range_surr: cleanOverride.bacteria_surr, range: '', zone_label_op: '局部', zone_label_surr: '其他区域' };
        // 其他等级:覆盖洁净度range和inputType
        if(p.key === 'particle' && cleanOverride.particle) return { ...p, range: cleanOverride.particle, inputType: cleanOverride.particleInput || p.inputType };
        // 其他等级:覆盖细菌浓度range
        if(p.key === 'bacteria' && cleanOverride.bacteria) return { ...p, range: cleanOverride.bacteria };
        return p;
    });
    const tempType = { ...detType, params: auxParams };
    const prevType = currentDetectionType;
    currentDetectionType = detType;
    renderParamsForRoom(rid, tempType);
    currentDetectionType = prevType;
    updateRoomRangesByPriority(rid);
    room.querySelectorAll('.pb[data-itype="particle_4"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="particle_4_8"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_p4_8(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="noise_corrected"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_noise(rid, pk);
    });
    updateRoomSummary(rid);
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


function renderParams(rid,level){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    let h='';
    level.params.forEach(p=>{
        h+=`<div class="pb" data-pk="${p.key}" data-itype="${p.inputType}">`;
        h+=`<div class="pb-head"><div><div class="pb-name">${p.name}</div>`;
        const selfRendersRange = ['numeric','airchange','airchange_speed_only','particle_4','particle_4_051','particle_4_8','settling_control','floating_control','noise_corrected','wind_uniformity','illumination_uniformity','hepa_leak_multi','bacteria_control','bacteria_zone_control','bacteria_zone'].includes(p.inputType);
        const isZoneRangeType = ['particle_zone','bacteria_zone','bacteria_zone_control'].includes(p.inputType);
        if(p.inputType!=='pressure_bsl' && !selfRendersRange && !isZoneRangeType){
            const pr = getParamRange(rid, p.key);
            const displayRange = pr.range || '';
            const displayRangeOp = pr.range_op || '';
            const displayRangeSurr = pr.range_surr || '';
            const displayUnit = pr.unit || p.unit || '';
            const displayStd = pr.standard || '';
            if(displayRange) h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;"><span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span><span style="color:#2e7d32;">${displayRange} ${displayUnit}</span>${displayStd ? ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>` : ''}</div>`;
            if(displayRangeOp) h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;"><span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span>${p.zone_label_op||'手术区'}:<span style="color:#2e7d32;">${displayRangeOp}</span> | ${p.zone_label_surr||'周边区'}:<span style="color:#2e7d32;">${displayRangeSurr}</span>${displayStd ? ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>` : ''}</div>`;
        }
        if(p.inputType!=='pressure_bsl' && p.calc&&p.calc!=='/') h+=`<div class="pb-calc">计算:${p.calc}</div>`;
        h+=`</div></div>`;
        h+=renderInput(rid,p);
        if(p.inputType!=='pressure_bsl' && p.inputType!=='hepa_leak_multi'){
            h+=`<div class="cr"><span>结果:</span><span class="cv" data-res="${p.key}">-</span></div>`;
        }
        h+=`</div>`;
    });
    room.querySelector('.rparams').innerHTML=h;
}

function renderInput(rid,p){
    const t=p.inputType;
    if(t==='numeric') return renderNumeric(rid,p);
    if(t==='numeric_range_manual') return renderNumericRangeManual(rid,p);
    if(t==='hepa_leak_multi') return renderHepaLeakMulti(rid,p);
    if(t==='text') return renderText(rid,p);
    if(t==='noise_corrected') return renderNoiseCorrected(rid,p);
    if(t==='airchange') return renderAirchange(rid,p);
    if(t==='airchange_speed_only') return renderAirchangeSpeedOnly(rid,p);
    if(t==='pass_box_volume') return renderPassBoxVolume(rid,p);
    if(t==='particle_zone') return renderParticleZone(rid,p);
    if(t==='particle_4') return renderParticle4(rid,p);
    if(t==='particle_4_051') return renderParticle4_051(rid,p);
    if(t==='particle_4_8') return renderParticle4_8(rid,p);
    if(t==='bacteria_zone') return renderBacteriaZone(rid,p);
    if(t==='bacteria_zone_control') return renderBacteriaZoneControl(rid,p);
    if(t==='bacteria_control') return renderBacteriaControl(rid,p);
    if(t==='settling') return renderSettling(rid,p);
    if(t==='settling_control') return renderSettlingControl(rid,p);
    if(t==='floating') return renderFloating(rid,p);
    if(t==='floating_control') return renderFloatingControl(rid,p);
    if(t==='pressure_bsl') return renderPressureBSL(rid,p);
    if(t==='temp_diff') return renderTempDiff(rid,p);
    if(t==='pass_fail') return renderPassFail(rid,p);
    if(t==='wind_uniformity') return renderWindUniformity(rid,p);
    if(t==='illumination_uniformity') return renderIllumUniformity(rid,p);
    return renderNumeric(rid,p);
}

function renderPassBoxVolume(rid,p){
    let h = '';
    h += `<div class="dp dp-wide" data-dp-passbox-volume="${p.key}">`;
    h += `<div style="font-size:12px;color:#666;margin-bottom:6px;">先录入传递窗箱体内尺寸，自动计算体积，供换气次数共用</div>`;
    h += `<div class="sub-grid" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;">`;
    h += `<div class="sub-item"><label>内长(m)</label><input type="number" step="any" data-dim="length" oninput="calc_pass_box_volume('${rid}')"></div>`;
    h += `<div class="sub-item"><label>内宽(m)</label><input type="number" step="any" data-dim="width" oninput="calc_pass_box_volume('${rid}')"></div>`;
    h += `<div class="sub-item"><label>内高(m)</label><input type="number" step="any" data-dim="height" oninput="calc_pass_box_volume('${rid}')"></div>`;
    h += `</div>`;
    h += `<div style="margin-top:6px;padding:6px;background:#f0f0f0;border-radius:4px;font-size:12px;" data-passbox-volume="shared">`;
    h += `<span style="color:#666;">体积:</span><span style="font-weight:bold;color:#333;">--</span>`;
    h += `</div>`;
    h += `</div>`;
    return h;
}

function renderAirchangeSpeedOnly(rid,p){
    const pr = getParamRange(rid, p.key);
    const displayRange = pr.range || p.range || '';
    const displayUnit = pr.unit || p.unit || '次/h';
    const displayStd = pr.standard || '';
    let h = '';
    if(displayRange){
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span><span style="color:#2e7d32;">${displayRange} ${displayUnit}</span>${displayStd ? ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>` : ''}`;
        h += `</div>`;
    }
    h += `<div class="dp dp-wide" data-dp-airspeedonly="${p.key}">`;
    h += `<div style="font-size:12px;color:#666;margin-bottom:6px;">仅按风速仪法录入风口面积与风速，自动计算换气次数</div>`;
    h += `<div data-ac-vents="${p.key}">`;
    h += `<div class="vent-grid" data-vent-row>
        <div class="vent-item"><label>面积(m²)</label><input type="number" step="any" data-va oninput="calc_airchange('${rid}','${p.key}')"></div>
        <div class="vent-item"><label>风速(m/s)</label><input type="number" step="any" data-vs oninput="calc_airchange('${rid}','${p.key}')"></div>
        <div class="vent-item"><label>风量(m³/h)</label><input type="number" step="any" data-vq readonly style="background:#f5f5f5;"></div>
    </div>`;
    h += `</div>`;
    h += `<button class="add-pt" style="margin-top:6px;width:100%;" onclick="addVent('${rid}','${p.key}')">+ 添加风口</button>`;
    h += `</div>`;
    h += `<div class="cr"><span>结果:</span><span class="cv" data-res="${p.key}">-</span></div>`;
    return h;
}

function calc_pass_box_volume(rid){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return;
    const length = parseFloat(room.querySelector('.pb[data-pk="box_inner_size"] [data-dim="length"]')?.value);
    const width = parseFloat(room.querySelector('.pb[data-pk="box_inner_size"] [data-dim="width"]')?.value);
    const height = parseFloat(room.querySelector('.pb[data-pk="box_inner_size"] [data-dim="height"]')?.value);
    const boxes = room.querySelectorAll('[data-passbox-volume]');
    if(isNaN(length) || isNaN(width) || isNaN(height) || length <= 0 || width <= 0 || height <= 0){
        boxes.forEach(box => box.innerHTML = `<span style="color:#666;">体积:</span><span style="font-weight:bold;color:#333;">--</span>`);
        setRes(rid,'box_inner_size','-','');
        return;
    }
    const volume = length * width * height;
    boxes.forEach(box => box.innerHTML = `<span style="color:#666;">体积:</span><span style="font-weight:bold;color:#333;">${volume.toFixed(3)} m³</span>`);
    setRes(rid,'box_inner_size',`${volume.toFixed(3)} m³`,true);
    calc_airchange(rid,'airchange_b12');
    calc_airchange(rid,'airchange_b3');
}

// 符合/不符合按钮选择
function renderPassFail(rid,p){
    return `<div class="dp" data-dp="${p.key}" style="display:flex;gap:8px;margin:6px 0;">
        <button type="button" class="level-btn" style="padding:6px 16px;font-size:13px;" onclick="selPassFail('${rid}','${p.key}',true,this)">符合要求</button>
        <button type="button" class="level-btn" style="padding:6px 16px;font-size:13px;" onclick="selPassFail('${rid}','${p.key}',false,this)">不符合要求</button>
    </div>`;
}

function selPassFail(rid, pk, pass, btn){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const container = room.querySelector(`[data-pk="${pk}"] [data-dp="${pk}"]`);
    if(container) container.querySelectorAll('.level-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    room.dataset['pf_'+pk] = pass ? 'pass' : 'fail';
    setRes(rid, pk, pass ? '符合要求 ✅' : '不符合要求 ❌', pass);
}

// 最大日温差:最高温度 - 最低温度 = 温差
function renderTempDiff(rid,p){
    let h = `<div class="dp" data-dp="${p.key}" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">`;
    h += `<input type="number" step="any" placeholder="最高温度" style="width:90px;" data-td="high" oninput="calc_temp_diff('${rid}','${p.key}')">`;
    h += `<span style="font-size:14px;color:#666;">-</span>`;
    h += `<input type="number" step="any" placeholder="最低温度" style="width:90px;" data-td="low" oninput="calc_temp_diff('${rid}','${p.key}')">`;
    h += `<span style="font-size:14px;color:#666;">=</span>`;
    h += `<input type="number" step="any" placeholder="温差" style="width:80px;background:#f5f5f5;" data-td="diff" readonly>`;
    h += `<span style="font-size:12px;color:#888;">°C</span>`;
    h += `</div>`;
    return h;
}

function calc_temp_diff(rid, pk){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const pb = room.querySelector(`[data-pk="${pk}"]`);
    if(!pb) return;
    const high = parseFloat(pb.querySelector('[data-td="high"]').value);
    const low = parseFloat(pb.querySelector('[data-td="low"]').value);
    const diffInput = pb.querySelector('[data-td="diff"]');
    if(isNaN(high) || isNaN(low)){ diffInput.value=''; setRes(rid,pk,'-',''); return; }
    const diff = Math.abs(high - low);
    diffInput.value = diff.toFixed(1);
    const range = getParamRange(rid, pk).range || '';
    const pass = judgeRange(diff, range);
    setRes(rid, pk, diff.toFixed(1)+' °C', pass);
}

// 生物安全领域压差:正压/负压切换+可编辑范围+数据录入
function renderPressureBSL(rid,p){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    const isHospitalAuxPressure = detType && detType.id === 'operating_room' && (room?.dataset.surgeryRoomType || '') === '洁净辅房';
    const pr = getParamRange(rid, p.key);
    const displayRange = isHospitalAuxPressure && !pr.range ? '5～10' : (pr.range || '');
    const displayStandard = isHospitalAuxPressure && !pr.range ? 'GB 50333-2013' : (pr.standard || '');
    const {unit} = pr;
    const stdLabel = displayStandard || '';
    let h = '';
    if(displayRange) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${displayRange} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div class="dp-bsl-pressure" data-dp-bsl="${p.key}" data-rid="${rid}">`;
    h += `<div style="font-size:12px;color:#666;margin-bottom:4px;">相对房间 + 静压差(支持多组)</div>`;
    h += `<div data-bsl-pairs="${p.key}">`;
    h += renderPressurePairRow(rid,p.key,1);
    h += `</div>`;
    h += `<button class="add-pt" style="margin-top:6px;width:100%;" onclick="addPressurePair('${rid}','${p.key}')">+ 添加相对房间</button>`;
    h += `</div>`;
    h += `<div class="cr"><span>结果:</span><span class="cv" data-res="${p.key}">-</span></div>`;
    return h;
}

function renderPressurePairRow(rid, pk, index, refRoom='', values=[]){
    const vals = Array.isArray(values) && values.length ? values : ['','',''];
    const pr = getParamRange(rid, pk);
    const defaultRange = pr?.range || '';
    let h = `<div class="pressure-pair-row" data-pressure-pair-row="${pk}" style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin-bottom:8px;background:#fafafa;">`;
    h += `<div style="display:flex;gap:6px;align-items:center;margin-bottom:8px;">`;
    h += `<span style="font-size:12px;color:#888;white-space:nowrap;">相对房间${index}:</span>`;
    h += `<input type="text" placeholder="如:走廊、缓冲间" value="${refRoom||''}" style="flex:1;border:1px solid #ddd;padding:4px 6px;border-radius:4px;font-size:12px;" data-bsl-ref-room="${pk}" oninput="calc_pressure_pairs('${rid}','${pk}')">`;
    h += `<button type="button" class="add-pt" style="width:auto;padding:4px 8px;" onclick="removePressurePair(this,'${rid}','${pk}')">删除</button>`;
    h += `</div>`;
    h += `<div style="display:flex;gap:6px;align-items:center;margin-bottom:8px;flex-wrap:wrap;">`;
    h += `<button type="button" class="level-btn active" style="padding:4px 12px;font-size:12px;" onclick="switchPressurePairType('${rid}','${pk}',this,'positive')" data-pair-ptype="positive">正压</button>`;
    h += `<button type="button" class="level-btn" style="padding:4px 12px;font-size:12px;" onclick="switchPressurePairType('${rid}','${pk}',this,'negative')" data-pair-ptype="negative">负压</button>`;
    h += `<span style="font-size:12px;color:#888;margin-left:6px;">判定范围:</span>`;
    h += `<input type="text" value="${defaultRange}" placeholder="如:≥10" style="width:100px;border:1px solid #ddd;padding:4px 6px;border-radius:4px;font-size:12px;" data-pair-range="${pk}" oninput="calc_pressure_pairs('${rid}','${pk}')">`;
    h += `</div>`;
    h += `<div style="font-size:12px;color:#666;margin-bottom:4px;">该组静压差测点值:</div>`;
    h += `<div class="dp" data-dp="${pk}">`;
    for(let i=0;i<3;i++) h += `<input type="number" step="any" placeholder="${i+1}" value="${vals[i]||''}" oninput="calc_pressure_pairs('${rid}','${pk}')">`;
    h += `<button class="add-pt" onclick="addPressureValuePt(this,'${rid}','${pk}')">+</button>`;
    h += `</div>`;
    h += `<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:12px;">`;
    h += `<div><span style="color:#888;">该组平均值:</span><span data-pressure-pair-avg="${pk}">-</span></div>`;
    h += `<div><span style="color:#888;">该组判定结果:</span><span data-pressure-pair-judge="${pk}">-</span></div>`;
    h += `</div>`;
    h += `</div>`;
    return h;
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

function calc_pressure_pairs(rid, pk){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const pb = room?.querySelector(`[data-pk="${pk}"]`);
    if(!pb) return;
    const pairRows = Array.from(pb.querySelectorAll('[data-pressure-pair-row]'));
    const dbRange = getParamRange(rid, pk).range || '';

    const summaries = [];
    let completeCount = 0;
    let failCount = 0;
    let passCount = 0;

    pairRows.forEach((row, idx)=>{
        const avgEl = row.querySelector(`[data-pressure-pair-avg="${pk}"]`);
        const judgeEl = row.querySelector(`[data-pressure-pair-judge="${pk}"]`);
        const refRoom = (row.querySelector(`[data-bsl-ref-room="${pk}"]`)?.value || '').trim() || `相对房间${idx+1}`;
        const manualRange = (row.querySelector(`[data-pair-range="${pk}"]`)?.value || '').trim();
        const effectiveRange = manualRange || dbRange;
        const vals = [];
        row.querySelectorAll(`[data-dp="${pk}"] input`).forEach(i=>{
            const raw = (i.value || '').trim();
            const v = parseFloat(raw);
            if(!isNaN(v)) vals.push(v);
        });

        if(!vals.length){
            if(avgEl) avgEl.textContent = '-';
            if(judgeEl) judgeEl.textContent = '-';
            return;
        }

        const avg = vals.reduce((a,b)=>a+b,0)/vals.length;
        const pass = effectiveRange ? judgeRange(avg, effectiveRange) : false;
        const avgText = `${avg.toFixed(1)} Pa`;
        if(avgEl) avgEl.textContent = avgText;
        if(judgeEl) judgeEl.textContent = pass===true ? '符合要求' : (pass===false ? '不符合要求' : '-');

        summaries.push(`${refRoom}:${avg.toFixed(1)} Pa${manualRange ? `[手动:${manualRange}]` : (dbRange ? `[数据库:${dbRange}]` : '')}`);
        completeCount += 1;
        if(pass === true) passCount += 1;
        if(pass === false) failCount += 1;
    });

    if(completeCount > 0){
        room.dataset[`pressurePairSummary_${pk}`] = summaries.join('；');
        room.dataset[`pressurePairCarrier_${pk}`] = 'true';
    } else {
        delete room.dataset[`pressurePairSummary_${pk}`];
        if(pb){
            room.dataset[`pressurePairCarrier_${pk}`] = 'true';
        } else {
            delete room.dataset[`pressurePairCarrier_${pk}`];
        }
        setRes(rid, pk, '-', '');
        updateRoomSummary(rid);
        return;
    }

    if(failCount > 0){
        setRes(rid, pk, `共${completeCount}组压差：${failCount}组不符合要求`, false);
    } else if(passCount === completeCount){
        setRes(rid, pk, `共${completeCount}组压差：全部符合要求`, true);
    } else {
        setRes(rid, pk, `共${completeCount}组压差：待补全`, '');
    }
    updateRoomSummary(rid);
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

// 普通数值:默认3个输入框+扩展按钮
function renderNumeric(rid,p){
    if(p.inputType === 'numeric_range_manual'){
        return renderNumericRangeManual(rid,p);
    }
    const pr = getParamRange(rid, p.key);
    const displayRange = pr.range || '';
    const displayUnit = pr.unit || p.unit || '';
    const displayStd = pr.standard || '';
    const inputMin = ['temperature','humidity'].includes(p.key) ? '' : ' min="0"';
    let h = '';
    if(displayRange){
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${displayRange} ${displayUnit}</span>`;
        if(displayStd) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>`;
        h += `</div>`;
    }
    h += `<div class="dp" data-dp="${p.key}">`;
    for(let i=0;i<3;i++) h+=`<input type="number" step="any"${inputMin} placeholder="${i+1}" oninput="calc_numeric('${rid}','${p.key}')">`;
    h+=`<button class="add-pt" onclick="addPt('${rid}','${p.key}')">+</button></div>`;
    return h;
}

function renderNumericRangeManual(rid,p){
    const pr = getParamRange(rid, p.key);
    const displayRange = pr.range || '';
    const stdLabel = pr.standard || '';
    const inputMin = ['temperature','humidity'].includes(p.key) ? '' : ' min="0"';
    let h=`<div style="display:flex;flex-direction:column;gap:8px;">`;
    h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;">`;
    h+=`<span style="color:#2e7d32;font-weight:600;">📋 判定范围:</span><span class="pb-range-value" style="color:#2e7d32;">${displayRange}</span>${stdLabel ? ` <span class="pb-range-std" style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>` : ''}</div>`;
    h+=`<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:12px;color:#666;">`;
    h+=`<span>修改判定:</span>`;
    h+=`<input type="number" step="any" placeholder="下限" style="width:65px;border:1px solid #ddd;padding:4px 6px;border-radius:4px;font-size:12px;" data-mr-min="${p.key}" oninput="handleManualRangeChange('${rid}','${p.key}')">`;
    h+=`<span style="margin:0 2px;">~</span>`;
    h+=`<input type="number" step="any" placeholder="上限" style="width:65px;border:1px solid #ddd;padding:4px 6px;border-radius:4px;font-size:12px;" data-mr-max="${p.key}" oninput="handleManualRangeChange('${rid}','${p.key}')">`;
    h+=`<span>${p.unit||''}</span>`;
    h+=`</div>`;
    h+=`<div class="dp" data-dp="${p.key}">`;
    for(let i=0;i<3;i++) h+=`<input type="number" step="any"${inputMin} placeholder="${i+1}" oninput="calc_numeric('${rid}','${p.key}')">`;
    h+=`<button class="add-pt" onclick="addPt('${rid}','${p.key}')">+</button></div>`;
    h+=`</div>`;
    return h;
}

// 高效过滤器检漏(多对象)
function renderHepaLeakMulti(rid,p){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const pr = getParamRange(rid, p.key);
    const displayRange = pr.range || '';
    const displayUnit = pr.unit || p.unit || '%';
    const stdLabel = pr.standard || '';
    if(room && room.dataset.hepaLeakSummarySource && !room.dataset.hepaLeakSourceState){
        room.dataset.hepaLeakSourceState = 'saved';
    }
    
    let h=`<div class="hepa-multi-container" data-hepa-container="${p.key}">`;
    h+=`<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
    h+=`<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
    h+=`<span style="color:#2e7d32;">${displayRange} ${displayUnit}</span>`;
    h+=` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
    h+=`</div>`;
    h+=`<div class="hepa-object" data-hepa-idx="0" style="border:1px solid #e0e0e0;border-radius:6px;padding:12px;background:#fafafa;margin-bottom:8px;">`;
    h+=`<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">`;
    h+=`<input type="text" placeholder="检测对象名称（如：送风口1）" class="hepa-name" style="flex:1;padding:6px;border:1px solid #ddd;border-radius:4px;font-size:13px;" oninput="calc_hepa_multi('${rid}','${p.key}')">`;
    h+=`<button class="del-hepa-obj" onclick="delHepaObj('${rid}','${p.key}',0)" style="padding:4px 8px;background:#ff5252;color:white;border:none;border-radius:3px;cursor:pointer;font-size:12px;">删除</button>`;
    h+=`</div>`;
    h+=`<div style="display:flex;align-items:center;gap:8px;">`;
    h+=`<span style="color:#666;font-size:13px;">检测值：</span>`;
    h+=`<input type="number" step="any" min="0" placeholder="输入检测值" data-hepa-value="${p.key}-0" style="flex:1;padding:6px;border:1px solid #ddd;border-radius:4px;" oninput="calc_hepa_multi('${rid}','${p.key}')">`;
    h+=`<span style="color:#666;font-size:13px;">${displayUnit}</span>`;
    h+=`</div>`;
    h+=`<div class="cr" style="margin-top:8px;"><span>结果:</span><span class="cv" data-hepa-res="${p.key}-0">-</span></div>`;
    h+=`</div>`;
    h+=`<button class="add-pt" style="margin-top:6px;width:100%;" onclick="addHepaObj('${rid}','${p.key}')">＋ 添加检测对象</button>`;
    h+=`</div>`;
    h+=`<div class="cr"><span>结果:</span><span class="cv" data-res="${p.key}">-</span></div>`;
    return h;
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

// 文本输入
function renderText(rid,p){
    return `<div class="dp dp-wide"><input type="text" style="width:100%;text-align:left;" placeholder="输入观察结果" data-tv="${p.key}" oninput="calc_text('${rid}','${p.key}')"></div>`;
}

// 换气次数:风速仪法/风量仪法切换
function renderAirchange(rid,p){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    const typeId = room?.dataset?.typeId || detType?.id || '';
    const isIvc = typeId === 'ivc';
    const hospitalAirchangeKeys = ['airchange','airchange_clean'];
    const hospitalNeedsGenericRange = false;
    const isNegativePressureCleanArea = detType && detType.id === 'negative_pressure' && p.key === 'airchange_clean';
    const pr = isNegativePressureCleanArea
        ? (() => {
            const activeStds = JSON.parse(room?.dataset.judgementPriority || '[]').filter(c => JSON.parse(room?.dataset.judgementChecked || '[]').includes(c));
            const stdCode = activeStds.includes('GB/T 35428-2017') ? 'GB/T 35428-2017' : (activeStds[activeStds.length - 1] || 'GB/T 35428-2017');
            const stdRanges = SYSTEM_DB.standardRanges?.[stdCode]?.negative_pressure || SYSTEM_DB.standardRanges?.['GB/T 35428-2017']?.negative_pressure || {};
            const obj = stdRanges?._default?.airchange_clean || stdRanges?.airchange_clean || null;
            return obj ? { range: obj.range || '', unit: obj.unit || p.unit || '', standard: stdCode } : { range: p.range || '', unit: p.unit || '', standard: stdCode };
        })()
        : getParamRange(rid, p.key);
    const {range, unit, standard} = pr;
    const stdLabel = standard || '';
    let h = '';
    if(!hospitalNeedsGenericRange && range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    if(isIvc){
    }
    h += `<div class="method-switch">
        <div class="method-btn active" onclick="switchMethod('${rid}','${p.key}','speed',this)">风速仪法</div>
        <div class="method-btn" onclick="switchMethod('${rid}','${p.key}','volume',this)">风量仪法</div>
    </div>
    <div data-ac-panel="${p.key}">
        <div data-ac-speed="${p.key}">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">风口数据(每行一个风口):</div>
            <div data-ac-vents="${p.key}">
                <div class="vent-grid" data-vent-row>
                    <div class="vent-item"><label>面积(m2)</label><input type="number" step="any" data-va oninput="calc_airchange('${rid}','${p.key}')"></div>
                    <div class="vent-item"><label>风速(m/s)</label><input type="number" step="any" data-vs oninput="calc_airchange('${rid}','${p.key}')"></div>
                    <div class="vent-item"><label>风量(m3/h)</label><input type="number" step="any" data-vq readonly style="background:#f0f0f0;"></div>
                </div>
            </div>
            <button class="add-pt" style="width:100%;margin-top:6px;" onclick="addVent('${rid}','${p.key}')">+ 添加风口</button>
        </div>
        <div data-ac-volume="${p.key}" class="hidden">
            <div style="font-size:12px;color:#666;margin-bottom:4px;">直接输入各风口风量(m3/h):</div>
            <div class="dp" data-dp-vol="${p.key}">
                <input type="number" step="any" placeholder="风口1" oninput="calc_airchange_vol('${rid}','${p.key}')">
                <input type="number" step="any" placeholder="风口2" oninput="calc_airchange_vol('${rid}','${p.key}')">
                <input type="number" step="any" placeholder="风口3" oninput="calc_airchange_vol('${rid}','${p.key}')">
                <button class="add-pt" onclick="addVolPt('${rid}','${p.key}')">+</button>
            </div>
        </div>
    </div>`;
    return h;
}

// 噪声修正
function renderNoiseCorrected(rid,p){
    const {range, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';
    let h = '';
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div class="sub-grid">
        <div class="sub-item"><label>本底噪声</label><input type="number" step="0.1" data-noise="background" oninput="calc_noise('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>室内噪声</label><input type="number" step="0.1" data-noise="indoor" oninput="calc_noise('${rid}','${p.key}')"></div>
    </div>
    <div style="margin-top:6px;padding:6px;background:#f0f0f0;border-radius:4px;font-size:12px;" data-noise-result="${p.key}">
        <span style="color:#666;">修正后噪声:</span><span style="font-weight:bold;color:#333;">--</span>
    </div>`;
    return h;
}

// 洁净度(分手术区/周边区)- 医院用
function renderParticleZone(rid,p){
    const lbl_op = p.zone_label_op || '手术区';
    const lbl_surr = p.zone_label_surr || '周边区';
    const pr = getParamRange(rid, p.key);
    const stdLabel = pr?.standard || '';
    const rangeOp = pr?.range_op || '';
    const rangeSurr = pr?.range_surr || '';
    let rangeBlock = '';
    if(rangeOp || rangeSurr){
        rangeBlock += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        rangeBlock += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        rangeBlock += `${lbl_op}:<span style="color:#2e7d32;">${rangeOp || '-'}</span> | ${lbl_surr}:<span style="color:#2e7d32;">${rangeSurr || '-'}</span>`;
        if(stdLabel) rangeBlock += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        rangeBlock += `</div>`;
    }
    return `${rangeBlock}<div class="zone-label">🔵 ${lbl_op}</div>
    <div class="sub-grid">
        <div class="sub-item"><label>≥0.5μm 最大值</label><input type="number" data-pz="op_05_max" oninput="calc_pzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥0.5μm 95%UCL</label><input type="number" data-pz="op_05_ucl" oninput="calc_pzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥5μm 最大值</label><input type="number" data-pz="op_5_max" oninput="calc_pzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥5μm 95%UCL</label><input type="number" data-pz="op_5_ucl" oninput="calc_pzone('${rid}','${p.key}')"></div>
    </div>
    <div class="zone-label">🟢 ${lbl_surr}</div>
    <div class="sub-grid">
        <div class="sub-item"><label>≥0.5μm 最大值</label><input type="number" data-pz="surr_05_max" oninput="calc_pzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥0.5μm 95%UCL</label><input type="number" data-pz="surr_05_ucl" oninput="calc_pzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥5μm 最大值</label><input type="number" data-pz="surr_5_max" oninput="calc_pzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥5μm 95%UCL</label><input type="number" data-pz="surr_5_ucl" oninput="calc_pzone('${rid}','${p.key}')"></div>
    </div>`;
}

// 洁净度(4个值)- 非医院用
function renderParticle4(rid,p){
    const pr = getParamRange(rid, p.key);
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const isCleanFunction = (room?.dataset.typeId || '') === 'clean_function_room';
    const displayRange = pr.range || '';
    const displayUnit = pr.unit || p.unit || '';
    const displayStd = pr.standard || '';
    let h = '';
    if(displayRange){
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${displayRange}${displayUnit ? ` ${displayUnit}` : ''}</span>`;
        if(displayStd) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>`;
        h += `</div>`;
    }
    h += `<div class="sub-grid">`;
    h += `<div class="sub-item"><label>≥0.5μm 最大值</label><input type="number" data-p4="p05_max" oninput="calc_p4('${rid}','${p.key}')"></div>`;
    h += `<div class="sub-item"><label>≥0.5μm 95%UCL</label><input type="number" data-p4="p05_ucl" oninput="calc_p4('${rid}','${p.key}')"></div>`;
    h += `<div class="sub-item"><label>≥5μm 最大值</label><input type="number" data-p4="p5_max" oninput="calc_p4('${rid}','${p.key}')"></div>`;
    h += `<div class="sub-item"><label>≥5μm 95%UCL</label><input type="number" data-p4="p5_ucl" oninput="calc_p4('${rid}','${p.key}')"></div>`;
    h += `</div>`;
    return h;
}

function renderParticle4_051(rid,p){
    const pr = getParamRange(rid, p.key);
    const displayRange = pr.range || '';
    const displayUnit = pr.unit || p.unit || '';
    const displayStd = pr.standard || '';
    let h = '';
    if(displayRange){
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${displayRange} ${displayUnit}</span>`;
        if(displayStd) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>`;
        h += `</div>`;
    }
    return `${h}<div class="sub-grid">
        <div class="sub-item"><label>≥0.5μm 最大值</label><input type="number" data-p4="p05_max" oninput="calc_p4_051('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥0.5μm 95%UCL</label><input type="number" data-p4="p05_ucl" oninput="calc_p4_051('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥1μm 最大值</label><input type="number" data-p4="p1_max" oninput="calc_p4_051('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥1μm 95%UCL</label><input type="number" data-p4="p1_ucl" oninput="calc_p4_051('${rid}','${p.key}')"></div>
    </div>`;
}

function renderParticle4_8(rid,p){
    const pr = getParamRange(rid, p.key);
    const displayRange = pr.range || '';
    const displayUnit = pr.unit || p.unit || '';
    const displayStd = pr.standard || '';
    let h = '';
    if(displayRange){
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${displayRange} ${displayUnit}</span>`;
        if(displayStd) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${displayStd}]</span>`;
        h += `</div>`;
    }
    return `${h}<div class="sub-grid">
        <div class="sub-item"><label>≥0.5μm 最大值</label><input type="number" data-p48="p05_max" oninput="calc_p4_8('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥0.5μm 95%UCL</label><input type="number" data-p48="p05_ucl" oninput="calc_p4_8('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥5μm 最大值</label><input type="number" data-p48="p5_max" oninput="calc_p4_8('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>≥5μm 95%UCL</label><input type="number" data-p48="p5_ucl" oninput="calc_p4_8('${rid}','${p.key}')"></div>
    </div>`;
}

// 细菌浓度(分手术区/周边区)
function renderBacteriaZone(rid,p){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const pr = getParamRange(rid, p.key);
    const stdLabel = pr?.standard || '';
    const rangeOp = pr?.range_op || '';
    const rangeSurr = pr?.range_surr || '';
    let rangeBlock = '';
    if(rangeOp || rangeSurr){
        rangeBlock += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        rangeBlock += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        rangeBlock += `手术区:<span style="color:#2e7d32;">${rangeOp || '-'}</span> | 周边区:<span style="color:#2e7d32;">${rangeSurr || '-'}</span>`;
        if(stdLabel) rangeBlock += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        rangeBlock += `</div>`;
    }
    return `${rangeBlock}<div class="zone-label">🔵 手术区</div>
    <div class="sub-grid">
        <div class="sub-item"><label>采样点数</label><input type="number" data-bz="op_points" oninput="calc_bzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>采样总数(cfu)</label><input type="number" step="1" min="0" data-bz="op_total" oninput="calc_bzone('${rid}','${p.key}')"></div>
    </div>
    <div class="zone-label">🟢 周边区</div>
    <div class="sub-grid">
        <div class="sub-item"><label>采样点数</label><input type="number" data-bz="surr_points" oninput="calc_bzone('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>采样总数(cfu)</label><input type="number" step="1" min="0" data-bz="surr_total" oninput="calc_bzone('${rid}','${p.key}')"></div>
    </div>`;
}

// 沉降菌
function renderSettling(rid,p){
    const {range, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';
    let h = '';
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div class="sub-grid">
        <div class="sub-item"><label>采样点数</label><input type="number" min="0" step="1" data-st="points" oninput="calc_settling('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>采样总数(cfu)</label><input type="number" min="0" step="1" data-st="total" oninput="calc_settling('${rid}','${p.key}')"></div>
    </div>`;
    return h;
}

// 浮游菌
function renderFloating(rid,p){
    return `<div class="sub-grid" style="grid-template-columns:1fr 1fr;">
        <div class="sub-item"><label>采样量(L)</label><input type="number" step="any" min="0" data-fl="volume" oninput="calc_floating('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>菌落数(cfu/皿)</label><input type="number" min="0" step="1" data-fl="total" oninput="calc_floating('${rid}','${p.key}')"></div>
    </div>`;
}

// 风速不均匀度(自动计算)
function renderWindUniformity(rid,p){
    const {range, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';
    let h = '';
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div style="font-size:12px;color:#888;padding:6px;">⚡ 自动从"${p.sourceKey==='wind_speed'?'截面风速':p.sourceKey==='downflow_speed'?'下降气流流速':p.sourceKey==='avg_speed'?'垂直气流平均风速':p.sourceKey==='down_wind_speed'?'下降气流流速':'关联风速'}"数据计算</div>`;
    return h;
}

// 照度均匀度(自动计算)
function renderIllumUniformity(rid,p){
    const {range, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';
    let h = '';
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div style="font-size:12px;color:#888;padding:6px;">⚡ 自动从照度数据计算(最小值/平均值)</div>`;
    return h;
}

// ========== 计算函数 ==========

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

// 高效过滤器:增加检测对象
function addHepaObj(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const container=room.querySelector(`[data-hepa-container="${pk}"]`);
    const objs=container.querySelectorAll('.hepa-object');
    const newIdx=objs.length;

    let h=`<div class="hepa-object" data-hepa-idx="${newIdx}" style="border:1px solid #e0e0e0;border-radius:6px;padding:12px;background:#fafafa;margin-bottom:8px;">`;
    h+=`<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">`;
    h+=`<input type="text" placeholder="检测对象名称(如:送风口${newIdx+1})" class="hepa-name" style="flex:1;padding:6px;border:1px solid #ddd;border-radius:4px;font-size:13px;" oninput="calc_hepa_multi('${rid}','${pk}')">`;
    h+=`<button class="del-hepa-obj" onclick="delHepaObj('${rid}','${pk}',${newIdx})" style="padding:4px 8px;background:#ff5252;color:white;border:none;border-radius:3px;cursor:pointer;font-size:12px;">删除</button>`;
    h+=`</div>`;
    h+=`<div style="display:flex;align-items:center;gap:8px;">`;
    h+=`<span style="color:#666;font-size:13px;">检测值:</span>`;
    h+=`<input type="number" step="any" min="0" placeholder="输入检测值" data-hepa-value="${pk}-${newIdx}" style="flex:1;padding:6px;border:1px solid #ddd;border-radius:4px;" oninput="calc_hepa_multi('${rid}','${pk}')">`;
    h+=`<span style="color:#666;font-size:13px;">%</span>`;
    h+=`</div>`;
    h+=`<div class="cr" style="margin-top:8px;"><span>结果:</span><span class="cv" data-hepa-res="${pk}-${newIdx}">-</span></div>`;
    h+=`</div>`;

    const btn=container.querySelector('.add-pt');
    btn.insertAdjacentHTML('beforebegin', h);
}

// 高效过滤器:删除检测对象
function delHepaObj(rid,pk,idx){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const container=room.querySelector(`[data-hepa-container="${pk}"]`);
    const obj=container.querySelector(`[data-hepa-idx="${idx}"]`);
    if(container.querySelectorAll('.hepa-object').length <= 1){
        showToast('至少保留一个检测对象','error');
        return;
    }
    obj.remove();
    calc_hepa_multi(rid,pk);
    const firstObj = container.querySelector('.hepa-object');
    if(firstObj){
        const firstName = firstObj.querySelector('.hepa-name')?.value || '对象1';
        const pr = getParamRange(rid,pk);
        const sourceStandard = pr.standard || 'GB 50591-2010';
        room.dataset.hepaLeakSummary = `${firstName}:${pr.range||''}[${sourceStandard}]`;
        room.dataset.hepaLeakSummarySource = sourceStandard;
        room.dataset.hepaLeakSourceState = 'live';
    } else {
        delete room.dataset.hepaLeakSummary;
        delete room.dataset.hepaLeakSummarySource;
        delete room.dataset.hepaLeakSourceState;
    }
    updateRoomSummary(rid);
}

// 高效过滤器:增加数据点
// 高效过滤器:计算结果
// 高效过滤器:计算单个对象结果
function calc_hepa_single(rid,pk,idx){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const obj=room.querySelector(`[data-hepa-idx="${idx}"]`);
    const resSpan=room.querySelector(`[data-hepa-res="${pk}-${idx}"]`);

    if(!obj || !resSpan) return;

    const input = obj.querySelector(`[data-hepa-value="${pk}-${idx}"]`) || obj.querySelector('input[type="number"]');
    if(!input) return;
    const rawVal = (input.value || '').trim();
    const val=parseFloat(rawVal);

    if(rawVal === '' || isNaN(val)){
        resSpan.textContent='-';
        resSpan.style.color='#999';
        resSpan.style.background='';
        const container = room.querySelector(`[data-hepa-container="${pk}"]`);
        if(container){
            const firstObj = container.querySelector('.hepa-object');
            const otherEffective = Array.from(container.querySelectorAll(`[data-hepa-res^="${pk}-"]`))
                .map(el => (el.textContent || '').trim())
                .filter(v => v && v !== '-');
            if(firstObj){
                const firstName = firstObj?.querySelector('.hepa-name')?.value || '对象1';
                if(otherEffective.length > 0){
                    const pr = getParamRange(rid,pk);
                    const sourceStandard = pr.standard || 'GB 50591-2010';
                    room.dataset.hepaLeakSummary = `${firstName}:${pr.range||''}[${sourceStandard}]`;
                    room.dataset.hepaLeakSummarySource = sourceStandard;
                    room.dataset.hepaLeakSourceState = 'live';
                } else {
                    delete room.dataset.hepaLeakSummary;
                    delete room.dataset.hepaLeakSummarySource;
                    delete room.dataset.hepaLeakSourceState;
                }
            } else {
                delete room.dataset.hepaLeakSummary;
                delete room.dataset.hepaLeakSummarySource;
                delete room.dataset.hepaLeakSourceState;
            }
            updateRoomSummary(rid);
        }
        return;
    }

    // 保留4位小数
    const result=val.toFixed(4);

    // 获取判定范围（统一只依赖数据库命中结果）
    let {range}=getParamRange(rid,pk);

    // 判定（空字符串也交给 judgeRange 处理，它会返回 true）
    const pass = judgeRange(val, range);

    // 显示结果（参照温度的方式，添加✔️和❌）
    resSpan.textContent = result + '%' + (pass ? ' ✅' : ' ❌');
    resSpan.className = pass ? 'cv pass' : 'cv fail';

    const container = room.querySelector(`[data-hepa-container="${pk}"]`);
    if(container){
        const firstObj = container.querySelector('.hepa-object');
        const firstName = firstObj?.querySelector('.hepa-name')?.value || '对象1';
        const standard = getParamRange(rid,pk).standard || 'GB 50591-2010';
        room.dataset.hepaLeakSummary = `${firstName}:${range||''}[${standard}]`;
        room.dataset.hepaLeakSummarySource = standard;
        room.dataset.hepaLeakSourceState = rawVal ? 'live' : '';
        updateRoomSummary(rid);
    }
}

// 兼容旧的 calc_hepa_multi 调用
function calc_hepa_multi(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const container=room.querySelector(`[data-hepa-container="${pk}"]`);
    if(!container) return;
    const objs=container.querySelectorAll('.hepa-object');
    objs.forEach((obj,idx)=>{
        calc_hepa_single(rid,pk,idx);
    });

    const resultEls = Array.from(container.querySelectorAll(`[data-hepa-res^="${pk}-"]`));
    const values = resultEls.map(el => (el.textContent || '').trim()).filter(Boolean);
    const effective = values.filter(v => v && v !== '-');
    if(effective.length === 0){
        room.dataset.hepaLeakSourceState = '';
        delete room.dataset.hepaLeakSummary;
        delete room.dataset.hepaLeakSummarySource;
        setRes(rid, pk, '-', '');
    } else {
        const failCount = effective.filter(v => v.includes('❌')).length;
        const passCount = effective.filter(v => v.includes('✅')).length;
        const totalCount = effective.length;
        if(failCount > 0){
            setRes(rid, pk, `共${totalCount}个检测对象：${failCount}项不合格`, false);
        } else if(passCount === totalCount){
            setRes(rid, pk, `共${totalCount}个检测对象：全部合格`, true);
        } else {
            setRes(rid, pk, `共${totalCount}个检测对象：待补全`, '');
        }
    }

    const firstObj = container.querySelector('.hepa-object');
    if(firstObj){
        const firstName = firstObj.querySelector('.hepa-name')?.value || '对象1';
        if(effective.length > 0){
            const pr = getParamRange(rid,pk);
            const sourceStandard = pr.standard || 'GB 50591-2010';
            room.dataset.hepaLeakSummary = `${firstName}:${pr.range||''}[${sourceStandard}]`;
            room.dataset.hepaLeakSummarySource = sourceStandard;
            room.dataset.hepaLeakSourceState = 'live';
        } else {
            delete room.dataset.hepaLeakSummary;
            delete room.dataset.hepaLeakSummarySource;
            delete room.dataset.hepaLeakSourceState;
        }
    } else {
        delete room.dataset.hepaLeakSummary;
        delete room.dataset.hepaLeakSummarySource;
        delete room.dataset.hepaLeakSourceState;
    }
    updateRoomSummary(rid);
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

function getRoomVolume(rid){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    let l=parseFloat(room.querySelector('[data-room-dimensions] [data-dim="length"]')?.value)||0;
    let w=parseFloat(room.querySelector('[data-room-dimensions] [data-dim="width"]')?.value)||0;
    let h=parseFloat(room.querySelector('[data-room-dimensions] [data-dim="height"]')?.value)||0;
    if((room?.dataset.typeId || '') === 'pass_box' && (!l || !w || !h)){
        l = parseFloat(room.querySelector('.pb[data-pk="box_inner_size"] [data-dim="length"]')?.value)||0;
        w = parseFloat(room.querySelector('.pb[data-pk="box_inner_size"] [data-dim="width"]')?.value)||0;
        h = parseFloat(room.querySelector('.pb[data-pk="box_inner_size"] [data-dim="height"]')?.value)||0;
    }
    return l*w*h;
}

function handleRoomDimensionChange(rid){
    const room = document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return;
    room.querySelectorAll('.pb[data-itype="airchange"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_airchange(rid, pk);
    });
    room.querySelectorAll('.pb[data-itype="airchange_speed_only"]').forEach(pb => {
        const pk = pb.dataset.pk;
        if(pk) calc_airchange(rid, pk);
    });
    updateRoomSummary(rid);
}

// 普通数值计算
function calc_numeric(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    // 从数据源读取判定范围
    const pr = getParamRange(rid, pk);
    let range = pr.range;
    const unit = pr.unit;

    // 如果是 numeric_range_manual 类型,允许读取界面手动修改后的判定范围（合法保留场景）
    const itype = pb.dataset.itype;
    if(itype === 'numeric_range_manual'){
        const rangeText = getDisplayRangeText(pb);
        if(rangeText){
            range = rangeText;
        }
    }

    // 动物房普通环境的部分参数强制走标准库映射,避免旧内联范围或空范围导致判定不生效
    const detType = getRoomDetType(rid);
    const cleanClass = room?.dataset.cleanClass || '';
    if(detType?.id === 'animal_room' && ['普通环境','隔离环境'].includes(cleanClass) && ['humidity','work_illumination','animal_illumination','cage_airspeed'].includes(pk)){
        range = pr.range || range;
    }

    // 从DOM中读取参数信息
    const paramName = pb.querySelector('.pb-name')?.textContent;

    const inputs=room.querySelectorAll(`[data-dp="${pk}"] input`);
    const vals=Array.from(inputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    if(!vals.length){setRes(rid,pk,'-','');return;}

    let result;
    const calcText = pb.querySelector('.pb-calc')?.textContent;
    if(calcText && calcText.includes('平均值')) result=vals.reduce((a,b)=>a+b,0)/vals.length;
    else if(calcText && calcText.includes('最小值')) result=Math.min(...vals);
    else if(calcText && calcText.includes('最大值')) result=Math.max(...vals);
    else result=vals[0];

    const pass=judgeRange(result,range);

    // 根据参数类型设置小数位数
    let decimals = 2;
    if(paramName && (paramName.includes('温度') || paramName.includes('湿度') || paramName.includes('噪声') || paramName.includes('静压差'))) decimals = 1;
    else if(paramName && paramName.includes('照度均匀度')) decimals = 2;
    else if(paramName && (paramName.includes('照度') || paramName.includes('最低照度'))) decimals = 0;
    else if(paramName && paramName.includes('高效过滤器')) decimals = 4;
    else if(paramName && (paramName.includes('截面风速') || paramName.includes('风速不均匀度') || paramName.includes('气流速度'))) decimals = 2;

    setRes(rid,pk,result.toFixed(decimals)+' '+unit,pass);

    // 触发关联计算(风速不均匀度、照度均匀度)
    if(itype === 'numeric'){
        // 检查是否有关联的uniformity参数
        room.querySelectorAll('[data-itype="wind_uniformity"]').forEach(upb=>{
            const sourceKey = upb.dataset.sourcekey || upb.getAttribute('data-sourcekey');
            if(sourceKey === pk) calc_wind_uniformity(rid, upb.dataset.pk, vals);
        });
        room.querySelectorAll('[data-itype="illumination_uniformity"]').forEach(upb=>{
            const sourceKey = upb.dataset.sourcekey || upb.getAttribute('data-sourcekey');
            if(sourceKey === pk) calc_illum_uniformity(rid, upb.dataset.pk, vals);
        });
    }
}

// 通用:从DOM读取参数的判定范围
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

function getParamRange(rid, pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    if(!room) return {range:'',range_op:'',range_surr:'',unit:'',standard:''};

    const normalizeNegativePressureRangeKey = (typeId, key) => {
        if(typeId !== 'negative_pressure') return key;
        const aliasMap = {
            airchange_polluted: 'airchange',
            static_pressure_diff: 'pressure'
        };
        return aliasMap[key] || key;
    };

    // 统一参数业务key -> 范围key 映射：保证客户端参数与标准数据库参数一一对应
    const rangeKeyMap = {
        noise_corrected: 'noise',
        hepa_leak_multi: 'hepa_leak',
        settling_control: 'settling',
        floating_control: 'floating',
        bacteria_control: 'bacteria',
        bacteria_zone_control: 'bacteria',
        bacteria_zone: 'bacteria',
        particle_4: 'particle',
        particle_4_051: 'particle',
        particle_4_8: 'particle',
        airchange_clean: 'airchange_clean',
        illumination: 'illumination',
        work_illumination: 'work_illumination',
        illumination_main_room: 'illumination_main_room',
        illumination_aux_room: 'illumination_aux_room',
        illumination_min: 'illumination_min',
        airchange_b12: 'airchange_b12',
        airchange_b3: 'airchange_b3'
    };
    let rangePk = rangeKeyMap[pk] || pk;

    // 获取房间信息
    const detType = getRoomDetType(rid);
    if(!detType) return {range:'',range_op:'',range_surr:'',unit:'',standard:''};

    const typeId = detType.id;
    rangePk = normalizeNegativePressureRangeKey(typeId, rangePk);
    const pbEl = room.querySelector(`[data-pk="${pk}"]`);
    const inputType = pbEl?.dataset?.itype || '';
    if(typeId === 'clean_function_room' && pk === 'bacteria' && inputType === 'settling_control'){
        rangePk = 'settling';
    }
    const cleanClass = room.dataset.cleanClass || '';
    const barrierRoomClass = room.dataset.barrierRoomClass || '';
    const barrierAuxRoom = room.dataset.barrierAuxRoom || '';
    const cleanFunctionSubroom = room.dataset.cleanFunctionSubroom || '';
    const cleanFunctionStandardSubroom = room.dataset.cleanFunctionStandardSubroom || cleanFunctionSubroom;
    const surgeryAuxRoom = room.dataset.surgeryAuxRoom || '';
    const priorityList = JSON.parse(room.dataset.judgementPriority || '[]');
    const checkedList = JSON.parse(room.dataset.judgementChecked || '[]');
    const activeStds = priorityList.filter(c => checkedList.includes(c));

    const ranges = SYSTEM_DB.standardRanges || {};
    const isHospitalDomain = room.dataset.domain === 'hospital';
    const isHospitalParticle = isHospitalDomain && ['particle','particle_zone','particle_4','particle_4_051','particle_4_8'].includes(pk);
    const isGmpWorkshop = typeId === 'gmp_workshop';
    const isVetWorkshop = typeId === 'veterinary_gmp_workshop';
    const isLaminarHood = typeId === 'laminar_hood';
    const isPassBox = typeId === 'pass_box';
    const isElectronicsWorkshop = typeId === 'electronics_workshop';

    // 兽药车间判定来源固定规则：
    // 沉降菌→GB/T 16294-2010；浮游菌→GB/T 16293-2010；高效过滤器检漏→GB 50591-2010；其余→GB 50457-2019
    if(isGmpWorkshop){
        if(rangePk === 'settling'){
            const stdCode = 'GB/T 16294-2010';
            const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
            const obj = map?.[rangePk] || null;
            if(obj) return { range: obj.range || '', range_op: obj.range_op || '', range_surr: obj.range_surr || '', unit: obj.unit || '', standard: stdCode };
        }
        if(rangePk === 'floating'){
            const stdCode = 'GB/T 16293-2010';
            const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
            const obj = map?.[rangePk] || null;
            if(obj) return { range: obj.range || '', range_op: obj.range_op || '', range_surr: obj.range_surr || '', unit: obj.unit || '', standard: stdCode };
        }
        if(rangePk === 'hepa_leak'){
            const universalStdCode = 'GB 50591-2010';
            const universal = ranges[universalStdCode]?._universal || null;
            if(universal){
                const mapped = (cleanClass && universal[cleanClass]) || universal['_default'] || null;
                const hepaObj = mapped?.[rangePk] || null;
                if(hepaObj){
                    return {
                        range: (hepaObj.range || '').replace(/\s*%\s*$/,'').trim(),
                        range_op: hepaObj.range_op || '',
                        range_surr: hepaObj.range_surr || '',
                        unit: hepaObj.unit || '%',
                        standard: universalStdCode
                    };
                }
            }
            return {range:'≤0.01',range_op:'',range_surr:'',unit:'%',standard:universalStdCode};
        }
        const stdCode = 'GB 50457-2019';
        const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
        const obj = map?.[rangePk] || null;
        if(obj){
            return {
                range: obj.range || '',
                range_op: obj.range_op || '',
                range_surr: obj.range_surr || '',
                unit: obj.unit || '',
                standard: stdCode
            };
        }
    }

    if(isPassBox){
        if(rangePk === 'hepa_leak'){
            const universalStdCode = 'GB 50591-2010';
            const universal = ranges[universalStdCode]?._universal || null;
            if(universal){
                const mapped = universal['_default'] || null;
                const hepaObj = mapped?.[rangePk] || null;
                if(hepaObj){
                    return {
                        range: (hepaObj.range || '').replace(/\s*%\s*$/,'').trim(),
                        range_op: hepaObj.range_op || '',
                        range_surr: hepaObj.range_surr || '',
                        unit: hepaObj.unit || '%',
                        standard: universalStdCode
                    };
                }
            }
            return {range:'≤0.01',range_op:'',range_surr:'',unit:'%',standard:universalStdCode};
        }
        const stdCode = 'JG/T 382-2012';
        let map = ranges[stdCode]?.[typeId]?._default || null;
        if(rangePk === 'airchange_b12') map = ranges[stdCode]?.[typeId]?.['B1/B2型'] || map;
        if(rangePk === 'airchange_b3') map = ranges[stdCode]?.[typeId]?.['B3型'] || map;
        const obj = map?.[rangePk] || null;
        if(obj){
            return {
                range: obj.range || '',
                range_op: obj.range_op || '',
                range_surr: obj.range_surr || '',
                unit: obj.unit || '',
                standard: stdCode
            };
        }
    }

    if(isLaminarHood){
        if(rangePk === 'hepa_leak'){
            const universalStdCode = 'GB 50591-2010';
            const universal = ranges[universalStdCode]?._universal || null;
            if(universal){
                const mapped = universal['_default'] || null;
                const hepaObj = mapped?.[rangePk] || null;
                if(hepaObj){
                    return {
                        range: (hepaObj.range || '').replace(/\s*%\s*$/,'').trim(),
                        range_op: hepaObj.range_op || '',
                        range_surr: hepaObj.range_surr || '',
                        unit: hepaObj.unit || '%',
                        standard: universalStdCode
                    };
                }
            }
            return {range:'≤0.01',range_op:'',range_surr:'',unit:'%',standard:universalStdCode};
        }
        const stdCode = 'GB 50591-2010-laminar-hood';
        const map = ranges[stdCode]?.[typeId]?._default || null;
        const obj = map?.[rangePk] || null;
        if(obj){
            return {
                range: obj.range || '',
                range_op: obj.range_op || '',
                range_surr: obj.range_surr || '',
                unit: obj.unit || '',
                standard: 'GB 50591-2010'
            };
        }
    }


    if(isElectronicsWorkshop){
        if(rangePk === 'hepa_leak'){
            const universalStdCode = 'GB 50591-2010';
            const universal = ranges[universalStdCode]?._universal || null;
            if(universal){
                const mapped = (cleanClass && universal[cleanClass]) || universal['_default'] || null;
                const hepaObj = mapped?.[rangePk] || null;
                if(hepaObj){
                    return {
                        range: (hepaObj.range || '').replace(/\s*%\s*$/,'').trim(),
                        range_op: hepaObj.range_op || '',
                        range_surr: hepaObj.range_surr || '',
                        unit: hepaObj.unit || '%',
                        standard: universalStdCode
                    };
                }
            }
            return {range:'≤0.01',range_op:'',range_surr:'',unit:'%',standard:universalStdCode};
        }
        const stdCode = 'GB 50472-2008';
        const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
        const obj = map?.[rangePk] || null;
        if(obj){
            return {
                range: obj.range || '',
                range_op: obj.range_op || '',
                range_surr: obj.range_surr || '',
                unit: obj.unit || '',
                standard: stdCode
            };
        }
        if(rangePk === 'particle'){
            const fallbackStd = 'GB 50591-2010';
            const fallbackMap = ranges[fallbackStd]?._universal?.[cleanClass] || ranges[fallbackStd]?._universal?._default || null;
            const fallbackObj = fallbackMap?.[rangePk] || null;
            if(fallbackObj){
                return {
                    range: fallbackObj.range || '',
                    range_op: fallbackObj.range_op || '',
                    range_surr: fallbackObj.range_surr || '',
                    unit: fallbackObj.unit || '',
                    standard: fallbackStd
                };
            }
        }
    }

    if(isVetWorkshop){
        if(rangePk === 'settling'){
            const stdCode = 'GB/T 16294-2010';
            const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
            const obj = map?.[rangePk] || null;
            if(obj) return { range: obj.range || '', range_op: obj.range_op || '', range_surr: obj.range_surr || '', unit: obj.unit || '', standard: stdCode };
        }
        if(rangePk === 'floating'){
            const stdCode = 'GB/T 16293-2010';
            const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
            const obj = map?.[rangePk] || null;
            if(obj) return { range: obj.range || '', range_op: obj.range_op || '', range_surr: obj.range_surr || '', unit: obj.unit || '', standard: stdCode };
        }
        if(rangePk === 'hepa_leak'){
            const universalStdCode = 'GB 50591-2010';
            const universal = ranges[universalStdCode]?._universal || null;
            if(universal){
                const mapped = (cleanClass && universal[cleanClass]) || universal['_default'] || null;
                const hepaObj = mapped?.[rangePk] || null;
                if(hepaObj){
                    return {
                        range: (hepaObj.range || '').replace(/\s*%\s*$/,'').trim(),
                        range_op: hepaObj.range_op || '',
                        range_surr: hepaObj.range_surr || '',
                        unit: hepaObj.unit || '%',
                        standard: universalStdCode
                    };
                }
            }
            return {range:'≤0.01',range_op:'',range_surr:'',unit:'%',standard:universalStdCode};
        }
        const stdCode = 'GB 50457-2019';
        const map = ranges[stdCode]?.[typeId]?.[cleanClass] || ranges[stdCode]?.[typeId]?._default || null;
        const obj = map?.[rangePk] || null;
        if(obj){
            return {
                range: obj.range || '',
                range_op: obj.range_op || '',
                range_surr: obj.range_surr || '',
                unit: obj.unit || '',
                standard: stdCode
            };
        }
    }

    // 高效过滤器检漏是跨领域统一参数：所有领域统一按 GB 50591-2010 判定
    if(rangePk === 'hepa_leak'){
        const universalStdCode = 'GB 50591-2010';
        const universal = ranges[universalStdCode]?._universal || null;
        if(universal){
            const mapped = (cleanClass && universal[cleanClass]) || universal['_default'] || null;
            const hepaObj = mapped?.[rangePk] || null;
            if(hepaObj){
                return {
                    range: (hepaObj.range || '').replace(/\s*%\s*$/,'').trim(),
                    range_op: hepaObj.range_op || '',
                    range_surr: hepaObj.range_surr || '',
                    unit: hepaObj.unit || '%',
                    standard: universalStdCode
                };
            }
        }
        return {range:'≤0.01',range_op:'',range_surr:'',unit:'%',standard:universalStdCode};
    }

    if(activeStds.length === 0) return {range:'',range_op:'',range_surr:'',unit:'',standard:''};

    // 按优先级查找最后一个有该参数range的标准（后面的优先级更高）
    let finalResult = {range:'',range_op:'',range_surr:'',unit:'',standard:''};
    for(const stdCode of activeStds){
        const stdRanges = ranges[stdCode];
        if(!stdRanges) continue;

        let rangeMap = null;

        // 通用标准(如GB 50591-2010)
        if(stdRanges['_universal']){
            const u = stdRanges['_universal'];
            if(cleanClass && u[cleanClass]) rangeMap = u[cleanClass];
            else if(u['_default']) rangeMap = u['_default'];
        }
        // 专门标准
        else if(stdRanges[typeId]){
            const t = stdRanges[typeId];
            // 洁净辅房特殊处理（先取具体辅房，再叠加辅房等级范围）
            if(typeId === 'operating_room' && room.dataset.surgeryAuxRoom && t['辅房'] && t['辅房'][room.dataset.surgeryAuxRoom]){
                rangeMap = {
                    ...t['辅房'][room.dataset.surgeryAuxRoom],
                    ...((t['辅房等级'] && cleanClass && t['辅房等级'][cleanClass]) ? t['辅房等级'][cleanClass] : {})
                };
                if(rangePk === 'pressure' && !rangeMap[rangePk]){
                    const mainLevelMap = cleanClass && t[cleanClass] ? t[cleanClass] : null;
                    if(mainLevelMap?.[rangePk]) rangeMap[rangePk] = mainLevelMap[rangePk];
                }
                if(rangePk === 'illumination_min' && !rangeMap[rangePk] && t['辅房']?.[room.dataset.surgeryAuxRoom]?.[rangePk]){
                    rangeMap[rangePk] = t['辅房'][room.dataset.surgeryAuxRoom][rangePk];
                }
                if(rangePk === 'work_illumination' && !rangeMap[rangePk]){
                    if(t['辅房']?.[room.dataset.surgeryAuxRoom]?.illumination_min) rangeMap[rangePk] = t['辅房'][room.dataset.surgeryAuxRoom].illumination_min;
                    else if(t['辅房等级']?.[cleanClass]?.illumination_min) rangeMap[rangePk] = t['辅房等级'][cleanClass].illumination_min;
                }
            }
            // 普通手术室Ⅳ级洁净度按 ISO 8.5 单区处理
            else if(typeId === 'operating_room' && room.dataset.surgeryRoomType === '手术室' && cleanClass === 'Ⅳ级（十万级）'){
                rangeMap = t[cleanClass] ? { ...t[cleanClass] } : {};
                if(rangePk === 'particle'){
                    rangeMap[rangePk] = { range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' };
                }
            }
            // 普通手术室Ⅱ/Ⅲ/Ⅳ级走主手术室标准范围，不带开门后门内0.6m处洁净度
            else if(typeId === 'operating_room' && room.dataset.surgeryRoomType === '手术室' && ['Ⅱ级（千级）','Ⅲ级（万级）'].includes(cleanClass)){
                rangeMap = t[cleanClass] ? { ...t[cleanClass] } : {};
            }
            // 眼科手术室Ⅳ级洁净度按 ISO 8.5 单区处理
            else if(typeId === 'operating_room' && room.dataset.surgeryRoomType === '眼科手术室' && cleanClass === 'Ⅳ级（十万级）'){
                rangeMap = stdRanges['eye_operating_room'] && stdRanges['eye_operating_room'][cleanClass] ? { ...stdRanges['eye_operating_room'][cleanClass] } : {};
                if(rangePk === 'particle'){
                    rangeMap[rangePk] = { range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' };
                }
            }
            // 眼科手术室特殊处理
            else if(typeId === 'operating_room' && room.dataset.surgeryRoomType === '眼科手术室' && stdRanges['eye_operating_room'] && cleanClass && stdRanges['eye_operating_room'][cleanClass]){
                rangeMap = { ...stdRanges['eye_operating_room'][cleanClass] };
                if(rangePk === 'particle'){
                    if(cleanClass === 'Ⅰ级（百级）') rangeMap[rangePk] = { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' };
                    if(cleanClass === 'Ⅱ级（千级）') rangeMap[rangePk] = { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' };
                    if(cleanClass === 'Ⅲ级（万级）') rangeMap[rangePk] = { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' };
                }
            }
            // 动物房洁净辅房特殊处理：仅限屏障环境业务链闭合后进入
            else if(typeId === 'animal_room' && cleanClass === '屏障环境' && barrierRoomClass === '洁净辅房' && barrierAuxRoom && t['屏障环境洁净辅房'] && t['屏障环境洁净辅房'][barrierAuxRoom]) rangeMap = t['屏障环境洁净辅房'][barrierAuxRoom];
            else if(typeId === 'bsl') {
                const bslToIsoMap = {
                    'BSL-1（P1）': 'ISO-5',
                    'BSL-2（P2）': 'ISO-7',
                    'BSL-3（P3）': 'ISO-7',
                    'BSL-4（P4）': 'ISO-5'
                };
                const bslValue = room.dataset.bsl || '';
                const isoKey = bslToIsoMap[bslValue] || cleanClass || 'ISO-7';
                rangeMap = t[isoKey] || t['_default'] || null;
            }
            // 洁净功能用房子房间映射优先承接
            else if(typeId === 'clean_function_room' && cleanFunctionSubroom) {
                const subroomAliasMap = { '通用洁净功能用房': cleanClass || 'Ⅲ级（万级）' };
                const subroomKey = cleanFunctionStandardSubroom || subroomAliasMap[cleanFunctionSubroom] || cleanFunctionSubroom;
                if(t[subroomKey]) {
                    const levelMap = cleanClass && t[cleanClass] ? t[cleanClass] : {};
                    const subroomMap = t[subroomKey] || {};
                    rangeMap = { ...levelMap, ...subroomMap };
                    if(rangePk === 'airchange') {
                        rangeMap[rangePk] = subroomMap.airchange || levelMap.airchange || t['_default']?.airchange || null;
                    }
                    if(rangePk === 'particle') {
                        const particleObj = subroomMap.particle || levelMap.particle || null;
                        if(particleObj){
                            const particleRange = particleObj.range || [particleObj.range_op, particleObj.range_surr].filter(Boolean).join(' | ');
                            rangeMap[rangePk] = { range: particleRange || '', unit: particleObj.unit || '' };
                        }
                    }
                    if(rangePk === 'temperature') {
                        rangeMap[rangePk] = levelMap.temperature || subroomMap.temperature || null;
                    }
                    if(rangePk === 'humidity') {
                        rangeMap[rangePk] = levelMap.humidity || subroomMap.humidity || null;
                    }
                    if(rangePk === 'noise') {
                        rangeMap[rangePk] = levelMap.noise || subroomMap.noise || null;
                    }
                    if(rangePk === 'settling') {
                        rangeMap[rangePk] = levelMap.settling || levelMap.bacteria || subroomMap.settling || subroomMap.bacteria || null;
                    }
                    if(rangePk === 'illumination' || rangePk === 'work_illumination') {
                        rangeMap[rangePk] = levelMap.illumination || levelMap.work_illumination || subroomMap.illumination || subroomMap.work_illumination || null;
                    }
                }
            }
            else if(typeId === 'animal_room' && ['普通环境','隔离环境','屏障环境'].includes(cleanClass)) {
                rangeMap = t[cleanClass] ? { ...t[cleanClass] } : (t['_default'] ? { ...t['_default'] } : {});
                if(rangePk === 'pressure') {
                    rangeMap[rangePk] = rangeMap[rangePk] || t['_default']?.pressure || null;
                }
                if(rangePk === 'animal_illumination') {
                    rangeMap[rangePk] = rangeMap[rangePk] || t['_default']?.animal_illumination || null;
                }
            }
            else if(typeId === 'negative_pressure') {
                rangeMap = { ...(t['_default'] || t[cleanClass] || {}) };
                if(rangePk === 'illumination' && !rangeMap[rangePk] && t['_default']?.illumination) rangeMap[rangePk] = t['_default'].illumination;
                if(rangePk === 'airchange_clean' && !rangeMap[rangePk]) rangeMap[rangePk] = { range: '6～10', unit: '次/h' };
                if(rangePk === 'settling' && !rangeMap[rangePk]) rangeMap[rangePk] = t['_default']?.bacteria || null;
                if(rangePk === 'surface_bacteria' && !rangeMap[rangePk]) rangeMap[rangePk] = t['_default']?.surface_bacteria || { range: '≤10', unit: 'cfu/cm²' };
            }
            // 制药/兽药车间等级标准
            else if(['gmp_workshop','veterinary_gmp_workshop'].includes(typeId) && cleanClass && t[cleanClass]) {
                rangeMap = t[cleanClass];
            }
            // 普通手术室/通用洁净功能用房
            else if(cleanClass && t[cleanClass]) rangeMap = t[cleanClass];
            else if(t['_default']) rangeMap = t['_default'];
        }

        if(rangeMap && rangeMap[rangePk]){
            const p = rangeMap[rangePk];
            const standardForDisplay = isHospitalParticle ? 'GB 50333-2013' : stdCode;
            let normalized = p;
            if(typeId === 'clean_function_room' && rangePk === 'particle'){
                const singleRange = p.range || '';
                const dualRange = [p.range_op, p.range_surr].filter(Boolean).join(' | ');
                normalized = {
                    ...p,
                    range: singleRange || dualRange,
                    range_op: '',
                    range_surr: ''
                };
            }
            const nextResult = {
                range: normalized.range || '',
                range_op: normalized.range_op || '',
                range_surr: normalized.range_surr || '',
                unit: normalized.unit || '',
                standard: standardForDisplay
            };
            if(nextResult.range || nextResult.range_op || nextResult.range_surr){
                const shouldKeepExistingSingleParticle = (
                    typeId === 'clean_function_room' &&
                    rangePk === 'particle' &&
                    finalResult.range &&
                    !finalResult.range.includes('|') &&
                    String(nextResult.range || '').includes('|')
                );
                const shouldKeepOperatingRoomIso85 = (
                    typeId === 'operating_room' &&
                    ['手术室','眼科手术室'].includes(room.dataset.surgeryRoomType || '') &&
                    cleanClass === 'Ⅳ级（十万级）' &&
                    rangePk === 'particle' &&
                    String(finalResult.range || '').includes('11120000') &&
                    String(nextResult.range || '').includes('3520000, ≥5μm≤29300')
                );
                const shouldKeepEyeOperatingRoom50333Particle = (
                    typeId === 'operating_room' &&
                    room.dataset.surgeryRoomType === '眼科手术室' &&
                    ['Ⅰ级（百级）','Ⅲ级（万级）'].includes(cleanClass) &&
                    rangePk === 'particle' &&
                    stdCode === 'GB 50591-2010' &&
                    !!finalResult.range_op &&
                    !!finalResult.range_surr &&
                    ((cleanClass === 'Ⅰ级（百级）' && String(finalResult.range_surr || '').includes('352000') && !String(nextResult.range_surr || '').includes('352000')) ||
                     (cleanClass === 'Ⅲ级（万级）' && String(finalResult.range_surr || '').includes('35200000') && !String(nextResult.range_surr || '').includes('35200000')))
                );
                const shouldKeepVet50457Priority = (
                    typeId === 'veterinary_gmp_workshop' &&
                    stdCode !== 'GB 50457-2019' &&
                    !!finalResult.standard &&
                    finalResult.standard === 'GB 50457-2019' &&
                    ['temperature','humidity','wind_speed_uniformity','self_clean','airflow_pattern','airchange','particle','pressure','noise','illumination_main_room','illumination_aux_room','settling','floating','wind_speed'].includes(rangePk)
                );
                if(!shouldKeepExistingSingleParticle && !shouldKeepOperatingRoomIso85 && !shouldKeepEyeOperatingRoom50333Particle && !shouldKeepVet50457Priority){
                    finalResult = nextResult;
                }
            }
        } else if(typeId === 'pass_box' && (rangePk === 'airchange_b12' || rangePk === 'airchange_b3')){
            const p = (rangeMap && (rangeMap.airchange || rangeMap.airchange_b12 || rangeMap.airchange_b3)) || null;
            if(p){
                finalResult = {
                    range: p.range || '',
                    range_op: p.range_op || '',
                    range_surr: p.range_surr || '',
                    unit: p.unit || '',
                    standard: stdCode
                };
            }
        }
    }

    return finalResult;
}

// 文本判定
function calc_text(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const val=room.querySelector(`[data-tv="${pk}"]`)?.value?.trim();
    if(!val){setRes(rid,pk,'-','');return;}
    const pr=getParamRange(rid,pk);
    if(!pr.range)return;
    const pass=val.includes(pr.range)||pr.range.includes(val);
    setRes(rid,pk,val,pass);
}

// 换气次数-风速仪法
function calc_airchange(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const rows=room.querySelectorAll(`[data-ac-vents="${pk}"] [data-vent-row]`);
    let totalQ=0;
    rows.forEach(row=>{
        const area=parseFloat(row.querySelector('[data-va]')?.value)||0;
        const speed=parseFloat(row.querySelector('[data-vs]')?.value)||0;
        const q=area*speed*3600;
        row.querySelector('[data-vq]').value=q>0?q.toFixed(1):'';
        totalQ+=q;
    });
    const vol=getRoomVolume(rid);
    if(totalQ>0&&vol>0){
        const ac=totalQ/vol;
        const pr=getParamRange(rid,pk);
        const pass=judgeRange(ac,pr.range);
        setRes(rid,pk,`总风量${totalQ.toFixed(0)}m3/h ÷ 体积${vol.toFixed(1)}m3 = ${ac.toFixed(1)}次/h`,pass);
    } else {
        const hint = totalQ > 0 && vol <= 0 ? '缺少房间体积' : '-';
        setRes(rid,pk,hint,'');
    }
}

// 换气次数-风量仪法
function calc_airchange_vol(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const inputs=room.querySelectorAll(`[data-dp-vol="${pk}"] input`);
    const vals=Array.from(inputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    const totalQ=vals.reduce((a,b)=>a+b,0);
    const vol=getRoomVolume(rid);
    if(totalQ>0&&vol>0){
        const ac=totalQ/vol;
        const pr=getParamRange(rid,pk);
        const pass=judgeRange(ac,pr.range);
        setRes(rid,pk,`总风量${totalQ.toFixed(0)}m3/h ÷ 体积${vol.toFixed(1)}m3 = ${ac.toFixed(1)}次/h`,pass);
    } else {
        setRes(rid,pk,'-','');
    }
}

// 噪声修正计算
function calc_noise(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const bg=parseFloat(room.querySelector(`[data-noise="background"]`).value);
    const indoor=parseFloat(room.querySelector(`[data-noise="indoor"]`).value);
    const resultDiv=room.querySelector(`[data-noise-result="${pk}"]`);

    if(isNaN(bg)||isNaN(indoor)){
        resultDiv.innerHTML='<span style="color:#666;">修正后噪声:</span><span style="font-weight:bold;color:#333;">--</span>';
        setRes(rid,pk,'-','');
        return;
    }

    const diff=indoor-bg;
    let corrected;
    let msg='';

    if(diff>=6&&diff<=9){
        corrected=indoor-1;
        msg=`差值${diff.toFixed(1)}dB(A),修正-1`;
    }else if(diff>=4&&diff<6){
        corrected=indoor-2;
        msg=`差值${diff.toFixed(1)}dB(A),修正-2`;
    }else if(diff===3){
        corrected=indoor-3;
        msg=`差值3dB(A),修正-3`;
    }else if(diff<3){
        resultDiv.innerHTML='<span style="color:#d00;">⚠️ 差值<3dB(A),需重新测试</span>';
        setRes(rid,pk,'-','');
        return;
    }else{
        corrected=indoor;
        msg=`差值${diff.toFixed(1)}dB(A),无需修正`;
    }

    resultDiv.innerHTML=`<span style="color:#666;">${msg}</span><br><span style="font-weight:bold;color:#333;">修正后:${corrected.toFixed(1)} dB(A)</span>`;

    const pr=getParamRange(rid,pk);
    const pass=judgeRange(corrected,pr.range);
    setRes(rid,pk,corrected.toFixed(1)+' dB(A)',pass);
}

// 洁净度-分区(医院)
function calc_pzone(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    const pr=getParamRange(rid,pk);
    const opRange = (pb.dataset.rangeOp || '').trim() || pr.range_op || '';
    const surrRange = (pb.dataset.rangeSurr || '').trim() || pr.range_surr || '';

    const g=k=>parseFloat(room.querySelector(`[data-pz="${k}"]`)?.value);
    const op05max=g('op_05_max'),op05ucl=g('op_05_ucl'),op5max=g('op_5_max'),op5ucl=g('op_5_ucl');
    const surr05max=g('surr_05_max'),surr05ucl=g('surr_05_ucl'),surr5max=g('surr_5_max'),surr5ucl=g('surr_5_ucl');

    // 解析限值(支持区间格式:3520000>0.5μm≤11120000)
    const parseLimit=(rangeStr)=>{
        const mRange05=rangeStr.match(/(\d+)[<>]0\.5μm≤(\d+)/);
        const mRange5=rangeStr.match(/(\d+)[<>]5μm≤(\d+)/);
        const m05=rangeStr.match(/0\.5μm≤(\d+)/);
        const m5=rangeStr.match(/5μm≤(\d+)/);
        let lo05=0, hi05=Infinity, lo5=0, hi5=Infinity;
        if(mRange05){ lo05=parseInt(mRange05[1]); hi05=parseInt(mRange05[2]); }
        else if(m05){ hi05=parseInt(m05[1]); }
        if(mRange5){ lo5=parseInt(mRange5[1]); hi5=parseInt(mRange5[2]); }
        else if(m5){ hi5=parseInt(m5[1]); }
        return {lo05, hi05, lo5, hi5};
    };
    const opLim=parseLimit(opRange);
    const surrLim=parseLimit(surrRange);

    const judgeP=(val,lo,hi)=> lo>0 ? (val>lo && val<=hi) : (val<=hi);

    let parts=[];
    let allPass=true;
    if(!isNaN(op05ucl)){
        const p=judgeP(op05ucl,opLim.lo05,opLim.hi05);
        if(!p)allPass=false;
        parts.push(`手术区0.5μm:${op05ucl}${p?'✅':'❌'}`);
    }
    if(!isNaN(op5ucl)){
        const p=judgeP(op5ucl,opLim.lo5,opLim.hi5);
        if(!p)allPass=false;
        parts.push(`5μm:${op5ucl}${p?'✅':'❌'}`);
    }
    if(!isNaN(surr05ucl)){
        const p=judgeP(surr05ucl,surrLim.lo05,surrLim.hi05);
        if(!p)allPass=false;
        parts.push(`周边区0.5μm:${surr05ucl}${p?'✅':'❌'}`);
    }
    if(!isNaN(surr5ucl)){
        const p=judgeP(surr5ucl,surrLim.lo5,surrLim.hi5);
        if(!p)allPass=false;
        parts.push(`5μm:${surr5ucl}${p?'✅':'❌'}`);
    }

    if(parts.length>0) setRes(rid,pk,parts.join(' | '),allPass);
    else setRes(rid,pk,'-','');
}

// 洁净度-4值
function calc_p4(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    // 优先走数据库范围，DOM 仅作回退
    const pr = getParamRange(rid,pk);
    const rangeStr = pr.range || '';

    const g=k=>parseFloat(pb.querySelector(`[data-p4="${k}"]`)?.value);
    const p05max=g('p05_max'), p05ucl=g('p05_ucl'), p5max=g('p5_max'), p5ucl=g('p5_ucl');

    // 支持区间格式:3520000>0.5μm≤11120000 和普通格式:0.5μm≤3520000
    const mRange05=rangeStr.match(/(\d+)[<>]0\.5μm≤(\d+)/);
    const mRange5=rangeStr.match(/(\d+)[<>]5μm≤(\d+)/);
    const m05=rangeStr.match(/0\.5μm≤(\d+)/);
    const m5=rangeStr.match(/5μm≤(\d+)/);

    let lo05=0, hi05=Infinity, lo5=0, hi5=Infinity;
    if(mRange05){ lo05=parseInt(mRange05[1]); hi05=parseInt(mRange05[2]); }
    else if(m05){ hi05=parseInt(m05[1]); }
    if(mRange5){ lo5=parseInt(mRange5[1]); hi5=parseInt(mRange5[2]); }
    else if(m5){ hi5=parseInt(m5[1]); }

    let parts=[];
    let allPass=true;
    if(!isNaN(p05max)){
        const p = lo05>0 ? (p05max>lo05 && p05max<=hi05) : (p05max<=hi05);
        if(!p)allPass=false;
        parts.push(`0.5μm最大值:${p05max}${p?'✅':'❌'}`);
    }
    if(!isNaN(p05ucl)){
        const p = lo05>0 ? (p05ucl>lo05 && p05ucl<=hi05) : (p05ucl<=hi05);
        if(!p)allPass=false;
        parts.push(`0.5μm95%UCL:${p05ucl}${p?'✅':'❌'}`);
    }
    if(!isNaN(p5max)){
        const p = lo5>0 ? (p5max>lo5 && p5max<=hi5) : (p5max<=hi5);
        if(!p)allPass=false;
        parts.push(`5μm最大值:${p5max}${p?'✅':'❌'}`);
    }
    if(!isNaN(p5ucl)){
        const p = lo5>0 ? (p5ucl>lo5 && p5ucl<=hi5) : (p5ucl<=hi5);
        if(!p)allPass=false;
        parts.push(`5μm95%UCL:${p5ucl}${p?'✅':'❌'}`);
    }

    if(parts.length>0) setRes(rid,pk,parts.join(' | '),allPass);
    else setRes(rid,pk,'-','');
}

function calc_p4_051(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    const pr = getParamRange(rid,pk);
    const rangeStr = pr.range || '';

    const g=k=>parseFloat(pb.querySelector(`[data-p4="${k}"]`)?.value);
    const p05max=g('p05_max'), p05ucl=g('p05_ucl'), p1max=g('p1_max'), p1ucl=g('p1_ucl');

    const mRange05=rangeStr.match(/(\d+)[<>]0\.5μm≤(\d+)/);
    const mRange1=rangeStr.match(/(\d+)[<>]1μm≤(\d+)/);
    const m05=rangeStr.match(/0\.5μm≤(\d+)/);
    const m1=rangeStr.match(/1μm≤(\d+)/);

    let lo05=0, hi05=Infinity, lo1=0, hi1=Infinity;
    if(mRange05){ lo05=parseInt(mRange05[1]); hi05=parseInt(mRange05[2]); }
    else if(m05){ hi05=parseInt(m05[1]); }
    if(mRange1){ lo1=parseInt(mRange1[1]); hi1=parseInt(mRange1[2]); }
    else if(m1){ hi1=parseInt(m1[1]); }

    let parts=[];
    let allPass=true;
    if(!isNaN(p05max)){
        const p = lo05>0 ? (p05max>lo05 && p05max<=hi05) : (p05max<=hi05);
        if(!p)allPass=false;
        parts.push(`0.5μm最大值:${p05max}${p?'✅':'❌'}`);
    }
    if(!isNaN(p05ucl)){
        const p = lo05>0 ? (p05ucl>lo05 && p05ucl<=hi05) : (p05ucl<=hi05);
        if(!p)allPass=false;
        parts.push(`0.5μm95%UCL:${p05ucl}${p?'✅':'❌'}`);
    }
    if(!isNaN(p1max)){
        const p = lo1>0 ? (p1max>lo1 && p1max<=hi1) : (p1max<=hi1);
        if(!p)allPass=false;
        parts.push(`1μm最大值:${p1max}${p?'✅':'❌'}`);
    }
    if(!isNaN(p1ucl)){
        const p = lo1>0 ? (p1ucl>lo1 && p1ucl<=hi1) : (p1ucl<=hi1);
        if(!p)allPass=false;
        parts.push(`1μm95%UCL:${p1ucl}${p?'✅':'❌'}`);
    }

    if(parts.length>0) setRes(rid,pk,parts.join(' | '),allPass);
    else setRes(rid,pk,'-','');
}

function calc_p4_8(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    const pr = getParamRange(rid,pk);
    const rangeStr = pr.range || '';

    const g=k=>parseFloat(pb.querySelector(`[data-p48="${k}"]`)?.value);
    const p05max=g('p05_max'), p05ucl=g('p05_ucl'), p5max=g('p5_max'), p5ucl=g('p5_ucl');

    const mRange05=rangeStr.match(/(\d+)[<>]0\.5μm≤(\d+)/);
    const mRange5=rangeStr.match(/(\d+)[<>]5μm≤(\d+)/);
    const m05=rangeStr.match(/0\.5μm≤(\d+)/);
    const m5=rangeStr.match(/5μm≤(\d+)/);

    let lo05=0, hi05=Infinity, lo5=0, hi5=Infinity;
    if(mRange05){ lo05=parseInt(mRange05[1]); hi05=parseInt(mRange05[2]); }
    else if(m05){ hi05=parseInt(m05[1]); }
    if(mRange5){ lo5=parseInt(mRange5[1]); hi5=parseInt(mRange5[2]); }
    else if(m5){ hi5=parseInt(m5[1]); }

    let parts=[];
    let allPass=true;
    if(!isNaN(p05max)){
        const p = lo05>0 ? (p05max>lo05 && p05max<=hi05) : (p05max<=hi05);
        if(!p)allPass=false;
        parts.push(`0.5μm最大值:${p05max}${p?'✅':'❌'}`);
    }
    if(!isNaN(p05ucl)){
        const p = lo05>0 ? (p05ucl>lo05 && p05ucl<=hi05) : (p05ucl<=hi05);
        if(!p)allPass=false;
        parts.push(`0.5μm95%UCL:${p05ucl}${p?'✅':'❌'}`);
    }
    if(!isNaN(p5max)){
        const p = lo5>0 ? (p5max>lo5 && p5max<=hi5) : (p5max<=hi5);
        if(!p)allPass=false;
        parts.push(`5μm最大值:${p5max}${p?'✅':'❌'}`);
    }
    if(!isNaN(p5ucl)){
        const p = lo5>0 ? (p5ucl>lo5 && p5ucl<=hi5) : (p5ucl<=hi5);
        if(!p)allPass=false;
        parts.push(`5μm95%UCL:${p5ucl}${p?'✅':'❌'}`);
    }

    if(parts.length>0) setRes(rid,pk,parts.join(' | '),allPass);
    else setRes(rid,pk,'-','');
}

// 细菌浓度-分区
function calc_bzone(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pr=getParamRange(rid,pk);

    const g=k=>parseFloat(room.querySelector(`[data-bz="${k}"]`)?.value);
    const opPts=g('op_points'),opTotal=g('op_total');
    const surrPts=g('surr_points'),surrTotal=g('surr_total');

    const opLimit=parseFloat((pr.range_op||'').replace(/[≤≥]/g,''));
    const surrLimit=parseFloat((pr.range_surr||'').replace(/[≤≥]/g,''));

    let parts=[];
    let allPass=true;
    if(!isNaN(opPts)&&!isNaN(opTotal)&&opPts>0){
        const avg=opTotal/opPts;
        const p=avg<=opLimit;
        if(!p)allPass=false;
        parts.push(`手术区:${avg.toFixed(1)}cfu/m3${p?'✅':'❌'}`);
    }
    if(!isNaN(surrPts)&&!isNaN(surrTotal)&&surrPts>0){
        const avg=surrTotal/surrPts;
        const p=avg<=surrLimit;
        if(!p)allPass=false;
        parts.push(`周边区:${avg.toFixed(1)}cfu/m3${p?'✅':'❌'}`);
    }

    if(parts.length>0){
        // 手术区和周边区分别显示判定结果
        const resEl = room.querySelector(`[data-res="${pk}"]`);
        if(resEl){
            resEl.innerHTML = parts.join('<br>');
            resEl.className = 'cv ' + (allPass ? 'pass' : 'fail');
        }
    }
    else setRes(rid,pk,'-','');
}

// 沉降菌
function calc_settling(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pr=getParamRange(rid,pk);

    const pts=parseFloat(room.querySelector(`[data-st="points"]`)?.value);
    const total=parseFloat(room.querySelector(`[data-st="total"]`)?.value);

    if(!isNaN(pts)&&!isNaN(total)&&pts>0){
        const avg=total/pts;
        const pass=judgeRange(avg,pr.range);
        const detType = getRoomDetType(rid);
        const cleanClass = room?.dataset.cleanClass || '';
        if(detType?.id === 'animal_room' && cleanClass === '隔离环境' && pk === 'settling' && pass === true && avg === 0){
            setRes(rid,pk,`无检出`,pass);
            return;
        }
        setRes(rid,pk,`${pts}点采样,总数${total},平均${avg.toFixed(1)}`,pass);
    } else {
        setRes(rid,pk,'-','');
    }
}

// 浮游菌
function calc_floating(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pr=getParamRange(rid,pk);

    const vol=parseFloat(room.querySelector(`[data-fl="volume"]`)?.value);
    const total=parseFloat(room.querySelector(`[data-fl="total"]`)?.value);

    if(!isNaN(vol)&&!isNaN(total)&&vol>0){
        const avgConc=total/vol*1000;
        const pass=judgeRange(avgConc,pr.range);
        setRes(rid,pk,`平均浓度 = ${total}/${vol}L×1000 = ${avgConc.toFixed(1)}`,pass);
    } else {
        setRes(rid,pk,'-','');
    }
}

// 风速不均匀度(自动计算)
function calc_wind_uniformity(rid,pk,vals){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    if(!vals||vals.length<2){
        setRes(rid,pk,'-','');
        return;
    }
    const pb=room?.querySelector(`[data-pk="${pk}"]`);
    const pr=getParamRange(rid,pk);
    const range = pr.range || '';

    // 检查calc字段判断计算方式，优先使用页面已挂载的真实业务定义
    const calcMethod = pb?.dataset.calc || pr.calc || '';

    if(calcMethod.includes('最大值') && calcMethod.includes('最小值')){
        // GMP方式:(最大值-最小值)/(最大值+最小值)
        const max = Math.max(...vals);
        const min = Math.min(...vals);
        const uniformity = (max+min)>0 ? (max-min)/(max+min) : 0;
        const pass = judgeRange(uniformity, range);
        setRes(rid,pk,`${uniformity.toFixed(2)}(max=${max.toFixed(2)}, min=${min.toFixed(2)})`,pass);
    } else {
        // 手术室方式:标准偏差/平均值
        const avg=vals.reduce((a,b)=>a+b,0)/vals.length;
        const variance=vals.reduce((a,b)=>a+Math.pow(b-avg,2),0)/vals.length;
        const std=Math.sqrt(variance);
        const uniformity=avg>0?std/avg:0;
        const pass=judgeRange(uniformity,range);
        setRes(rid,pk,`${uniformity.toFixed(2)}(σ=${std.toFixed(4)} / μ=${avg.toFixed(2)})`,pass);
    }
}

// 照度均匀度(自动计算)
function calc_illum_uniformity(rid,pk,vals){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    if(!vals||vals.length<2){
        setRes(rid,pk,'-','');
        return;
    }
    const pb=room?.querySelector(`[data-pk="${pk}"]`);
    const pr=getParamRange(rid,pk);

    const min=Math.min(...vals);
    const avg=vals.reduce((a,b)=>a+b,0)/vals.length;
    const uniformity=avg>0?min/avg:0;

    const range = pr.range || '';
    const pass=judgeRange(uniformity,range);
    const resultText = `${min} / ${avg.toFixed(1)} = ${uniformity.toFixed(2)}`;
    setRes(rid,pk,resultText,pass);
}

// 通用判定
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

function setRes(rid,pk,text,pass){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const span=room.querySelector(`[data-res="${pk}"]`);
    if(!span)return;
    if(pass===''||pass===undefined){
        span.textContent=text;
        span.className='cv';
        if(room && (room.dataset.typeId || '') === 'pass_box'){
            room.dataset.passBoxResultState = getPassBoxResultState(room);
            syncPassBoxResultState(rid);
        }
        updateRoomSummary(rid);
        return;
    }
    span.textContent=text+(pass===true?' ✅':pass===false?' ❌':'');
    span.className=pass?'cv pass':'cv fail';
    if(room && (room.dataset.typeId || '') === 'pass_box'){
        room.dataset.passBoxResultState = getPassBoxResultState(room);
        syncPassBoxResultState(rid);
    }
    updateRoomSummary(rid);
}

// ========== 数据收集 ==========

function collectData(){
    const basisChecked=[];
    document.querySelectorAll('input[name="basis"]:checked').forEach(cb=>basisChecked.push(cb.value));
    const judgementChecked=[];
    document.querySelectorAll('input[name="judgement"]:checked').forEach(cb=>judgementChecked.push(cb.value));
    const criteriaData=(currentDomain && SYSTEM_DB.criteria && SYSTEM_DB.criteria[currentDomain])||[];
    const criteria=currentCriteriaIdx!==null&&criteriaData.length?criteriaData[currentCriteriaIdx]:null;

    const rooms=[];
    document.querySelectorAll('.room-card').forEach(card=>{
        const rid=card.dataset.rid;
        const detType = getRoomDetType(rid);
        if(!detType) return;

        // 获取参数列表:优先从levelParams获取,否则用默认params
        const cleanClass = card.dataset.cleanClass || card.dataset.levelName || '';
        let paramsList = null;
        if(detType.levelParams && detType.levelParams[cleanClass]){
            paramsList = detType.levelParams[cleanClass];
        } else if(detType.params){
            paramsList = detType.params;
        }
        if(!paramsList)return;

        const params={};
        const animalContextIncomplete = isAnimalBarrierContextIncomplete(card);
        paramsList.forEach(p=>{
            if(animalContextIncomplete) return;
            const pb=card.querySelector(`[data-pk="${p.key}"]`);
            if(!pb)return;
            const result=pb.querySelector(`[data-res="${p.key}"]`)?.textContent||'-';
            const itype=p.inputType;

            if(itype==='numeric' || itype==='numeric_range_manual'){
                const inputs=pb.querySelectorAll(`[data-dp="${p.key}"] input`);
                const vals=Array.from(inputs).map(i=>i.value).filter(v=>v);
                const manualRange = pb.querySelector(`[data-manual-range="${p.key}"]`)?.value||'';
                const manualMin = pb.querySelector(`[data-mr-min="${p.key}"]`)?.value||'';
                const manualMax = pb.querySelector(`[data-mr-max="${p.key}"]`)?.value||'';
                if(vals.length || manualRange || manualMin || manualMax) params[p.key]={type:itype,values:vals,manualRange,manualMin,manualMax,result};
            } else if(itype==='text'){
                const val=pb.querySelector(`[data-tv="${p.key}"]`)?.value;
                if(val) params[p.key]={type:'text',values:[val],result};
            } else if(itype==='airchange'){
                const method=pb.dataset.acMethod||'speed';
                if(method==='speed'){
                    const vents=[];
                    pb.querySelectorAll('[data-vent-row]').forEach(row=>{
                        const a=row.querySelector('[data-va]')?.value;
                        const s=row.querySelector('[data-vs]')?.value;
                        const q=row.querySelector('[data-vq]')?.value;
                        if(a||s) vents.push({area:a,speed:s,volume:q});
                    });
                    if(vents.length) params[p.key]={type:'airchange_speed',vents,result};
                } else {
                    const inputs=pb.querySelectorAll(`[data-dp-vol="${p.key}"] input`);
                    const vals=Array.from(inputs).map(i=>i.value).filter(v=>v);
                    if(vals.length) params[p.key]={type:'airchange_volume',values:vals,result};
                }
            } else if(itype==='particle_zone'){
                const g=k=>pb.querySelector(`[data-pz="${k}"]`)?.value||'';
                const d={op_05_max:g('op_05_max'),op_05_ucl:g('op_05_ucl'),op_5_max:g('op_5_max'),op_5_ucl:g('op_5_ucl'),
                    surr_05_max:g('surr_05_max'),surr_05_ucl:g('surr_05_ucl'),surr_5_max:g('surr_5_max'),surr_5_ucl:g('surr_5_ucl')};
                if(Object.values(d).some(v=>v)) params[p.key]={type:'particle_zone',data:d,result};
            } else if(itype==='particle_4'){
                const g=k=>pb.querySelector(`[data-p4="${k}"]`)?.value||'';
                const d={p05_max:g('p05_max'),p05_ucl:g('p05_ucl'),p5_max:g('p5_max'),p5_ucl:g('p5_ucl')};
                if(Object.values(d).some(v=>v)) params[p.key]={type:'particle_4',data:d,result};
            } else if(itype==='particle_4_051'){
                const g=k=>pb.querySelector(`[data-p4="${k}"]`)?.value||'';
                const d={p05_max:g('p05_max'),p05_ucl:g('p05_ucl'),p1_max:g('p1_max'),p1_ucl:g('p1_ucl')};
                if(Object.values(d).some(v=>v)) params[p.key]={type:'particle_4_051',data:d,result};
            } else if(itype==='particle_4_8'){
                const g=k=>pb.querySelector(`[data-p48="${k}"]`)?.value||'';
                const d={p05_max:g('p05_max'),p05_ucl:g('p05_ucl'),p5_max:g('p5_max'),p5_ucl:g('p5_ucl')};
                if(Object.values(d).some(v=>v)) params[p.key]={type:'particle_4_8',data:d,result};
            } else if(itype==='bacteria_zone'){
                const g=k=>pb.querySelector(`[data-bz="${k}"]`)?.value||'';
                const d={op_points:g('op_points'),op_total:g('op_total'),surr_points:g('surr_points'),surr_total:g('surr_total')};
                if(Object.values(d).some(v=>v)) params[p.key]={type:'bacteria_zone',data:d,result};
            } else if(itype==='settling'){
                const pts=pb.querySelector('[data-st="points"]')?.value||'';
                const total=pb.querySelector('[data-st="total"]')?.value||'';
                if(pts||total) params[p.key]={type:'settling',data:{points:pts,total},result};
            } else if(itype==='floating'){
                const vol=pb.querySelector('[data-fl="volume"]')?.value||'';
                const total=pb.querySelector('[data-fl="total"]')?.value||'';
                if(vol||total) params[p.key]={type:'floating',data:{volume:vol,total},result};
            } else if(itype==='bacteria_control'){
                const inputs=pb.querySelectorAll(`[data-dp="${p.key}"] input`);
                const vals=Array.from(inputs).map(i=>i.value).filter(v=>v);
                const blank=pb.querySelector(`[data-bc-blank="${p.key}"]`)?.value||'';
                const neg=pb.querySelector(`[data-bc-neg="${p.key}"]`)?.value||'';
                if(vals.length||blank||neg) params[p.key]={type:'bacteria_control',values:vals,blank,neg,result};
            } else if(itype==='bacteria_zone_control'){
                const opInputs=pb.querySelectorAll(`[data-dp="${p.key}_op"] input`);
                const opVals=Array.from(opInputs).map(i=>i.value).filter(v=>v);
                const surrInputs=pb.querySelectorAll(`[data-dp="${p.key}_surr"] input`);
                const surrVals=Array.from(surrInputs).map(i=>i.value).filter(v=>v);
                const opBlank=pb.querySelector(`[data-bzc-blank-op="${p.key}"]`)?.value||'';
                const opNeg=pb.querySelector(`[data-bzc-neg-op="${p.key}"]`)?.value||'';
                const surrBlank=pb.querySelector(`[data-bzc-blank-surr="${p.key}"]`)?.value||'';
                const surrNeg=pb.querySelector(`[data-bzc-neg-surr="${p.key}"]`)?.value||'';
                if(opVals.length||surrVals.length||opBlank||opNeg||surrBlank||surrNeg) params[p.key]={
                    type:'bacteria_zone_control',
                    data:{op_values:opVals,surr_values:surrVals},
                    op_values:opVals,
                    surr_values:surrVals,
                    op_blank:opBlank,
                    op_neg:opNeg,
                    surr_blank:surrBlank,
                    surr_neg:surrNeg,
                    result
                };
            } else if(itype==='settling_control'){
                const inputs=pb.querySelectorAll(`[data-dp="${p.key}"] input`);
                const vals=Array.from(inputs).map(i=>i.value).filter(v=>v);
                const blank=pb.querySelector(`[data-sc-blank="${p.key}"]`)?.value||'';
                const neg=pb.querySelector(`[data-sc-neg="${p.key}"]`)?.value||'';
                if(vals.length||blank||neg) params[p.key]={type:'settling_control',values:vals,blank,neg,result};
            } else if(itype==='floating_control'){
                const vol=pb.querySelector(`[data-fc-vol="${p.key}"]`)?.value||'';
                const inputs=pb.querySelectorAll(`[data-dp="${p.key}"] input`);
                const vals=Array.from(inputs).map(i=>i.value).filter(v=>v);
                const blank=pb.querySelector(`[data-fc-blank="${p.key}"]`)?.value||'';
                const neg=pb.querySelector(`[data-fc-neg="${p.key}"]`)?.value||'';
                if(vol||vals.length||blank||neg) params[p.key]={type:'floating_control',volume:vol,values:vals,blank,neg,result};
            } else if(itype==='hepa_leak_multi'){
                const objects = Array.from(pb.querySelectorAll('.hepa-object')).map(obj=>{
                    const name = obj.querySelector('.hepa-name')?.value || '';
                    const value = obj.querySelector('input[type="number"]')?.value || '';
                    return {name, value};
                }).filter(item=>item.name || item.value);
                const pr = getParamRange(rid, p.key);
                const primaryObject = objects[0] || {};
                const standardLabel = pr.standard || 'GB 50591-2010';
                const primarySummary = primaryObject.name ? `${primaryObject.name}:${pr.range||''}[${standardLabel}]` : '';
                if(objects.length) params[p.key]={type:'hepa_leak_multi',objects,standard:standardLabel,range:pr.range||'',primarySummary,result};
            } else if(itype==='pressure_bsl'){
                const pairRows = pb.querySelectorAll('[data-pressure-pair-row]');
                const pairs = Array.from(pairRows).map(row=>{
                    const refRoom = row.querySelector(`[data-bsl-ref-room="${p.key}"]`)?.value||'';
                    const range = row.querySelector(`[data-pair-range="${p.key}"]`)?.value||'';
                    const activeBtn = row.querySelector('[data-pair-ptype].active');
                    const pressureType = activeBtn?.dataset.pairPtype || 'positive';
                    const values = Array.from(row.querySelectorAll(`[data-dp="${p.key}"] input`)).map(i=>i.value).filter(v=>v);
                    return {refRoom, pressureType, range, values};
                }).filter(item=>item.refRoom || item.range || (item.values && item.values.length));
                const legacyVals = pairs.flatMap(item=>item.values||[]);
                const legacyRef = pairs.map(item=>item.refRoom).filter(Boolean).join(';');
                const primaryPair = pairs[0] || {};
                const primarySummary = primaryPair.refRoom ? `${primaryPair.refRoom}:${primaryPair.range||''}` : '';
                if(pairs.length) params[p.key]={type:'pressure_bsl',refRoom: legacyRef,pairs,values:legacyVals,pressureType:primaryPair.pressureType||'positive',range:primaryPair.range||'',primarySummary,result};
            } else if(itype==='temp_diff'){
                const high = pb.querySelector('[data-td="high"]')?.value || '';
                const low = pb.querySelector('[data-td="low"]')?.value || '';
                const diff = pb.querySelector('[data-td="diff"]')?.value || '';
                if(high||low) params[p.key]={type:'temp_diff',high,low,diff,result};
            } else if(itype==='pass_fail'){
                const val = card.dataset['pf_'+p.key] || '';
                if(val) params[p.key]={type:'pass_fail',value:val==='pass'?'符合要求':'不符合要求',pass:val==='pass',result};
            } else if(itype==='wind_uniformity'||itype==='illumination_uniformity'){
                params[p.key]={type:itype,values:[],result};
            } else if(itype==='noise_corrected'){
                const bgInput=pb.querySelector('[data-noise="background"]');
                const indoorInput=pb.querySelector('[data-noise="indoor"]');
                const bg=bgInput?bgInput.value:'';
                const indoor=indoorInput?indoorInput.value:'';
                if(bg||indoor) params[p.key]={type:'noise_corrected',background:bg,indoor:indoor,result};
            } else if(itype==='airchange_speed_only'){
                const vents=[];
                pb.querySelectorAll('[data-vent-row]').forEach(row=>{
                    const a=row.querySelector('[data-va]')?.value;
                    const s=row.querySelector('[data-vs]')?.value;
                    if(a||s) vents.push({area:a,speed:s});
                });
                if(vents.length) params[p.key]={type:'airchange_speed_only',vents,result};
            } else if(itype==='pass_box_volume'){
                const l=pb.querySelector('[data-dim="length"]')?.value||'';
                const w=pb.querySelector('[data-dim="width"]')?.value||'';
                const h=pb.querySelector('[data-dim="height"]')?.value||'';
                const vol=(parseFloat(l)&&parseFloat(w)&&parseFloat(h))?(parseFloat(l)*parseFloat(w)*parseFloat(h)).toFixed(4):'';
                if(l||w||h) params[p.key]={type:'pass_box_volume',length:l,width:w,height:h,volume:vol,result};
            }
        });

        // 收集房间级检测依据
        const roomBasis = [];
        card.querySelectorAll('[data-rb-code]:checked').forEach(cb => roomBasis.push(cb.dataset.rbCode));

        // 收集房间级判定标准(按优先级顺序)
        const judgementPriority = JSON.parse(card.dataset.judgementPriority || '[]');
        const judgementChecked = JSON.parse(card.dataset.judgementChecked || '[]');
        const roomJudgement = judgementPriority.filter(c => judgementChecked.includes(c));
        const activeJudgement = roomJudgement[0] || '';

        const roomTypeId = card.dataset.typeId || '';
        const animalBarrierContextIncomplete = isAnimalBarrierContextIncomplete(card);
        const savedBasisDataset = animalBarrierContextIncomplete ? [] : JSON.parse(card.dataset.basisChecked || '[]');
        const savedJudgementPriority = animalBarrierContextIncomplete ? [] : JSON.parse(card.dataset.judgementPriority || '[]');
        const savedJudgementChecked = animalBarrierContextIncomplete ? [] : JSON.parse(card.dataset.judgementChecked || '[]');
        const passBoxHasParamsLive = ((card.dataset.typeId||'') === 'pass_box') && (card.querySelectorAll('.pb').length > 0);
        const savedJudgementActive = animalBarrierContextIncomplete ? [] : JSON.parse(card.dataset.judgementActive || '[]');
        const passBoxJudgementActive = (card.dataset.typeId||'') === 'pass_box'
            ? (passBoxHasParamsLive ? savedJudgementActive : [])
            : [];
        const roomBasisSafe = animalBarrierContextIncomplete ? [] : roomBasis;
        const roomJudgementSafe = animalBarrierContextIncomplete ? [] : roomJudgement;
        const activeJudgementSafe = animalBarrierContextIncomplete ? [] : activeJudgement;

        const animalContextIncompleteForRoom = isAnimalBarrierContextIncomplete(card);
        const pressurePairSummarySafe = animalContextIncompleteForRoom ? '' : (card.dataset.pressurePairSummary_pressure || '');
        const hepaLeakSummarySafe = animalContextIncompleteForRoom ? '' : (card.dataset.hepaLeakSummary || '');
        const animalIlluminationSourceSafe = (card.dataset.typeId||'') === 'animal_room' && (((card.dataset.animalIlluminationSource || '') === 'saved') || !!card.querySelector(`[data-pk="animal_illumination"] [data-mr-min="animal_illumination"]`)?.value || !!card.querySelector(`[data-pk="animal_illumination"] [data-mr-max="animal_illumination"]`)?.value)
            ? (card.dataset.animalIlluminationSource || '')
            : '';
        rooms.push({
            name: card.querySelector('.rname')?.value||'',
            length: card.querySelector('[data-dim="length"]')?.value||'',
            width: card.querySelector('[data-dim="width"]')?.value||'',
            height: card.querySelector('[data-dim="height"]')?.value||'',
            level_name: card.dataset.levelName||'',
            level_class: card.dataset.levelClass||'',
            clean_class: card.dataset.cleanClass||'',
            bsl: card.dataset.bsl||'',
            type_id: card.dataset.typeId||'',
            type_name: card.dataset.typeName||'',
            business_domain_hint: (card.dataset.typeId||'') === 'pass_box'
                ? 'pharma'
                : ((card.dataset.typeId||'') === 'laminar_hood' ? 'pharma' : ''),
            clean_function_subroom: card.dataset.cleanFunctionSubroom||'',
            barrier_room_class: card.dataset.barrierRoomClass||'',
            barrier_aux_room: card.dataset.barrierAuxRoom||'',
            surgery_aux_room: card.dataset.surgeryAuxRoom||'',
            surgery_room_type: card.dataset.surgeryRoomType||'',
            surgery_aux_clean_class: card.dataset.surgeryAuxCleanClass||'',
            basis: roomBasisSafe,
            basis_dataset: savedBasisDataset,
            basis_expanded: animalBarrierContextIncomplete ? false : (card.dataset.basisExpanded === 'true'),
            judgement: roomJudgementSafe,
            judgement_priority: savedJudgementPriority,
            judgement_checked: savedJudgementChecked,
            judgement_active: savedJudgementActive,
            summary: {
                result_state: card.dataset.resultState || '',
                input_result_state: card.dataset.inputResultState || '',
                judgement_engine: card.dataset.judgementEngine || '',
                judgement_reason: card.dataset.judgementReason || '',
                judgement_overridden: card.dataset.judgementOverridden === 'true' ? true : (card.dataset.judgementOverridden === 'false' ? false : null),
                abnormal_items: JSON.parse(card.dataset.abnormalItems || '[]'),
                judgement_active: savedJudgementActive,
                basis_primary: savedBasisDataset[0] || '',
                judgement_primary: activeJudgement || ''
            },
            pass_box_judgement_active: passBoxJudgementActive,
            pass_box_result_state: (card.dataset.typeId||'') === 'pass_box' ? getPassBoxResultState(card) : '',
            electronics_manual_range_keys: (card.dataset.typeId||'') === 'electronics_workshop'
                ? Array.from(card.querySelectorAll('.pb[data-itype="numeric_range_manual"]')).map(pb => pb.dataset.pk || '').filter(Boolean).filter(pk => {
                    const manualRange = card.querySelector(`[data-manual-range="${pk}"]`)?.value || '';
                    const manualMin = card.querySelector(`[data-mr-min="${pk}"]`)?.value || '';
                    const manualMax = card.querySelector(`[data-mr-max="${pk}"]`)?.value || '';
                    return !!(manualRange || manualMin || manualMax);
                })
                : [],
            judgement_expanded: animalBarrierContextIncomplete ? false : (card.dataset.judgementExpanded === 'true'),
            hepa_leak_summary: hepaLeakSummarySafe,
            animal_context_incomplete: isAnimalBarrierContextIncomplete(card),
            animal_illumination_source: animalIlluminationSourceSafe,
            active_judgement: activeJudgementSafe,
            params
        });
    });

    ensureEditingRecordId();
    return {
        project_name: document.getElementById('projectName').value,
        report_number: document.getElementById('reportNumber').value,
        client_name: document.getElementById('clientName').value,
        contact_info: document.getElementById('contactInfo').value,
        project_address: document.getElementById('projectAddress').value,
        inspection_area: document.getElementById('inspectionArea').value,
        detection_date: document.getElementById('detectionDate').value,
        detection_state: document.querySelector('input[name="detectionState"]:checked')?.value||'静态',
        weather:{temperature:document.getElementById('weatherTemp').value,humidity:document.getElementById('weatherHumidity').value,pressure:document.getElementById('weatherPressure').value},
        domain: currentDomain,
        domain_name: currentDomain?SYSTEM_DB.domains.find(d=>d.id===currentDomain)?.name:'',
        detection_type: rooms.map(r=>r.type_id).filter((v,i,a)=>v&&a.indexOf(v)===i).join(','),
        detection_type_name: rooms.map(r=>r.type_name).filter((v,i,a)=>v&&a.indexOf(v)===i).join('、'),
        basis: rooms.flatMap(r=>r.basis||[]).filter((v,i,a)=>a.indexOf(v)===i),
        judgement: rooms.flatMap(r=>r.judgement||[]).filter((v,i,a)=>a.indexOf(v)===i),
        rooms, remarks: (document.getElementById('remarks')||{}).value||'',
        inspector: currentUser, timestamp: new Date().toISOString(),
        record_id: window._editingRecordId || ''
    };
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

// ============================================================
// PWA离线存储与自动同步
// ============================================================
// 注销旧的Service Worker,避免缓存导致页面异常刷新
if('serviceWorker' in navigator){
    navigator.serviceWorker.getRegistrations().then(regs=>{
        regs.forEach(reg=>reg.unregister());

    });
}

const DB_NAME='pudi_records',DB_VERSION=2,STORE_NAME='pending';
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

async function saveToLocal(data, action='save_draft', options={}){
    const db=await openDB();
    const task=buildOfflineTask(data, action, options);
    const all=await getAllLocalTasks().catch(()=>[]);
    if(!task._localId){
        const sameRecord = all.find(r => (r.record_id || '') && (r.record_id === task.record_id));
        if(sameRecord && sameRecord._localId){
            task._localId = sameRecord._localId;
        }
    }
    return new Promise((resolve,reject)=>{
        const tx=db.transaction(STORE_NAME,'readwrite');
        const store=tx.objectStore(STORE_NAME);
        if(task._localId){
            store.put(task);
        }else{
            task._retryCount=0;
            store.add(task);
        }
        tx.oncomplete=()=>{ if(task._localId) window._localEditingTaskId = task._localId; resolve(task._localId || true); };
        tx.onerror=e=>reject(e.target.error);
    });
}

async function getAllLocalTasks(){
    const db=await openDB();
    return new Promise((resolve,reject)=>{
        const tx=db.transaction(STORE_NAME,'readonly');
        const req=tx.objectStore(STORE_NAME).getAll();
        req.onsuccess=()=>resolve(req.result||[]);req.onerror=e=>reject(e.target.error);
    });
}

async function getPendingRecords(){
    const all=await getAllLocalTasks();
    return all.filter(r=>['pending','failed'].includes(r._queueStatus||'pending'));
}

async function updateLocalTask(localId, patch){
    const db=await openDB();
    return new Promise((resolve,reject)=>{
        const tx=db.transaction(STORE_NAME,'readwrite');const store=tx.objectStore(STORE_NAME);
        const req=store.get(localId);
        req.onsuccess=()=>{
            const r=req.result;
            if(r){ Object.assign(r, patch||{}); store.put(r); }
        };
        tx.oncomplete=()=>resolve();tx.onerror=e=>reject(e.target.error);
    });
}

async function markProcessing(localId){
    return updateLocalTask(localId,{_queueStatus:'processing',_queueError:'',_lastAttemptAt:new Date().toISOString()});
}

async function markSynced(localId, result){
    return updateLocalTask(localId,{_queueStatus:'done',_queueError:'',_serverResult:result||null,_synced:true});
}

async function markFailed(localId, errorText){
    const all=await getAllLocalTasks();
    const current=all.find(r=>r._localId===localId);
    const retry=(current?current._retryCount:0)+1;
    const action=current?._queueAction || 'save_draft';
    return updateLocalTask(localId,{_queueStatus:'failed',_queueError:normalizeQueueError(errorText, action),_retryCount:retry,_synced:false});
}

async function purgeExpiredAutoDrafts(){
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
    const db=await openDB();
    return new Promise((resolve,reject)=>{
        const tx=db.transaction(STORE_NAME,'readwrite');
        const store=tx.objectStore(STORE_NAME);
        const req=store.getAll();
        req.onsuccess=()=>{
            (req.result||[]).forEach(r=>{
                if((r._draftKind||'') !== 'auto') return;
                const t = Date.parse(r._savedAt || r.save_time || '');
                if(Number.isFinite(t) && t < cutoff){
                    store.delete(r._localId);
                }
            });
        };
        tx.oncomplete=()=>resolve();tx.onerror=e=>reject(e.target.error);
    });
}

async function clearActiveLocalDrafts(recordId=''){
    const all=await getAllLocalTasks().catch(()=>[]);
    const targets = all.filter(r => {
        const action = r._queueAction || 'save_draft';
        if(action !== 'save_draft') return false;
        if(recordId && (r.record_id || '') && r.record_id !== recordId) return false;
        return true;
    });
    await Promise.all(targets.map(r => deleteLocalTask(r._localId)));
}

async function deleteSynced(){
    const db=await openDB();
    return new Promise((resolve,reject)=>{
        const tx=db.transaction(STORE_NAME,'readwrite');const store=tx.objectStore(STORE_NAME);
        const req=store.getAll();
        req.onsuccess=()=>{req.result.filter(r=>(r._queueStatus==='done'||r._synced)).forEach(r=>store.delete(r._localId));};
        tx.oncomplete=()=>resolve();tx.onerror=e=>reject(e.target.error);
    });
}

async function getLocalTaskByRecordId(recordId){
    const all=await getAllLocalTasks();
    return all.find(r => (r.record_id===recordId) || (`LOCAL_${r._localId}`===recordId)) || null;
}

async function deleteLocalTask(localId){
    const db=await openDB();
    return new Promise((resolve,reject)=>{
        const tx=db.transaction(STORE_NAME,'readwrite');
        tx.objectStore(STORE_NAME).delete(localId);
        tx.oncomplete=()=>resolve();tx.onerror=e=>reject(e.target.error);
    });
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

async function retryLocalTask(recordId){
    try{
        const task=await getLocalTaskByRecordId(recordId);
        if(!task){ showToast('未找到离线任务','error'); return; }
        await updateLocalTask(task._localId,{_queueStatus:'pending',_queueError:''});
        updatePendingCount();
        showToast('已加入重试队列','success');
        if(isOnline) await syncPendingRecords();
        else loadHistory();
    }catch(e){ showToast('重试失败: '+e.message,'error'); }
}

async function abandonLocalTask(recordId){
    try{
        const task=await getLocalTaskByRecordId(recordId);
        if(!task){ showToast('未找到离线任务','error'); return; }
        if(!confirm('确定删除这条离线任务吗?删除后本地未同步数据将丢失。')) return;
        await deleteLocalTask(task._localId);
        updatePendingCount();
        loadHistory();
        showToast('已删除离线任务','success');
    }catch(e){ showToast('删除失败: '+e.message,'error'); }
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

// 网络状态
let isOnline=navigator.onLine;
function updateOnlineStatus(){
    isOnline=navigator.onLine;
    const badge=document.getElementById('syncBadge');
    if(badge) badge.style.display=isOnline?'none':'inline-block';
    if(isOnline) syncPendingRecords();
}
window.addEventListener('online',updateOnlineStatus);
window.addEventListener('offline',updateOnlineStatus);

// 自动同步
let syncing=false;
async function syncPendingRecords(){
    if(syncing||!isOnline) return;
    syncing=true;
    try{
        const pending=await getPendingRecords();
        if(pending.length===0){syncing=false;return;}
        let ok=0;
        let successByAction={};
        for(const record of pending){
            try{
                await markProcessing(record._localId);
                const clean={...record};
                delete clean._localId;delete clean._savedAt;delete clean._synced;
                delete clean._queueAction;delete clean._queueStatus;delete clean._queueError;delete clean._retryCount;delete clean._lastAttemptAt;delete clean._serverResult;
                const action=record._queueAction||'save_draft';
                const endpoint=getSyncEndpoint(action, record);
                const resp=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(clean)});
                const result=await resp.json().catch(()=>({success:false,error:'服务器返回异常'}));
                if(resp.ok && result.success){
                    await markSynced(record._localId, result);
                    ok++;
                    successByAction[action]=(successByAction[action]||0)+1;
                }else{
                    await markFailed(record._localId, result.error || ('服务器错误('+resp.status+')'));
                }
            }catch(e){
                await markFailed(record._localId, e.message||'网络异常');
                break;
            }
        }
        if(ok>0){
            const msgs=Object.entries(successByAction).map(([action,count])=>getSyncSuccessText(action,count));
            showToast(msgs.join(';'),'success');
            await deleteSynced();
            if((successByAction['submit_only']||0) > 0 || (successByAction['submit_and_generate']||0) > 0 || (successByAction['submit_and_export']||0) > 0){
                await clearActiveLocalDrafts();
            }
            updatePendingCount();
            loadHistory();
        }
    }catch(e){}
    syncing=false;
}

async function updatePendingCount(){
    try{
        const pending=await getPendingRecords();
        const badge=document.getElementById('pendingCount');
        if(badge){
            const failedCount=pending.filter(r=>r._queueStatus==='failed').length;
            badge.textContent=failedCount>0?`${pending.length}!`:pending.length;
            badge.title=failedCount>0?`待同步 ${pending.length} 条,其中失败 ${failedCount} 条`:`待同步 ${pending.length} 条`;
            badge.style.display=pending.length>0?'inline-block':'none';
        }
    }catch(e){}
}

setInterval(()=>{if(isOnline)syncPendingRecords();},30000);
setTimeout(()=>{updatePendingCount();if(isOnline)syncPendingRecords();},2000);
setTimeout(()=>{purgeExpiredAutoDrafts().then(()=>updatePendingCount()).catch(()=>{});},2500);
setInterval(()=>{purgeExpiredAutoDrafts().then(()=>updatePendingCount()).catch(()=>{});},6*60*60*1000);

// ============ 自动暂存 & 退出拦截 ============
let _autoSaveDirty=false;
let _autoSaveTimer=null;
let _lastDraftFingerprint='';

function ensureEditingRecordId(){
    if(window._editingRecordId) return window._editingRecordId;
    window._editingRecordId = 'D' + Date.now() + '_' + Math.random().toString(16).slice(2,10);
    return window._editingRecordId;
}

function isGeneratedRecordData(d){
    const hasReport = !!(d?.report_info?.feishu_url || d?.report_info?.filename);
    const hasExport = !!(d?.export_info?.feishu_url || d?.export_info?.filename);
    return hasReport && hasExport;
}

function buildDraftFingerprint(d){
    const clone = JSON.parse(JSON.stringify(d||{}));
    delete clone.timestamp;
    delete clone.save_time;
    delete clone.report_info;
    delete clone.export_info;
    return JSON.stringify(clone);
}

// 监听表单变化,标记为"有未保存修改"
document.addEventListener('wheel', function(e){
    const target = e.target;
    if(target && target.matches && target.matches('input[type="number"]')){
        // 避免滚轮误触修改 number 输入框的值，但不拦截页面滚动
        target.blur();
    }
}, {capture:true, passive:true});

document.addEventListener('input',function(e){
    if(!window._isRestoringDraft) _autoSaveDirty=true;
    if(e.target.type==='number' && e.target.closest('[data-rid]') && parseFloat(e.target.value)<0){
        if(!e.target.closest('[data-dp-bsl]')){
            const pname=e.target.closest('[data-pk]')?.querySelector('.pb-name')?.textContent||'';
            if(!pname.includes('温度')) e.target.value='0';
        }
    }
},true);
document.addEventListener('change',function(e){
    if(!window._isRestoringDraft) _autoSaveDirty=true;
    if(e.target.type==='number' && e.target.closest('[data-rid]') && parseFloat(e.target.value)<0){
        if(!e.target.closest('[data-dp-bsl]')){
            const pname=e.target.closest('[data-pk]')?.querySelector('.pb-name')?.textContent||'';
            if(!pname.includes('温度')) e.target.value='0';
        }
    }
},true);

// 每2分钟自动暂存(仅在有修改时，且不在恢复草稿期间)
_autoSaveTimer=setInterval(()=>{
    if(window._isRestoringDraft) return;
    if(!_autoSaveDirty)return;
    try{
        const d=collectData();d.status='draft'; d._draft_kind='auto';
        const fingerprint = buildDraftFingerprint(d);
        if(fingerprint===_lastDraftFingerprint){
            _autoSaveDirty=false;
            return;
        }
        if(!isOnline){
            saveToLocal(d,'save_draft', {auto:true}).then(()=>{_autoSaveDirty=false;_lastDraftFingerprint=fingerprint;showToast('⏱ 已自动保存到本地','success');updatePendingCount();}).catch(()=>{});
            return;
        }
        doSave(d).then(r=>{if(r.success){_autoSaveDirty=false;_lastDraftFingerprint=fingerprint;if(r.record_id) window._editingRecordId=r.record_id;showToast('⏱ 已自动暂存','success');}else{showToast('⏱ 自动暂存失败: '+r.error,'error');}}).catch(()=>{
            saveToLocal(d,'save_draft', {auto:true}).then(()=>{_autoSaveDirty=false;_lastDraftFingerprint=fingerprint;showToast('⏱ 网络异常,已自动保存到本地','success');updatePendingCount();}).catch(()=>{});
        });
    }catch(e){}
},120000);

// 退出/刷新页面时提醒
window.addEventListener('beforeunload',(e)=>{
    if(_autoSaveDirty){e.preventDefault();e.returnValue='';}
});
// ============================================================

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

let submitting=false;
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

// ==================== 核心链路保护区(勿随意删除/重构) ====================
// 说明:
// 1. 历史记录/暂存记录列表中的记录条目,必须通过 onclick="loadRecordForEdit(record_id)"
//    返回到录入页编辑,不能改成页面重载、URL跳转、或只改内部状态。
// 2. loadRecordForEdit() 内部的加载顺序(先取记录→回填基础字段→房间/参数异步回填→切回录入页)
//    是当前可用版本验证过的主链路。后续优化只能在充分验证后做最小改动。
// 3. 旧版 3 秒状态检查调试代码已在本阶段收尾中移除，当前以真实导出、页面回归和收楼文档作为验收依据。
//    当前不再依赖该调试弹窗确认主链，后续只允许做文档化说明，不得恢复阻塞式调试提示。
// ======================================================================
function fuzzyKeywordsMatch(fields, keyword){
    const kw=(keyword||'').trim().toLowerCase();
    if(!kw) return true;
    const text=(fields||[]).join(' ').toLowerCase();
    const parts=kw.split(/\s+/).filter(Boolean);
    return parts.every(part=>text.includes(part));
}

function previewReportFile(feishuUrl, localFilename, label){
    // 统一预览入口：优先飞书 → 失败回退本地（带来源提示）
    var overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:flex-start;justify-content:center;z-index:10001;padding:12px;padding-top:20px';
    overlay.innerHTML='<div style="background:#fff;border-radius:12px;padding:12px;width:min(1200px,100%);max-width:100%;max-height:92vh;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;flex-direction:column"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #f0f0f0;flex-shrink:0"><h3 style="margin:0;font-size:15px;line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1">加载中...</h3><div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:58%"><button type="button" data-zoom-out style="padding:6px 10px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">A-</button><button type="button" data-zoom-reset style="padding:6px 10px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">100%</button><button type="button" data-zoom-in style="padding:6px 10px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">A+</button><span id="pv-source" style="display:none;padding:4px 8px;border-radius:4px;font-size:11px;align-self:center"></span><button onclick="this.closest(\'.pv-overlay\').remove()" style="padding:6px 12px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">关闭</button></div></div><div id="pv-body" style="border:1px solid #d9d9d9;border-radius:8px;padding:12px;background:#f8fafc;flex:1;overflow:auto;-webkit-overflow-scrolling:touch"><div id="pv-stage" style="transform-origin:top center;transition:transform .15s ease;width:max-content;min-width:100%;margin:0 auto"><p style="text-align:center;color:#999">加载中...</p></div></div></div>';
    overlay.className='pv-overlay';
    overlay.addEventListener('click',function(e){if(e.target===overlay)overlay.remove();});
    document.body.appendChild(overlay);
    var pvStage=overlay.querySelector('#pv-stage');
    var zoomResetBtn=overlay.querySelector('[data-zoom-reset]');
    var initialZoom=(window.innerWidth<=768?0.6:1);
    var zoom=initialZoom;
    function applyZoom(){
        if(zoom<0.5) zoom=0.5;
        if(zoom>2) zoom=2;
        pvStage.style.transform='scale('+zoom+')';
        zoomResetBtn.textContent=Math.round(zoom*100)+'%';
    }
    overlay.querySelector('[data-zoom-in]').onclick=function(){ zoom=Math.min(2, zoom+0.1); applyZoom(); };
    overlay.querySelector('[data-zoom-out]').onclick=function(){ zoom=Math.max(0.5, zoom-0.1); applyZoom(); };
    overlay.querySelector('[data-zoom-reset]').onclick=function(){ zoom=initialZoom; applyZoom(); };

    function renderPreview(d, source){
        overlay.querySelector('h3').textContent=(label||d.filename||'预览')+' ('+((d.file_size||0)/1024).toFixed(1)+' KB)';
        var srcEl=overlay.querySelector('#pv-source');
        if(source==='feishu'){
            srcEl.textContent='☁️ 来源：飞书云盘';
            srcEl.style.cssText='display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;background:#e6f4ff;color:#0958d9;border:1px solid #91caff;';
        }else{
            srcEl.textContent='💾 来源：本地文件';
            srcEl.style.cssText='display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;background:#fff7e6;color:#d46b08;border:1px solid #ffd591;';
        }
        var style='<style>'+
            '.pv-c{max-width:100%;overflow-wrap:anywhere;word-break:break-word;background:#fff;padding:16px 18px;font-family:SimSun,serif;font-size:14px;line-height:1.8;color:#000}' +
            '.pv-c .table-scroll{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:12px 0}' +
            '.pv-c table{border-collapse:collapse;width:max-content;min-width:100%;margin:0;background:#fff}' +
            '.pv-c td,.pv-c th{border:1px solid #000;padding:8px;text-align:center;vertical-align:top;white-space:pre-wrap;word-break:break-word}' +
            '.pv-c p{margin:8px 0;overflow-wrap:anywhere;word-break:break-word}' +
            '.pv-c img{max-width:100%;height:auto}' +
            '@media (max-width:768px){.pv-c{font-size:13px;line-height:1.7;padding:12px}.pv-c td,.pv-c th{padding:6px;font-size:12px}}' +
            '</style>';
        var wrapped=(d.html||'').replace(/<table\b/gi,'<div class="table-scroll"><table').replace(/<\/table>/gi,'</table></div>');
        pvStage.innerHTML=style+'<div class="pv-c">'+wrapped+'</div>';
        applyZoom();
    }

    function fallbackToLocal(){
        if(!localFilename){
            pvStage.innerHTML='<p style="text-align:center;color:#ff4d4f">飞书预览失败且本地文件不可用</p>';
            return;
        }
        fetch('/api/preview/'+encodeURIComponent(localFilename),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){
            if(!d.success){pvStage.innerHTML='<p style="text-align:center;color:#ff4d4f">预览失败: '+(d.error||'未知错误')+'</p>';return;}
            renderPreview(d, 'local');
        }).catch(function(e){
            pvStage.innerHTML='<p style="text-align:center;color:#ff4d4f">本地预览失败: '+e.message+'</p>';
        });
    }

    // 优先飞书
    if(feishuUrl){
        var fileToken='';
        var m=feishuUrl.match(/\/drive\/file\/([A-Za-z0-9]+)/);
        if(m) fileToken=m[1];
        if(!fileToken){m=feishuUrl.match(/\/(docx|sheets)\/([A-Za-z0-9]+)/); if(m) fileToken=m[2];}
        if(fileToken){
            fetch('/api/preview_feishu_file?file_token='+encodeURIComponent(fileToken),{credentials:'same-origin'})
                .then(function(r){return r.json()})
                .then(function(d){
                    if(!d.success) throw new Error(d.error||'飞书预览失败');
                    renderPreview(d, 'feishu');
                })
                .catch(function(e){
                    console.warn('飞书预览失败，回退本地:', e.message);
                    fallbackToLocal();
                });
            return;
        }
    }
    // 没有飞书URL，直接本地
    fallbackToLocal();
}

function previewFile(filename){
    var overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:flex-start;justify-content:center;z-index:10001;padding:12px;padding-top:20px';
    overlay.innerHTML='<div style="background:#fff;border-radius:12px;padding:12px;width:min(1200px,100%);max-width:100%;max-height:92vh;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;flex-direction:column"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #f0f0f0;flex-shrink:0"><h3 style="margin:0;font-size:15px;line-height:1.35;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1">加载中...</h3><div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:58%"><button type="button" data-zoom-out style="padding:6px 10px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">A-</button><button type="button" data-zoom-reset style="padding:6px 10px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">100%</button><button type="button" data-zoom-in style="padding:6px 10px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">A+</button><a id="pv-dl" style="display:none;padding:6px 12px;background:#1890ff;color:white;border-radius:4px;font-size:12px;text-decoration:none" target="_blank">下载</a><button onclick="this.closest(\'.pv-overlay\').remove()" style="padding:6px 12px;border:1px solid #d9d9d9;border-radius:4px;background:#fff;cursor:pointer;font-size:12px">关闭</button></div></div><div id="pv-body" style="border:1px solid #d9d9d9;border-radius:8px;padding:12px;background:#f8fafc;flex:1;overflow:auto;-webkit-overflow-scrolling:touch;text-align:center"><div id="pv-stage" style="transform-origin:top center;transition:transform .15s ease;display:inline-block;margin:0 auto;text-align:left"><p style="text-align:center;color:#999">加载中...</p></div></div></div>';
    overlay.className='pv-overlay';
    overlay.addEventListener('click',function(e){if(e.target===overlay)overlay.remove();});
    document.body.appendChild(overlay);
    var pvStage=overlay.querySelector('#pv-stage');
    var zoomResetBtn=overlay.querySelector('[data-zoom-reset]');
    var initialZoom=(window.innerWidth<=768?0.6:1);
    var zoom=initialZoom;
    function applyZoom(){
        if(zoom<0.5) zoom=0.5;
        if(zoom>2) zoom=2;
        pvStage.style.transform='scale('+zoom+')';
        zoomResetBtn.textContent=Math.round(zoom*100)+'%';
    }
    overlay.querySelector('[data-zoom-in]').onclick=function(){ zoom=Math.min(2, zoom+0.1); applyZoom(); };
    overlay.querySelector('[data-zoom-out]').onclick=function(){ zoom=Math.max(0.5, zoom-0.1); applyZoom(); };
    overlay.querySelector('[data-zoom-reset]').onclick=function(){ zoom=initialZoom; applyZoom(); };
    fetch('/api/preview/'+encodeURIComponent(filename),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){
        if(!d.success){pvStage.innerHTML='<p style="text-align:center;color:#ff4d4f">预览失败: '+(d.error||'未知错误')+'</p>';return;}
        overlay.querySelector('h3').textContent=filename+' ('+((d.file_size||0)/1024).toFixed(1)+' KB)';
        var dl=overlay.querySelector('#pv-dl');dl.href='/download/'+encodeURIComponent(filename);dl.style.display='inline-block';
        var style='<style>'+
            '.pv-c{max-width:100%;overflow-wrap:anywhere;word-break:break-word;background:#fff;padding:16px 18px;font-family:SimSun,serif;font-size:14px;line-height:1.8;color:#000}' +
            '.pv-c .table-scroll{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:12px 0}' +
            '.pv-c table{border-collapse:collapse;width:max-content;min-width:100%;margin:0;background:#fff}' +
            '.pv-c td,.pv-c th{border:1px solid #000;padding:8px;text-align:center;vertical-align:top;white-space:pre-wrap;word-break:break-word}' +
            '.pv-c p{margin:8px 0;overflow-wrap:anywhere;word-break:break-word}' +
            '.pv-c img{max-width:100%;height:auto}' +
            '@media (max-width:768px){.pv-c{font-size:13px;line-height:1.7;padding:12px}.pv-c td,.pv-c th{padding:6px;font-size:12px}}' +
            '</style>';
        var wrapped=(d.html||'').replace(/<table\b/gi,'<div class="table-scroll"><table').replace(/<\/table>/gi,'</table></div>');
        pvStage.innerHTML=style+'<div class="pv-c">'+wrapped+'</div>';
        applyZoom();
    }).catch(function(e){
        pvStage.innerHTML='<p style="text-align:center;color:#ff4d4f">网络错误: '+e.message+'</p>';
    });
    applyZoom();
}

function buildRoomHierarchySummary(room){
    const typeName = room.type_name || room.type_id || '未命名对象';
    const roomName = room.room_name || room.name || '';
    const surgeryRoomType = room.surgery_room_type || room?.context?.surgery_room_type || '';
    const surgeryAuxRoom = room.surgery_aux_room || room?.context?.surgery_aux_room || '';
    const surgeryAuxCleanClass = room.surgery_aux_clean_class || room?.context?.surgery_aux_clean_class || '';
    const cleanFunctionSubroom = room.clean_function_subroom || room?.context?.clean_function_subroom || '';
    const barrierRoomClass = room.barrier_room_class || room?.context?.barrier_room_class || '';
    const barrierAuxRoom = room.barrier_aux_room || room?.context?.barrier_aux_room || '';
    const bslLevel = room.bsl || room?.context?.bsl || '';
    const cleanClass = room.clean_class || room.level_name || '';

    const parts = [typeName];

    if(room.type_id === 'operating_room'){
        if(surgeryRoomType) parts.push(surgeryRoomType);
        if(surgeryRoomType === '洁净辅房' && surgeryAuxRoom) parts.push(surgeryAuxRoom);
        if(surgeryAuxCleanClass) parts.push(surgeryAuxCleanClass);
        else if(cleanClass) parts.push(cleanClass);
    }else if(room.type_id === 'clean_function_room'){
        if(cleanFunctionSubroom) parts.push(cleanFunctionSubroom);
        if(cleanClass) parts.push(cleanClass);
    }else if(room.type_id === 'animal_room'){
        if(cleanClass) parts.push(cleanClass);
        if(barrierRoomClass) parts.push(barrierRoomClass);
        if(barrierRoomClass === '洁净辅房' && barrierAuxRoom) parts.push(barrierAuxRoom);
    }else if(room.type_id === 'bsl'){
        if(bslLevel) parts.push(bslLevel);
    }else{
        if(cleanClass) parts.push(cleanClass);
    }

    if(roomName) parts.push(roomName);
    return parts.filter(Boolean).join(' / ');
}

function buildStatusText(status){
    const text = String(status || '未生成');
    const done = text.includes('已生成') || text.includes('已完成');
    const voided = text.includes('已作废');
    const color = voided ? '#c62828' : (done ? '#2e7d32' : '#c62828');
    return `<span style="color:${color};font-weight:600;">${text}</span>`;
}

async function voidReportRecord(recordId){
    if(!recordId) return;
    const reason = (prompt('请输入作废理由：') || '').trim();
    if(!reason){
        showToast('必须填写作废理由','error');
        return;
    }
    try{
        const res = await fetch('/api/void_export/' + recordId, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({reason})
        }).then(r=>r.json());
        if(!res.success){
            showToast(res.error || '作废失败','error');
            return;
        }
        showToast('已标记作废','success');
        loadHistory();
    }catch(e){
        showToast('作废失败','error');
    }
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

function buildRecordItem(r){
    let actionButtons='';
    const hasReport = !!(r.report_info?.feishu_url || r.report_info?.filename);
    const hasExport = !!(r.export_info?.feishu_url || r.export_info?.filename);
    const statusMeta = r._queueAction ? getQueueStatusMeta(r) : null;
    // 第二层隔离：非本人草稿可看不可编辑（仅限暂存记录，报告记录不受限）
    const isOwnRecord = !r.inspector || r.inspector === currentUser;
    const isDraft = isDraftRecord(r);
    if(hasReport || hasExport){
        if(hasReport){
            var _rpFeishu = r.report_info?.feishu_url || '';
            var _rpLocal = r.report_info?.filename || '';
            actionButtons+=`<button onclick="event.stopPropagation();previewReportFile('${_rpFeishu}','${_rpLocal}','检测报告')" class="record-action-btn report-btn">📄 预览检测报告</button>`;
        }
        if(hasExport){
            var _exFeishu = r.export_info?.feishu_url || '';
            var _exLocal = r.export_info?.filename || '';
            actionButtons+=`<button onclick="event.stopPropagation();previewReportFile('${_exFeishu}','${_exLocal}','原始记录')" class="record-action-btn export-btn">📋 预览原始记录</button>`;
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
        ? rooms.slice(0,3).map(room => buildRoomHierarchySummary(room)).join('；') + (rooms.length > 3 ? ` 等${rooms.length}项` : '')
        : (r.detection_type_name || r.detection_type || '未识别对象');

    const savedAt = r.save_time ? r.save_time.replace('T',' ').substring(0,16) : (r.detection_date || '');
    const reportStatus = r.voided ? '已作废' : (statusMeta?.label || (hasReport ? '已生成' : '未生成'));
    const recordStatus = r.voided ? '已作废' : (statusMeta?.label || (hasExport ? '已生成' : '未生成'));
    const currentStatus = (hasReport || hasExport)
        ? `<div class="record-status-row"><span class="record-status-chip">检测报告：${buildStatusText(reportStatus)}</span><span class="record-status-chip">原始记录：${buildStatusText(recordStatus)}</span></div>`
        : `<div class="record-status-row"><span class="record-status-chip">当前状态：${buildStatusText(statusMeta?.label || '草稿')}</span></div>`;
    const timeInspectorLine = [`生成时间：${savedAt}`, `检测员：${r.inspector || '-'}`].join(' / ');
    const clientLine = r.client_name ? `委托单位：${r.client_name}` : '';
    const headerLine = [r.project_name||'未命名项目', r.report_number||''].filter(Boolean).join(' / ');
    const voidReasonLine = r.voided && r.void_reason ? `<div class="record-extra record-error">作废理由：${r.void_reason}</div>` : '';
    const errorLine = r._queueError ? `<div class="record-extra record-error">${r._queueError}</div>` : '';

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

function isReportRecord(r){
    const hasReport = !!(r.report_info?.feishu_url || r.report_info?.filename);
    const hasExport = !!(r.export_info?.feishu_url || r.export_info?.filename);
    const hasAnyOutput = hasReport || hasExport;
    const queuedForReport = !!(r._queueAction === 'submit_and_export' || r._queueAction === 'submit_and_generate');
    return hasAnyOutput || queuedForReport;
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

function renderDraftRecords(){
    const list=document.getElementById('draftRecordsList');
    const kw=(document.getElementById('draftSearch')||{}).value||'';
    const drafts=(allHistoryRecords||[])
        .filter(isDraftRecord)
        .slice()
        // 统一规则：暂存记录按最近时间倒序显示（最新在最前）
        .sort(compareDraftPriority);
    const filtered=drafts.filter(r=>fuzzyKeywordsMatch([r.project_name,r.client_name,r.detection_date,r.save_time,r.inspector], kw));
    list.innerHTML=filtered.length?filtered.map(buildRecordItem).join(''):'<li style="text-align:center;color:#999;padding:30px;">暂无匹配的暂存记录</li>';
}

function renderHistoryRecords(){
    const list=document.getElementById('recordsList');
    const kw=(document.getElementById('historySearch')||{}).value||'';
    const history=(allHistoryRecords||[])
        .filter(isReportRecord)
        .slice()
        // 统一规则：报告记录按最近时间倒序显示（最新在最前）
        .sort((a,b)=> String(b.save_time || b.updated_at || b.created_at || '').localeCompare(String(a.save_time || a.updated_at || a.created_at || '')));
    const filtered=history.filter(r=>fuzzyKeywordsMatch([r.project_name,r.client_name,r.report_number,r.inspector], kw));
    list.innerHTML=filtered.length?filtered.map(buildRecordItem).join(''):'<li style="text-align:center;color:#999;padding:30px;">暂无匹配的报告记录</li>';
}

let allHistoryRecords=[];
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

function normalizeEditableRoomParams(params){
    if(!params) return {};
    if(Array.isArray(params)){
        const out = {};
        params.forEach(item => {
            if(!item || typeof item !== 'object') return;
            const key = item.key || item.name || item.param_key || '';
            if(!key) return;
            const normalized = {...item};
            if(normalized.value != null && normalized.values == null){
                normalized.values = [String(normalized.value)];
            }
            if(normalized.result != null && normalized.value == null && (!Array.isArray(normalized.values) || normalized.values.length === 0)){
                normalized.values = [String(normalized.result)];
            }
            if(normalized.data && typeof normalized.data === 'object' && normalized.value == null){
                if(normalized.data.total != null){
                    normalized.value = normalized.data.total;
                }else if(normalized.data.value != null){
                    normalized.value = normalized.data.value;
                }
            }
            if((normalized.value != null) && (!Array.isArray(normalized.values) || normalized.values.length === 0)){
                normalized.values = [String(normalized.value)];
            }
            out[key] = normalized;
        });
        return out;
    }
    if(typeof params === 'object') return params;
    return {};
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

// 转让草稿给其他检测员
async function transferDraft(draftId){
    try{
        const res = await fetch('/api/x/inspectors').then(r=>r.json());
        if(!res.success || !res.inspectors || res.inspectors.length === 0){
            showToast('没有可转让的检测员','error');
            return;
        }
        const inspectors = res.inspectors;
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
        let optionsHtml = inspectors.map(u =>
            `<button onclick="doTransferDraft('${draftId}','${u.username}',this)" style="display:block;width:100%;padding:12px;margin:4px 0;border:1px solid #ddd;border-radius:8px;background:#fff;font-size:15px;cursor:pointer;text-align:left;">${u.display_name} (${u.username})</button>`
        ).join('');
        overlay.innerHTML = `<div style="background:white;border-radius:12px;padding:24px;max-width:340px;width:88%;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
            <p style="font-size:16px;margin:0 0 16px;color:#333;font-weight:600;">转让草稿给：</p>
            <div style="max-height:300px;overflow-y:auto;">${optionsHtml}</div>
            <button onclick="this.closest('div[style*=fixed]').remove()" style="width:100%;padding:10px;margin-top:12px;border:1px solid #ddd;border-radius:8px;background:#f5f5f5;font-size:15px;cursor:pointer;">取消</button>
        </div>`;
        document.body.appendChild(overlay);
    }catch(e){
        showToast('加载检测员列表失败: '+e.message,'error');
    }
}

async function doTransferDraft(draftId, targetUser, btn){
    btn.disabled = true;
    btn.textContent = '转让中...';
    try{
        const res = await fetch('/api/x/transfer_draft', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({draft_id: draftId, target_user: targetUser})
        }).then(r=>r.json());
        // 关闭弹窗
        btn.closest('div[style*=fixed]')?.remove();
        if(res.success){
            showToast('✅ 已转让','success');
            loadHistory();
        } else {
            showToast('转让失败: '+(res.error||'未知错误'),'error');
        }
    }catch(e){
        btn.closest('div[style*=fixed]')?.remove();
        showToast('转让失败: '+e.message,'error');
    }
}

// 核心编辑入口:
// - 由历史记录/暂存记录点击进入
// - 目标是"返回录入页编辑当前记录",不是重新打开页面,不是进入新建空表
// - 这段逻辑一旦调整,必须完整验证:打开记录、回填数据、继续暂存、继续生成报告
async function loadRecordForEdit(id){
    pullRefreshDisabled = true;
    window._suppressReturnToEditPrompt = true;
    // 第一层止血：恢复期间暂停 auto-save，避免保存中间态
    window._isRestoringDraft = true;
    _autoSaveDirty = false;
    showToast('加载中...','success');
    try{
        let d=null;
        if(String(id).startsWith('LOCAL_')){
            d = await getLocalTaskByRecordId(id);
            if(!d){ showToast('加载失败: 本地离线记录不存在','error'); return; }
        }else{
            const localTask = await getLocalTaskByRecordId(id).catch(()=>null);
            if(localTask && localTask._queueAction){
                d = localTask;
            }else{
                const res = await fetch('/api/get/'+id).then(r=>r.json());
                if(!res.success){showToast('加载失败: '+res.error,'error');return;}
                d = res.record;
            }
        }
        d = normalizeEditableRecordData(d, id);
        window._localEditingTaskId = d._localId || '';
        showTab('new');

        // 已生成记录:进入编辑时不直接改原记录,而是记录来源ID,后续暂存生成新草稿
        if(isGeneratedRecordData(d)){
            window._sourceGeneratedRecordId = d.record_id || id;
            window._isEditingGeneratedRecord = true;
            window._editingRecordId = '';
        }else{
            window._sourceGeneratedRecordId = d.source_generated_record_id || '';
            window._isEditingGeneratedRecord = false;
            window._editingRecordId = d.record_id || id;
        }
        _lastDraftFingerprint = buildDraftFingerprint(d);
        _autoSaveDirty = false;

        // 1. 填充项目信息
        document.getElementById('projectName').value = d.project_name||'';
        document.getElementById('reportNumber').value = d.report_number||'';
        // 报告编号回填:解析 PDJC-BG年份-周份+自定义
        (function(){
            const rn = d.report_number||'';
            const m = rn.match(/^PDJC-BG(\d{4})-(\d{1,2})(.*)$/);
            if(m){
                document.getElementById('reportYearDisplay').textContent=m[1];
                document.getElementById('reportWeekInput').value=m[2];
                document.getElementById('reportNumberSuffix').value=m[3]||'';
                sanitizeReportWeekInput();
            } else {
                document.getElementById('reportYearDisplay').textContent=new Date().getFullYear();
                document.getElementById('reportNumberSuffix').value=rn;
            }
        })();
        document.getElementById('clientName').value = d.client_name||'';
        document.getElementById('contactInfo').value = d.contact_info||'';
        document.getElementById('projectAddress').value = d.project_address||'';
        document.getElementById('inspectionArea').value = d.inspection_area||'';
        document.getElementById('detectionDate').value = d.detection_date||'';

        // 检测状态
        const stateRadio = document.querySelector(`input[name="detectionState"][value="${d.detection_state||'静态'}"]`);
        if(stateRadio) stateRadio.checked = true;

        // 气象条件
        if(d.weather){
            document.getElementById('weatherTemp').value = d.weather.temperature||'';
            document.getElementById('weatherHumidity').value = d.weather.humidity||'';
            document.getElementById('weatherPressure').value = d.weather.pressure||'';
        }

        // 2. 选择领域(直接设置,不依赖按钮点击)
        if(d.domain){
            // 清空已有房间
            document.getElementById('roomsContainer').innerHTML = '';
            roomCounter = 0;

            // 直接设置领域状态
            currentDomain = d.domain;
            currentDetectionType = null;

            // 高亮对应按钮
            document.querySelectorAll('.domain-btn').forEach(b=>{
                b.classList.remove('active');
                if(b.getAttribute('onclick')?.includes("'"+d.domain+"'")) b.classList.add('active');
            });

            // 编辑回填时保留全局引导区可见，避免用户误判内容缺失
            document.getElementById('detectionTypeCard')?.classList.remove('hidden');
            document.getElementById('basisCard')?.classList.remove('hidden');
            document.getElementById('judgementCard')?.classList.remove('hidden');
            document.getElementById('roomsCard')?.classList.remove('hidden');
        }

        // 3. 清空已有房间
        document.getElementById('roomsContainer').innerHTML = '';
        roomCounter = 0;

        // 4. 逐个添加房间并填充数据
        if(d.rooms && d.rooms.length > 0){
            d.rooms.forEach((room, ri) => {
                addRoom();
                const rid = 'r' + roomCounter;
                const card = document.querySelector(`[data-rid="${rid}"]`);

                if(!card) return;

                // 房间名称
                const nameInput = card.querySelector('.rname');
                if(nameInput) nameInput.value = room.room_name || room.name || '';

                // 尺寸
                const dimL = card.querySelector('[data-room-dimensions] [data-dim="length"]');
                const dimW = card.querySelector('[data-room-dimensions] [data-dim="width"]');
                const dimH = card.querySelector('[data-room-dimensions] [data-dim="height"]');
                if(dimL) dimL.value = room.length || '';
                if(dimW) dimW.value = room.width || '';
                if(dimH) dimH.value = room.height || '';
                if(room.type_id === 'ivc'){
                    card.dataset.roomLength = room.length || '';
                    card.dataset.roomWidth = room.width || '';
                    card.dataset.roomHeight = room.height || '';
                }

                // 选择检测类型
                if(room.type_id){
                    let typeBtn = null;
                    card.querySelectorAll('.level-btn').forEach(btn=>{
                        if(btn.getAttribute('onclick')?.includes("'"+room.type_id+"'")) typeBtn = btn;
                    });
                    if(typeBtn) selRoomType(rid, room.type_id);
                }

                // 等待检测类型渲染完成后填充洁净等级和参数
                setTimeout(()=>{
                    // 恢复房间级 dataset / summary（第一轮抽离）
                    restoreRoomDatasets(rid, room, card);

                    // 重新按已恢复dataset渲染依据/判定面板
                    const detTypeForRestore = getRoomDetType(rid);
                    if(detTypeForRestore){
                        renderRoomBasis(rid, currentDomain, detTypeForRestore);
                        renderRoomJudgementForType(rid, currentDomain, detTypeForRestore);
                    }
                    if(room.type_id === 'electronics_workshop' && card.dataset.electronicsParamsReady !== 'true'){
                        card.dataset.electronicsManualRangeKeys = '[]';
                        card.dataset.electronicsManualSource = '';
                    }
                    if(room.type_id === 'pass_box'){
                        const passBoxParams = room.params && typeof room.params === 'object' ? room.params : null;
                        const hasSavedPassBoxParams = !!(passBoxParams && Object.keys(passBoxParams).length > 0);
                        card.dataset.businessDomainHint = 'pharma';
                        card.dataset.passBoxParamsReady = hasSavedPassBoxParams ? 'true' : 'false';
                        if(!hasSavedPassBoxParams){
                            card.dataset.passBoxJudgementActive = '[]';
                            card.dataset.passBoxJudgementSource = '';
                            card.dataset.passBoxResultState = '';
                        } else if(!(Array.isArray(room.pass_box_judgement_active) && room.pass_box_judgement_active.length > 0)){
                            card.dataset.passBoxJudgementSource = '';
                        }
                    } else {
                        card.dataset.passBoxParamsReady = 'false';
                        card.dataset.passBoxJudgementActive = '[]';
                        card.dataset.passBoxJudgementSource = '';
                        card.dataset.passBoxResultState = '';
                    }
                    if(room.type_id === 'animal_room'){
                        if(room.clean_class) {
                            card.dataset.cleanClass = room.clean_class;
                            card.dataset.levelName = room.clean_class;
                        }
                        if(room.barrier_room_class) card.dataset.barrierRoomClass = room.barrier_room_class;
                        if(room.barrier_aux_room) card.dataset.barrierAuxRoom = room.barrier_aux_room;
                        card.dataset.animalContextIncomplete = room.animal_context_incomplete ? 'true' : 'false';
                        if(room.animal_context_incomplete){
                            card.querySelector('.rb-summary') && (card.querySelector('.rb-summary').textContent = '未完成');
                            card.querySelector('.rj-summary') && (card.querySelector('.rj-summary').textContent = '未完成');
                            card.querySelector('.rb-body') && (card.querySelector('.rb-body').style.display = 'none');
                            card.querySelector('.rj-body') && (card.querySelector('.rj-body').style.display = 'none');
                            card.querySelector('.rb-arrow') && (card.querySelector('.rb-arrow').textContent = '▼');
                            card.querySelector('.rj-arrow') && (card.querySelector('.rj-arrow').textContent = '▼');
                        }
                    }
                    if(room.type_id === 'clean_function_room'){
                        if(room.clean_function_subroom) card.dataset.cleanFunctionSubroom = room.clean_function_subroom;
                        if(room.clean_class){
                            const normalizedFoodCleanClass = room.type_id === 'food_workshop' ? normalizeFoodGradeValue(room.clean_class) : room.clean_class;
                            card.dataset.cleanClass = normalizedFoodCleanClass;
                            card.dataset.levelName = normalizedFoodCleanClass;
                        }
                    }
                    updateRoomSummary(rid);
                    if(room.animal_context_incomplete){
                        if(room.clean_class === '屏障环境' && !room.barrier_room_class){
                            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择房间类别</p>';
                        } else if(room.clean_class === '屏障环境' && room.barrier_room_class === '洁净辅房' && !room.barrier_aux_room){
                            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择洁净辅房名称</p>';
                        }
                    }

                    // 统一恢复对象上下文 / 等级选择（第一轮抽离）
                    restoreNestedRoomContext(rid, room, card);
                    if(room.type_id === 'animal_room'){
                        setTimeout(()=>{
                            syncAnimalRoomContextSummary(rid);
                            updateRoomSummary(rid);
                        }, 120);
                    }

                    // 等待参数渲染完成后填充数据
                    waitForRoomRestore(()=>isRoomParamRestoreReady(card, room), ()=>{
                        if(room.type_id === 'ivc'){
                            handleRoomDimensionChange(rid);
                        }
                        const animalContextIncompleteBeforeFill = isAnimalBarrierContextIncomplete(card);
                        if(!animalContextIncompleteBeforeFill){
                            fillRoomParams(rid, card, room.params||{});
                            const hasAirchangeParam = !!Object.keys(room.params || {}).find(k => {
                                const p = room.params[k] || {};
                                const t = p.type || p.inputType || '';
                                return t.includes('airchange') || k === 'airchange' || k === 'airchange_clean';
                            });
                            if(hasAirchangeParam){
                                setTimeout(()=>{ handleRoomDimensionChange(rid); }, 80);
                            }
                            if(room.type_id === 'operating_room'){
                                setTimeout(()=>{ fillRoomParams(rid, card, room.params||{}); updateRoomSummary(rid); }, 180);
                            }
                            if(room.type_id === 'animal_room' && room.clean_class === '屏障环境'){
                                setTimeout(()=>{ fillRoomParams(rid, card, room.params||{}); updateRoomSummary(rid); }, 220);
                            }
                            if(room.type_id === 'pass_box'){
                                const hasPassBoxParams = (room.params && Object.keys(room.params||{}).length > 0) || !!card.querySelector('.pb');
                                card.dataset.passBoxParamsReady = hasPassBoxParams ? 'true' : 'false';
                                setTimeout(()=>{ syncPassBoxResultState(rid); updateRoomJudgementSummary(rid); }, 80);
                            }
                            if(room.type_id === 'electronics_workshop'){
                                setTimeout(()=>{ syncElectronicsManualState(rid); }, 60);
                            }
                            if(room.type_id === 'bsl'){
                                setTimeout(()=>{ syncPressurePairSummaryState(rid, 'pressure'); }, 60);
                            }
                            if(room.type_id === 'animal_room'){
                                setTimeout(()=>{ syncAnimalContextMarker(rid); }, 60);
                            }
                            if((room.type_id === 'pass_box' || room.type_id === 'laminar_hood') && room.hepa_leak_summary && !card.dataset.hepaLeakSourceState){
                                card.dataset.hepaLeakSourceState = 'saved';
                            }
                        } else if(room.clean_class === '屏障环境' && !room.barrier_room_class){
                            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择房间类别</p>';
                        } else if(room.clean_class === '屏障环境' && room.barrier_room_class === '洁净辅房' && !room.barrier_aux_room){
                            card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择洁净辅房名称</p>';
                        }
                        restoreRoomExpandedStates(card, room);
                        if(room.type_id === 'animal_room'){
                            syncAnimalRoomContextSummary(rid);
                            const animalContextIncomplete = isAnimalBarrierContextIncomplete(card);
                            if(animalContextIncomplete){
                                const rbBody = card.querySelector('.rb-body');
                                const rjBody = card.querySelector('.rj-body');
                                if(rbBody) rbBody.innerHTML = '';
                                if(rjBody) rjBody.innerHTML = '';
                                renderRoomBasis(rid, currentDomain, detTypeForRestore);
                                renderRoomJudgementForType(rid, currentDomain, detTypeForRestore);
                                syncAnimalRoomContextSummary(rid);
                                if(room.clean_class === '屏障环境' && !room.barrier_room_class){
                                    card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择房间类别</p>';
                                } else if(room.clean_class === '屏障环境' && room.barrier_room_class === '洁净辅房' && !room.barrier_aux_room){
                                    card.querySelector('.rparams').innerHTML = '<p style="color:#999;font-size:13px;text-align:center;padding:20px;">💡 请选择洁净辅房名称</p>';
                                }
                            }
                        }
                        updateRoomSummary(rid);
                    }, { retries: 16, delay: 40 });
                }, 200);
            });
        }

        // 5. 切到新建记录tab
        showTab('new');
        const roomCount = d.rooms?.length || 0;
        const safeDelay = Math.max(1500, roomCount * 500 + 800);
        setTimeout(()=>{
            window.scrollTo(0,0);
            // 恢复完成，解除恢复中状态，重新允许 auto-save
            window._isRestoringDraft = false;
            _autoSaveDirty = false;
        }, safeDelay);
        updateProjectInfoSummary();
        showToast('✅ 记录已加载,可以修改','success');

        // 当前阶段以真实导出、页面回归和收楼文档作为验收依据。

    }catch(e){showToast('加载失败: '+e.message, 'error');}
}

function fillRoomParams(rid, card, params){
    const detTypeForFill = getRoomDetType(rid);
    const paramTypeMap = {};
    (detTypeForFill?.params || []).forEach(p => { if(p && p.key) paramTypeMap[p.key] = p.inputType || p.type || ''; });
    if(isAnimalBarrierContextIncomplete(card)){
        card.querySelectorAll('.pb .cv[data-res]').forEach(resEl => {
            resEl.textContent = '-';
            resEl.style.color = '';
            resEl.style.fontWeight = '';
        });
        card.querySelectorAll('.pb').forEach(pb => {
            pb.querySelectorAll('input').forEach(input => {
                if(input.type === 'checkbox' || input.type === 'radio' || input.type === 'button' || input.type === 'submit') return;
                input.value = '';
            });
            pb.querySelectorAll('select').forEach(sel => sel.selectedIndex = 0);
            pb.querySelectorAll('textarea').forEach(ta => ta.value = '');
        });
        return;
    }
    for(const [key, param] of Object.entries(params)){
        const pb = card.querySelector(`[data-pk="${key}"]`);
        if(!pb) continue;
        const ptype = param.type || param.inputType || paramTypeMap[key] || pb.dataset.itype || '';

        if(ptype === 'numeric' || ptype === 'wind_uniformity' || ptype === 'illumination_uniformity' || ptype === 'numeric_range_manual'){
            const vals = param.values||[];
            const inputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            const isBSLPressureLike = ptype === 'numeric' && pb.closest('[data-dp-bsl]');
            // 先确保有足够的输入框
            const addBtn = pb.querySelector('.add-pt');
            while(inputs.length < vals.length && addBtn){
                addBtn.click();
            }
            const updatedInputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            vals.forEach((v, i)=>{
                if(updatedInputs[i]) updatedInputs[i].value = v;
            });
            // 恢复手动判定范围
            if(ptype === 'numeric_range_manual'){
                const mrInput = pb.querySelector(`[data-manual-range="${key}"]`);
                const mrMin = pb.querySelector(`[data-mr-min="${key}"]`);
                const mrMax = pb.querySelector(`[data-mr-max="${key}"]`);
                if(mrInput && param.manualRange) mrInput.value = param.manualRange;
                if(mrMin) mrMin.value = param.manualMin || '';
                if(mrMax) mrMax.value = param.manualMax || '';
                const hasSavedManualCarrier = !!((param.manualMin || '') || (param.manualMax || ''));
                if((card.dataset.typeId || '') === 'animal_room' && key === 'animal_illumination'){
                    card.dataset.animalIlluminationSource = hasSavedManualCarrier ? 'saved' : '';
                }
                updateManualNumericRange(rid, key, (mrInput && mrInput.value) ? mrInput.value : (param.manualRange || ''));
                if((card.dataset.typeId || '') === 'animal_room' && key === 'animal_illumination' && card.dataset.animalIlluminationSource === 'saved' && hasSavedManualCarrier){
                    card.dataset.animalIlluminationSource = 'saved';
                }
            }
            // 触发计算
            if(isBSLPressureLike){
                card.dataset[`pressurePairSummary_${key}`] = param.primarySummary || '';
                if((param.primarySummary || '').trim()){
                    card.dataset[`pressurePairCarrier_${key}`] = 'true';
                } else {
                    delete card.dataset[`pressurePairCarrier_${key}`];
                }
                calc_pressure_pairs(rid, key);
                updateRoomSummary(rid);
            } else if(updatedInputs[0]) {
                updatedInputs[0].dispatchEvent(new Event('input',{bubbles:true}));
                if(ptype === 'numeric_range_manual' && (card.dataset.typeId || '') === 'animal_room' && key === 'animal_illumination' && card.dataset.animalIlluminationSource === 'saved' && ((param.manualMin || '') || (param.manualMax || ''))){
                    card.dataset.animalIlluminationSource = 'saved';
                }
            }

        } else if(ptype === 'particle_zone'){
            const d = param.data||{};
            const set = (k,v)=>{ const el=pb.querySelector(`[data-pz="${k}"]`); if(el) el.value=v||''; };
            set('op_05_max',d.op_05_max); set('op_05_ucl',d.op_05_ucl);
            set('op_5_max',d.op_5_max); set('op_5_ucl',d.op_5_ucl);
            set('surr_05_max',d.surr_05_max); set('surr_05_ucl',d.surr_05_ucl);
            set('surr_5_max',d.surr_5_max); set('surr_5_ucl',d.surr_5_ucl);
            // 触发计算
            const firstInput = pb.querySelector('[data-pz]');
            if(firstInput) firstInput.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'particle_4'){
            const d = param.data||{};
            const set = (k,v)=>{ const el=pb.querySelector(`[data-p4="${k}"]`); if(el) el.value=v||''; };
            set('p05_max',d.p05_max); set('p05_ucl',d.p05_ucl);
            set('p5_max',d.p5_max); set('p5_ucl',d.p5_ucl);
            const firstInput = pb.querySelector('[data-p4]');
            if(firstInput) firstInput.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'particle_4_051'){
            const d = param.data||{};
            const set = (k,v)=>{ const el=pb.querySelector(`[data-p4="${k}"]`); if(el) el.value=v||''; };
            set('p05_max',d.p05_max); set('p05_ucl',d.p05_ucl);
            set('p1_max',d.p1_max); set('p1_ucl',d.p1_ucl);
            const firstInput = pb.querySelector('[data-p4]');
            if(firstInput) firstInput.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'particle_4_8'){
            const d = param.data||{};
            const set = (k,v)=>{ const el=pb.querySelector(`[data-p48="${k}"]`); if(el) el.value=v||''; };
            set('p05_max',d.p05_max); set('p05_ucl',d.p05_ucl);
            set('p5_max',d.p5_max); set('p5_ucl',d.p5_ucl);
            const firstInput = pb.querySelector('[data-p48]');
            if(firstInput) firstInput.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'noise_corrected'){
            const bgInput = pb.querySelector('[data-noise="background"]');
            const indoorInput = pb.querySelector('[data-noise="indoor"]');
            const bg = param.background ?? param.bg ?? param.noise_background ?? param.data?.background ?? '';
            const indoor = param.room_noise ?? param.indoor ?? param.noise_indoor ?? param.data?.indoor ?? '';
            if(bgInput) bgInput.value = bg;
            if(indoorInput) indoorInput.value = indoor;
            if(bgInput || indoorInput) calc_noise(rid, key);

        } else if(ptype === 'bacteria_zone'){
            const d = param.data||{};
            const set = (k,v)=>{ const el=pb.querySelector(`[data-bz="${k}"]`); if(el) el.value=v||''; };
            set('op_points',d.op_points); set('op_total',d.op_total);
            set('surr_points',d.surr_points); set('surr_total',d.surr_total);
            const firstInput = pb.querySelector('[data-bz]');
            if(firstInput) firstInput.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'bacteria_zone_control'){
            const opVals = (param.data?.op_values || param.op_values || param.values_op || []);
            const surrVals = (param.data?.surr_values || param.surr_values || param.values_surr || []);
            const opInputs = pb.querySelectorAll(`[data-dp="${key}_op"] input`);
            const surrInputs = pb.querySelectorAll(`[data-dp="${key}_surr"] input`);
            const addOpBtn = pb.querySelector('[data-dp="'+key+'_op"] .add-pt');
            const addSurrBtn = pb.querySelector('[data-dp="'+key+'_surr"] .add-pt');
            while(opInputs.length < opVals.length && addOpBtn) addOpBtn.click();
            while(surrInputs.length < surrVals.length && addSurrBtn) addSurrBtn.click();
            const updatedOpInputs = pb.querySelectorAll(`[data-dp="${key}_op"] input`);
            const updatedSurrInputs = pb.querySelectorAll(`[data-dp="${key}_surr"] input`);
            opVals.forEach((v, i)=>{ if(updatedOpInputs[i]) updatedOpInputs[i].value = v; });
            surrVals.forEach((v, i)=>{ if(updatedSurrInputs[i]) updatedSurrInputs[i].value = v; });
            const opBlankEl = pb.querySelector(`[data-bzc-blank-op="${key}"]`);
            const opNegEl = pb.querySelector(`[data-bzc-neg-op="${key}"]`);
            const surrBlankEl = pb.querySelector(`[data-bzc-blank-surr="${key}"]`);
            const surrNegEl = pb.querySelector(`[data-bzc-neg-surr="${key}"]`);
            if(opBlankEl) opBlankEl.value = param.op_blank ?? param.blank_op ?? '';
            if(opNegEl) opNegEl.value = param.op_neg ?? param.neg_op ?? '';
            if(surrBlankEl) surrBlankEl.value = param.surr_blank ?? param.blank_surr ?? '';
            if(surrNegEl) surrNegEl.value = param.surr_neg ?? param.neg_surr ?? '';
            if(updatedOpInputs[0]) {
                updatedOpInputs[0].dispatchEvent(new Event('input',{bubbles:true}));
            } else if(updatedSurrInputs[0]) {
                updatedSurrInputs[0].dispatchEvent(new Event('input',{bubbles:true}));
            }

        } else if(ptype === 'pass_fail'){
            const isPass = param.pass === true || param.pass === 'true' || param.value === '符合要求';
            const btns = pb.querySelectorAll('.level-btn');
            btns.forEach(btn=>{
                const txt = (btn.textContent || '').trim();
                if((isPass && txt === '符合要求') || (!isPass && txt === '不符合要求')){
                    btn.click();
                }
            });

        } else if(ptype === 'airchange_speed_only'){
            const vents = param.vents||[];
            const ventRows = pb.querySelectorAll('[data-vent-row]');
            const addVentBtn = pb.querySelector('.add-pt');
            while(ventRows.length < vents.length && addVentBtn) addVentBtn.click();
            const updatedRows = pb.querySelectorAll('[data-vent-row]');
            vents.forEach((v, i)=>{
                if(!updatedRows[i]) return;
                const a = updatedRows[i].querySelector('[data-va]');
                const s = updatedRows[i].querySelector('[data-vs]');
                if(a) a.value = v.area||'';
                if(s) s.value = v.speed||'';
            });
            calc_airchange(rid, key);

        } else if(ptype === 'airchange_speed'){
            const vents = param.vents||[];
            const ventRows = pb.querySelectorAll('[data-vent-row]');
            const addVentBtn = pb.querySelector('.add-pt');
            while(ventRows.length < vents.length && addVentBtn) addVentBtn.click();
            const updatedRows = pb.querySelectorAll('[data-vent-row]');
            vents.forEach((v, i)=>{
                if(!updatedRows[i]) return;
                const a = updatedRows[i].querySelector('[data-va]');
                const s = updatedRows[i].querySelector('[data-vs]');
                if(a) a.value = v.area||'';
                if(s) s.value = v.speed||'';
            });
            calc_airchange(rid, key);

        } else if(ptype === 'airchange_volume'){
            const vals = param.values||[];
            const inputs = pb.querySelectorAll(`[data-dp-vol="${key}"] input`);
            vals.forEach((v, i)=>{ if(inputs[i]) inputs[i].value = v; });
            if(inputs[0]) inputs[0].dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'bacteria_control'){
            const vals = param.values||[];
            const inputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            const addBtn = pb.querySelector('.add-pt');
            while(inputs.length < vals.length && addBtn) addBtn.click();
            const updatedInputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            vals.forEach((v, i)=>{ if(updatedInputs[i]) updatedInputs[i].value = v; });
            const blankEl = pb.querySelector(`[data-bc-blank="${key}"]`);
            const negEl = pb.querySelector(`[data-bc-neg="${key}"]`);
            if(blankEl) blankEl.value = param.blank||'';
            if(negEl) negEl.value = param.neg||'';
            if(updatedInputs[0]) {
                updatedInputs[0].dispatchEvent(new Event('input',{bubbles:true}));
            }

        } else if(ptype === 'settling_control'){
            const vals = param.values||[];
            const inputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            const addBtn = pb.querySelector('.add-pt');
            while(inputs.length < vals.length && addBtn) addBtn.click();
            const updatedInputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            vals.forEach((v, i)=>{ if(updatedInputs[i]) updatedInputs[i].value = v; });
            const blankEl = pb.querySelector(`[data-sc-blank="${key}"]`);
            const negEl = pb.querySelector(`[data-sc-neg="${key}"]`);
            if(blankEl) blankEl.value = param.blank||'';
            if(negEl) negEl.value = param.neg||'';
            if(updatedInputs[0]) {
                updatedInputs[0].dispatchEvent(new Event('input',{bubbles:true}));
            }

        } else if(ptype === 'floating_control'){
            const volEl = pb.querySelector(`[data-fc-vol="${key}"]`);
            if(volEl) volEl.value = param.volume||'';
            const vals = param.values||[];
            const inputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            const addBtn = pb.querySelector('.add-pt');
            while(inputs.length < vals.length && addBtn) addBtn.click();
            const updatedInputs = pb.querySelectorAll(`[data-dp="${key}"] input`);
            vals.forEach((v, i)=>{ if(updatedInputs[i]) updatedInputs[i].value = v; });
            const blankEl = pb.querySelector(`[data-fc-blank="${key}"]`);
            const negEl = pb.querySelector(`[data-fc-neg="${key}"]`);
            if(blankEl) blankEl.value = param.blank||'';
            if(negEl) negEl.value = param.neg||'';
            if(updatedInputs[0]) {
                updatedInputs[0].dispatchEvent(new Event('input',{bubbles:true}));
            }

        } else if(ptype === 'settling'){
            const ptsEl = pb.querySelector('[data-st="points"]');
            const totalEl = pb.querySelector('[data-st="total"]');
            if(ptsEl) ptsEl.value = (param.data||{}).points||'';
            if(totalEl) totalEl.value = (param.data||{}).total||'';
            if(ptsEl) ptsEl.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'floating'){
            const volEl = pb.querySelector('[data-fl="volume"]');
            const totalEl = pb.querySelector('[data-fl="total"]');
            if(volEl) volEl.value = (param.data||{}).volume||'';
            if(totalEl) totalEl.value = (param.data||{}).total||'';
            if(volEl) volEl.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'pressure_bsl'){
            const container = pb.querySelector(`[data-dp-bsl="${key}"]`);
            const pairsContainer = container?.querySelector(`[data-bsl-pairs="${key}"]`);
            const pairList = Array.isArray(param.pairs) && param.pairs.length
                ? param.pairs
                : [{refRoom:param.refRoom||'', values:param.values||[], pressureType:param.pressureType||'positive', range:param.range||''}];
            if(param.primarySummary) card.dataset[`pressurePairSummary_${key}`] = param.primarySummary;
            if(pairsContainer){
                pairsContainer.innerHTML = '';
                pairList.forEach((pair, idx)=>{
                    pairsContainer.insertAdjacentHTML('beforeend', renderPressurePairRow(rid, key, idx+1, pair.refRoom||'', pair.values||[]));
                });
                pairsContainer.querySelectorAll('[data-pressure-pair-row]').forEach((row, idx)=>{
                    const pair = pairList[idx] || {};
                    const ptype = pair.pressureType === 'negative' ? 'negative' : 'positive';
                    row.querySelectorAll('[data-pair-ptype]').forEach(b=>b.classList.remove('active'));
                    const activeBtn = row.querySelector(`[data-pair-ptype="${ptype}"]`);
                    if(activeBtn) activeBtn.classList.add('active');
                    const rangeInput = row.querySelector(`[data-pair-range="${key}"]`);
                    if(rangeInput) rangeInput.value = pair.range || '';
                });
            }
            calc_pressure_pairs(rid, key);
            setTimeout(()=>{ syncPressurePairSummaryState(rid, key); }, 30);

        } else if(ptype === 'temp_diff'){
            const highEl = pb.querySelector('[data-td="high"]');
            const lowEl = pb.querySelector('[data-td="low"]');
            if(highEl) highEl.value = param.high||'';
            if(lowEl) lowEl.value = param.low||'';
            if(highEl) highEl.dispatchEvent(new Event('input',{bubbles:true}));

        } else if(ptype === 'hepa_leak_multi'){
            const container = pb.querySelector(`[data-hepa-container="${key}"]`);
            const objects = Array.isArray(param.objects) && param.objects.length
                ? param.objects
                : [{ name: param.objectName || '', value: (Array.isArray(param.values) && param.values.length) ? param.values[0] : '' }];
            if(container){
                while(container.querySelectorAll('.hepa-object').length < objects.length){
                    addHepaObj(rid, key);
                    if(container.querySelectorAll('.hepa-object').length >= objects.length) break;
                }
                const objEls = container.querySelectorAll('.hepa-object');
                objEls.forEach((objEl, idx)=>{
                    const item = objects[idx] || {};
                    const nameInput = objEl.querySelector('.hepa-name');
                    const numInput = objEl.querySelector('input[type="number"]');
                    if(nameInput) nameInput.value = item.name || '';
                    if(numInput) numInput.value = item.value || '';
                    calc_hepa_single(rid, key, idx);
                });
                calc_hepa_multi(rid, key);
            }
            const savedSummary = param.primarySummary || param.summary || card.dataset.hepaLeakSummary || '';
            const savedStandard = param.standard || 'GB 50591-2010';
            const savedRange = param.range || '';
            if(savedSummary){
                card.dataset.hepaLeakSummary = savedSummary.includes('[') ? savedSummary : `${savedSummary}[${savedStandard}]`;
            } else if(savedRange){
                const firstName = objects[0]?.name || '对象1';
                card.dataset.hepaLeakSummary = `${firstName}:${savedRange}[${savedStandard}]`;
            }
            if((param.primarySummary || param.summary || param.standard || param.range) && !card.dataset.hepaLeakSourceState){
                card.dataset.hepaLeakSourceState = 'saved';
            }
            updateRoomSummary(rid);

        } else if(ptype === 'text'){
            const vals = param.values||[];
            const el = pb.querySelector(`[data-tv="${key}"]`);
            if(el && vals[0]) el.value = vals[0];
        }
    }
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
function hideExportLoading(){
    var div = document.getElementById('export-loading-overlay');
    if(div) div.remove();
}

// ========== V3.4 带对照的渲染函数 ==========
function renderBacteriaControl(rid,p){
    const {range, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';
    let h = '';
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div style="font-size:12px;color:#666;margin-bottom:4px;">菌落数(cfu/m3):</div>
    <div class="dp" data-dp="${p.key}">
        <input type="number" step="1" min="0" placeholder="1" oninput="calc_bacteria_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="2" oninput="calc_bacteria_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="3" oninput="calc_bacteria_control('${rid}','${p.key}')">
        <button class="add-pt" onclick="addPt_bc('${rid}','${p.key}')">+</button>
    </div>
    <div style="margin-top:8px;display:flex;gap:8px;">
        <div style="flex:1;"><label style="font-size:11px;color:#666;">空白对照(cfu)</label><input type="number" data-bc-blank="${p.key}" oninput="calc_bacteria_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
        <div style="flex:1;"><label style="font-size:11px;color:#666;">阴性对照(cfu)</label><input type="number" data-bc-neg="${p.key}" oninput="calc_bacteria_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
    </div>`;
    return h;
}
function renderSettlingControl(rid,p){
    // 获取判定标准
    const room = document.querySelector(`[data-rid="${rid}"]`);
    const detType = getRoomDetType(rid);
    // 医院洁净功能用房中的“细菌浓度（沉降法）”前后台统一按沉降法标准取值
    const rangeKey = ((room?.dataset?.typeId || '') === 'clean_function_room' && p.key === 'bacteria') ? 'settling' : p.key;
    // 从 standardRanges 获取判定范围和实际命中的标准
    const {range, unit, standard} = getParamRange(rid, rangeKey);
    const stdLabel = standard || '';
    
    let h = '';
    // 添加判定范围显示
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div style="font-size:12px;color:#666;margin-bottom:4px;">菌落数(cfu/皿):</div>
    <div class="dp" data-dp="${p.key}">
        <input type="number" step="1" min="0" placeholder="1" oninput="calc_settling_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="2" oninput="calc_settling_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="3" oninput="calc_settling_control('${rid}','${p.key}')">
        <button class="add-pt" onclick="addPt_sc('${rid}','${p.key}')">+</button>
    </div>
    <div style="margin-top:8px;display:flex;gap:8px;">
        <div style="flex:1;"><label style="font-size:11px;color:#666;">空白对照(cfu)</label><input type="number" data-sc-blank="${p.key}" oninput="calc_settling_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
        <div style="flex:1;"><label style="font-size:11px;color:#666;">阴性对照(cfu)</label><input type="number" data-sc-neg="${p.key}" oninput="calc_settling_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
    </div>`;
    return h;
}
function renderFloatingControl(rid,p){
    const {range, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';

    let h = '';
    if(range) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `<span style="color:#2e7d32;">${range} ${unit || p.unit || ''}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    h += `<div class="sub-grid" style="grid-template-columns:1fr;margin-bottom:6px;">
        <div class="sub-item"><label>采样量(L)</label><input type="number" step="any" data-fc-vol="${p.key}" oninput="calc_floating_control('${rid}','${p.key}')"></div>
    </div>
    <div style="font-size:12px;color:#666;margin-bottom:4px;">菌落数(cfu/皿):</div>
    <div class="dp" data-dp="${p.key}">
        <input type="number" step="any" placeholder="1" oninput="calc_floating_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="2" oninput="calc_floating_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="3" oninput="calc_floating_control('${rid}','${p.key}')">
        <button class="add-pt" onclick="addPt_fc('${rid}','${p.key}')">+</button>
    </div>
    <div style="margin-top:8px;display:flex;gap:8px;">
        <div style="flex:1;"><label style="font-size:11px;color:#666;">空白对照(cfu)</label><input type="number" data-fc-blank="${p.key}" oninput="calc_floating_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
        <div style="flex:1;"><label style="font-size:11px;color:#666;">阴性对照(cfu)</label><input type="number" data-fc-neg="${p.key}" oninput="calc_floating_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
    </div>`;
    return h;
}
function renderBacteriaZoneControl(rid,p){
    const lbl_op = p.zone_label_op || '手术区';
    const lbl_surr = p.zone_label_surr || '周边区';
    const {range_op, range_surr, unit, standard} = getParamRange(rid, p.key);
    const stdLabel = standard || '';
    let h = '';
    if(range_op || range_surr) {
        h += `<div class="pb-range" style="background:#e8f5e9;padding:4px 8px;border-radius:4px;border-left:3px solid #4caf50;margin-bottom:8px;">`;
        h += `<span style="color:#2e7d32;font-weight:600;">📋 判定范围：</span>`;
        h += `${lbl_op}:<span style="color:#2e7d32;">${range_op || '-'}</span> | ${lbl_surr}:<span style="color:#2e7d32;">${range_surr || '-'}</span>`;
        if(stdLabel) h += ` <span style="color:#999;font-size:11px;margin-left:4px;">[${stdLabel}]</span>`;
        h += `</div>`;
    }
    return `<div style="font-weight:600;margin-bottom:8px;color:#333;">${lbl_op}</div>
    ${h}
    <div class="dp" data-dp="${p.key}_op">
        <input type="number" step="any" placeholder="1" oninput="calc_bacteria_zone_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="2" oninput="calc_bacteria_zone_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="3" oninput="calc_bacteria_zone_control('${rid}','${p.key}')">
        <button class="add-pt" onclick="addPt_bzc('${rid}','${p.key}','_op')">+</button>
    </div>
    <div style="margin-top:6px;display:flex;gap:8px;">
        <div style="flex:1;"><label style="font-size:11px;color:#666;">空白对照</label><input type="number" data-bzc-blank-op="${p.key}" oninput="calc_bacteria_zone_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
        <div style="flex:1;"><label style="font-size:11px;color:#666;">阴性对照</label><input type="number" data-bzc-neg-op="${p.key}" oninput="calc_bacteria_zone_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
    </div>
    <div style="font-weight:600;margin:12px 0 8px;color:#333;">${lbl_surr}</div>
    <div class="dp" data-dp="${p.key}_surr">
        <input type="number" step="any" placeholder="1" oninput="calc_bacteria_zone_control('${rid}','${p.key}')">
        <input type="number" step="any" placeholder="2" oninput="calc_bacteria_zone_control('${rid}','${p.key}')">
        <input type="number" step="1" min="0" placeholder="3" oninput="calc_bacteria_zone_control('${rid}','${p.key}')">
        <button class="add-pt" onclick="addPt_bzc('${rid}','${p.key}','_surr')">+</button>
    </div>
    <div style="margin-top:6px;display:flex;gap:8px;">
        <div style="flex:1;"><label style="font-size:11px;color:#666;">空白对照</label><input type="number" data-bzc-blank-surr="${p.key}" oninput="calc_bacteria_zone_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
        <div style="flex:1;"><label style="font-size:11px;color:#666;">阴性对照</label><input type="number" data-bzc-neg-surr="${p.key}" oninput="calc_bacteria_zone_control('${rid}','${p.key}')" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:6px;"></div>
    </div>`;
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
function calc_settling_control(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;
    
    // 统一只依赖数据库命中的判定范围
    let range = getParamRange(rid,pk).range || '';
    
    const inputs=room.querySelectorAll(`[data-dp="${pk}"] input`);
    const vals=Array.from(inputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    const blank=parseFloat(room.querySelector(`[data-sc-blank="${pk}"]`)?.value);
    const neg=parseFloat(room.querySelector(`[data-sc-neg="${pk}"]`)?.value);
    
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
function calc_floating_control(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;
    
    let range = getParamRange(rid,pk).range || '';
    
    const vol=parseFloat(room.querySelector(`[data-fc-vol="${pk}"]`)?.value);
    const inputs=room.querySelectorAll(`[data-dp="${pk}"] input`);
    const vals=Array.from(inputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    const blank=parseFloat(room.querySelector(`[data-fc-blank="${pk}"]`)?.value);
    const neg=parseFloat(room.querySelector(`[data-fc-neg="${pk}"]`)?.value);
    
    let parts=[];
    let allPass=true;
    
    if(!isNaN(vol)&&vals.length>0&&vol>0){
        const avgData=vals.reduce((a,b)=>a+b,0)/vals.length;
        const avgConc=avgData/vol*1000;
        const pass = judgeRange(avgConc, range);
        if(!pass)allPass=false;
        parts.push(`平均浓度:${avgConc.toFixed(1)}${pass?'✅':'❌'}`);
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
function calc_bacteria_zone_control(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const pb=room.querySelector(`[data-pk="${pk}"]`);
    if(!pb)return;

    const pr=getParamRange(rid,pk);
    const opRange = (pb.dataset.rangeOp || '').trim() || pr.range_op || '';
    const surrRange = (pb.dataset.rangeSurr || '').trim() || pr.range_surr || '';
    
    const opInputs=room.querySelectorAll(`[data-dp="${pk}_op"] input`);
    const opVals=Array.from(opInputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    const opBlank=parseFloat(room.querySelector(`[data-bzc-blank-op="${pk}"]`)?.value);
    const opNeg=parseFloat(room.querySelector(`[data-bzc-neg-op="${pk}"]`)?.value);
    
    const surrInputs=room.querySelectorAll(`[data-dp="${pk}_surr"] input`);
    const surrVals=Array.from(surrInputs).map(i=>parseFloat(i.value)).filter(v=>!isNaN(v));
    const surrBlank=parseFloat(room.querySelector(`[data-bzc-blank-surr="${pk}"]`)?.value);
    const surrNeg=parseFloat(room.querySelector(`[data-bzc-neg-surr="${pk}"]`)?.value);
    
    let parts=[];
    let allPass=true;
    
    if(opVals.length>0){
        const avg=opVals.reduce((a,b)=>a+b,0)/opVals.length;
        const pass = judgeRange(avg, opRange);
        if(!pass)allPass=false;
        parts.push(`手术区平均:${avg.toFixed(1)}${pass?'✅':'❌'}`);
    }
    
    if(!isNaN(opBlank)){
        const pass=opBlank===0;
        if(!pass)allPass=false;
        parts.push(`手术区空白:${opBlank}${pass?'✅':'❌'}`);
    }
    
    if(!isNaN(opNeg)){
        const pass=opNeg===0;
        if(!pass)allPass=false;
        parts.push(`手术区阴性:${opNeg}${pass?'✅':'❌'}`);
    }
    
    if(surrVals.length>0){
        const avg=surrVals.reduce((a,b)=>a+b,0)/surrVals.length;
        const pass = judgeRange(avg, surrRange);
        if(!pass)allPass=false;
        parts.push(`周边区平均:${avg.toFixed(1)}${pass?'✅':'❌'}`);
    }
    
    if(!isNaN(surrBlank)){
        const pass=surrBlank===0;
        if(!pass)allPass=false;
        parts.push(`周边区空白:${surrBlank}${pass?'✅':'❌'}`);
    }
    
    if(!isNaN(surrNeg)){
        const pass=surrNeg===0;
        if(!pass)allPass=false;
        parts.push(`周边区阴性:${surrNeg}${pass?'✅':'❌'}`);
    }
    
    if(parts.length>0)setRes(rid,pk,parts.join(' | '),allPass);
    else {
        setRes(rid,pk,'-','');
    }
}

/* ============================================================
 * 我的任务（检测员侧）
 * ============================================================ */

var _myTasksFilter = 'active';

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

function renderMyTasks(items){
  var box = document.getElementById('mytasks-list');
  if(!box) return;
  if(!items.length){
    box.innerHTML = '<div style="text-align:center;color:#999;padding:30px;">暂无任务</div>';
    return;
  }
  var palette = {
    '待指派': 'background:#fafafa;color:#666;border:1px solid #d9d9d9;',
    '待检测': 'background:#e6f4ff;color:#0958d9;border:1px solid #91caff;',
    '检测中': 'background:#fff7e6;color:#d46b08;border:1px solid #ffd591;',
    '检测完成': 'background:#f6ffed;color:#389e0d;border:1px solid #b7eb8f;',
    '已取消': 'background:#fff1f0;color:#cf1322;border:1px solid #ffa39e;'
  };
  function tag(label){
    var s = palette[label] || palette['待指派'];
    return '<span style="display:inline-flex;align-items:center;padding:2px 10px;border-radius:999px;font-size:12px;white-space:nowrap;' + s + '">' + esc(label||'-') + '</span>';
  }
  function esc(v){ return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  var html = '';
  items.forEach(function(t){
    var status = t.task_status;
    html += '<div style="padding:14px 16px;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:10px;background:#fff;">';
    // 标题行
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
    html += '<div style="font-weight:600;font-size:15px;color:#111827;">' + esc(t.project_name || t.task_name) + '</div>';
    html += tag(t.task_status_label);
    html += '</div>';
    // 信息
    html += '<div style="display:grid;grid-template-columns:80px 1fr 80px 1fr;gap:4px 10px;font-size:13px;color:#374151;">';
    html += '<div style="color:#6b7280;">任务名称</div><div>' + esc(t.task_name) + '</div>';
    html += '<div style="color:#6b7280;">任务类型</div><div>' + esc(t.task_type_label) + '</div>';
    html += '<div style="color:#6b7280;">客户</div><div>' + esc(t.client_name || '—') + '</div>';
    html += '<div style="color:#6b7280;">预计日期</div><div>' + esc(t.expected_execute_date || '—') + '</div>';
    if(t.started_at) html += '<div style="color:#6b7280;">开始时间</div><div>' + esc(t.started_at.replace('T',' ').slice(0,16)) + '</div>';
    if(t.completed_at) html += '<div style="color:#6b7280;">完成时间</div><div>' + esc(t.completed_at.replace('T',' ').slice(0,16)) + '</div>';
    if(t.remarks) html += '<div style="color:#6b7280;">备注</div><div style="grid-column:span 3;">' + esc(t.remarks) + '</div>';
    html += '</div>';
    // 操作按钮（三态简化：只保留"进入录入"和"完成任务"）
    var btns = [];
    if(status === 'assigned' || status === 'accepted' || status === 'in_progress') btns.push('<button class="btn btn-sm" style="background:#667eea;color:#fff;border:none;" onclick="prefillFromTask(' + t.id + ', this)">进入录入</button>');
    if(status === 'assigned' || status === 'accepted' || status === 'in_progress') btns.push('<button class="btn btn-sm" style="background:#389e0d;color:#fff;border:none;" onclick="doTaskAction(' + t.id + ',\'complete\', this)">完成任务</button>');
    if(btns.length) html += '<div style="margin-top:10px;display:flex;gap:8px;justify-content:flex-end;">' + btns.join('') + '</div>';
    html += '</div>';
  });
  box.innerHTML = html;
}
function doTaskAction(taskId, action, btnEl){
  var confirmMsg = {complete:'确认完成任务？'}[action] || '确认？';
  if(!confirm(confirmMsg)) return;
  var btn = btnEl || null;
  var oldText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = action === 'complete' ? '提交中...' : '处理中...'; }
  fetch('/api/project_tasks/' + taskId + '/' + action, {method:'POST'})
    .then(function(r){ return r.json().then(function(d){ return {ok:r.ok, data:d}; }); })
    .then(function(res){
      if(!res.ok || !res.data.success) throw new Error(res.data.error || '操作失败');
      if(typeof showToast === 'function') showToast('操作成功','success');
      loadMyTasks(_myTasksFilter);
      if(typeof pollTaskCount === 'function') pollTaskCount();
    })
    .catch(function(err){
      console.error(err);
      alert(err.message || '操作失败');
    })
    .finally(function(){
      if(btn){ btn.disabled = false; btn.textContent = oldText || '完成任务'; }
    });
}

function prefillFromTask(taskId, btnEl){
  var btn = btnEl || null;
  var oldText = btn ? btn.textContent : '';
  if(btn){ btn.disabled = true; btn.textContent = '进入中...'; }
  fetch('/api/project_tasks/' + taskId + '/prefill')
    .then(function(r){ return r.json().then(function(d){ return {ok:r.ok, data:d}; }); })
    .then(function(res){
      if(!res.ok || !res.data.success) throw new Error(res.data.error || '获取项目信息失败');
      var d = res.data;
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
          el.dispatchEvent(new Event('input', {bubbles:true}));
          el.dispatchEvent(new Event('change', {bubbles:true}));
        }
      }
      window._currentTaskId = taskId;
      window._currentProjectId = d.project_id;
      var body = document.getElementById('projectInfoBody');
      if(body && body.style.display === 'none'){
        var card = document.getElementById('projectInfoCard');
        if(card) card.click();
      }
      if(typeof showToast === 'function') showToast('已从任务自动填入项目信息');
      loadMyTasks(_myTasksFilter);
      if(typeof pollTaskCount === 'function') pollTaskCount();
    })
    .catch(function(err){
      console.error(err);
      alert(err.message || '获取项目信息失败');
    })
    .finally(function(){
      if(btn){ btn.disabled = false; btn.textContent = oldText || '进入录入'; }
    });
}

/* ====== 我的任务 — 角标 + 提示音 ====== */
(function(){
  var _lastTaskCount = -1; // -1 表示首次加载不响

  function playTaskSound(){
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      // 三音提示（do-mi-sol 上行）
      [523, 659, 784].forEach(function(freq, i){
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.13, ctx.currentTime + i * 0.12);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.12);
        osc.stop(ctx.currentTime + i * 0.12 + 0.25);
      });
    } catch(e){}
  }

  window.pollTaskCount = pollTaskCount;
  function pollTaskCount(){
    fetch('/api/my_tasks/pending_count')
      .then(function(r){ return r.json(); })
      .then(function(d){
        var badge = document.getElementById('mytask-badge');
        if(!badge) return;
        var count = d.count || 0;
        if(count > 0){
          badge.textContent = count;
          badge.style.display = '';
          // 有新任务时响
          if(_lastTaskCount >= 0 && count > _lastTaskCount) playTaskSound();
        } else {
          badge.style.display = 'none';
        }
        _lastTaskCount = count;
      })
      .catch(function(){});
  }

  // 页面加载后立即查一次，然后每 60 秒轮询
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){ pollTaskCount(); setInterval(pollTaskCount, 30000); });
  } else {
    pollTaskCount();
    setInterval(pollTaskCount, 30000);
  }

  // 切到任务 tab 时刷新
  var _origShowTab = window.showTab;
  if(_origShowTab){
    window.showTab = function(tab){
      _origShowTab(tab);
      if(tab === 'mytasks') pollTaskCount();
    };
  }
})();
