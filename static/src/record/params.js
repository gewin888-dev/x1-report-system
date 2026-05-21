// params.js - 34 functions
// Auto-extracted from record.js

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

function renderText(rid,p){
    return `<div class="dp dp-wide"><input type="text" style="width:100%;text-align:left;" placeholder="输入观察结果" data-tv="${p.key}" oninput="calc_text('${rid}','${p.key}')"></div>`;
}

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

function renderFloating(rid,p){
    return `<div class="sub-grid" style="grid-template-columns:1fr 1fr;">
        <div class="sub-item"><label>采样量(L)</label><input type="number" step="any" min="0" data-fl="volume" oninput="calc_floating('${rid}','${p.key}')"></div>
        <div class="sub-item"><label>菌落数(cfu/皿)</label><input type="number" min="0" step="1" data-fl="total" oninput="calc_floating('${rid}','${p.key}')"></div>
    </div>`;
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
    '已派单': 'background:#e6f4ff;color:#0958d9;border:1px solid #91caff;',
    '已接单': 'background:#e6f4ff;color:#0958d9;border:1px solid #91caff;',
    '检测中': 'background:#fff7e6;color:#d46b08;border:1px solid #ffd591;',
    '执行中': 'background:#fff7e6;color:#d46b08;border:1px solid #ffd591;',
    '检测完成': 'background:#f6ffed;color:#389e0d;border:1px solid #b7eb8f;',
    '已完成': 'background:#f6ffed;color:#389e0d;border:1px solid #b7eb8f;',
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
    if(status === 'assigned' || status === 'accepted' || status === 'in_progress') btns.push('<button class="btn btn-sm" style="background:#667eea;color:#fff;border:none;" onclick="prefillFromTask(' + t.id + ')">进入录入</button>');
    if(status === 'assigned' || status === 'accepted' || status === 'in_progress') btns.push('<button class="btn btn-sm" style="background:#389e0d;color:#fff;border:none;" onclick="doTaskAction(' + t.id + ',\'complete\')">完成任务</button>');
    if(btns.length) html += '<div style="margin-top:10px;display:flex;gap:8px;justify-content:flex-end;">' + btns.join('') + '</div>';
    html += '</div>';
  });
  box.innerHTML = html;
}


// Export all functions
export {
    renderParamsForRoom,
    renderRoomBasis,
    renderRoomJudgementForType,
    renderRoomJudgementList,
    getPassBoxResultState,
    syncPassBoxResultState,
    isRoomParamRestoreReady,
    renderParams,
    renderInput,
    renderPassFail,
    selPassFail,
    renderTempDiff,
    renderPressureBSL,
    renderPressurePairRow,
    renderNumeric,
    renderNumericRangeManual,
    renderText,
    renderParticleZone,
    renderParticle4,
    renderParticle4_051,
    renderParticle4_8,
    renderBacteriaZone,
    renderSettling,
    renderFloating,
    getParamRange,
    renderDraftRecords,
    renderHistoryRecords,
    normalizeEditableRoomParams,
    fillRoomParams,
    renderBacteriaControl,
    renderSettlingControl,
    renderFloatingControl,
    renderBacteriaZoneControl,
    renderMyTasks
};
