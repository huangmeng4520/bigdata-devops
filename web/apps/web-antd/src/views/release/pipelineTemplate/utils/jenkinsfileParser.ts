/**
 * Jenkinsfile 解析工具
 * 用于解析和更新 Jenkinsfile 中的 stage 内容
 */

export interface Stage {
  name: string;
  startIndex: number;
  endIndex: number;
  content: string;
}

/**
 * 从 Jenkinsfile 内容中解析 stages
 */
export function parseStages(jenkinsfileContent: string): Stage[] {
  if (!jenkinsfileContent) return [];

  const stages: Stage[] = [];
  const lines = jenkinsfileContent.split('\n');

  let inStages = false;
  let braceCount = 0;
  let currentStage: { name: string; startLine: number; contentLines: string[] } | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();

    // 检测进入 stages 区域
    if (trimmedLine === 'stages {' || trimmedLine.startsWith('stages {')) {
      inStages = true;
      braceCount = 1;
      continue;
    }

    if (!inStages) continue;

    // 计算大括号
    const openBraces = (line.match(/{/g) || []).length;
    const closeBraces = (line.match(/}/g) || []).length;

    // 检测 stage 开始
    const stageMatch = trimmedLine.match(/^stage\(['"](.+?)['"]\)\s*{/);
    if (stageMatch && braceCount === 1) {
      currentStage = {
        name: stageMatch[1],
        startLine: i,
        contentLines: [line],
      };
      braceCount += openBraces - closeBraces;
      continue;
    }

    // 收集 stage 内容
    if (currentStage) {
      currentStage.contentLines.push(line);
      braceCount += openBraces - closeBraces;

      // stage 结束（braceCount 回到 1 表示 stages 层级）
      if (braceCount === 1) {
        stages.push({
          name: currentStage.name,
          startIndex: currentStage.startLine,
          endIndex: i,
          content: currentStage.contentLines.join('\n'),
        });
        currentStage = null;
      }
      continue;
    }

    braceCount += openBraces - closeBraces;
  }

  return stages;
}

/**
 * 从 stage 内容中提取 steps 部分的脚本
 */
export function extractStageScript(stageContent: string): string {
  const lines = stageContent.split('\n');
  const scriptLines: string[] = [];
  let inSteps = false;
  let braceCount = 0;

  for (const line of lines) {
    const trimmedLine = line.trim();

    if (trimmedLine === 'steps {' || trimmedLine.startsWith('steps {')) {
      inSteps = true;
      braceCount = 1;
      continue;
    }

    if (!inSteps) continue;

    const openBraces = (line.match(/{/g) || []).length;
    const closeBraces = (line.match(/}/g) || []).length;

    braceCount += openBraces - closeBraces;

    if (braceCount === 0) {
      break;
    }

    // 去掉前导空格（保留相对缩进）
    scriptLines.push(line);
  }

  // 统一去除前导空格
  return normalizeIndentation(scriptLines.join('\n'));
}

/**
 * 更新 stage 中的 steps 内容
 */
export function updateStageSteps(
  jenkinsfileContent: string,
  stageName: string,
  newStepsScript: string
): string {
  const stages = parseStages(jenkinsfileContent);
  const targetStage = stages.find((s) => s.name === stageName);

  if (!targetStage) {
    throw new Error(`Stage "${stageName}" not found`);
  }

  const lines = jenkinsfileContent.split('\n');
  const stageStartLine = targetStage.startIndex;
  const stageEndLine = targetStage.endIndex;

  // 在 stage 内容中找到 steps 区域
  let stepsStartLine = -1;
  let stepsEndLine = -1;
  let inSteps = false;
  let braceCount = 0;

  for (let i = stageStartLine; i <= stageEndLine; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();

    if (trimmedLine === 'steps {' || trimmedLine.startsWith('steps {')) {
      stepsStartLine = i;
      inSteps = true;
      braceCount = 1;
      continue;
    }

    if (inSteps) {
      const openBraces = (line.match(/{/g) || []).length;
      const closeBraces = (line.match(/}/g) || []).length;
      braceCount += openBraces - closeBraces;

      if (braceCount === 0) {
        stepsEndLine = i;
        break;
      }
    }
  }

  if (stepsStartLine === -1 || stepsEndLine === -1) {
    throw new Error(`Steps section not found in stage "${stageName}"`);
  }

  // 计算 steps 的缩进
  const stepsLine = lines[stepsStartLine];
  const stepsIndent = stepsLine.match(/^(\s*)/)?.[1] || '';
  const contentIndent = stepsIndent + '    ';

  // 构建新的 steps 内容
  const formattedScript = newStepsScript
    .split('\n')
    .map((line) => (line.trim() ? contentIndent + line : ''))
    .join('\n');

  const newStepsContent = `${stepsIndent}steps {\n${formattedScript}\n${stepsIndent}}`;

  // 替换原来的 steps 区域
  const beforeSteps = lines.slice(0, stepsStartLine).join('\n');
  const afterSteps = lines.slice(stepsEndLine + 1).join('\n');

  return beforeSteps + newStepsContent + afterSteps;
}

/**
 * 获取所有 stage 名称列表
 */
export function getStageNames(jenkinsfileContent: string): string[] {
  return parseStages(jenkinsfileContent).map((s) => s.name);
}

/**
 * 统一缩进
 */
function normalizeIndentation(content: string): string {
  const lines = content.split('\n');

  // 找到最小缩进
  let minIndent = Infinity;
  for (const line of lines) {
    if (line.trim()) {
      const indent = line.match(/^(\s*)/)?.[1].length || 0;
      minIndent = Math.min(minIndent, indent);
    }
  }

  if (minIndent === Infinity) return content;

  // 去除最小缩进
  return lines
    .map((line) => (line.trim() ? line.substring(minIndent) : line))
    .join('\n');
}

/**
 * 验证 Jenkinsfile 格式
 */
export function validateJenkinsfile(content: string): { valid: boolean; error?: string } {
  if (!content.trim()) {
    return { valid: false, error: 'Jenkinsfile 内容不能为空' };
  }

  if (!content.includes('pipeline {')) {
    return { valid: false, error: '无效的 Jenkinsfile 格式：缺少 pipeline 定义' };
  }

  if (!content.includes('stages {')) {
    return { valid: false, error: '无效的 Jenkinsfile 格式：缺少 stages 定义' };
  }

  // 检查大括号匹配
  let braceCount = 0;
  for (const char of content) {
    if (char === '{') braceCount++;
    if (char === '}') braceCount--;
    if (braceCount < 0) {
      return { valid: false, error: '大括号不匹配' };
    }
  }

  if (braceCount !== 0) {
    return { valid: false, error: '大括号不匹配' };
  }

  return { valid: true };
}
