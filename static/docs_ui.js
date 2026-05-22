(function(){
  var DOC_META={
    VERSION_NOTE:{title:'系统当前版本说明',meta:'当前部署形态、运行事实、任务口径与维护边界'},
    ARCHITECTURE:{title:'系统架构说明',meta:'当前系统结构、双库分层、关键模块与主业务链'},
    API:{title:'系统接口说明',meta:'当前常用接口、权限口径与主链接口参考'},
    TASK_RULES:{title:'任务链规则文档',meta:'员工端动作、任务状态映射、项目阶段推进与禁止场景'},
    PERMISSION_MODEL:{title:'权限系统说明',meta:'role_permission_final 真相来源、旧表定位与读写边界'},
    OPS_FAQ:{title:'常见问题排障手册',meta:'启动失败、双库、脚本入口、权限与任务口径等常见问题'},
    OPS_DAEMON:{title:'运维启动-停止-验活说明',meta:'标准启停脚本、健康检查、日志与自动备份说明'},
    OPS_DEPLOY:{title:'部署与迁移说明',meta:'双库迁移、目录迁移、最小业务验证与迁移边界'}
  };

  var WORKSPACE_DOC_MAP={
    VERSION_NOTE:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_系统当前版本说明.md',
    ARCHITECTURE:'/Users/fuwuqi/检测报告生成系统_X1/docs/ARCHITECTURE.md',
    API:'/Users/fuwuqi/检测报告生成系统_X1/docs/API.md',
    TASK_RULES:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_任务链规则文档_v1.md',
    PERMISSION_MODEL:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1_权限系统新模型说明_v2.md',
    OPS_FAQ:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 常见问题排障手册.md',
    OPS_DAEMON:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 运维启动-停止-验活说明.md',
    OPS_DEPLOY:'/Users/fuwuqi/检测报告生成系统_X1/docs/X1 部署与迁移说明.md'
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
