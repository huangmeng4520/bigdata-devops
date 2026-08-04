-- ============================================================
-- 清理环境策略及 CD 配置导出功能相关菜单、按钮权限及数据表
--
-- 说明：
--   环境策略功能已废弃，审批统一由审批规则（ApprovalRule）引擎决定。
--   CD 配置导出（CDConfigExport）模型已在 migration 0019 中删除，
--   此脚本补充清理数据库中残留的菜单、按钮权限及环境策略数据表。
--
-- 执行顺序：角色权限关联 -> 菜单 -> 菜单元数据 -> 数据表
-- ============================================================

-- 1. 删除环境策略按钮权限的角色关联（release:environment_strategy:*）
DELETE FROM `system_role_permission`
WHERE `menu_id` IN (
    SELECT `id` FROM `system_menu`
    WHERE `auth_code` LIKE 'release:environment_strategy:%'
       OR `auth_code` LIKE 'release:environment-strategy:%'
);

-- 2. 删除环境策略按钮权限菜单
DELETE FROM `system_menu`
WHERE `auth_code` LIKE 'release:environment_strategy:%'
   OR `auth_code` LIKE 'release:environment-strategy:%';

-- 3. 删除环境策略导航菜单（name=ReleaseEnvironmentStrategy, path=/release/environment-strategy）
DELETE FROM `system_role_permission`
WHERE `menu_id` IN (
    SELECT `id` FROM `system_menu`
    WHERE `name` = 'ReleaseEnvironmentStrategy' AND `path` = '/release/environment-strategy'
);

DELETE FROM `system_menu`
WHERE `name` = 'ReleaseEnvironmentStrategy' AND `path` = '/release/environment-strategy';

-- 4. 清理可能残留的菜单元数据（标题为环境策略相关）
DELETE FROM `system_menu_meta`
WHERE `title` IN ('环境策略', '新增环境策略', '编辑环境策略', '删除环境策略')
  AND `id` NOT IN (SELECT `meta_id` FROM `system_menu` WHERE `meta_id` IS NOT NULL);

-- 5. 删除环境策略数据表（由 migration 0026_remove_environment_strategy 触发，此处作为兜底）
DROP TABLE IF EXISTS `release_environment_strategy`;

-- 6. 删除 CD 配置导出数据表（模型已在 migration 0019 删除，此处作为兜底）
DROP TABLE IF EXISTS `release_cd_config_export`;
