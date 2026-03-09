-- 发布管理菜单配置
-- 说明：需要在后台管理系统中手动添加，或通过以下SQL语句插入
-- 注意：执行前请先查询最大ID，确保ID不冲突：
-- SELECT MAX(id) FROM system_menu_meta;
-- SELECT MAX(id) FROM system_menu;

-- 1. 首先添加发布记录菜单元数据
INSERT INTO `system_menu_meta` (`id`, `remark`, `creator`, `modifier`, `update_time`, `create_time`, `is_deleted`, `title`, `icon`, `sort`, `affix_tab`, `badge`, `badge_type`, `badge_variants`, `iframe_src`, `link`, `hide_children_in_menu`, `hide_in_menu`) 
VALUES (300, '发布记录菜单', 'admin', 'admin', NOW(), NOW(), 0, '发布记录', 'mdi:history', 0, 0, '', '', '', '', '', 0, 0);

-- 2. 添加发布统计菜单元数据
INSERT INTO `system_menu_meta` (`id`, `remark`, `creator`, `modifier`, `update_time`, `create_time`, `is_deleted`, `title`, `icon`, `sort`, `affix_tab`, `badge`, `badge_type`, `badge_variants`, `iframe_src`, `link`, `hide_children_in_menu`, `hide_in_menu`) 
VALUES (301, '发布统计菜单', 'admin', 'admin', NOW(), NOW(), 0, '发布统计', 'mdi:chart-bar', 0, 0, '', '', '', '', '', 0, 0);

-- 3. 添加应用发布按钮权限元数据
INSERT INTO `system_menu_meta` (`id`, `remark`, `creator`, `modifier`, `update_time`, `create_time`, `is_deleted`, `title`, `icon`, `sort`, `affix_tab`, `badge`, `badge_type`, `badge_variants`, `iframe_src`, `link`, `hide_children_in_menu`, `hide_in_menu`) 
VALUES (302, '应用发布按钮', 'admin', 'admin', NOW(), NOW(), 0, '发布', '', 0, 0, '', '', '', '', '', 0, 0);

-- 4. 查找发布管理父菜单ID（需要先在系统中创建发布管理目录菜单，或使用以下SQL查找）
-- 假设发布管理父菜单ID为X，这里需要根据实际情况调整

-- 5. 添加发布记录菜单
-- 注意：pid_id 需要设置为发布管理目录菜单的ID
INSERT INTO `system_menu` (`id`, `remark`, `creator`, `modifier`, `update_time`, `create_time`, `is_deleted`, `name`, `status`, `type`, `path`, `component`, `auth_code`, `pid_id`, `meta_id`, `sort`) 
VALUES (300, '发布记录菜单', 'admin', 'admin', NOW(), NOW(), 0, 'ReleaseRecord', 1, 'menu', '/release/record', '/release/record/index', 'release:record:view', NULL, 300, 7);

-- 6. 添加发布统计菜单
INSERT INTO `system_menu` (`id`, `remark`, `creator`, `modifier`, `update_time`, `create_time`, `is_deleted`, `name`, `status`, `type`, `path`, `component`, `auth_code`, `pid_id`, `meta_id`, `sort`) 
VALUES (301, '发布统计菜单', 'admin', 'admin', NOW(), NOW(), 0, 'ReleaseStatistics', 1, 'menu', '/release/statistics', '/release/statistics/index', 'release:statistics:view', NULL, 301, 8);

-- 7. 添加应用发布按钮权限
-- 注意：pid_id 需要设置为应用管理菜单的ID，需要先查询应用管理菜单的ID
-- SELECT id, name FROM system_menu WHERE name = 'ReleaseApplication' OR path LIKE '%application%';
INSERT INTO `system_menu` (`id`, `remark`, `creator`, `modifier`, `update_time`, `create_time`, `is_deleted`, `name`, `status`, `type`, `path`, `component`, `auth_code`, `pid_id`, `meta_id`, `sort`) 
VALUES (302, '应用发布按钮', 'admin', 'admin', NOW(), NOW(), 0, 'ReleaseApplicationButton', 1, 'button', '', '', 'release:application:release', NULL, 104, 1);

-- ============================================================
-- 推荐方式：通过后台管理系统添加菜单和按钮权限
-- ============================================================
-- 
-- 在菜单管理中找到「应用管理」菜单，添加按钮权限：
-- 类型: button
-- 名称: ReleaseApplicationButton  
-- 标题: 发布
-- 权限码: release:application:release
-- 排序: 1

-- 发布记录菜单
-- 名称: ReleaseRecord
-- 标题: 发布记录
-- 图标: mdi:history
-- 路径: /release/record
-- 组件: /release/record/index
-- 权限码: release:record:view
-- 排序: 7

-- 发布统计菜单
-- 名称: ReleaseStatistics
-- 标题: 发布统计
-- 图标: mdi:chart-bar
-- 路径: /release/statistics
-- 组件: /release/statistics/index
-- 权限码: release:statistics:view
-- 排序: 8
