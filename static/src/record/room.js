// room.js - 34 functions
// Auto-extracted from record.js

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

function toggleRoom(rid){
    const card = document.querySelector(`[data-rid="${rid}"]`);
    if(!card) return;
    card.classList.toggle('collapsed');
    updateRoomSummary(rid);
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


// Export all functions
export {
    updateAllRoomsRanges,
    getRoomLevels,
    addRoom,
    toggleRoomBasis,
    updateRoomBasisSummary,
    selRoomType,
    syncAnimalRoomContextSummary,
    toggleRoomJudgementCode,
    toggleRoom,
    updateRoomSummary,
    toggleRoomJudgement,
    updateRoomJudgementSummary,
    switchRoomStar,
    updateRoomRanges,
    updateRoomRangesByPriority,
    normalizeOperatingRoomTypeValue,
    normalizeOperatingAuxRoomValue,
    normalizeOperatingAuxCleanClassValue,
    normalizeFoodGradeValue,
    applyFlatCleanClassRestore,
    waitForRoomRestore,
    restoreRoomDatasets,
    restoreRoomExpandedStates,
    restoreNestedRoomContext,
    selCleanClass,
    selBarrierRoomClass,
    selBarrierAuxRoom,
    selSurgeryRoomType,
    cleanClassOrDefault,
    selCleanFunctionSubroom,
    selSurgeryAuxRoom,
    selSurgeryAuxCleanClass,
    handleRoomDimensionChange,
    buildRoomHierarchySummary
};
