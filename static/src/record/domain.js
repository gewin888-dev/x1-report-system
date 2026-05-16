// domain.js - 3 functions
// Auto-extracted from record.js

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


// Export all functions
export {
    renderDomainGrid,
    selectDomain,
    getRoomDetType
};
