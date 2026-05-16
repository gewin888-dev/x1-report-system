(function(){
  var DOC_META={
    VERSION_NOTE:{title:'系统当前版本说明',meta:'当前版本定位、能力范围、对象覆盖、已知边界'},
    VERSION_RULES:{title:'版本号管理规则',meta:'统一版本号格式、升级条件、同步位置与备份留档口径'},
    ARCHITECTURE:{title:'系统架构说明',meta:'整体架构、核心模块、业务主链、运行边界'},
    API:{title:'系统接口说明',meta:'接口分组、接口职责、权限边界（126个路由）'},
    MAIN_CHAIN_DESIGN:{title:'架构重构计划',meta:'分阶段架构健康度提升路线图'},
    CODE_STATS:{title:'全量代码审计报告',meta:'安全、质量、性能、数据库全维度审计（73.8/100）'},
    OPS_FAQ:{title:'常见问题排障手册',meta:'启动失败、端口占用、模板缺失、飞书上传失败等常见问题'},
    OPS_DAEMON:{title:'运维启动-停止-验活说明',meta:'守护进程启停、PID 管理、端口检查、健康体检'},
    OPS_DEPLOY:{title:'部署与迁移说明',meta:'macOS 部署、路径迁移、配置更新、备份还原'},
    OPS_FEISHU_SOP:{title:'飞书上传失败治理 SOP',meta:'飞书上传失败的排查流程、Token 刷新、重试机制'}
  };

  var WORKSPACE_DOC_MAP={
    VERSION_NOTE:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_系统当前版本说明.md',
    VERSION_RULES:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_版本号管理规则.md',
    ARCHITECTURE:'/Users/fuwuqi/检测报告生成系统_X1/docs/ARCHITECTURE.md',
    API:'/Users/fuwuqi/检测报告生成系统_X1/docs/API.md',
    MAIN_CHAIN_DESIGN:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_架构重构计划_2026-05-16.md',
    CODE_STATS:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_全量代码审计报告_2026-05-16_v2.md',
    OPS_FAQ:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 常见问题排障手册.md',
    OPS_DAEMON:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 运维启动-停止-验活说明.md',
    OPS_DEPLOY:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 部署与迁移说明.md',
    OPS_FEISHU_SOP:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 飞书上传失败治理 SOP.md'
  };

  function setActiveDocButton(docKey){
    document.querySelectorAll('.docs-nav-btn').forEach(function(btn){
      btn.classList.toggle('active', btn.getAttribute('data-doc-btn')===docKey);
    });
  }

  function setDocHeader(docKey){
    var meta = DOC_META[docKey] || {title:docKey,meta:''};
    var titleEl = document.getElementById('doc-view-title');
    var metaEl = document.getElementById('doc-view-meta');
    if(titleEl) titleEl.textContent = meta.title;
    if(metaEl) metaEl.textContent = meta.meta || '';
  }

  function getDocContentEl(){ return document.getElementById('doc-content'); }

  window.loadWorkspaceDoc = function(docKey){
    setActiveDocButton(docKey);
    setDocHeader(docKey);
    var content = getDocContentEl();
    if(!content) return;
    content.style.whiteSpace='pre-wrap';
    content.style.fontFamily='ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
    content.textContent='正在加载...';
    var path = WORKSPACE_DOC_MAP[docKey];
    if(!path){
      content.textContent='未找到文档: '+docKey;
      return;
    }
    fetch('/admin/api/workspace_doc?path='+encodeURIComponent(path)).then(function(r){return r.json();}).then(function(d){
      if(d.error){ content.textContent='错误: '+d.error; return; }
      content.textContent = d.content || '文档为空';
    }).catch(function(e){
      content.textContent='加载失败: '+e.message;
    });
  };

  window.loadDoc = function(docName, event){
    // 统一走 workspace doc 加载
    window.loadWorkspaceDoc(docName);
  };

  window.initDocsPanel = function(){
    if(window._docsInited) return;
    window._docsInited = true;
    // 默认加载第一份：系统当前版本说明
    window.loadWorkspaceDoc('VERSION_NOTE');
  };

  document.addEventListener('click', function(e){
    var nav = e.target.closest('.nav-item');
    if(nav && nav.textContent.indexOf('系统文档') !== -1){
      setTimeout(function(){ if(window.initDocsPanel) window.initDocsPanel(); }, 0);
    }
  });
})();
