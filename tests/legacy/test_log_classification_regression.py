#!/usr/bin/env python3
"""操作日志分类筛选与摘要卡防回退。"""
from pathlib import Path


def main():
    app = Path('app_x1.py').read_text(encoding='utf-8')
    html = Path('templates/admin.html').read_text(encoding='utf-8')

    # 后端：分类口径与联动数据源必须存在
    assert 'LOG_ACTION_CATEGORY_MAP = {' in app, '缺少操作日志分类映射表'
    assert 'LOG_ACTION_CATEGORIES = [' in app, '缺少操作日志分类清单'
    assert 'def get_log_action_category(action: str) -> str:' in app, '缺少操作日志分类函数'
    assert "category_filter = (request.args.get('category') or '').strip()" in app, '日志接口缺少分类筛选参数'
    assert "row['category'] = get_log_action_category(row.get('action'))" in app, '日志行未注入分类字段'
    assert "category_action_map = {cat: [] for cat in LOG_ACTION_CATEGORIES}" in app, '缺少分类到具体操作映射'
    assert "'category_action_map': category_action_map" in app, '日志接口未返回分类动作联动数据'
    assert "category_summary = [{'category': cat, 'count': category_counter.get(cat, 0)} for cat in LOG_ACTION_CATEGORIES]" in app, '分类摘要未固定返回 0 值项'

    # 前端：三层筛选与联动渲染必须存在
    assert '用户筛选' in html, '日志页缺少用户筛选'
    assert '操作分类' in html, '日志页缺少操作分类'
    assert '具体操作' in html, '日志页缺少具体操作'
    assert 'function onLogCategoryChange()' in html, '缺少分类切换联动函数'
    assert 'function rebuildLogActionOptions(keepValue)' in html, '缺少具体操作重建函数'
    assert "window.currentLogCategoryActionMap=d.category_action_map||{};" in html, '前端未接收分类动作映射'
    assert "rebuildLogActionOptions(currentAction);" in html, '日志加载后未重建具体操作下拉'
    assert "onchange=\"onLogCategoryChange()\"" in html, '操作分类下拉未绑定联动事件'

    # 摘要卡：固定展示全部分类并保留总数卡
    assert "var wantedCategories=['认证与会话','报告记录治理','操作日志治理','系统设置与运维','权限与用户管理','模板注册与模板治理','标准库/文档/查看类','其他/未分类'];" in html, '摘要卡未固定完整分类集合'
    assert '操作日志总数' in html, '摘要卡缺少日志总数'
    assert 'grid-template-columns:repeat(9,minmax(0,1fr));' in html, '摘要卡未固定一行展示'

    print('PASS test_log_classification_regression')


if __name__ == '__main__':
    main()
