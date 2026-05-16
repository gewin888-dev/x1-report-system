// collect.js - 1 functions
// Auto-extracted from record.js

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


// Export all functions
export {
    collectData
};
