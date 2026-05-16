// index.js - Record module entry point
// Imports all modules and exposes functions globally

// Global variables
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
    // 报告编号:自动填充年份和周份
    document.getElementById('reportYearDisplay').textContent=new Date().getFullYear();
    (function(){const now=new Date(),start=new Date(now.getFullYear(),0,1),diff=Math.floor((now-start)/86400000),week=Math.ceil((diff+start.getDay()+1)/7);document.getElementById('reportWeekDisplay').textContent=week;})();
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



// calc module (34 functions)
import { bindRoomParamAutoCalc, renderPassBoxVolume, renderAirchangeSpeedOnly, calc_pass_box_volume, calc_temp_diff, calc_pressure_pairs, renderHepaLeakMulti, renderAirchange, renderNoiseCorrected, renderWindUniformity, renderIllumUniformity, addHepaObj, delHepaObj, calc_hepa_single, calc_hepa_multi, getRoomVolume, calc_numeric, calc_text, calc_airchange, calc_airchange_vol, calc_noise, calc_pzone, calc_p4, calc_p4_051, calc_p4_8, calc_bzone, calc_settling, calc_floating, calc_wind_uniformity, calc_illum_uniformity, setRes, calc_settling_control, calc_floating_control, calc_bacteria_zone_control } from "./calc.js";

// collect module (1 functions)
import { collectData } from "./collect.js";

// domain module (3 functions)
import { renderDomainGrid, selectDomain, getRoomDetType } from "./domain.js";

// export module (7 functions)
import { isGeneratedRecordData, doSave, submitRecord, submitAndGenerate, submitAndExport, exportRecordExcel, hideExportLoading } from "./export.js";

// params module (34 functions)
import { renderParamsForRoom, renderRoomBasis, renderRoomJudgementForType, renderRoomJudgementList, getPassBoxResultState, syncPassBoxResultState, isRoomParamRestoreReady, renderParams, renderInput, renderPassFail, selPassFail, renderTempDiff, renderPressureBSL, renderPressurePairRow, renderNumeric, renderNumericRangeManual, renderText, renderParticleZone, renderParticle4, renderParticle4_051, renderParticle4_8, renderBacteriaZone, renderSettling, renderFloating, getParamRange, renderDraftRecords, renderHistoryRecords, normalizeEditableRoomParams, fillRoomParams, renderBacteriaControl, renderSettlingControl, renderFloatingControl, renderBacteriaZoneControl, renderMyTasks } from "./params.js";

// restore module (6 functions)
import { getRestoreFlow, buildDraftFingerprint, saveDraft, getDraftTypeMeta, isDraftRecord, compareDraftPriority } from "./restore.js";

// room module (34 functions)
import { updateAllRoomsRanges, getRoomLevels, addRoom, toggleRoomBasis, updateRoomBasisSummary, selRoomType, syncAnimalRoomContextSummary, toggleRoomJudgementCode, toggleRoom, updateRoomSummary, toggleRoomJudgement, updateRoomJudgementSummary, switchRoomStar, updateRoomRanges, updateRoomRangesByPriority, normalizeOperatingRoomTypeValue, normalizeOperatingAuxRoomValue, normalizeOperatingAuxCleanClassValue, normalizeFoodGradeValue, applyFlatCleanClassRestore, waitForRoomRestore, restoreRoomDatasets, restoreRoomExpandedStates, restoreNestedRoomContext, selCleanClass, selBarrierRoomClass, selBarrierAuxRoom, selSurgeryRoomType, cleanClassOrDefault, selCleanFunctionSubroom, selSurgeryAuxRoom, selSurgeryAuxCleanClass, handleRoomDimensionChange, buildRoomHierarchySummary } from "./room.js";

// ui module (70 functions)
import { handleAdminEntry, updateReportNumber, showResetDialog, hasMeaningfulEditingContent, showReturnToEditDialog, resetForm, showTab, toggleCard, updateProjectInfoSummary, updateCardSummary, initCardCollapse, setActiveJudgement, isAnimalBarrierContextIncomplete, moveJudgementPriority, syncAnimalContextMarker, syncPressurePairSummaryState, syncElectronicsManualState, isAnimalReadyMissing, isCleanFunctionReadyMissing, isOperatingReadyMissing, hasAnimalReverseAnomaly, hasCleanFunctionReverseAnomaly, hasOperatingReverseAnomaly, isAnimalChainClosed, isCleanFunctionChainClosed, isOperatingChainClosed, isAnimalAcceptanceState, isCleanFunctionAcceptanceState, isOperatingAcceptanceState, isOperatingContextIncomplete, selEquipmentAlias, selBSL, addPressurePair, removePressurePair, addPressureValuePt, switchPressurePairType, switchPressureType, updateBSLPressureRange, handleManualRangeChange, updateManualNumericRange, addPt, addVent, addVolPt, switchMethod, getDisplayRangeText, judgeRange, validate, openDB, buildOfflineTask, normalizeQueueError, getQueueStatusMeta, getSyncEndpoint, getSyncSuccessText, updateOnlineStatus, ensureEditingRecordId, fuzzyKeywordsMatch, previewFile, buildStatusText, openFileWithWPS, openFeishuFile, buildRecordItem, isReportRecord, normalizeLocalTaskRecord, loadHistory, normalizeEditableRecordData, showToast, addPt_bc, loadMyTasks, doTaskAction, prefillFromTask } from "./ui.js";


// Expose all functions globally (for onclick handlers in HTML)
window.addHepaObj = addHepaObj;
window.addPressurePair = addPressurePair;
window.addPressureValuePt = addPressureValuePt;
window.addPt = addPt;
window.addPt_bc = addPt_bc;
window.addRoom = addRoom;
window.addVent = addVent;
window.addVolPt = addVolPt;
window.applyFlatCleanClassRestore = applyFlatCleanClassRestore;
window.bindRoomParamAutoCalc = bindRoomParamAutoCalc;
window.buildDraftFingerprint = buildDraftFingerprint;
window.buildOfflineTask = buildOfflineTask;
window.buildRecordItem = buildRecordItem;
window.buildRoomHierarchySummary = buildRoomHierarchySummary;
window.buildStatusText = buildStatusText;
window.calc_airchange = calc_airchange;
window.calc_airchange_vol = calc_airchange_vol;
window.calc_bacteria_zone_control = calc_bacteria_zone_control;
window.calc_bzone = calc_bzone;
window.calc_floating = calc_floating;
window.calc_floating_control = calc_floating_control;
window.calc_hepa_multi = calc_hepa_multi;
window.calc_hepa_single = calc_hepa_single;
window.calc_illum_uniformity = calc_illum_uniformity;
window.calc_noise = calc_noise;
window.calc_numeric = calc_numeric;
window.calc_p4 = calc_p4;
window.calc_p4_051 = calc_p4_051;
window.calc_p4_8 = calc_p4_8;
window.calc_pass_box_volume = calc_pass_box_volume;
window.calc_pressure_pairs = calc_pressure_pairs;
window.calc_pzone = calc_pzone;
window.calc_settling = calc_settling;
window.calc_settling_control = calc_settling_control;
window.calc_temp_diff = calc_temp_diff;
window.calc_text = calc_text;
window.calc_wind_uniformity = calc_wind_uniformity;
window.cleanClassOrDefault = cleanClassOrDefault;
window.collectData = collectData;
window.compareDraftPriority = compareDraftPriority;
window.delHepaObj = delHepaObj;
window.doSave = doSave;
window.doTaskAction = doTaskAction;
window.ensureEditingRecordId = ensureEditingRecordId;
window.exportRecordExcel = exportRecordExcel;
window.fillRoomParams = fillRoomParams;
window.fuzzyKeywordsMatch = fuzzyKeywordsMatch;
window.getDisplayRangeText = getDisplayRangeText;
window.getDraftTypeMeta = getDraftTypeMeta;
window.getParamRange = getParamRange;
window.getPassBoxResultState = getPassBoxResultState;
window.getQueueStatusMeta = getQueueStatusMeta;
window.getRestoreFlow = getRestoreFlow;
window.getRoomDetType = getRoomDetType;
window.getRoomLevels = getRoomLevels;
window.getRoomVolume = getRoomVolume;
window.getSyncEndpoint = getSyncEndpoint;
window.getSyncSuccessText = getSyncSuccessText;
window.handleAdminEntry = handleAdminEntry;
window.handleManualRangeChange = handleManualRangeChange;
window.handleRoomDimensionChange = handleRoomDimensionChange;
window.hasAnimalReverseAnomaly = hasAnimalReverseAnomaly;
window.hasCleanFunctionReverseAnomaly = hasCleanFunctionReverseAnomaly;
window.hasMeaningfulEditingContent = hasMeaningfulEditingContent;
window.hasOperatingReverseAnomaly = hasOperatingReverseAnomaly;
window.hideExportLoading = hideExportLoading;
window.initCardCollapse = initCardCollapse;
window.isAnimalAcceptanceState = isAnimalAcceptanceState;
window.isAnimalBarrierContextIncomplete = isAnimalBarrierContextIncomplete;
window.isAnimalChainClosed = isAnimalChainClosed;
window.isAnimalReadyMissing = isAnimalReadyMissing;
window.isCleanFunctionAcceptanceState = isCleanFunctionAcceptanceState;
window.isCleanFunctionChainClosed = isCleanFunctionChainClosed;
window.isCleanFunctionReadyMissing = isCleanFunctionReadyMissing;
window.isDraftRecord = isDraftRecord;
window.isGeneratedRecordData = isGeneratedRecordData;
window.isOperatingAcceptanceState = isOperatingAcceptanceState;
window.isOperatingChainClosed = isOperatingChainClosed;
window.isOperatingContextIncomplete = isOperatingContextIncomplete;
window.isOperatingReadyMissing = isOperatingReadyMissing;
window.isReportRecord = isReportRecord;
window.isRoomParamRestoreReady = isRoomParamRestoreReady;
window.judgeRange = judgeRange;
window.loadHistory = loadHistory;
window.loadMyTasks = loadMyTasks;
window.moveJudgementPriority = moveJudgementPriority;
window.normalizeEditableRecordData = normalizeEditableRecordData;
window.normalizeEditableRoomParams = normalizeEditableRoomParams;
window.normalizeFoodGradeValue = normalizeFoodGradeValue;
window.normalizeLocalTaskRecord = normalizeLocalTaskRecord;
window.normalizeOperatingAuxCleanClassValue = normalizeOperatingAuxCleanClassValue;
window.normalizeOperatingAuxRoomValue = normalizeOperatingAuxRoomValue;
window.normalizeOperatingRoomTypeValue = normalizeOperatingRoomTypeValue;
window.normalizeQueueError = normalizeQueueError;
window.openDB = openDB;
window.openFeishuFile = openFeishuFile;
window.openFileWithWPS = openFileWithWPS;
window.prefillFromTask = prefillFromTask;
window.previewFile = previewFile;
window.removePressurePair = removePressurePair;
window.renderAirchange = renderAirchange;
window.renderAirchangeSpeedOnly = renderAirchangeSpeedOnly;
window.renderBacteriaControl = renderBacteriaControl;
window.renderBacteriaZone = renderBacteriaZone;
window.renderBacteriaZoneControl = renderBacteriaZoneControl;
window.renderDomainGrid = renderDomainGrid;
window.renderDraftRecords = renderDraftRecords;
window.renderFloating = renderFloating;
window.renderFloatingControl = renderFloatingControl;
window.renderHepaLeakMulti = renderHepaLeakMulti;
window.renderHistoryRecords = renderHistoryRecords;
window.renderIllumUniformity = renderIllumUniformity;
window.renderInput = renderInput;
window.renderMyTasks = renderMyTasks;
window.renderNoiseCorrected = renderNoiseCorrected;
window.renderNumeric = renderNumeric;
window.renderNumericRangeManual = renderNumericRangeManual;
window.renderParams = renderParams;
window.renderParamsForRoom = renderParamsForRoom;
window.renderParticle4 = renderParticle4;
window.renderParticle4_051 = renderParticle4_051;
window.renderParticle4_8 = renderParticle4_8;
window.renderParticleZone = renderParticleZone;
window.renderPassBoxVolume = renderPassBoxVolume;
window.renderPassFail = renderPassFail;
window.renderPressureBSL = renderPressureBSL;
window.renderPressurePairRow = renderPressurePairRow;
window.renderRoomBasis = renderRoomBasis;
window.renderRoomJudgementForType = renderRoomJudgementForType;
window.renderRoomJudgementList = renderRoomJudgementList;
window.renderSettling = renderSettling;
window.renderSettlingControl = renderSettlingControl;
window.renderTempDiff = renderTempDiff;
window.renderText = renderText;
window.renderWindUniformity = renderWindUniformity;
window.resetForm = resetForm;
window.restoreNestedRoomContext = restoreNestedRoomContext;
window.restoreRoomDatasets = restoreRoomDatasets;
window.restoreRoomExpandedStates = restoreRoomExpandedStates;
window.saveDraft = saveDraft;
window.selBSL = selBSL;
window.selBarrierAuxRoom = selBarrierAuxRoom;
window.selBarrierRoomClass = selBarrierRoomClass;
window.selCleanClass = selCleanClass;
window.selCleanFunctionSubroom = selCleanFunctionSubroom;
window.selEquipmentAlias = selEquipmentAlias;
window.selPassFail = selPassFail;
window.selRoomType = selRoomType;
window.selSurgeryAuxCleanClass = selSurgeryAuxCleanClass;
window.selSurgeryAuxRoom = selSurgeryAuxRoom;
window.selSurgeryRoomType = selSurgeryRoomType;
window.selectDomain = selectDomain;
window.setActiveJudgement = setActiveJudgement;
window.setRes = setRes;
window.showResetDialog = showResetDialog;
window.showReturnToEditDialog = showReturnToEditDialog;
window.showTab = showTab;
window.showToast = showToast;
window.submitAndExport = submitAndExport;
window.submitAndGenerate = submitAndGenerate;
window.submitRecord = submitRecord;
window.switchMethod = switchMethod;
window.switchPressurePairType = switchPressurePairType;
window.switchPressureType = switchPressureType;
window.switchRoomStar = switchRoomStar;
window.syncAnimalContextMarker = syncAnimalContextMarker;
window.syncAnimalRoomContextSummary = syncAnimalRoomContextSummary;
window.syncElectronicsManualState = syncElectronicsManualState;
window.syncPassBoxResultState = syncPassBoxResultState;
window.syncPressurePairSummaryState = syncPressurePairSummaryState;
window.toggleCard = toggleCard;
window.toggleRoom = toggleRoom;
window.toggleRoomBasis = toggleRoomBasis;
window.toggleRoomJudgement = toggleRoomJudgement;
window.toggleRoomJudgementCode = toggleRoomJudgementCode;
window.updateAllRoomsRanges = updateAllRoomsRanges;
window.updateBSLPressureRange = updateBSLPressureRange;
window.updateCardSummary = updateCardSummary;
window.updateManualNumericRange = updateManualNumericRange;
window.updateOnlineStatus = updateOnlineStatus;
window.updateProjectInfoSummary = updateProjectInfoSummary;
window.updateReportNumber = updateReportNumber;
window.updateRoomBasisSummary = updateRoomBasisSummary;
window.updateRoomJudgementSummary = updateRoomJudgementSummary;
window.updateRoomRanges = updateRoomRanges;
window.updateRoomRangesByPriority = updateRoomRangesByPriority;
window.updateRoomSummary = updateRoomSummary;
window.validate = validate;
window.waitForRoomRestore = waitForRoomRestore;
