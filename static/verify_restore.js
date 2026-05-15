// X1 草稿回填验证脚本
// 使用方法：
// 1. 在暂存记录里点击一条草稿，等页面恢复完成
// 2. 打开浏览器控制台（F12 → Console）
// 3. 粘贴运行本脚本
// 4. 查看输出的对比结果

(async function verifyRestoreIntegrity(){
    console.log('🔍 开始验证草稿回填完整性...\n');

    // 1. 获取当前编辑页面的 collectData 结果
    const current = collectData();
    if(!current || !current.rooms || current.rooms.length === 0){
        console.error('❌ 当前页面没有房间数据，请先从暂存恢复一条记录');
        return;
    }

    // 2. 从后端重新加载原始数据
    const recordId = window._editingRecordId;
    if(!recordId){
        console.error('❌ 未找到当前编辑记录ID');
        return;
    }

    let original = null;
    try{
        const res = await fetch('/api/get/' + recordId).then(r => r.json());
        if(res.success){
            original = res.record;
        } else {
            // 可能是本地记录
            console.warn('⚠️ 后端未找到记录，可能是本地离线草稿，跳过对比');
            return;
        }
    }catch(e){
        console.error('❌ 加载原始数据失败:', e);
        return;
    }

    const origRooms = original.rooms || [];
    const currRooms = current.rooms || [];

    console.log(`📊 原始记录: ${origRooms.length} 个房间`);
    console.log(`📊 当前页面: ${currRooms.length} 个房间\n`);

    // 3. 项目级字段对比
    const projectFields = ['project_name', 'client_name', 'report_number', 'detection_date', 'contact_info', 'project_address', 'inspection_area'];
    let projectOk = true;
    projectFields.forEach(f => {
        const orig = String(original[f] || '').trim();
        const curr = String(current[f] || '').trim();
        if(orig !== curr){
            console.warn(`⚠️ 项目字段 ${f}: 原="${orig}" → 当前="${curr}"`);
            projectOk = false;
        }
    });
    if(projectOk) console.log('✅ 项目级字段: 全部一致');

    // 4. 房间数量对比
    if(origRooms.length !== currRooms.length){
        console.error(`❌ 房间数量不一致: 原=${origRooms.length} 当前=${currRooms.length}`);
    } else {
        console.log(`✅ 房间数量: ${origRooms.length} 一致`);
    }

    // 5. 逐房间逐参数对比
    const minLen = Math.min(origRooms.length, currRooms.length);
    let totalParams = 0;
    let matchedParams = 0;
    let missingParams = [];
    let mismatchParams = [];

    for(let i = 0; i < minLen; i++){
        const origRoom = origRooms[i];
        const currRoom = currRooms[i];
        const roomName = origRoom.room_name || origRoom.name || `room_${i}`;
        const origParams = origRoom.params || {};
        const currParams = currRoom.params || {};

        // 检查房间基础字段
        const roomFields = ['type_id', 'level_name', 'clean_class'];
        roomFields.forEach(f => {
            const o = String(origRoom[f] || '').trim();
            const c = String(currRoom[f] || '').trim();
            if(o && o !== c){
                console.warn(`  ⚠️ room[${i}] ${roomName} 字段 ${f}: 原="${o}" → 当前="${c}"`);
            }
        });

        // 检查参数
        const origKeys = Object.keys(origParams);
        origKeys.forEach(pk => {
            totalParams++;
            const origP = origParams[pk];
            const currP = currParams[pk];

            if(!currP){
                missingParams.push(`room[${i}] ${roomName} → ${pk}`);
                return;
            }

            // 对比 values
            const origVals = JSON.stringify(origP.values || origP.data || '');
            const currVals = JSON.stringify(currP.values || currP.data || '');
            if(origVals === currVals){
                matchedParams++;
            } else {
                // 检查是否只是空值差异
                const origEmpty = !origP.values?.length && !origP.data;
                const currEmpty = !currP.values?.length && !currP.data;
                if(origEmpty && currEmpty){
                    matchedParams++;
                } else {
                    mismatchParams.push({
                        location: `room[${i}] ${roomName} → ${pk}`,
                        original: origVals.substring(0, 80),
                        current: currVals.substring(0, 80)
                    });
                }
            }
        });

        // 检查当前页面多出来的参数（不算错误，可能是默认值）
        const currOnlyKeys = Object.keys(currParams).filter(k => !origParams[k]);
        if(currOnlyKeys.length > 0){
            console.log(`  ℹ️ room[${i}] ${roomName}: 当前页面多出 ${currOnlyKeys.length} 个参数: ${currOnlyKeys.join(', ')}`);
        }
    }

    // 6. 输出汇总
    console.log('\n========== 验证结果汇总 ==========');
    console.log(`参数总数: ${totalParams}`);
    console.log(`✅ 一致: ${matchedParams}`);
    console.log(`❌ 丢失: ${missingParams.length}`);
    console.log(`⚠️ 不一致: ${mismatchParams.length}`);

    if(missingParams.length > 0){
        console.log('\n--- 丢失的参数 ---');
        missingParams.forEach(p => console.log(`  ❌ ${p}`));
    }

    if(mismatchParams.length > 0){
        console.log('\n--- 不一致的参数 ---');
        mismatchParams.forEach(p => {
            console.log(`  ⚠️ ${p.location}`);
            console.log(`     原: ${p.original}`);
            console.log(`     现: ${p.current}`);
        });
    }

    if(missingParams.length === 0 && mismatchParams.length === 0){
        console.log('\n🎉 所有参数回填验证通过！');
    }

    return {totalParams, matchedParams, missingParams, mismatchParams};
})();
