from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
from xml.sax.saxutils import escape

OBJECT_TITLE_MAP = {
    'pass_box': 'X1 样板报告 - 传递窗',
    'laminar_hood': 'X1 样板报告 - 层流罩',
    'operating_room': 'X1 样板报告 - 手术室',
    'clean_function_room': 'X1 样板报告 - 洁净功能用房',
    'bsl': 'X1 样板报告 - 生物安全实验室',
    'bsc': 'X1 样板报告 - 生物安全柜',
    'clean_bench': 'X1 样板报告 - 洁净工作台',
    'ivc': 'X1 样板报告 - IVC笼具',
}

OBJECT_NOTE_MAP = {
    'pass_box': '本文件为 X1 独立空间生成的传递窗样板报告，用于验证 canonical model → export payload → docx 输出链。',
    'laminar_hood': '本文件为 X1 独立空间生成的层流罩样板报告，用于验证 canonical model → export payload → docx 输出链。',
    'operating_room': '本文件为 X1 独立空间生成的手术室样板报告，用于验证 canonical model → export payload → docx 输出链。',
    'clean_function_room': '本文件为 X1 独立空间生成的洁净功能用房样板报告，用于验证子房间语义、等级语义与报告上下文链。',
    'bsl': '本文件为 X1 独立空间生成的生物安全实验室样板报告，用于验证 BSL 等级、洁净等级与报告上下文链。',
    'bsc': '本文件为 X1 独立空间生成的生物安全柜样板报告，用于验证设备类对象 canonical model → export payload → docx 输出链。',
    'clean_bench': '本文件为 X1 独立空间生成的洁净工作台样板报告，用于验证设备类对象 canonical model → export payload → docx 输出链。',
    'ivc': '本文件为 X1 独立空间生成的 IVC 笼具样板报告，用于验证设备类对象 canonical model → export payload → docx 输出链。',
}


def build_simple_docx(report_title: str, paragraphs: list[str], output_path: str):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    def para_xml(text: str) -> str:
        return f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

    body = ''.join(para_xml(p) for p in paragraphs)

    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:w10="urn:schemas-microsoft-com:office:word"
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
 xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
 xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
 xmlns:wne="http://schemas.microsoft.com/office/2006/wordml"
 xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
 mc:Ignorable="w14 wp14">
 <w:body>
 {para_xml(report_title)}
 {body}
 <w:sectPr>
   <w:pgSz w:w="11906" w:h="16838"/>
   <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
 </w:sectPr>
 </w:body>
</w:document>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'''

    with ZipFile(output, 'w', ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('word/document.xml', document_xml)
        zf.writestr('word/_rels/document.xml.rels', doc_rels)

    return str(output)


def build_object_report(export_payload: dict, output_path: str):
    project = export_payload.get('project', {})
    room = export_payload.get('room', {})
    summary = room.get('summary', {})
    type_id = room.get('type_id', '')
    type_name = room.get('type_name', '') or '检测对象'
    business_context = room.get('business_context', {}) or {}

    paragraphs = [
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"项目名称：{project.get('project_name', '')}",
        f"报告编号：{project.get('report_number', '')}",
        f"委托单位：{project.get('client_name', '')}",
        f"联系人：{project.get('contact_info', '')}",
        f"项目地址：{project.get('project_address', '')}",
        f"检测区域：{project.get('inspection_area', '')}",
        f"检测日期：{project.get('detection_date', '')}",
        f"检测领域：{project.get('domain_name', '')}",
        f"对象名称：{room.get('room_name', '')}",
        f"检测对象：{type_name}",
        f"对象类型ID：{type_id}",
        f"洁净等级：{room.get('clean_class', '') or room.get('level_name', '')}",
        f"检测依据：{', '.join(room.get('basis', []) or [])}",
        f"判定标准：{', '.join(room.get('judgement', []) or [])}",
        f"结果状态：{summary.get('result_state', '')}",
        f"主判定：{summary.get('judgement_primary', '')}",
        f"模板资源：{(export_payload.get('template_resource', {}) or {}).get('template_name', '')}",
        f"模板路径：{(export_payload.get('template_resource', {}) or {}).get('template_path', '')}",
        f"模板命中：{(export_payload.get('template_resource', {}) or {}).get('template_found', False)}",
        f"资源状态：{(export_payload.get('template_resource', {}) or {}).get('resource_status', '')}",
        f"资源说明：{(export_payload.get('template_resource', {}) or {}).get('resource_note', '')}",
    ]

    if type_id == 'operating_room':
        paragraphs.extend([
            '',
            '【手术室业务上下文】',
            f"房型分支：{business_context.get('room_branch', '')}",
            f"分支模式：{business_context.get('branch_mode', '')}",
            f"辅房名称：{business_context.get('aux_room_name', '')}",
            f"辅房等级：{business_context.get('aux_clean_class', '')}",
            f"参数策略：{business_context.get('parameter_strategy', '')}",
            f"上下文模式：{business_context.get('context_mode', '')}",
        ])
    elif type_id == 'clean_function_room':
        template_rule = export_payload.get('template_rule', {}) or {}
        semantics = export_payload.get('clean_class_semantics', {}) or {}
        paragraphs.extend([
            '',
            '【洁净功能用房业务上下文】',
            f"子房间：{business_context.get('clean_function_subroom', '')}",
            f"上下文模式：{business_context.get('clean_function_context_mode', '')}",
            f"模板键：{template_rule.get('template_key', '')}",
            f"模板名：{template_rule.get('template_name', '')}",
            f"等级语义：{semantics.get('level_semantic_key', '')}",
            f"语义说明：{semantics.get('semantic_note', '')}",
        ])
    elif type_id == 'bsl':
        template_rule = export_payload.get('template_rule', {}) or {}
        semantics = export_payload.get('clean_class_semantics', {}) or {}
        paragraphs.extend([
            '',
            '【生物安全业务上下文】',
            f"生物安全等级：{business_context.get('bsl_level', '')}",
            f"上下文模式：{business_context.get('biosafety_context_mode', '')}",
            f"模板键：{template_rule.get('template_key', '')}",
            f"模板名：{template_rule.get('template_name', '')}",
            f"等级语义：{semantics.get('level_semantic_key', '')}",
            f"语义说明：{semantics.get('semantic_note', '')}",
        ])

    paragraphs.extend([
        '',
        OBJECT_NOTE_MAP.get(type_id, '本文件为 X1 独立空间生成的对象样板报告，用于验证 canonical model → export payload → docx 输出链。'),
    ])
    title = OBJECT_TITLE_MAP.get(type_id, f"X1 样板报告 - {type_name}")
    return build_simple_docx(title, paragraphs, output_path)


def build_canonical_object_report(export_payload: dict, output_path: str):
    return build_object_report(export_payload, output_path)


def build_passbox_report(export_payload: dict, output_path: str):
    return build_canonical_object_report(export_payload, output_path)
