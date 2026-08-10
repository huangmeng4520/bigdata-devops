/**
 * Jenkinsfile 解析工具
 * 使用 Pipeline 语法分析，支持各种复杂格式
 */

export interface Stage {
  name: string;
  startIndex: number;
  endIndex: number;
  content: string;
}

/**
 * Token 类型
 */
enum TokenType {
  WORD,        // 标识符、关键字
  STRING,      // 字符串 'xxx' 或 "xxx"
  LBRACE,      // {
  RBRACE,      // }
  LPAREN,      // (
  RPAREN,      // )
  NEWLINE,     // 换行
  WHITESPACE,  // 空白
  COMMENT,     // 注释
  OTHER,       // 其他
}

interface Token {
  type: TokenType;
  value: string;
  line: number;
  col: number;
}

/**
 * 词法分析器 - 将源代码转换为 token 流
 */
function tokenize(content: string): Token[] {
  const tokens: Token[] = [];
  let line = 0;
  let col = 0;
  let i = 0;

  while (i < content.length) {
    const char = content[i];

    if (char === '\n') {
      tokens.push({ type: TokenType.NEWLINE, value: char, line, col });
      line++;
      col = 0;
      i++;
    } else if (char === '{') {
      tokens.push({ type: TokenType.LBRACE, value: char, line, col });
      col++;
      i++;
    } else if (char === '}') {
      tokens.push({ type: TokenType.RBRACE, value: char, line, col });
      col++;
      i++;
    } else if (char === '(') {
      tokens.push({ type: TokenType.LPAREN, value: char, line, col });
      col++;
      i++;
    } else if (char === ')') {
      tokens.push({ type: TokenType.RPAREN, value: char, line, col });
      col++;
      i++;
    } else if (char === "'" || char === '"') {
      // 字符串（支持 Groovy 三引号 """...""" 和 '''...'''）
      const startChar = char;
      const triple = content[i + 1] === startChar && content[i + 2] === startChar;
      let value = '';
      if (triple) {
        // 三引号字符串：扫描直到匹配的三个连续引号
        value = content.slice(i, i + 3);
        i += 3;
        col += 3;
        while (i < content.length) {
          const c = content[i];
          value += c;
          if (c === startChar
            && content[i + 1] === startChar
            && content[i + 2] === startChar
            && content[i - 1] !== '\\') {
            value += content.slice(i + 1, i + 3);
            i += 3;
            col += 3;
            break;
          }
          if (c === '\n') {
            line++;
            col = 0;
          } else {
            col++;
          }
          i++;
        }
      } else {
        // 单引号 / 双引号字符串
        value = char;
        i++;
        col++;
        while (i < content.length) {
          const c = content[i];
          value += c;
          if (c === startChar && content[i - 1] !== '\\') {
            i++;
            col++;
            break;
          }
          if (c === '\n') {
            line++;
            col = 0;
          } else {
            col++;
          }
          i++;
        }
      }
      tokens.push({ type: TokenType.STRING, value, line: tokens[tokens.length - 1]?.line || 0, col });
    } else if (char === '/' && content[i + 1] === '/') {
      // 单行注释
      let value = '';
      while (i < content.length && content[i] !== '\n') {
        value += content[i];
        i++;
        col++;
      }
      tokens.push({ type: TokenType.COMMENT, value, line, col });
    } else if (/\s/.test(char)) {
      // 空白字符
      let value = '';
      while (i < content.length && /\s/.test(content[i]) && content[i] !== '\n') {
        value += content[i];
        i++;
        col++;
      }
      tokens.push({ type: TokenType.WHITESPACE, value, line, col });
    } else if (/[a-zA-Z_]/.test(char)) {
      // 标识符
      let value = '';
      while (i < content.length && /[a-zA-Z0-9_]/.test(content[i])) {
        value += content[i];
        i++;
        col++;
      }
      tokens.push({ type: TokenType.WORD, value, line, col });
    } else {
      tokens.push({ type: TokenType.OTHER, value: char, line, col });
      i++;
      col++;
    }
  }

  return tokens;
}

/**
 * 获取 token 对应的行号（从原始内容计算）
 */
function getTokenLine(content: string, targetLine: number): number {
  const lines = content.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (i === targetLine) return i;
  }
  return 0;
}

/**
 * 从 Jenkinsfile 内容中解析 stages
 */
export function parseStages(jenkinsfileContent: string): Stage[] {
  if (!jenkinsfileContent) return [];

  const tokens = tokenize(jenkinsfileContent);
  const lines = jenkinsfileContent.split('\n');
  const stages: Stage[] = [];

  let inStages = false;
  let braceDepth = 0;
  let stagesStartBraceDepth = 0;

  // 用于追踪当前位置
  let currentStage: { name: string; startTokenIndex: number; startLine: number } | null = null;
  let tokenLineMap = new Map<number, number>();
  let lineCounter = 0;
  let charCounter = 0;

  // 建立 token 到行号的映射
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    // 计算这个 token 对应的行号
    while (charCounter < jenkinsfileContent.length) {
      if (jenkinsfileContent.substring(charCounter, charCounter + token.value.length) === token.value) {
        tokenLineMap.set(i, lineCounter);
        // 更新行计数器
        for (const c of token.value) {
          if (c === '\n') {
            lineCounter++;
          }
        }
        charCounter += token.value.length;
        break;
      }
      if (jenkinsfileContent[charCounter] === '\n') {
        lineCounter++;
      }
      charCounter++;
    }
  }

  // 解析 token 流
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    if (token.type === TokenType.WORD && token.value === 'stages') {
      // 查找下一个 {
      for (let j = i + 1; j < tokens.length; j++) {
        if (tokens[j].type === TokenType.LBRACE) {
          inStages = true;
          stagesStartBraceDepth = braceDepth;
          braceDepth++;
          i = j; // 跳过已处理的 token
          break;
        }
        if (tokens[j].type === TokenType.NEWLINE) continue;
        if (tokens[j].type === TokenType.WHITESPACE) continue;
        if (tokens[j].type === TokenType.COMMENT) continue;
        break;
      }
      continue;
    }

    if (token.type === TokenType.LBRACE) {
      braceDepth++;
    }

    if (token.type === TokenType.RBRACE) {
      braceDepth--;

      // 检查是否 stage 结束
      if (currentStage && braceDepth === stagesStartBraceDepth + 1) {
        const endLine = tokenLineMap.get(i) || 0;
        const startLine = currentStage.startLine;
        const content = lines.slice(startLine, endLine + 1).join('\n');

        stages.push({
          name: currentStage.name,
          startIndex: startLine,
          endIndex: endLine,
          content,
        });

        currentStage = null;
      }

      // 检查是否 stages 块结束
      if (inStages && braceDepth === stagesStartBraceDepth) {
        inStages = false;
      }
    }

    // 检测 stage 开始
    if (inStages && token.type === TokenType.WORD && token.value === 'stage' && !currentStage) {
      // 查找 stage('xxx')
      let stageName = '';
      let foundLParen = false;
      let foundString = false;

      for (let j = i + 1; j < tokens.length; j++) {
        const t = tokens[j];
        if (t.type === TokenType.WHITESPACE || t.type === TokenType.NEWLINE || t.type === TokenType.COMMENT) continue;
        if (t.type === TokenType.LPAREN) {
          foundLParen = true;
          continue;
        }
        if (foundLParen && t.type === TokenType.STRING) {
          stageName = t.value.slice(1, -1); // 去掉引号
          foundString = true;
          continue;
        }
        if (foundString && t.type === TokenType.RPAREN) {
          // 查找 {
          for (let k = j + 1; k < tokens.length; k++) {
            const tk = tokens[k];
            if (tk.type === TokenType.WHITESPACE || tk.type === TokenType.NEWLINE || tk.type === TokenType.COMMENT) continue;
            if (tk.type === TokenType.LBRACE) {
              // 找到 stage 开始
              currentStage = {
                name: stageName,
                startTokenIndex: i,
                startLine: tokenLineMap.get(i) || 0,
              };
              i = k - 1; // 继续处理 { token
              break;
            }
            break;
          }
          break;
        }
        break;
      }
    }
  }

  return stages;
}

/**
 * 从 stage 内容中提取 steps 部分的脚本
 */
export function extractStageScript(stageContent: string): string {
  const tokens = tokenize(stageContent);
  const lines = stageContent.split('\n');

  let inSteps = false;
  let stepsStartLine = 0;
  let stepsEndLine = 0;
  let braceDepth = 0;
  let stepsBraceDepth = 0;

  // 建立 token 到行号的映射
  let lineCounter = 0;
  let charCounter = 0;
  const tokenLineMap = new Map<number, number>();

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    while (charCounter < stageContent.length) {
      if (stageContent.substring(charCounter, charCounter + token.value.length) === token.value) {
        tokenLineMap.set(i, lineCounter);
        for (const c of token.value) {
          if (c === '\n') lineCounter++;
        }
        charCounter += token.value.length;
        break;
      }
      if (stageContent[charCounter] === '\n') lineCounter++;
      charCounter++;
    }
  }

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    if (!inSteps && token.type === TokenType.WORD && token.value === 'steps') {
      // 查找 {
      for (let j = i + 1; j < tokens.length; j++) {
        const t = tokens[j];
        if (t.type === TokenType.WHITESPACE || t.type === TokenType.NEWLINE || t.type === TokenType.COMMENT) continue;
        if (t.type === TokenType.LBRACE) {
          inSteps = true;
          stepsBraceDepth = braceDepth;
          braceDepth++;
          stepsStartLine = tokenLineMap.get(j) || 0;
          i = j;
          break;
        }
        break;
      }
      continue;
    }

    if (token.type === TokenType.LBRACE) {
      braceDepth++;
    }

    if (token.type === TokenType.RBRACE) {
      braceDepth--;

      if (inSteps && braceDepth === stepsBraceDepth) {
        // steps 结束
        stepsEndLine = tokenLineMap.get(i) || 0;
        // 提取 steps 内容
        const stepsContent = lines.slice(stepsStartLine + 1, stepsEndLine).join('\n');
        return normalizeIndentation(stepsContent);
      }
    }
  }

  return '';
}

/**
 * 更新 stage 中的 steps 内容
 * 使用语法分析，精确定位和替换
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
  const stageContent = targetStage.content;

  console.log('[updateStageSteps] stage:', stageName, 'lines:', targetStage.startIndex, '-', targetStage.endIndex);

  // 在 stage 内容中找到 steps 区域
  const tokens = tokenize(stageContent);
  let stepsKeywordToken = -1;  // 'steps' 关键字的 token 索引
  let stepsEndToken = -1;      // steps 块结束的 } token 索引
  let braceDepth = 0;
  let stepsStartBraceDepth = 0;  // steps { 之后的 braceDepth
  let inSteps = false;
  let foundFirstBrace = false;  // 是否已经处理了 stage 的第一个 {

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    // 跳过直到找到 stage 的第一个 {（stage 开括号）
    if (!foundFirstBrace) {
      if (token.type === TokenType.LBRACE) {
        foundFirstBrace = true;
        braceDepth = 1;  // stage { 已经让 depth = 1
      }
      continue;
    }

    if (!inSteps && token.type === TokenType.WORD && token.value === 'steps') {
      // 记录 steps 关键字位置
      stepsKeywordToken = i;
      
      // 查找 steps 后面的 {
      for (let j = i + 1; j < tokens.length; j++) {
        const t = tokens[j];
        if (t.type === TokenType.WHITESPACE || t.type === TokenType.NEWLINE || t.type === TokenType.COMMENT) continue;
        if (t.type === TokenType.LBRACE) {
          inSteps = true;
          braceDepth++;  // steps { 让 depth +1
          stepsStartBraceDepth = braceDepth;  // 记录 steps 开始时的 depth
          i = j; // 继续处理 { token
          break;
        }
        break;
      }
      continue;
    }

    if (token.type === TokenType.LBRACE) {
      braceDepth++;
    }

    if (token.type === TokenType.RBRACE) {
      braceDepth--;
      
      if (inSteps && braceDepth === stepsStartBraceDepth - 1) {
        // 找到 steps 块的结束 }
        // 当遇到 steps 的 } 时，depth 会减到 stepsStartBraceDepth - 1
        stepsEndToken = i;
        break;
      }
    }
  }

  if (stepsKeywordToken === -1 || stepsEndToken === -1) {
    throw new Error(`Steps section not found in stage "${stageName}"`);
  }

  console.log('[updateStageSteps] stepsKeywordToken:', stepsKeywordToken, 'stepsEndToken:', stepsEndToken);
  console.log('[updateStageSteps] stepsKeywordToken value:', tokens[stepsKeywordToken]?.value);
  console.log('[updateStageSteps] stepsEndToken value:', tokens[stepsEndToken]?.value);

  // 计算 stage 内容在原始 jenkinsfileContent 中的起始字符位置
  let stageStartChar = 0;
  for (let i = 0; i < targetStage.startIndex; i++) {
    stageStartChar += lines[i].length + 1; // +1 for newline
  }

  console.log('[updateStageSteps] stageStartChar:', stageStartChar, 'stage start line:', targetStage.startIndex);

  // 计算 steps 块在原始 jenkinsfileContent 中的字符位置
  // stepsStartChar: 'steps' 关键字在原始内容中的起始位置
  // stepsEndChar: steps 块结束 } 在原始内容中的结束位置
  let stepsStartChar = stageStartChar;
  let stepsEndChar = stageStartChar;

  // 累积字符到 stepsKeywordToken（包含 steps 关键字本身的起始位置）
  for (let i = 0; i < stepsKeywordToken; i++) {
    stepsStartChar += tokens[i].value.length;
  }

  // 累积字符到 stepsEndToken（包含结束 } token 的结束位置）
  for (let i = 0; i <= stepsEndToken; i++) {
    stepsEndChar += tokens[i].value.length;
  }

  console.log('[updateStageSteps] stepsStartChar:', stepsStartChar);
  console.log('[updateStageSteps] stepsEndChar:', stepsEndChar);
  console.log('[updateStageSteps] content at stepsStartChar:', jenkinsfileContent.substring(stepsStartChar - 5, stepsStartChar + 20));
  console.log('[updateStageSteps] content at stepsEndChar-5:', jenkinsfileContent.substring(stepsEndChar - 10, stepsEndChar + 10));

  // 计算新的 steps 内容
  const stageIndent = lines[targetStage.startIndex].match(/^(\s*)/)?.[1] || '';
  const stepsIndent = stageIndent + '    ';
  const contentIndent = stepsIndent + '    ';

  const formattedScript = newStepsScript
    .split('\n')
    .map((line) => (line.trim() ? contentIndent + line.trim() : ''))
    .join('\n');

  const newStepsBlock = `${stepsIndent}steps {\n${formattedScript}\n${stepsIndent}}`;

  // 构建新的 Jenkinsfile
  // beforeSteps: 从开头到 steps 关键字之前
  // afterSteps: 从 steps 结束 } 之后开始
  const beforeSteps = jenkinsfileContent.substring(0, stepsStartChar);
  const afterSteps = jenkinsfileContent.substring(stepsEndChar);

  console.log('[updateStageSteps] beforeSteps length:', beforeSteps.length);
  console.log('[updateStageSteps] afterSteps start:', JSON.stringify(afterSteps.substring(0, 50)));

  // afterSteps 应该包含 stage 的闭合括号
  // 格式通常是: "\n    }" 或 "        }\n..."
  // 如果 afterSteps 以空白开头然后是 }，说明包含 stage 的闭括号
  const afterStepsTrimmed = afterSteps.trimStart();
  console.log('[updateStageSteps] afterStepsTrimmed start:', JSON.stringify(afterStepsTrimmed.substring(0, 20)));

  if (afterStepsTrimmed.startsWith('}')) {
    // afterSteps 包含 stage 的闭括号，直接拼接
    const newContent = beforeSteps + newStepsBlock + afterSteps;
    console.log('[updateStageSteps] newContent length:', newContent.length);
    return newContent;
  } else {
    // afterSteps 不包含 stage 的闭括号，需要添加
    const newContent = beforeSteps + newStepsBlock + '\n' + stageIndent + '}' + afterSteps;
    console.log('[updateStageSteps] newContent length:', newContent.length);
    return newContent;
  }
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
    .join('\n')
    .trim();
}

/**
 * 从 Jenkinsfile 内容中提取 environment 块的内容
 */
export function extractEnvironment(jenkinsfileContent: string): string {
  if (!jenkinsfileContent) return '';

  const tokens = tokenize(jenkinsfileContent);

  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i] && tokens[i].type === TokenType.WORD && tokens[i].value === 'environment') {
      for (let j = i + 1; j < tokens.length; j++) {
        if (tokens[j] && tokens[j].type === TokenType.LBRACE) {
          let result = '';
          let k = j + 1;
          let depth = 1;
          while (k < tokens.length && depth > 0) {
            if (tokens[k] && tokens[k].type === TokenType.LBRACE) depth++;
            if (tokens[k] && tokens[k].type === TokenType.RBRACE) depth--;
            if (depth > 0) {
              result += tokens[k].value;
            }
            k++;
          }
          return result.trim();
        }
      }
      return '';
    }
  }

  return '';
}

function findMatchingBrace(tokens: Token[], openBraceIndex: number): number {
  let depth = 1;
  for (let i = openBraceIndex + 1; i < tokens.length; i++) {
    if (tokens[i].type === TokenType.LBRACE) depth++;
    if (tokens[i].type === TokenType.RBRACE) {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

/**
 * 更新 Jenkinsfile 中的 environment 块
 * 将 environment { ... } 块替换为新的内容
 */
export function updateEnvironment(
  jenkinsfileContent: string,
  newEnvContent: string
): string {
  if (!jenkinsfileContent) return jenkinsfileContent;

  const tokens = tokenize(jenkinsfileContent);
  const lines = jenkinsfileContent.split('\n');

  // 找到 environment { ... } 的起止 token 索引
  let envKeywordToken = -1;
  let envOpenBraceToken = -1;
  let envCloseBraceToken = -1;

  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type === TokenType.WORD && tokens[i].value === 'environment') {
      envKeywordToken = i;
      for (let j = i + 1; j < tokens.length; j++) {
        if (tokens[j].type === TokenType.LBRACE) {
          envOpenBraceToken = j;
          envCloseBraceToken = findMatchingBrace(tokens, j);
          break;
        }
      }
      break;
    }
  }

  if (envKeywordToken === -1 || envOpenBraceToken === -1 || envCloseBraceToken === -1) {
    throw new Error('Environment block not found in Jenkinsfile');
  }

  // 计算 environment 块在原始内容中的字符位置
  let beforeEnvContent = '';
  let afterEnvContent = '';

  // 从开始到 environment 关键字之前
  let envStartChar = 0;
  for (let i = 0; i < envKeywordToken; i++) {
    envStartChar += tokens[i].value.length;
  }
  beforeEnvContent = jenkinsfileContent.substring(0, envStartChar);

  // 从 environment 块结束 } 之后到最后
  let envEndChar = 0;
  for (let i = 0; i <= envCloseBraceToken; i++) {
    envEndChar += tokens[i].value.length;
  }
  afterEnvContent = jenkinsfileContent.substring(envEndChar);

  // 计算缩进
  const envLine = tokens[envKeywordToken].line;
  const envIndent = lines[envLine]?.match(/^(\s*)/)?.[1] || '';

  // 格式化新的 environment 块
  const contentIndent = envIndent + '    ';
  const formattedContent = newEnvContent
    .split('\n')
    .map((line) => (line.trim() ? contentIndent + line.trim() : ''))
    .join('\n');

  const newEnvBlock = `${envIndent}environment {\n${formattedContent}\n${envIndent}}`;

  return beforeEnvContent + newEnvBlock + afterEnvContent;
}

/**
 * 验证 Jenkinsfile 格式
 */
export function validateJenkinsfile(content: string): { valid: boolean; error?: string } {
  if (!content.trim()) {
    return { valid: false, error: 'Jenkinsfile 内容不能为空' };
  }

  // 使用词法分析验证括号匹配
  const tokens = tokenize(content);
  let braceCount = 0;
  let hasPipeline = false;
  let hasStages = false;

  for (const token of tokens) {
    if (token.type === TokenType.LBRACE) braceCount++;
    if (token.type === TokenType.RBRACE) {
      braceCount--;
      if (braceCount < 0) {
        return { valid: false, error: '大括号不匹配：多余的 }' };
      }
    }
    if (token.type === TokenType.WORD && token.value === 'pipeline') hasPipeline = true;
    if (token.type === TokenType.WORD && token.value === 'stages') hasStages = true;
  }

  if (!hasPipeline) {
    return { valid: false, error: '无效的 Jenkinsfile 格式：缺少 pipeline 定义' };
  }

  if (!hasStages) {
    return { valid: false, error: '无效的 Jenkinsfile 格式：缺少 stages 定义' };
  }

  if (braceCount !== 0) {
    return { valid: false, error: `大括号不匹配：缺少 ${braceCount} 个 }` };
  }

  return { valid: true };
}
