// calc.js - 34 functions
// Auto-extracted from record.js

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
    h+=`<input type="number" step="any" min="0" placeholder="输入检测值" style="flex:1;padding:6px;border:1px solid #ddd;border-radius:4px;" oninput="calc_hepa_single('${rid}','${p.key}',0)">`;
    h+=`<span style="color:#666;font-size:13px;">${displayUnit}</span>`;
    h+=`</div>`;
    h+=`</div>`;
    h+=`<button class="add-pt" style="margin-top:6px;width:100%;" onclick="addHepaObj('${rid}','${p.key}')">＋ 添加检测对象</button>`;
    h+=`</div>`;
    h+=`<div class="cr"><span>结果:</span><span class="cv" data-res="${p.key}">-</span></div>`;
    return h;
}

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
    h+=`<input type="number" step="any" min="0" placeholder="输入检测值" style="flex:1;padding:6px;border:1px solid #ddd;border-radius:4px;" oninput="calc_hepa_single('${rid}','${pk}',${newIdx})">`;
    h+=`<span style="color:#666;font-size:13px;">%</span>`;
    h+=`</div>`;
    h+=`<div class="cr" style="margin-top:8px;"><span>结果:</span><span class="cv" data-hepa-res="${pk}-${newIdx}">-</span></div>`;
    h+=`</div>`;

    const btn=container.querySelector('.add-pt');
    btn.insertAdjacentHTML('beforebegin', h);
}

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

function calc_hepa_single(rid,pk,idx){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const obj=room.querySelector(`[data-hepa-idx="${idx}"]`);
    const resSpan=room.querySelector(`[data-hepa-res="${pk}-${idx}"]`);

    if(!obj || !resSpan) return;

    const inputs=obj.querySelectorAll('input[type="number"]');
    const input=inputs[inputs.length-1];
    if(!input) return;
    const val=parseFloat(input.value);

    if(isNaN(val) || val === ''){
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
        room.dataset.hepaLeakSourceState = val.toString().trim() ? 'live' : '';
        updateRoomSummary(rid);
    }
}

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

function calc_text(rid,pk){
    const room=document.querySelector(`[data-rid="${rid}"]`);
    const val=room.querySelector(`[data-tv="${pk}"]`)?.value?.trim();
    if(!val){setRes(rid,pk,'-','');return;}
    const pr=getParamRange(rid,pk);
    if(!pr.range)return;
    const pass=val.includes(pr.range)||pr.range.includes(val);
    setRes(rid,pk,val,pass);
}

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


// Export all functions
export {
    bindRoomParamAutoCalc,
    renderPassBoxVolume,
    renderAirchangeSpeedOnly,
    calc_pass_box_volume,
    calc_temp_diff,
    calc_pressure_pairs,
    renderHepaLeakMulti,
    renderAirchange,
    renderNoiseCorrected,
    renderWindUniformity,
    renderIllumUniformity,
    addHepaObj,
    delHepaObj,
    calc_hepa_single,
    calc_hepa_multi,
    getRoomVolume,
    calc_numeric,
    calc_text,
    calc_airchange,
    calc_airchange_vol,
    calc_noise,
    calc_pzone,
    calc_p4,
    calc_p4_051,
    calc_p4_8,
    calc_bzone,
    calc_settling,
    calc_floating,
    calc_wind_uniformity,
    calc_illum_uniformity,
    setRes,
    calc_settling_control,
    calc_floating_control,
    calc_bacteria_zone_control
};
