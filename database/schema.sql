-- =====================================================
-- Video-to-Action MySQL Database Schema
-- Optimized for performance and scalability
-- =====================================================

-- Set character set and collation
ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =====================================================
-- 1. Videos Table (视频表)
-- =====================================================
CREATE TABLE IF NOT EXISTS videos (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(500) NOT NULL COMMENT '视频URL',
    url_hash CHAR(64) GENERATED ALWAYS AS (SHA2(url, 256)) STORED UNIQUE COMMENT 'URL哈希(用于唯一性)',
    platform ENUM('douyin', 'bilibili', 'youtube', 'unknown') NOT NULL DEFAULT 'unknown' COMMENT '平台',
    video_id VARCHAR(255) COMMENT '平台视频ID',
    title VARCHAR(500) COMMENT '视频标题',
    author_name VARCHAR(255) COMMENT '作者名称',
    author_id VARCHAR(255) COMMENT '作者ID',
    duration INT UNSIGNED COMMENT '视频时长(秒)',
    theme VARCHAR(200) COMMENT '主题标签',
    summary TEXT COMMENT '视频摘要',
    transcription_text LONGTEXT COMMENT '转录文本',
    analysis_result JSON COMMENT '分析结果(JSON)',
    file_path VARCHAR(500) COMMENT '本地文件路径',
    file_size BIGINT UNSIGNED COMMENT '文件大小(字节)',
    status ENUM('pending', 'downloading', 'downloaded', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '错误信息',
    view_count INT UNSIGNED DEFAULT 0 COMMENT '播放次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    downloaded_at DATETIME COMMENT '下载时间',
    
    INDEX idx_platform (platform),
    INDEX idx_video_id (video_id),
    INDEX idx_author_id (author_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_theme (theme(50)),
    FULLTEXT INDEX ft_title (title),
    FULLTEXT INDEX ft_transcription (transcription_text(1000))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频表';

-- =====================================================
-- 2. Tools Table (工具表)
-- =====================================================
CREATE TABLE IF NOT EXISTS tools (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL COMMENT '工具名称',
    name_normalized VARCHAR(255) GENERATED ALWAYS AS (LOWER(name)) STORED UNIQUE COMMENT '标准化名称(唯一)',
    category VARCHAR(100) COMMENT '工具类别',
    purpose TEXT COMMENT '用途说明',
    description TEXT COMMENT '详细描述',
    install_commands JSON COMMENT '安装命令(JSON数组)',
    config_steps JSON COMMENT '配置步骤(JSON数组)',
    usage_examples JSON COMMENT '使用示例(JSON数组)',
    warnings TEXT COMMENT '注意事项',
    alternatives JSON COMMENT '替代方案(JSON数组)',
    homepage_url VARCHAR(500) COMMENT '官网地址',
    documentation_url VARCHAR(500) COMMENT '文档地址',
    is_paid BOOLEAN DEFAULT FALSE COMMENT '是否付费',
    needs_credential BOOLEAN DEFAULT FALSE COMMENT '是否需要凭证',
    license_type VARCHAR(100) COMMENT '许可证类型',
    programming_language VARCHAR(100) COMMENT '编程语言',
    github_url VARCHAR(500) COMMENT 'GitHub地址',
    version VARCHAR(100) COMMENT '版本',
    tags JSON COMMENT '标签(JSON数组)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_category (category),
    INDEX idx_is_paid (is_paid),
    FULLTEXT INDEX ft_name (name),
    FULLTEXT INDEX ft_purpose (purpose(500))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工具表';

-- =====================================================
-- 3. Video-Tools Relationship Table (视频-工具关联表)
-- =====================================================
CREATE TABLE IF NOT EXISTS video_tools (
    video_id INT UNSIGNED NOT NULL,
    tool_id INT UNSIGNED NOT NULL,
    relevance_score DECIMAL(3,2) DEFAULT 0.50 COMMENT '相关性评分(0-1)',
    mention_count INT UNSIGNED DEFAULT 1 COMMENT '提及次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    PRIMARY KEY (video_id, tool_id),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
    
    INDEX idx_tool_id (tool_id),
    INDEX idx_relevance (relevance_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频-工具关联表';

-- =====================================================
-- 4. Download Jobs Table (下载任务表)
-- =====================================================
CREATE TABLE IF NOT EXISTS download_jobs (
    job_id VARCHAR(64) PRIMARY KEY COMMENT '任务ID',
    url TEXT NOT NULL COMMENT '下载URL',
    url_type VARCHAR(50) COMMENT 'URL类型',
    status ENUM('pending', 'running', 'success', 'failed', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    created_at DATETIME NOT NULL COMMENT '创建时间',
    started_at DATETIME COMMENT '开始时间',
    finished_at DATETIME COMMENT '完成时间',
    total_count INT UNSIGNED DEFAULT 0 COMMENT '总数',
    success_count INT UNSIGNED DEFAULT 0 COMMENT '成功数',
    failed_count INT UNSIGNED DEFAULT 0 COMMENT '失败数',
    skipped_count INT UNSIGNED DEFAULT 0 COMMENT '跳过数',
    error_message TEXT COMMENT '错误信息',
    author_nickname VARCHAR(255) COMMENT '作者昵称',
    author_sec_uid VARCHAR(255) COMMENT '作者安全UID',
    retry_count INT UNSIGNED DEFAULT 0 COMMENT '重试次数',
    last_retry_at DATETIME COMMENT '最后重试时间',
    last_retry_summary JSON COMMENT '最后重试摘要',
    retry_history JSON COMMENT '重试历史',
    overrides JSON COMMENT '覆盖配置',
    
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_author_sec_uid (author_sec_uid(50))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载任务表';

-- =====================================================
-- 5. Downloaded Videos Table (已下载视频表)
-- =====================================================
CREATE TABLE IF NOT EXISTS downloaded_videos (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    aweme_id VARCHAR(255) NOT NULL COMMENT '视频ID',
    aweme_id_hash CHAR(64) GENERATED ALWAYS AS (SHA2(aweme_id, 256)) STORED UNIQUE COMMENT '视频ID哈希',
    aweme_type VARCHAR(50) NOT NULL COMMENT '视频类型',
    title VARCHAR(500) COMMENT '标题',
    author_id VARCHAR(255) COMMENT '作者ID',
    author_name VARCHAR(255) COMMENT '作者名称',
    author_sec_uid VARCHAR(255) COMMENT '作者安全UID',
    create_time DATETIME COMMENT '视频创建时间',
    download_time DATETIME NOT NULL COMMENT '下载时间',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_size BIGINT UNSIGNED COMMENT '文件大小',
    metadata JSON COMMENT '元数据',
    
    INDEX idx_aweme_id (aweme_id),
    INDEX idx_author_id (author_id),
    INDEX idx_author_sec_uid (author_sec_uid(50)),
    INDEX idx_download_time (download_time),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='已下载视频表';

-- =====================================================
-- 6. Transcript Jobs Table (转录任务表)
-- =====================================================
CREATE TABLE IF NOT EXISTS transcript_jobs (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    aweme_id VARCHAR(255) NOT NULL COMMENT '视频ID',
    video_path VARCHAR(500) NOT NULL COMMENT '视频路径',
    transcript_dir VARCHAR(500) COMMENT '转录目录',
    text_path VARCHAR(500) COMMENT '文本文件路径',
    json_path VARCHAR(500) COMMENT 'JSON文件路径',
    model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o-mini-transcribe' COMMENT '转录模型',
    status ENUM('pending', 'processing', 'completed', 'failed', 'skipped') NOT NULL COMMENT '状态',
    skip_reason TEXT COMMENT '跳过原因',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME NOT NULL COMMENT '创建时间',
    updated_at DATETIME NOT NULL COMMENT '更新时间',
    
    UNIQUE KEY uk_aweme_video_model (aweme_id, video_path(255), model),
    INDEX idx_aweme_id (aweme_id),
    INDEX idx_status (status),
    INDEX idx_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='转录任务表';

-- =====================================================
-- 7. Download History Table (下载历史表)
-- =====================================================
CREATE TABLE IF NOT EXISTS download_history (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    url TEXT NOT NULL COMMENT '下载URL',
    url_type VARCHAR(50) NOT NULL COMMENT 'URL类型',
    download_time DATETIME NOT NULL COMMENT '下载时间',
    total_count INT UNSIGNED COMMENT '总数',
    success_count INT UNSIGNED COMMENT '成功数',
    config JSON COMMENT '配置信息',
    
    INDEX idx_download_time (download_time),
    INDEX idx_url_type (url_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载历史表';

-- =====================================================
-- 8. Search History Table (搜索历史表)
-- =====================================================
CREATE TABLE IF NOT EXISTS search_history (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) COMMENT '用户ID',
    query TEXT NOT NULL COMMENT '搜索查询',
    search_type ENUM('video', 'tool', 'all') DEFAULT 'all' COMMENT '搜索类型',
    result_count INT UNSIGNED DEFAULT 0 COMMENT '结果数量',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_search_type (search_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索历史表';

-- =====================================================
-- 9. User Preferences Table (用户偏好表)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL COMMENT '用户ID',
    user_id_hash CHAR(64) GENERATED ALWAYS AS (SHA2(user_id, 256)) STORED UNIQUE COMMENT '用户ID哈希',
    preferred_platforms JSON COMMENT '偏好平台(JSON数组)',
    preferred_categories JSON COMMENT '偏好类别(JSON数组)',
    language VARCHAR(10) DEFAULT 'zh-CN' COMMENT '语言',
    theme VARCHAR(20) DEFAULT 'dark' COMMENT '主题',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户偏好表';

-- =====================================================
-- 10. System Config Table (系统配置表)
-- =====================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(255) PRIMARY KEY COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type ENUM('string', 'integer', 'float', 'boolean', 'json') DEFAULT 'string' COMMENT '配置类型',
    description TEXT COMMENT '描述',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- =====================================================
-- Initial Data (初始数据)
-- =====================================================

INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('db_version', '1.0.0', 'string', '数据库版本'),
('max_concurrent_downloads', '3', 'integer', '最大并发下载数'),
('max_concurrent_transcripts', '2', 'integer', '最大并发转录数'),
('default_platform', 'douyin', 'string', '默认平台'),
('enable_notifications', 'true', 'boolean', '启用通知'),
('storage_path', './data/videos', 'string', '存储路径')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);

-- =====================================================
-- Views (视图)
-- =====================================================

DROP VIEW IF EXISTS v_video_stats;
CREATE VIEW v_video_stats AS
SELECT 
    platform,
    COUNT(*) as total_videos,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_videos,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_videos,
    AVG(file_size) as avg_file_size,
    SUM(file_size) as total_storage
FROM videos
GROUP BY platform;

DROP VIEW IF EXISTS v_tool_stats;
CREATE VIEW v_tool_stats AS
SELECT 
    t.id,
    t.name,
    t.category,
    COUNT(vt.video_id) as referenced_count,
    AVG(vt.relevance_score) as avg_relevance
FROM tools t
LEFT JOIN video_tools vt ON t.id = vt.tool_id
GROUP BY t.id, t.name, t.category;

-- =====================================================
-- Analyze tables for query optimization
-- =====================================================

ANALYZE TABLE videos;
ANALYZE TABLE tools;
ANALYZE TABLE video_tools;
ANALYZE TABLE download_jobs;
ANALYZE TABLE downloaded_videos;
ANALYZE TABLE transcript_jobs;

-- =====================================================
-- End of Schema
-- =====================================================
