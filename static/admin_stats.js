(function(){
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]); }); }
  function domainName(k){ try { return (window.DOMAIN_MAP && window.DOMAIN_MAP[k]) || k || '未知'; } catch(e){ return k || '未知'; } }
  var currentTrendMode = 'month';
  var currentDomainMode = 'month';
  var lastData = null;

  function topList(title, icon, items, key, domainMode){
    var rows = (items||[]).map(function(item, idx){
      var label = domainMode ? domainName(item[key]) : item[key];
      return '<div class="adv-top-item">'
        + '<div class="adv-top-left"><span class="adv-rank">TOP '+(idx+1)+'</span><span class="adv-name">'+esc(label||'-')+'</span></div>'
        + '<span class="adv-count">'+Number(item.count||0)+'</span>'
        + '</div>';
    }).join('') || '<div class="empty">暂无数据</div>';
    return '<div class="card adv-card adv-panel">'
      + '<div class="adv-section-head"><div><div class="adv-eyebrow">TOP 榜单</div><h4>'+icon+' '+title+'</h4></div></div>'
      + '<div class="adv-top-list">'+rows+'</div></div>';
  }

  function getTrendEntries(data){
    var src = currentTrendMode === 'week' ? (data.by_week||{}) : currentTrendMode === 'year' ? (data.by_year||{}) : (data.by_month||{});
    var keys = Object.keys(src).sort();
    if(currentTrendMode === 'month') keys = keys.slice(-12);
    if(currentTrendMode === 'week') keys = keys.slice(-12);
    if(currentTrendMode === 'year') keys = keys.slice(-8);
    return keys.map(function(k){ return {label:k, value:Number(src[k]||0)}; });
  }

  function getDomainSeries(data){
    var src = currentDomainMode === 'week' ? (data.by_domain_week||{}) : currentDomainMode === 'year' ? (data.by_domain_year||{}) : (data.by_domain_month||{});
    var keys = Object.keys(src).sort();
    if(currentDomainMode === 'month') keys = keys.slice(-6);
    if(currentDomainMode === 'week') keys = keys.slice(-8);
    if(currentDomainMode === 'year') keys = keys.slice(-6);
    var sliced = {};
    keys.forEach(function(k){ sliced[k] = src[k] || {}; });
    return sliced;
  }

  function shortLabel(label, mode){
    label = String(label||'');
    if(mode === 'month') return label.slice(2);
    if(mode === 'week') return label.replace(/^\d{4}-/, '');
    return label;
  }

  function trendTabs(){
    return '<div class="adv-tabs">'
      + '<button class="adv-tab'+(currentTrendMode==='week'?' active':'')+'" onclick="window.__setStatsTrendMode(\'week\')">周</button>'
      + '<button class="adv-tab'+(currentTrendMode==='month'?' active':'')+'" onclick="window.__setStatsTrendMode(\'month\')">月</button>'
      + '<button class="adv-tab'+(currentTrendMode==='year'?' active':'')+'" onclick="window.__setStatsTrendMode(\'year\')">年</button>'
      + '</div>';
  }

  function domainTabs(){
    return '<div class="adv-tabs">'
      + '<button class="adv-tab'+(currentDomainMode==='week'?' active':'')+'" onclick="window.__setStatsDomainMode(\'week\')">周</button>'
      + '<button class="adv-tab'+(currentDomainMode==='month'?' active':'')+'" onclick="window.__setStatsDomainMode(\'month\')">月</button>'
      + '<button class="adv-tab'+(currentDomainMode==='year'?' active':'')+'" onclick="window.__setStatsDomainMode(\'year\')">年</button>'
      + '</div>';
  }

  function lineChart(data){
    var entries = getTrendEntries(data);
    var modeLabel = currentTrendMode === 'week' ? '按周' : currentTrendMode === 'year' ? '按年' : '按月';
    if(!entries.length) return '<div class="card adv-card adv-panel"><div class="adv-card-head"><div><div class="adv-eyebrow">趋势观察</div><h4>📈 导出趋势</h4></div>'+trendTabs()+'</div><div class="empty">暂无数据</div></div>';
    var w=640,h=260,p=36,max=1;
    entries.forEach(function(x){ if(x.value>max) max=x.value; });
    var step = entries.length>1 ? (w-p*2)/(entries.length-1) : 0;
    var pts = entries.map(function(it,i){ var x=p+i*step, y=h-p-((h-p*2)*it.value/max); return {x:x,y:y,label:it.label,value:it.value}; });
    var poly = pts.map(function(pt){ return pt.x+','+pt.y; }).join(' ');
    var area = pts.map(function(pt,idx){ return (idx===0 ? 'M' : 'L') + pt.x + ' ' + pt.y; }).join(' ') + ' L ' + pts[pts.length-1].x + ' ' + (h-p) + ' L ' + pts[0].x + ' ' + (h-p) + ' Z';
    var labels = pts.map(function(pt){ return '<text x="'+pt.x+'" y="'+(h-10)+'" font-size="11" text-anchor="middle" fill="#667085">'+esc(shortLabel(pt.label, currentTrendMode))+'</text>'; }).join('');
    var dots = pts.map(function(pt){ return '<circle cx="'+pt.x+'" cy="'+pt.y+'" r="4.5" fill="#1677ff" stroke="#ffffff" stroke-width="2"></circle><text x="'+pt.x+'" y="'+(pt.y-12)+'" font-size="11" text-anchor="middle" fill="#1677ff">'+pt.value+'</text>'; }).join('');
    var grid = [0,0.25,0.5,0.75,1].map(function(r){ var y=h-p-((h-p*2)*r), v=Math.round(max*r); return '<line x1="'+p+'" y1="'+y+'" x2="'+(w-p)+'" y2="'+y+'" stroke="#edf2f7"></line><text x="'+(p-8)+'" y="'+(y+4)+'" font-size="11" text-anchor="end" fill="#98a2b3">'+v+'</text>'; }).join('');
    return '<div class="card adv-card adv-panel">'
      + '<div class="adv-card-head"><div><div class="adv-eyebrow">趋势观察</div><h4>📈 导出趋势（'+modeLabel+'）</h4></div>'+trendTabs()+'</div>'
      + '<div class="adv-chart adv-chart-blue"><svg viewBox="0 0 '+w+' '+h+'">'
      + '<defs><linearGradient id="advAreaBlue" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1677ff" stop-opacity="0.22"></stop><stop offset="100%" stop-color="#1677ff" stop-opacity="0.02"></stop></linearGradient></defs>'
      + grid + '<path d="'+area+'" fill="url(#advAreaBlue)"></path><polyline fill="none" stroke="#1677ff" stroke-width="3" points="'+poly+'"></polyline>'+dots+labels+'</svg></div></div>';
  }

  function barChart(data){
    var byDomainTime = getDomainSeries(data);
    var modeLabel = currentDomainMode === 'week' ? '周' : currentDomainMode === 'year' ? '年' : '月';
    var points = Object.keys(byDomainTime||{}).sort();
    if(!points.length) return '<div class="card adv-card adv-panel"><div class="adv-card-head"><div><div class="adv-eyebrow">结构分布</div><h4>📊 领域 × 时间分布</h4></div>'+domainTabs()+'</div><div class="empty">暂无数据</div></div>';
    var domains=[]; points.forEach(function(m){ Object.keys(byDomainTime[m]||{}).forEach(function(d){ if(domains.indexOf(d)<0) domains.push(d); }); });
    domains = domains.slice(0,5);
    var colors=['#1677ff','#52c41a','#faad14','#eb2f96','#722ed1'];
    var w=640,h=260,p=36,groupW=(w-p*2)/points.length,max=1;
    points.forEach(function(m){ domains.forEach(function(d){ var v=Number((byDomainTime[m]||{})[d]||0); if(v>max) max=v; }); });
    var barW=Math.max(12, Math.min(26, groupW/Math.max(domains.length,1)-6));
    var grid=[0,0.25,0.5,0.75,1].map(function(r){ var y=h-p-((h-p*2)*r), v=Math.round(max*r); return '<line x1="'+p+'" y1="'+y+'" x2="'+(w-p)+'" y2="'+y+'" stroke="#edf2f7"></line><text x="'+(p-8)+'" y="'+(y+4)+'" font-size="11" text-anchor="end" fill="#98a2b3">'+v+'</text>'; }).join('');
    var bars='';
    points.forEach(function(m,mi){
      var gx=p+mi*groupW;
      bars += '<text x="'+(gx+groupW/2)+'" y="'+(h-10)+'" font-size="11" text-anchor="middle" fill="#667085">'+esc(shortLabel(m, currentDomainMode))+'</text>';
      domains.forEach(function(d,di){
        var v=Number((byDomainTime[m]||{})[d]||0), bh=(h-p*2)*v/max, x=gx+8+di*(barW+6), y=h-p-bh;
        bars += '<rect x="'+x+'" y="'+y+'" width="'+barW+'" height="'+bh+'" rx="5" fill="'+colors[di%colors.length]+'"></rect>';
      });
    });
    var legend = '<div class="adv-legend">'+domains.map(function(d,i){ return '<span><i style="background:'+colors[i%colors.length]+'"></i>'+esc(domainName(d))+'</span>'; }).join('')+'</div>';
    return '<div class="card adv-card adv-panel">'
      + '<div class="adv-card-head"><div><div class="adv-eyebrow">结构分布</div><h4>📊 领域 × 时间分布（按'+modeLabel+'）</h4></div>'+domainTabs()+'</div>'
      + '<div class="adv-chart adv-chart-soft"><svg viewBox="0 0 '+w+' '+h+'">'+grid+bars+'</svg></div>'+legend+'</div>';
  }

  function summary(summary){
    summary = summary || {};
    var leadDomain = summary.lead_domain ? domainName(summary.lead_domain.domain) : '-';
    var delta = Number(summary.month_delta||0);
    var deltaText = delta>0 ? ('+'+delta) : String(delta);
    var deltaTone = delta>0 ? 'up' : (delta<0 ? 'down' : 'flat');
    var items = [
      ['峰值月份', (summary.peak_month&&summary.peak_month.label)||'-', '数量：'+((summary.peak_month&&summary.peak_month.count)||0), 'primary'],
      ['最近月份', (summary.latest_month&&summary.latest_month.label)||'-', '数量：'+((summary.latest_month&&summary.latest_month.count)||0), 'green'],
      ['环比变化', deltaText, '对比上月导出数量', deltaTone],
      ['主领域', leadDomain, '数量：'+((summary.lead_domain&&summary.lead_domain.count)||0), 'purple']
    ];
    return '<div class="adv-hero">'
      + '<div class="adv-hero-main"><div class="adv-hero-kicker">管理驾驶舱</div><div class="adv-hero-title">正式导出统计总览</div><div class="adv-hero-desc">折线图与柱状图都支持按周 / 月 / 年切换查看，当前统计口径以后台统计接口实时汇总结果为准。</div></div>'
      + '<div class="adv-summary-grid">'
      + items.map(function(it){ return '<div class="adv-summary-item tone-'+it[3]+'"><div class="adv-summary-label">'+it[0]+'</div><div class="adv-summary-value">'+esc(it[1])+'</div><div class="adv-summary-sub">'+esc(it[2])+'</div></div>'; }).join('')
      + '</div></div>';
  }

  function notes(statsNotes){
    var lines = [statsNotes&&statsNotes.exports_scope, statsNotes&&statsNotes.domain_scope, statsNotes&&statsNotes.trend_scope, statsNotes&&statsNotes.top_scope].filter(Boolean);
    return '<div class="card adv-card adv-panel adv-notes-panel"><div class="adv-section-head"><div><div class="adv-eyebrow">统计说明</div><h4>🧭 统计口径说明</h4></div></div><ul class="adv-notes">'+lines.map(function(x){ return '<li>'+esc(x)+'</li>'; }).join('')+'</ul></div>';
  }

  function style(){
    if(document.getElementById('adv-stats-style')) return;
    var css = ''
      + '#stats-advanced-mount{margin-top:4px}'
      + '.adv-hero{margin-top:2px;margin-bottom:16px;padding:20px 20px 18px;border:1px solid #dbe7ff;border-radius:18px;background:linear-gradient(135deg,#f5f9ff 0%,#ffffff 46%,#f8fbff 100%);box-shadow:0 12px 30px rgba(22,119,255,.08)}'
      + '.adv-hero-main{margin-bottom:16px}'
      + '.adv-hero-kicker,.adv-eyebrow{font-size:12px;font-weight:700;letter-spacing:.08em;color:#1677ff;text-transform:uppercase}'
      + '.adv-hero-title{font-size:24px;font-weight:800;color:#101828;margin-top:6px}'
      + '.adv-hero-desc{font-size:13px;line-height:1.8;color:#475467;margin-top:8px}'
      + '.adv-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px}'
      + '.adv-grid-4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-top:16px}'
      + '.adv-card{margin-bottom:0}'
      + '.adv-panel{border:1px solid #eaf0f7;border-radius:16px;box-shadow:0 8px 24px rgba(15,23,42,.05);overflow:hidden}'
      + '.adv-card-head,.adv-section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}'
      + '.adv-card-head h4,.adv-section-head h4{margin:4px 0 0 0;font-size:17px;color:#101828}'
      + '.adv-chart{border:1px solid #edf2f7;border-radius:14px;padding:12px;overflow:hidden;background:#fff}'
      + '.adv-chart-blue{background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%)}'
      + '.adv-chart-soft{background:linear-gradient(180deg,#fcfdff 0%,#ffffff 100%)}'
      + '.adv-legend{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;font-size:12px;color:#667085}'
      + '.adv-legend span{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:#f8fafc;border:1px solid #edf2f7}'
      + '.adv-legend i{display:inline-block;width:10px;height:10px;border-radius:999px}'
      + '.adv-top-list{display:flex;flex-direction:column;gap:10px}'
      + '.adv-top-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;border:1px solid #edf2f7;border-radius:12px;background:linear-gradient(180deg,#ffffff 0%,#f9fbff 100%)}'
      + '.adv-top-left{display:flex;align-items:center;gap:10px;min-width:0;flex:1}'
      + '.adv-rank{display:inline-flex;align-items:center;justify-content:center;min-width:52px;height:28px;border-radius:999px;background:#eaf2ff;color:#1677ff;font-weight:700;font-size:12px}'
      + '.adv-name{flex:1;min-width:0;color:#344054;font-weight:600}'
      + '.adv-count{font-weight:800;color:#111827;font-size:18px}'
      + '.adv-summary-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}'
      + '.adv-summary-item{border:1px solid #eaf0f7;border-radius:14px;padding:14px 14px 12px;background:#fff;box-shadow:0 4px 12px rgba(15,23,42,.03)}'
      + '.adv-summary-item.tone-primary{background:linear-gradient(180deg,#ffffff 0%,#f5f9ff 100%)}'
      + '.adv-summary-item.tone-green{background:linear-gradient(180deg,#ffffff 0%,#f6ffed 100%)}'
      + '.adv-summary-item.tone-purple{background:linear-gradient(180deg,#ffffff 0%,#f9f5ff 100%)}'
      + '.adv-summary-item.tone-up{background:linear-gradient(180deg,#ffffff 0%,#f6ffed 100%)}'
      + '.adv-summary-item.tone-down{background:linear-gradient(180deg,#ffffff 0%,#fff2f0 100%)}'
      + '.adv-summary-item.tone-flat{background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%)}'
      + '.adv-summary-label{font-size:12px;color:#667085;margin-bottom:8px}'
      + '.adv-summary-value{font-size:22px;font-weight:800;color:#101828}'
      + '.adv-summary-sub{font-size:12px;color:#98a2b3;margin-top:6px;line-height:1.6}'
      + '.adv-notes-panel{margin-top:16px}'
      + '.adv-notes{margin:0;padding-left:18px;color:#555;line-height:1.85;font-size:13px}'
      + '.adv-notes li+li{margin-top:6px}'
      + '.adv-tabs{display:flex;gap:8px;flex-wrap:wrap}'
      + '.adv-tab{border:1px solid #d0d5dd;background:#fff;color:#344054;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:600;cursor:pointer;transition:all .2s}'
      + '.adv-tab:hover{border-color:#91caff;color:#1677ff}'
      + '.adv-tab.active{background:linear-gradient(135deg,#1677ff 0%,#4096ff 100%);color:#fff;border-color:#1677ff;box-shadow:0 6px 14px rgba(22,119,255,.18)}'
      + '@media (max-width:1200px){.adv-grid-4{grid-template-columns:repeat(2,minmax(0,1fr))}.adv-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}'
      + '@media (max-width:960px){.adv-grid,.adv-grid-4,.adv-summary-grid{grid-template-columns:1fr}.adv-card-head,.adv-section-head{flex-direction:column;align-items:flex-start}.adv-hero-title{font-size:20px}}';
    var st = document.createElement('style'); st.id='adv-stats-style'; st.textContent = css; document.head.appendChild(st);
  }

  function render(data){
    lastData = data;
    var mount = document.getElementById('stats-advanced-mount');
    if(!mount) return;
    style();
    mount.innerHTML = summary(data.summary||{})
      + '<div class="adv-grid">' + lineChart(data) + barChart(data) + '</div>'
      + '<div class="adv-grid adv-grid-4">'
      + topList('检测员 TOP 5', '👨‍🔬', data.top_operators||[], 'name')
      + topList('领域 TOP 5', '🏷', data.top_domains||[], 'domain', true)
      + topList('月度 TOP 5', '🗓', data.top_months||[], 'name')
      + topList('客户 TOP 5（委托单位）', '🏢', data.top_clients||[], 'name')
      + '</div>'
      + notes(data.stats_notes||{});
  }

  window.__renderAdvancedStats = render;
  window.__setStatsTrendMode = function(mode){ currentTrendMode = mode; if(lastData) render(lastData); };
  window.__setStatsDomainMode = function(mode){ currentDomainMode = mode; if(lastData) render(lastData); };

  function boot(){
    var mount = document.getElementById('stats-advanced-mount');
    if(!mount) return;
    fetch('/admin/api/stats').then(function(r){ return r.json(); }).then(function(d){ render(d||{}); }).catch(function(err){ console.error('advanced stats render failed:', err); });
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
