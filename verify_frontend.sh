#!/bin/bash

echo "=== 验证前端代码 ==="

# 检查关键文件是否存在
echo "1. 检查文件..."
files=(
  "web/apps/web-antd/src/views/release/pipelineTemplate/index.vue"
  "web/apps/web-antd/src/views/release/pipelineTemplate/modules/versions.vue"
  "web/apps/web-antd/src/api/release/pipelineTemplate.ts"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "✓ $file 存在"
  else
    echo "✗ $file 不存在"
  fi
done

# 检查关键代码
echo ""
echo "2. 检查关键代码..."

echo "检查 index.vue 中的操作按钮..."
if grep -q "code: 'copy'" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue; then
  echo "✓ 复制按钮已添加"
else
  echo "✗ 复制按钮未找到"
fi

if grep -q "code: 'export'" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue; then
  echo "✓ 导出按钮已添加"
else
  echo "✗ 导出按钮未找到"
fi

if grep -q "onImport" web/apps/web-antd/src/views/release/pipelineTemplate/index.vue; then
  echo "✓ 导入功能已添加"
else
  echo "✗ 导入功能未找到"
fi

echo ""
echo "检查 versions.vue 中的操作按钮..."
if grep -q "handleAutoVersion" web/apps/web-antd/src/views/release/pipelineTemplate/modules/versions.vue; then
  echo "✓ 自动迭代功能已添加"
else
  echo "✗ 自动迭代功能未找到"
fi

if grep -q "handleEditStage" web/apps/web-antd/src/views/release/pipelineTemplate/modules/versions.vue; then
  echo "✓ 编辑阶段功能已添加"
else
  echo "✗ 编辑阶段功能未找到"
fi

echo ""
echo "3. 重启前端服务..."
echo "请执行以下命令："
echo "  cd web"
echo "  npm run dev:antd"
echo ""
echo "4. 清除浏览器缓存并刷新页面"
