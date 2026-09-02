-- 创建导出记录索引表
-- 用途：加速记录管理页面查询，建立项目与导出记录的关联

CREATE TABLE IF NOT EXISTS export_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    export_id TEXT UNIQUE NOT NULL,           -- X1EXPORT_20260827123355
    project_id INTEGER,                       -- 关联business_projects.id
    project_name TEXT NOT NULL,
    report_number TEXT DEFAULT '',
    client_name TEXT DEFAULT '',
    inspection_area TEXT DEFAULT '',          -- 受检区域（单房间）
    operator TEXT DEFAULT '',                 -- 检测员
    detection_date TEXT DEFAULT '',
    detection_state TEXT DEFAULT '',          -- 空态/静态/动态
    domain TEXT DEFAULT '',                   -- 领域
    room_name TEXT DEFAULT '',                -- 房间名称
    room_count INTEGER DEFAULT 1,             -- 该导出包含的房间数（通常为1）
    
    -- 文件路径
    json_path TEXT DEFAULT '',                -- JSON元数据文件
    xlsx_path TEXT DEFAULT '',                -- 原始记录Excel
    docx_path TEXT DEFAULT '',                -- 检测报告Word
    pdf_path TEXT DEFAULT '',                 -- PDF预览
    
    -- 状态标记
    template_ready BOOLEAN DEFAULT 0,         -- 模板是否命中
    report_success BOOLEAN DEFAULT 0,         -- 检测报告是否成功
    raw_record_success BOOLEAN DEFAULT 0,     -- 原始记录是否成功
    overall_status TEXT DEFAULT 'pending',    -- success/partial_success/failed
    
    -- 飞书上传状态
    feishu_report_url TEXT DEFAULT '',
    feishu_export_url TEXT DEFAULT '',
    feishu_report_status TEXT DEFAULT '',     -- success/failed/pending
    feishu_export_status TEXT DEFAULT '',
    
    -- 作废标记
    voided BOOLEAN DEFAULT 0,
    voided_at TEXT DEFAULT '',
    voided_by TEXT DEFAULT '',
    void_reason TEXT DEFAULT '',
    
    -- 时间戳
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    FOREIGN KEY (project_id) REFERENCES business_projects(id) ON DELETE SET NULL
);

-- 索引：加速常用查询
CREATE INDEX IF NOT EXISTS idx_export_records_project_id ON export_records(project_id);
CREATE INDEX IF NOT EXISTS idx_export_records_project_name ON export_records(project_name);
CREATE INDEX IF NOT EXISTS idx_export_records_report_number ON export_records(report_number);
CREATE INDEX IF NOT EXISTS idx_export_records_client_name ON export_records(client_name);
CREATE INDEX IF NOT EXISTS idx_export_records_operator ON export_records(operator);
CREATE INDEX IF NOT EXISTS idx_export_records_detection_date ON export_records(detection_date);
CREATE INDEX IF NOT EXISTS idx_export_records_created_at ON export_records(created_at);
CREATE INDEX IF NOT EXISTS idx_export_records_voided ON export_records(voided);

-- 复合索引：项目+报告编号（分组查询）
CREATE INDEX IF NOT EXISTS idx_export_records_project_report ON export_records(project_name, report_number);
