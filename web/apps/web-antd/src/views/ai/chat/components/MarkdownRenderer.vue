<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';
import taskLists from 'markdown-it-task-lists';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

// 代码块超过此行数时默认折叠
const COLLAPSE_THRESHOLD = 20;

function preprocess(src: string): string {
  let s = src
    .replace(/\r\n?/g, '\n')
    .replace(/\t/g, '  ')
    .replace(/\u00a0/g, ' ');
  s = s.replace(/(#{2,6})([^\s#\n])/g, '$1 $2');
  s = s.replace(/([^\n#])(#{2,6}\s)/g, '$1\n\n$2');
  s = s.replace(/^(#{2,6}.*?)(```+)/gm, '$1\n$2');
  s = s.replace(/^(\s*```+\w*\s*)(#{2,6})/gm, '$1\n$2');
  s = s.replace(/^(-{3,})(#{2,6})/gm, '$1\n$2');
  s = s.replace(/\n(-{3,})\n(?!\s)/g, '\n\n$1\n');
  s = s.replace(/\n\*{3,}\n/g, '\n\n***\n');
  // 表格修复：表格行前后补空行，确保 markdown-it 正确识别 GFM 表格
  s = s.replace(/([^\n])\n(\|[^\n]*)/g, '$1\n\n$2');
  s = s.replace(/(\|[^\n]*)\n([^\n|])/g, '$1\n\n$2');
  s = s.replace(/^(#{1,6}\s.*)\|([^|]+\|)$/gm, '$1\n|$2');
  s = s.replace(/^([^|\n]*\S)\|([^|]+\|[ \t]*)$/gm, '$1\n|$2');
  s = s.replace(/^(\|[-:| ]+)\n(\|[-:| ]+\|)$/gm, '$1$2');
  s = s.replace(/^(\s*[-*+])([^\s\-*+\n])/gm, '$1 $2');
  s = s.replace(/\n([-*+] |\d+\. )/g, '\n\n$1');
  s = s.replace(/\n{3,}/g, '\n\n');
  return s.trim();
}

// 将原始代码 base64 编码，安全地嵌入 data 属性供复制使用
function encodeCode(code: string): string {
  try {
    return btoa(unescape(encodeURIComponent(code)));
  } catch {
    return '';
  }
}

const md = new MarkdownIt({
  html: false,
  linkify: true,
});

// 自定义围栏代码块渲染：返回独立代码块 HTML（含 header + 复制按钮）
// 使用 renderer.rules.fence 而非 highlight 选项，避免被 markdown-it 的 <pre><code> 包裹
md.renderer.rules.fence = function (tokens: any, idx: number): string {
  const token = tokens[idx];
  const lang = (token.info || '').trim().split(/\s+/)[0] || '';
  const str = (token.content || '').replace(/\n$/, '');
  const langLabel = lang || 'text';

  let codeHtml: string;
  if (lang && hljs.getLanguage(lang)) {
    try {
      codeHtml = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value;
    } catch {
      codeHtml = md.utils.escapeHtml(str);
    }
  } else {
    codeHtml = md.utils.escapeHtml(str);
  }

  const lineCount = str ? str.split('\n').length : 0;
  const collapsible = lineCount > COLLAPSE_THRESHOLD;
  const encoded = encodeCode(str);

  return (
    `<div class="code-block${collapsible ? ' collapsible' : ''}">` +
    `<div class="code-block-header">` +
    `<span class="code-lang">${langLabel}</span>` +
    `<button class="code-copy-btn" data-code="${encoded}" type="button" title="复制代码">复制</button>` +
    `</div>` +
    `<pre class="hljs"><code class="language-${lang || 'text'}">${codeHtml}</code></pre>` +
    (collapsible ? `<button class="code-expand-btn" type="button">展开</button>` : '') +
    `</div>\n`
  );
};
try {
  md.use(taskLists, { label: true, labelAfter: true });
} catch { /* task-lists plugin not available */ }

const props = defineProps<{ content: string }>();

const html = computed(() => {
  if (!props.content) return '';
  try {
    const raw = md.render(preprocess(props.content));
    return DOMPurify.sanitize(raw, {
      ADD_ATTR: ['data-code', 'data-lang', 'target'],
      ADD_TAGS: ['button'],
    });
  } catch {
    return `<p>${props.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;
  }
});

// 事件委托：处理复制按钮和展开/折叠按钮
const rootRef = ref<HTMLElement | null>(null);

function handleClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target) return;

  if (target.classList.contains('code-copy-btn')) {
    const encoded = target.getAttribute('data-code') || '';
    try {
      const code = decodeURIComponent(escape(atob(encoded)));
      navigator.clipboard
        ?.writeText(code)
        .then(() => {
          const original = target.textContent;
          target.textContent = '已复制';
          target.classList.add('copied');
          setTimeout(() => {
            target.textContent = original;
            target.classList.remove('copied');
          }, 2000);
        })
        .catch(() => {});
    } catch { /* decode failed */ }
    return;
  }

  if (target.classList.contains('code-expand-btn')) {
    const wrapper = target.closest('.code-block');
    if (wrapper) {
      const expanded = wrapper.classList.toggle('expanded');
      target.textContent = expanded ? '收起' : '展开';
    }
  }
}

onMounted(() => {
  rootRef.value?.addEventListener('click', handleClick);
});

onBeforeUnmount(() => {
  rootRef.value?.removeEventListener('click', handleClick);
});
</script>

<template>
  <div class="md-body">
    <div ref="rootRef" class="md-content" v-html="html" />
    <div v-if="!html" class="md-empty">（空内容）</div>
  </div>
</template>

<style>
/* ============================================================
   DeepSeek 风格 Markdown 渲染
   - 浅色正文 + 深色代码块（对比鲜明）
   - sans-serif 字族，舒适行高
   - 精致间距与圆角
   ============================================================ */

.md-body { width: 100%; overflow-x: auto; }
.md-empty { color: #999; padding: 8px 0; font-size: 14px; }

.md-content {
  font-family: system-ui, -apple-system, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  font-size: 15px;
  line-height: 1.75;
  color: #1f1f1f;
  word-wrap: break-word;
}
.md-content > :first-child { margin-top: 0; }
.md-content > :last-child { margin-bottom: 0; }

/* ===== 标题 ===== */
.md-content h1,
.md-content h2,
.md-content h3,
.md-content h4,
.md-content h5,
.md-content h6 {
  margin-top: 1.6em;
  margin-bottom: 0.6em;
  font-weight: 600;
  line-height: 1.4;
  color: #0d0d0d;
}
.md-content h1 {
  font-size: 1.6em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #e8e8e8;
}
.md-content h2 {
  font-size: 1.35em;
  padding-bottom: 0.25em;
  border-bottom: 1px solid #e8e8e8;
}
.md-content h3 { font-size: 1.18em; }
.md-content h4 { font-size: 1.05em; }
.md-content h5 { font-size: 0.95em; color: #595959; }
.md-content h6 { font-size: 0.9em; color: #595959; }

/* ===== 段落 ===== */
.md-content p {
  margin: 0.75em 0;
  line-height: 1.75;
}

/* ===== 列表 ===== */
.md-content ul,
.md-content ol {
  padding-left: 1.8em;
  margin: 0.6em 0;
}
.md-content li { margin: 0.3em 0; line-height: 1.75; }
.md-content ul ul,
.md-content ol ol,
.md-content ul ol,
.md-content ol ul { margin: 0.3em 0; }

/* task list */
.md-content .task-list-item {
  list-style-type: none;
  padding-left: 0;
  margin-left: -1.5em;
}
.md-content .task-list-item input {
  margin: 0 0.5em 0 0;
  vertical-align: middle;
}

/* ===== 引用 ===== */
.md-content blockquote {
  margin: 1em 0;
  padding: 0.5em 1.2em;
  border-left: 4px solid #d0d7de;
  background: #f6f8fa;
  color: #57606a;
  border-radius: 0 6px 6px 0;
}
.md-content blockquote p { margin: 0.4em 0; }

/* ===== 链接 ===== */
.md-content a {
  color: #1677ff;
  text-decoration: none;
  border-bottom: 1px solid rgba(22, 119, 255, 0.3);
  transition: border-color 0.15s;
}
.md-content a:hover { border-bottom-color: #1677ff; }

/* ===== 行内代码 ===== */
.md-content code:not(pre code) {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace;
  font-size: 0.88em;
  padding: 2px 6px;
  background: #f0f2f5;
  border-radius: 4px;
  color: #c41d7f;
}

/* ===== 代码块（DeepSeek 风格：深色背景） ===== */
.md-content .code-block {
  margin: 1.1em 0;
  border-radius: 10px;
  overflow: hidden;
  background: #1e1e1e;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.md-content .code-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2a2a2a;
  border-bottom: 1px solid #3a3a3a;
  font-size: 12px;
  user-select: none;
}
.md-content .code-lang {
  color: #a0a0a0;
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-weight: 500;
  text-transform: lowercase;
}
.md-content .code-copy-btn {
  background: transparent;
  border: 1px solid #4a4a4a;
  border-radius: 4px;
  padding: 3px 12px;
  font-size: 12px;
  cursor: pointer;
  color: #c0c0c0;
  transition: all 0.15s;
  font-family: inherit;
}
.md-content .code-copy-btn:hover {
  background: #3a3a3a;
  border-color: #6a6a6a;
  color: #fff;
}
.md-content .code-copy-btn.copied {
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
}
.md-content .code-block pre {
  margin: 0;
  padding: 16px 18px;
  overflow-x: auto;
  background: #1e1e1e;
  border: none;
  border-radius: 0;
  font-size: 13.5px;
  line-height: 1.6;
}
.md-content .code-block pre code {
  background: transparent;
  color: #e0e0e0;
  padding: 0;
  border: none;
  font-size: inherit;
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace;
}
/* 可折叠代码块 */
.md-content .code-block.collapsible:not(.expanded) pre {
  max-height: 340px;
  overflow: hidden;
  mask-image: linear-gradient(to bottom, black 65%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 65%, transparent 100%);
}
.md-content .code-expand-btn {
  display: block;
  width: 100%;
  padding: 6px;
  background: #2a2a2a;
  border: none;
  border-top: 1px solid #3a3a3a;
  cursor: pointer;
  font-size: 12px;
  color: #a0a0a0;
  transition: background 0.15s;
  font-family: inherit;
}
.md-content .code-expand-btn:hover { background: #333; color: #fff; }

/* ===== 表格 ===== */
.md-content table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
  margin: 1em 0;
  font-size: 0.93em;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
}
.md-content th,
.md-content td {
  padding: 0.6em 1em;
  border-bottom: 1px solid #e8e8e8;
  text-align: left;
}
.md-content th {
  background: #fafbfc;
  font-weight: 600;
  color: #1f1f1f;
  border-bottom: 2px solid #e0e0e0;
}
.md-content tr:last-child td { border-bottom: none; }
.md-content tbody tr:nth-child(even) { background: #fafbfc; }
.md-content tbody tr:hover { background: #f0f5ff; }

/* ===== 分隔线 ===== */
.md-content hr {
  border: none;
  height: 1px;
  background: linear-gradient(to right, transparent, #d0d7de, transparent);
  margin: 1.5em 0;
}

/* ===== 图片 ===== */
.md-content img {
  max-width: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* ===== 强调 ===== */
.md-content strong { font-weight: 600; color: #0d0d0d; }
.md-content em { font-style: italic; }
.md-content del { color: #8c8c8c; }

/* ===== 键盘按键样式 ===== */
.md-content kbd {
  display: inline-block;
  padding: 1px 6px;
  font-size: 0.85em;
  font-family: ui-monospace, monospace;
  background: #fafbfc;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.1);
  color: #57606a;
}

/* ===== 暗色主题：跟随系统 ===== */
@media (prefers-color-scheme: dark) {
  .md-content { color: #e6e6e6; }
  .md-content h1, .md-content h2, .md-content h3,
  .md-content h4, .md-content h5, .md-content h6 { color: #f0f0f0; }
  .md-content h1, .md-content h2 { border-bottom-color: #303030; }
  .md-content h5, .md-content h6 { color: #a0a0a0; }

  .md-content blockquote {
    border-left-color: #444;
    background: #1a1a1a;
    color: #a0a0a0;
  }

  .md-content a { color: #4d9fff; border-bottom-color: rgba(77, 159, 255, 0.3); }
  .md-content a:hover { border-bottom-color: #4d9fff; }

  .md-content code:not(pre code) {
    background: #2a2a2a;
    color: #ff9ec4;
  }

  .md-content .code-block {
    background: #0d0d0d;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
  }
  .md-content .code-block-header {
    background: #1a1a1a;
    border-bottom-color: #2a2a2a;
  }
  .md-content .code-copy-btn {
    background: transparent;
    border-color: #3a3a3a;
    color: #b0b0b0;
  }
  .md-content .code-copy-btn:hover {
    background: #2a2a2a;
    border-color: #5a5a5a;
    color: #fff;
  }
  .md-content .code-block pre { background: #0d0d0d; }
  .md-content .code-expand-btn {
    background: #1a1a1a;
    border-top-color: #2a2a2a;
    color: #b0b0b0;
  }
  .md-content .code-expand-btn:hover { background: #2a2a2a; color: #fff; }

  .md-content table { border-color: #303030; }
  .md-content th {
    background: #1a1a1a;
    color: #f0f0f0;
    border-bottom-color: #404040;
  }
  .md-content th, .md-content td { border-bottom-color: #303030; }
  .md-content tbody tr:nth-child(even) { background: #1a1a1a; }
  .md-content tbody tr:hover { background: #1e2a3a; }

  .md-content hr {
    background: linear-gradient(to right, transparent, #444, transparent);
  }

  .md-content strong { color: #f0f0f0; }
  .md-content del { color: #666; }

  .md-content kbd {
    background: #2a2a2a;
    border-color: #444;
    color: #b0b0b0;
  }
  .md-empty { color: #666; }
}
</style>
