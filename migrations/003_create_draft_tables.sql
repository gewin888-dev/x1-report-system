-- 创建草稿导出状态跟踪表
-- 用途：记录草稿中每个房间的导出状态，支持多房间项目的增量导出

CREATE TABLE IF NOT EXISTS draft_export_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id TEXT NOT NULL,                   -- 草稿ID
    room_index INTEGER NOT NULL,              -- 房间索引（从0开始）
    room_name TEXT DEFAULT '',                -- 房间名称
    export_id TEXT DEFAULT '',                -- 导出ID（已导出时填写）
    exported BOOLEAN DEFAULT 0,               -- 是否已导出
    exported_at TEXT DEFAULT '',              -- 导出时间
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    UNIQUE(draft_id, room_index)              -- 同一草稿的同一房间只能有一条记录
);

-- 创建草稿元数据表
-- 用途：草稿的基本信息和统计数据入库，提升查询性能

CREATE TABLE IF NOT EXISTS draft_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id TEXT UNIQUE NOT NULL,            -- 草稿ID
    draft_kind TEXT DEFAULT 'manual',         -- manual/auto/boundary等
    project_id INTEGER,                       -- 关联business_projects.id
    project_name TEXT NOT NULL,
    report_number TEXT DEFAULT '',
    client_name TEXT DEFAULT '',
    operator TEXT DEFAULT '',                 -- 检测员
    detection_date TEXT DEFAULT '',
    domain TEXT DEFAULT '',                   -- 领域
    
    -- 房间统计
    room_count INTEGER DEFAULT 0,             -- 总房间数
    exported_room_count INTEGER DEFAULT 0,    -- 已导出房间数
    
    -- 文件路径
    json_path TEXT NOT NULL,                  -- 草稿JSON文件路径
    
    -- 状态标记
    all_exported BOOLEAN DEFAULT 0,           -- 是否全部房间已导出
    is_valid BOOLEAN DEFAULT 1,               -- 是否有效（内容不为空）
    
    -- 时间戳
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    file_mtime REAL NOT NULL,                 -- 文件修改时间戳（用于7天过滤）
    
    FOREIGN KEY (project_id) REFERENCES business_projects(id) ON DELETE SET NULL
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_draft_tracking_draft_id ON draft_export_tracking(draft_id);
CREATE INDEX IF NOT EXISTS idx_draft_tracking_exported ON draft_export_tracking(exported);

CREATE INDEX IF NOT EXISTS idx_draft_records_draft_kind ON draft_records(draft_kind);
CREATE INDEX IF NOT EXISTS idx_draft_records_operator ON draft_records(operator);
CREATE INDEX IF NOT EXISTS idx_draft_records_all_exported ON draft_records(all_exported);
CREATE INDEX IF NOT EXISTS idx_draft_records_file_mtime ON draft_records(file_mtime);
CREATE INDEX IF NOT EXISTS idx_draft_records_project_name ON draft_records(project_name);
