<script setup lang="ts">
import { computed } from 'vue';
import MarkdownIt from 'markdown-it';
import taskLists from 'markdown-it-task-lists';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';

function preprocess(src: string): string {
  let s = src
    .replace(/\r\n?/g, '\n')
    .replace(/\t/g, '  ')
    .replace(/\u00a0/g, ' ');
  // step 1: heading markers need a space: "##text" → "## text"
  s = s.replace(/(#{2,6})([^\s#\n])/g, '$1 $2');
  // step 2: newline before heading: "xxx### text" → "xxx\n\n### text"
  s = s.replace(/([^\n#])(#{2,6}\s)/g, '$1\n\n$2');
  // step 3: heading + code fence on same line: "### text```" → "### text\n```"
  s = s.replace(/^(#{2,6}.*?)(```+)/gm, '$1\n$2');
  s = s.replace(/^(\s*```+\w*\s*)(#{2,6})/gm, '$1\n$2');
  // step 4: "---###" → "---\n###"
  s = s.replace(/^(-{3,})(#{2,6})/gm, '$1\n$2');
  // step 5: blank line around HR --- or ***
  s = s.replace(/\n(-{3,})\n(?!\s)/g, '\n\n$1\n');
  s = s.replace(/\n\*{3,}\n/g, '\n\n***\n');
  // step 6: table row glued to heading: "### hdr |a|b|" → "### hdr\n|a|b|"
  s = s.replace(/^(#{1,6}\s.*)\|([^|]+\|)$/gm, '$1\n|$2');
  // step 7: table row glued to paragraph text
  s = s.replace(/^([^|\n]*\S)\|([^|]+\|[ \t]*)$/gm, '$1\n|$2');
  // step 8: broken table separator recovery
  s = s.replace(/^(\|[-:| ]+)\n(\|[-:| ]+\|)$/gm, '$1$2');
  // step 9: space after list marker: "-text" → "- text"
  s = s.replace(/^(\s*[-*+])([^\s\-*+\n])/gm, '$1 $2');
  // step 10: blank line before list items
  s = s.replace(/\n([-*+] |\d+\. )/g, '\n\n$1');
  // step 11: collapse excessive blank lines
  s = s.replace(/\n{3,}/g, '\n\n');
  return s.trim();
}

const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const html = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value;
        return `<pre class="hljs"><code class="language-${lang}">${html}</code></pre>`;
      } catch { /* fall through */ }
    }
    const escaped = md.utils.escapeHtml(str);
    return `<pre class="hljs"><code>${escaped}</code></pre>`;
  },
});
try {
  md.use(taskLists, { label: true, labelAfter: true });
} catch { /* task-lists plugin not available */ }

const props = defineProps<{ content: string }>();

const html = computed(() => {
  if (!props.content) return '';
  try {
    return md.render(preprocess(props.content));
  } catch {
    return `<p>${props.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;
  }
});
</script>

<template>
  <div class="md-body">
    <div class="md-content" v-html="html" />
    <div v-if="!html" class="md-empty">（空内容）</div>
  </div>
</template>

<style>
.md-body { width: 100%; overflow-x: auto; }
.md-empty { color: #999; padding: 8px 0; font-size: 13px; }

.md-content { font-size: 15px; line-height: 1.65; color: #1e1e1e; word-wrap: break-word; }
.md-content > :first-child { margin-top: 0; }
.md-content > :last-child { margin-bottom: 0; }

.md-content h1, .md-content h2, .md-content h3, .md-content h4 {
  margin-top: 1.3em; margin-bottom: 0.45em;
  font-weight: 600; line-height: 1.35; color: #111;
}
.md-content h1 { font-size: 1.55em; border-bottom: 2px solid #eee; padding-bottom: 0.2em; }
.md-content h2 { font-size: 1.3em; border-bottom: 1px solid #eee; padding-bottom: 0.15em; }
.md-content h3 { font-size: 1.1em; }
.md-content h4 { font-size: 1.05em; }

.md-content p { margin: 0.5em 0; line-height: 1.65; }
.md-content ul, .md-content ol { padding-left: 1.5em; margin: 0.35em 0; }
.md-content li { margin: 0.15em 0; }

.md-content blockquote {
  margin: 0.6em 0; padding: 0.3em 1em;
  border-left: 4px solid #d0d7de; color: #57606a; background: #fafbfc;
}

.md-content a { color: #0969da; text-decoration: none; }
.md-content a:hover { text-decoration: underline; }

.md-content pre {
  margin: 0.7em 0; border-radius: 8px; overflow-x: auto;
  background: #f6f8fa; border: 1px solid #e0e0e0;
  padding: 1em; font-size: 13px; line-height: 1.5;
}
.md-content pre code {
  background: transparent; color: inherit;
  padding: 0; border: none; font-size: inherit;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
}

.md-content code:not(pre code) {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 0.88em; padding: 2px 5px;
  background: #f0f0f0; border-radius: 4px; color: #d63384;
}

.md-content table {
  border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 0.93em;
}
.md-content th, .md-content td {
  padding: 0.4em 0.65em; border: 1px solid #d0d7de; text-align: left;
}
.md-content th { background: #f6f8fa; font-weight: 500; }

.md-content hr { border: none; border-top: 1px solid #d0d7de; margin: 1em 0; }
.md-content img { max-width: 100%; border-radius: 6px; }
.md-content strong { font-weight: 600; }
</style>
