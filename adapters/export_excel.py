from pathlib import Path
from datetime import datetime
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

THIN = Side(style='thin', color='000000')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill('solid', fgColor='D9EAF7')
SECTION_FILL = PatternFill('solid', fgColor='FFF2CC')
SUB_FILL = PatternFill('solid', fgColor='F2F2F2')


def _font(bold=False, size=11):
    return Font(name='Arial Unicode MS', size=size, bold=bold)


def _cell(ws, row, col, value='', *, bold=False, fill=None, align='center', size=11):
    c = ws.cell(row, col, value)
    c.font = _font(bold, size)
    c.alignment = Alignment(horizontal=align, vertical='center', wrap_text=True)
    c.border = BORDER
    if fill:
        c.fill = fill
    return c


def _apply_box_border(ws, r1, c1, r2, c2, fill=None):
    for row in range(r1, r2 + 1):
        for col in range(c1, c2 + 1):
            cell = ws.cell(row, col)
            left = THIN if col == c1 else cell.border.left
            right = THIN if col == c2 else cell.border.right
            top = THIN if row == r1 else cell.border.top
            bottom = THIN if row == r2 else cell.border.bottom
            cell.border = Border(left=left, right=right, top=top, bottom=bottom)
            if fill:
                cell.fill = fill
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)


def _merge(ws, r1, c1, r2, c2, value='', **kwargs):
    ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
    _apply_box_border(ws, r1, c1, r2, c2, kwargs.get('fill'))
    return _cell(ws, r1, c1, value, **kwargs)


def _clean_text(v):
    return str(v or '').replace('✅', '').replace('❌', '').replace('⚠️', '').strip()


def _judge_from_result(v):
    txt = str(v or '')
    return '不合格' if ('❌' in txt or '⚠' in txt) else '合格'


def _normalize_param_item(item):
    if isinstance(item, dict):
        if 'value' in item and 'values' not in item:
            value = item.get('value')
            item = {**item, 'values': [] if value in (None, '') else [value]}
        if 'result' not in item:
            vals = item.get('values')
            if isinstance(vals, list) and vals:
                item = {**item, 'result': vals[0]}
        return item
    if item in (None, ''):
        return {}
    return {'values': [item], 'result': item}


def _get_param(room, *keys):
    params = room.get('params', {}) or {}
    alias_map = {
        'settling': ('settling', 'settle_bacteria'),
        'floating': ('floating', 'floating_bacteria', 'particle'),
        'self_purification_time': ('self_purification_time', 'self_purify_time'),
        'illumination': ('illumination', 'illumination_main_room'),
    }
    search_keys = []
    for key in keys:
        aliases = alias_map.get(key, (key,))
        for a in aliases:
            if a not in search_keys:
                search_keys.append(a)

    if isinstance(params, dict):
        for key in search_keys:
            if key in params:
                return _normalize_param_item(params[key])
    elif isinstance(params, list):
        for item in params:
            if not isinstance(item, dict):
                continue
            if item.get('key') in search_keys:
                return _normalize_param_item(item)
    return {}


def _result(room, *keys, default=''):
    p = _get_param(room, *keys)
    return _clean_text(p.get('result', default))


def _values(room, *keys):
    p = _get_param(room, *keys)
    vals = p.get('values')
    if isinstance(vals, list):
        return [str(v) for v in vals if str(v).strip()]
    if vals not in (None, ''):
        return [str(vals)]
    return []


def _data(room, *keys):
    p = _get_param(room, *keys)
    return p.get('data') or {}


def _pairs(room, *keys):
    p = _get_param(room, *keys)
    return p.get('pairs') or []


def _vents(room, *keys):
    p = _get_param(room, *keys)
    return p.get('vents') or []


def _param_standard_text(key: str) -> str:
    mapping = {
        'appearance': '应外观完好、无异常',
        'alarm_interlock': '报警和连锁功能应正常',
        'function': '功能应正常',
        'downflow_speed': '按对应标准/设计要求',
        'inflow_speed': '按对应标准/设计要求',
        'air_velocity': '按对应标准/设计要求',
        'noise': '按对应标准/设计要求',
        'illumination': '按对应标准/设计要求',
        'uv_intensity': '按对应标准/设计要求',
        'vibration': '按对应标准/设计要求',
        'pressure': '按对应标准/设计要求',
        'ammonia': '按对应标准/设计要求',
        'cage_count': '按设计配置要求',
        'model': '与设备铭牌/登记信息一致',
        'type': '与设备类型要求一致',
    }
    return mapping.get(key, '按对应标准/设计要求')


def _set_base_layout(ws):
    for col, width in {'A':18,'B':18,'C':18,'D':18,'E':18,'F':18,'G':14,'H':14}.items():
        ws.column_dimensions[col].width = width
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = 'A10'


def _write_header(ws, project, room):
    _merge(ws, 1, 1, 1, 8, '检测原始记录', bold=True, size=14, fill=HEAD_FILL)
    _cell(ws, 3, 1, '项目名称：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 3, 2, 3, 4, project.get('project_name', ''), align='left')
    _cell(ws, 3, 5, '委托单位：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 3, 6, 3, 8, project.get('client_name', ''), align='left')
    _cell(ws, 4, 1, '报告编号：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 4, 2, 4, 4, project.get('report_number', ''), align='left')
    _cell(ws, 4, 5, '检测日期：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 4, 6, 4, 8, project.get('detection_date', ''), align='left')
    _cell(ws, 5, 1, '检测区域：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 5, 2, 5, 4, project.get('inspection_area', ''), align='left')
    _cell(ws, 5, 5, '检测状态：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 5, 6, 5, 8, project.get('detection_state', '') or project.get('detection_state_text', ''), align='left')
    _cell(ws, 6, 1, '检测类型：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 6, 2, 6, 4, room.get('type_name', ''), align='left')
    _cell(ws, 6, 5, '洁净等级：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 6, 6, 6, 8, room.get('clean_class', '') or room.get('level_name', ''), align='left')
    _cell(ws, 7, 1, '检测依据：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 7, 2, 7, 8, '、'.join(room.get('basis', []) or project.get('basis', []) or []), align='left')
    _cell(ws, 8, 1, '判定标准：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 8, 2, 8, 8, '、'.join(room.get('judgement', []) or project.get('judgement', []) or []), align='left')


def _block_four_layer(ws, row, title, base_titles, base_values, standard_text, result_text, judge):
    _merge(ws, row, 1, row, 8, title, bold=True, fill=SECTION_FILL, align='left')
    _cell(ws, row+1, 1, '基础数据', bold=True, fill=SUB_FILL)
    _merge(ws, row+1, 2, row+1, 4, ' / '.join([str(x) for x in base_titles if str(x).strip()]) or '测点数据', fill=SUB_FILL, align='left')
    _merge(ws, row+2, 1, row+2, 4, ' / '.join([str(x) for x in base_values if str(x).strip()]) or '', align='left')
    _cell(ws, row+1, 5, '标准（设计）要求', bold=True, fill=SUB_FILL)
    _merge(ws, row+1, 6, row+1, 8, standard_text or '', align='left')
    _cell(ws, row+2, 5, '检测结果', bold=True, fill=HEAD_FILL)
    _merge(ws, row+2, 6, row+2, 8, result_text or '', align='left')
    _cell(ws, row+3, 1, '单项结论', bold=True, fill=HEAD_FILL)
    _merge(ws, row+3, 2, row+3, 8, judge or '', align='left')
    _apply_box_border(ws, row, 1, row+3, 8)
    return row + 5


def _block_simple(ws, row, title, sample_titles, sample_values, result_text, judge):
    _merge(ws, row, 1, row, 8, title, bold=True, fill=SECTION_FILL, align='left')
    for i in range(1, 9):
        _cell(ws, row+1, i, sample_titles[i-1] if i-1 < len(sample_titles) else '', fill=SUB_FILL)
        _cell(ws, row+2, i, sample_values[i-1] if i-1 < len(sample_values) else '')
    _cell(ws, row+3, 1, '检测结果：', bold=True, fill=HEAD_FILL, align='left')
    _merge(ws, row+3, 2, row+3, 4, result_text, align='left')
    _cell(ws, row+3, 5, '判定：', bold=True, fill=HEAD_FILL, align='left')
    _merge(ws, row+3, 6, row+3, 8, judge, align='left')
    _apply_box_border(ws, row, 1, row+3, 8)
    return row + 5


def _build_pharma_cleanroom_record(export_payload, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    project = export_payload.get('project', {}) or {}
    room = export_payload.get('room', {}) or {}
    ws.title = str(room.get('room_name') or '原始记录')[:31]
    _set_base_layout(ws)
    _write_header(ws, project, room)

    dims = []
    for k in ('length', 'width', 'height'):
        v = room.get(k, '')
        if str(v).strip(): dims.append(str(v))
    dim_text = f"    尺寸：{'m × '.join(dims)}m" if len(dims) == 3 else ''
    _merge(ws, 10, 1, 10, 8, f"房间：{room.get('room_name', '')}{dim_text}", bold=True, fill=SECTION_FILL, align='left')
    _cell(ws, 11, 1, '检测依据：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 11, 2, 11, 8, '、'.join(room.get('basis', []) or project.get('basis', []) or []), align='left')
    _cell(ws, 12, 1, '判定标准：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 12, 2, 12, 8, '、'.join(room.get('judgement', []) or project.get('judgement', []) or []), align='left')
    for r in range(3, 13):
        _apply_box_border(ws, r, 1, r, 8)

    row = 14
    vents = _vents(room, 'airchange')
    airchange_vals = _values(room, 'airchange')
    if vents:
        v = vents[0]
        area = float(v.get('area') or 0)
        speed = float(v.get('speed') or 0)
        volume = float(v.get('volume') or 0)
        length = float(room.get('length') or 0)
        width = float(room.get('width') or 0)
        height = float(room.get('height') or 0)
        room_volume = round(length * width * height, 1) if length and width and height else 0
        if not volume and area and speed:
            volume = round(area * speed * 3600, 1)
        calc = f"总风量{volume}m³/h ÷ 体积{room_volume}m³" if volume and room_volume else '换气次数计算'
        row = _block_four_layer(ws, row, '换气次数（次/h）', ['计算说明'], [calc], '按送风量/房间体积换算', _result(room, 'airchange'), _judge_from_result(_result(room, 'airchange')))
    elif airchange_vals:
        row = _block_four_layer(ws, row, '换气次数（次/h）', [f'测点{i+1}' for i in range(len(airchange_vals))], airchange_vals, '按对应标准/设计要求', _result(room, 'airchange'), _judge_from_result(_result(room, 'airchange')))

    prs = _pairs(room, 'pressure')
    pressure_vals = _values(room, 'pressure')
    if prs:
        vals = prs[0].get('values') or []
        row = _block_four_layer(ws, row, '静压差（正压） 相对房间：洁净走廊（Pa）', [f'测点{i+1}' for i in range(max(1, len(vals)))], [str(v) for v in (vals or [''])], '符合对应洁净区压差要求', _result(room, 'pressure'), _judge_from_result(_result(room, 'pressure')))
    elif pressure_vals:
        row = _block_four_layer(ws, row, '静压差（Pa）', [f'测点{i+1}' for i in range(len(pressure_vals))], pressure_vals, '符合对应洁净区压差要求', _result(room, 'pressure'), _judge_from_result(_result(room, 'pressure')))


    hepa = _get_param(room, 'hepa_leak')
    if hepa:
        hepa_vals = _values(room, 'hepa_leak') or [(_data(room, 'hepa_leak').get('total') or '')]
        row = _block_four_layer(ws, row, '高效过滤器检漏（%）', [f'测点{i+1}' for i in range(max(1, len(hepa_vals)))], hepa_vals, '≤ 0.01%（按对应标准/模板要求）', _result(room, 'hepa_leak'), _judge_from_result(_result(room, 'hepa_leak')))

    pdata = _data(room, 'particle')
    particle_vals = _values(room, 'particle')
    if pdata:
        _merge(ws, row, 1, row, 8, '洁净度级别（悬浮粒子）（粒/m³）', bold=True, fill=SECTION_FILL, align='left')
        headers = ['粒径', '最大值', 'UCL/95%置信度', '', '', '', '', '']
        row1 = ['≥0.5μm', pdata.get('p05_max', ''), pdata.get('p05_ucl', ''), '', '', '', '', '']
        row2 = ['≥5μm', pdata.get('p5_max', ''), pdata.get('p5_ucl', ''), '', '', '', '', '']
        for i,v in enumerate(headers, start=1): _cell(ws, row+1, i, v, fill=SUB_FILL)
        for i,v in enumerate(row1, start=1): _cell(ws, row+2, i, v)
        for i,v in enumerate(row2, start=1): _cell(ws, row+3, i, v)
        _cell(ws, row+4, 1, '检测结果：', bold=True, fill=HEAD_FILL, align='left')
        _merge(ws, row+4, 2, row+4, 5, _result(room, 'particle'), align='left')
        _cell(ws, row+4, 6, '判定：', bold=True, fill=HEAD_FILL, align='left')
        _merge(ws, row+4, 7, row+4, 8, _judge_from_result(_get_param(room, 'particle').get('result', '')), align='left')
        _apply_box_border(ws, row, 1, row+4, 8)
        row += 6
    elif particle_vals:
        row = _block_four_layer(ws, row, '洁净度级别（悬浮粒子）（粒/m³）', [f'测点{i+1}' for i in range(len(particle_vals))], particle_vals, '按对应洁净等级标准要求', _result(room, 'particle'), _judge_from_result(_get_param(room, 'particle').get('result', '')))

    for title, key, standard_text, unit in [
        ('温度（℃）', 'temperature', '20～24℃', '℃'),
        ('相对湿度（%）', 'humidity', '45～60%', '%'),
        ('噪声（dB(A)）', 'noise', '≤65dB(A)', 'dB(A)'),
        ('照度（lx）', 'illumination_main_room', '≥300lx', 'lx'),
        ('自净时间（min）', 'self_purification_time', '≤20min', 'min'),
    ]:
        vals = _values(room, key)
        if not vals:
            continue
        result = _result(room, key)
        if unit and result and unit not in result:
            result = f'{result} {unit}'
        row = _block_four_layer(ws, row, title, [f'测点{i+1}' for i in range(len(vals))], vals, standard_text, result, _judge_from_result(_get_param(room, key).get('result', '')))

    for title, key, label, standard_text in [('沉降菌（cfu/皿）', 'settling', '平均值', '≤1 cfu/30min·Φ90皿'), ('浮游菌（cfu/m³）', 'floating_bacteria', '平均浓度', '≤5 cfu/m³')]:
        vals = _values(room, key)
        data = _data(room, key)
        raw = vals or ([str(data.get('total'))] if data.get('total') not in (None, '') else [])
        if not raw:
            continue
        detail = _result(room, key)
        if not detail and data:
            total = data.get('total', '')
            blank = data.get('blank', '0')
            neg = data.get('neg', '0')
            detail = f'{label}:{total} | 空白对照:{blank} | 阴性对照:{neg}'
        row = _block_four_layer(ws, row, title, [f'测点{i+1}' for i in range(len(raw))], raw, standard_text, detail, _judge_from_result(_get_param(room, key).get('result', '') or detail))

    _cell(ws, row, 1, '检测员：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row, 2, row, 4, project.get('inspector', ''), align='left')
    _cell(ws, row, 5, '校核人：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row, 6, row, 8, '', align='left')
    _cell(ws, row+1, 1, '检测日期：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row+1, 2, row+1, 4, project.get('detection_date', ''), align='left')
    _cell(ws, row+1, 5, '记录日期：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row+1, 6, row+1, 8, datetime.now().strftime('%Y-%m-%d'), align='left')
    _apply_box_border(ws, row, 1, row+1, 8)

    wb.save(output)
    wb.close()
    return str(output)


def _build_hospital_record(export_payload, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    project = export_payload.get('project', {}) or {}
    room = export_payload.get('room', {}) or {}
    ws.title = str(room.get('room_name') or '原始记录')[:31]
    _set_base_layout(ws)
    _write_header(ws, project, room)

    dims = []
    for k in ('length', 'width', 'height'):
        v = room.get(k, '')
        if str(v).strip(): dims.append(str(v))
    dim_text = f"    尺寸：{'m × '.join(dims)}m" if len(dims) == 3 else ''
    _merge(ws, 10, 1, 10, 8, f"房间：{room.get('room_name', '')}{dim_text}", bold=True, fill=SECTION_FILL, align='left')
    _cell(ws, 11, 1, '检测依据：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 11, 2, 11, 8, '、'.join(room.get('basis', []) or project.get('basis', []) or []), align='left')
    _cell(ws, 12, 1, '判定标准：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, 12, 2, 12, 8, '、'.join(room.get('judgement', []) or project.get('judgement', []) or []), align='left')
    for r in range(3, 13):
        _apply_box_border(ws, r, 1, r, 8)

    row = 14
    # airchange / pressure
    vents = _vents(room, 'airchange')
    if vents:
        row = _block_four_layer(ws, row, '换气次数（次/h）', ['计算说明'], ['按送风量与房间体积换算'], '按对应标准/设计要求', _result(room, 'airchange'), _judge_from_result(_result(room, 'airchange')))
    prs = _pairs(room, 'pressure')
    if prs:
        vals = prs[0].get('values') or []
        row = _block_four_layer(ws, row, '静压差（Pa）', [f'测点{i+1}' for i in range(max(1, len(vals)))], [str(v) for v in (vals or [''])], '按对应标准/设计要求', _result(room, 'pressure'), _judge_from_result(_result(room, 'pressure')))

    for title, key, aliases, standard_text in [
        ('温度（℃）', 'temperature', ('temperature',), '20～24℃'),
        ('相对湿度（%）', 'humidity', ('humidity',), '45～60%'),
        ('噪声（dB(A)）', 'noise', ('noise',), '≤65dB(A)'),
        ('照度（lx）', 'illumination', ('illumination', 'illumination_min'), '≥300lx'),
        ('平均风速（m/s）', 'wind_speed', ('wind_speed',), '按对应标准/设计要求'),
        ('风速不均匀度', 'wind_uniformity', ('wind_uniformity',), '按对应标准/设计要求'),
        ('沉降菌（cfu/皿）', 'bacteria', ('bacteria', 'settling'), '按对应标准/设计要求'),
        ('气流流型', 'airflow_pattern', ('airflow_pattern',), '符合设计气流组织要求'),
        ('气密性', 'airtightness', ('airtightness',), '符合要求'),
    ]:
        vals = []
        result = ''
        for a in aliases:
            vals = _values(room, a)
            result = _result(room, a)
            if vals or result:
                break
        if not vals and not result:
            continue
        row = _block_four_layer(ws, row, title, [f'测点{i+1}' for i in range(max(1, len(vals)))], [str(v) for v in (vals or [''])], standard_text, result, _judge_from_result(result))

    _cell(ws, row, 1, '检测员：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row, 2, row, 4, project.get('inspector', ''), align='left')
    _cell(ws, row, 5, '校核人：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row, 6, row, 8, '', align='left')
    _cell(ws, row+1, 1, '检测日期：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row+1, 2, row+1, 4, project.get('detection_date', ''), align='left')
    _cell(ws, row+1, 5, '记录日期：', bold=True, fill=HEAD_FILL, align='left'); _merge(ws, row+1, 6, row+1, 8, datetime.now().strftime('%Y-%m-%d'), align='left')
    _apply_box_border(ws, row, 1, row+1, 8)
    wb.save(output)
    wb.close()
    return str(output)


def _build_general_cleanroom_record(export_payload, output_path):
    return _build_hospital_record(export_payload, output_path)


def _build_fallback_record(export_payload, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    project = export_payload.get('project', {}) or {}
    room = export_payload.get('room', {}) or {}
    ws.title = str(room.get('room_name') or room.get('type_name') or '原始记录')[:31]
    _set_base_layout(ws)
    _write_header(ws, project, room)
    _merge(ws, 10, 1, 10, 8, f"房间/设备：{room.get('room_name', '')}", bold=True, fill=SECTION_FILL, align='left')
    _merge(ws, 12, 1, 12, 8, '检测项目汇总', bold=True, fill=SECTION_FILL, align='left')
    row = 13
    params = room.get('params', {}) or {}
    if isinstance(params, dict):
        iterable = []
        for key, item in params.items():
            iterable.append((key, item))
    elif isinstance(params, list):
        iterable = []
        for idx, item in enumerate(params, start=1):
            if isinstance(item, dict):
                key = item.get('key') or item.get('label') or item.get('name') or f'param_{idx}'
            else:
                key = f'param_{idx}'
            iterable.append((key, item))
    else:
        iterable = []
    for key, item in iterable:
        if not isinstance(item, dict):
            item = {'result': item}
        result = _clean_text(item.get('result', ''))
        raw_values = item.get('values')
        if isinstance(raw_values, list):
            vals = raw_values
        elif raw_values is not None:
            vals = [raw_values]
        elif item.get('value') is not None:
            vals = [item.get('value')]
        else:
            vals = []
        title = str(key)
        row = _block_four_layer(
            ws,
            row,
            title,
            [f'测点{i+1}' for i in range(max(1, len(vals)))],
            [str(v) for v in (vals or [''])],
            _param_standard_text(key),
            result,
            _judge_from_result(item.get('result', ''))
        )
    wb.save(output)
    wb.close()
    return str(output)


def build_canonical_excel_report(export_payload: dict, output_path: str):
    rooms_export = export_payload.get('rooms_export') or []
    if len(rooms_export) <= 1:
        # 单房间，走原有逻辑
        return _build_single_room_excel(export_payload, output_path)

    # 多房间：每个房间一个 Sheet
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    # 删除默认 sheet
    default_ws = wb.active

    for i, room_export in enumerate(rooms_export):
        # 构建虚拟 payload
        virtual_payload = dict(export_payload)
        virtual_payload['room'] = room_export['room']
        virtual_payload['template_rule'] = room_export['template_rule']
        virtual_payload['template_resource'] = room_export['template_resource']
        virtual_payload['report_context'] = room_export['report_context']
        virtual_payload['clean_class_semantics'] = room_export['clean_class_semantics']
        virtual_payload['judgement_result'] = room_export['judgement_result']

        room_name = room_export['room'].get('room_name', '') or f'房间{i+1}'
        sheet_name = str(room_name)[:31]  # Excel sheet 名最长 31 字符

        # 先导出到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name
        _build_single_room_excel(virtual_payload, tmp_path)

        # 读取临时文件的 sheet 内容复制到主 workbook
        import shutil
        src_wb = openpyxl.load_workbook(tmp_path)
        src_ws = src_wb.active

        if i == 0:
            # 第一个房间用默认 sheet
            ws = default_ws
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(title=sheet_name)

        # 复制单元格内容和格式
        for row in src_ws.iter_rows():
            for cell in row:
                new_cell = ws.cell(row=cell.row, column=cell.column, value=cell.value)
                if cell.has_style:
                    new_cell.font = cell.font.copy()
                    new_cell.fill = cell.fill.copy()
                    new_cell.alignment = cell.alignment.copy()
                    new_cell.border = cell.border.copy()
                    new_cell.number_format = cell.number_format

        # 复制合并单元格
        for merged_range in src_ws.merged_cells.ranges:
            ws.merge_cells(str(merged_range))

        # 复制列宽
        for col_letter, col_dim in src_ws.column_dimensions.items():
            ws.column_dimensions[col_letter].width = col_dim.width

        src_wb.close()
        os.unlink(tmp_path)

    wb.save(output)
    wb.close()
    return str(output)


def _build_single_room_excel(export_payload: dict, output_path: str):
    """\u5355\u623f\u95f4\u539f\u59cb\u8bb0\u5f55\u5bfc\u51fa\uff08\u539f build_canonical_excel_report \u903b\u8f91\uff09。"""
    room = export_payload.get('room', {}) or {}
    type_id = str(room.get('type_id', '') or '')
    if type_id in {'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop'}:
        return _build_pharma_cleanroom_record(export_payload, output_path)
    if type_id in {'negative_pressure', 'operating_room', 'clean_function_room', 'bsl', 'animal_room'}:
        return _build_hospital_record(export_payload, output_path)
    if type_id in {'electronics_workshop'}:
        return _build_general_cleanroom_record(export_payload, output_path)
    return _build_fallback_record(export_payload, output_path)
