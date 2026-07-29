<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Button,
  Col,
  Input,
  InputSearch,
  List,
  ListItem,
  Row,
  Select,
} from 'ant-design-vue';

import { AiChatConversationModel } from '#/models/ai/chat_conversation';
import { AiChatMessageModel } from '#/models/ai/chat_message';
import { fetchAIStream } from '#/api/ai/chat';
import MarkdownRenderer from './components/MarkdownRenderer.vue';

const route = useRoute();
const aiChatConversation = new AiChatConversationModel();
const aiChatMessageModel = new AiChatMessageModel();

interface Message {
  id: number;
  type: 'assistant' | 'user';
  content: string;
}

interface ChatItem {
  id: number;
  title: string;
  lastMessage: string;
}

const chatList = ref<ChatItem[]>([]);
const messages = ref<Message[]>([]);

const platformOptions = [
  { label: 'deepseek', value: 'deepseek' },
  { label: '通义千问', value: 'tongyi' },
];

const selectedChatId = ref<null | number>(null);
const selectedPlatform = ref(platformOptions[0]?.value);
const search = ref('');
const input = ref('');
const messagesRef = ref<HTMLElement | null>(null);
const isAiTyping = ref(false);

const filteredChats = computed(() => {
  if (!search.value) return chatList.value;
  return chatList.value.filter((chat) => chat.title.includes(search.value));
});

const lastAssistantMsg = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].type === 'assistant') return messages.value[i];
  }
  return null;
});

async function selectChat(id: number) {
  selectedChatId.value = id;
  const data = await aiChatMessageModel.list({ conversation_id: id });
  messages.value = data;
  nextTick(scrollToBottom);
}

async function handleNewChat() {
  const data = await aiChatConversation.create({
    platform: selectedPlatform.value!,
    title: '新对话',
  });
  await fetchConversations();
  selectedChatId.value = data;
  messages.value = [];
  nextTick(scrollToBottom);
}

async function handleSend() {
  const userMsg: Message = { id: null, type: 'user', content: input.value };
  messages.value.push(userMsg);

  const aiMsg: Message = { id: null, type: 'assistant', content: '' };
  messages.value.push(aiMsg);
  const aiIndex = messages.value.length - 1;

  isAiTyping.value = true;

  const stream = await fetchAIStream({
    content: input.value,
    platform: selectedPlatform.value,
    conversation_id: selectedChatId.value,
  });

  if (chatList.value.length > 0) {
    chatList.value[0]!.title = input.value.slice(0, 10);
  }

  input.value = '';

  for await (const chunk of stream) {
    messages.value[aiIndex]!.content += chunk;
    messages.value.splice(aiIndex, 1, { ...messages.value[aiIndex]! });
    await nextTick();
    scrollToBottom();
  }

  isAiTyping.value = false;
  nextTick(scrollToBottom);
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
  }
}

async function autoSend() {
  const lastMsg = messages.value[messages.value.length - 1];
  if (!lastMsg || lastMsg.type !== 'user') return;

  const aiMsg: Message = { id: null, type: 'assistant', content: '' };
  messages.value.push(aiMsg);
  const aiIndex = messages.value.length - 1;

  isAiTyping.value = true;
  try {
    const stream = await fetchAIStream({
      content: lastMsg.content,
      platform: selectedPlatform.value,
      conversation_id: selectedChatId.value,
      resume: true,
    });
    for await (const chunk of stream) {
      messages.value[aiIndex]!.content += chunk;
      messages.value.splice(aiIndex, 1, { ...messages.value[aiIndex]! });
      await nextTick();
      scrollToBottom();
    }
  } catch {
    // stream failed silently
  }
  isAiTyping.value = false;
  nextTick(scrollToBottom);
}

async function fetchConversations() {
  const data = await aiChatConversation.list();
  chatList.value = data.map((item: any) => ({
    id: item.id,
    title: item.title,
    lastMessage: item.last_message || '',
  }));
  const targetId = route.query.conversation_id
    ? Number(route.query.conversation_id)
    : chatList.value[0]?.id;
  if (targetId) {
    selectedChatId.value = targetId;
    await selectChat(targetId);
    if (route.query.auto_send !== undefined) {
      await autoSend();
    }
  }
}

onMounted(() => {
  fetchConversations();
});
</script>

<template>
  <Page auto-content-height>
    <Row style="height: 100%">
      <Col :span="5" class="chat-sider">
        <div class="sider-header">
          <Button type="primary" @click="handleNewChat">新建对话</Button>
          <Input
            v-model:value="search"
            placeholder="搜索历史对话"
            allow-clear
            style="margin: 12px 0 8px 0"
          />
        </div>
        <div class="chat-list">
          <List style="flex: 1; overflow-y: auto; padding-bottom: 12px">
            <ListItem
              v-for="item in filteredChats"
              :key="item.id"
              class="chat-list-item"
              :class="{ selected: item.id === selectedChatId }"
              @click="selectChat(item.id)"
            >
              <div class="chat-item-avatar">
                <span class="avatar-text">{{ item.title.slice(0, 1) }}</span>
              </div>
              <div class="chat-item-content">
                <div class="chat-item-title-row">
                  <span class="chat-title" :title="item.title">{{ item.title }}</span>
                </div>
                <div class="chat-desc">{{ item.lastMessage }}</div>
              </div>
            </ListItem>
          </List>
        </div>
      </Col>
      <Col :span="19" class="chat-content">
        <div class="content-header">
          <Select
            v-model:value="selectedPlatform"
            style="width: 220px"
            :options="platformOptions"
            placeholder="选择平台"
          />
        </div>
        <div class="chat-messages" ref="messagesRef">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="chat-message"
            :class="msg.type"
          >
            <div class="msg-avatar" :class="msg.type">
              <span>{{ msg.type === 'assistant' ? 'AI' : '我' }}</span>
            </div>
            <div class="msg-body">
              <div class="msg-role">{{ msg.type === 'assistant' ? 'AI 助手' : '你' }}</div>
              <div class="msg-content">
                <MarkdownRenderer
                  v-if="msg.type === 'assistant'"
                  :content="msg.content"
                />
                <span v-else class="user-text">{{ msg.content }}</span>
              </div>
              <div
                v-if="msg.type === 'assistant' && isAiTyping && msg === lastAssistantMsg"
                class="typing-indicator"
              >
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </div>
            </div>
          </div>
        </div>
        <div class="chat-input-wrap">
          <InputSearch
            v-model:value="input"
            enter-button="发送"
            @search="handleSend"
            placeholder="输入消息..."
          />
        </div>
      </Col>
    </Row>
  </Page>
</template>

<style scoped>
.chat-sider {
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #eee;
  padding: 16px 8px 8px 8px;
  height: 100%;
  min-width: 220px;
}
.sider-header { margin-bottom: 8px; }
.chat-list { flex: 1; overflow-y: auto; min-height: 0; }

.chat-list-item {
  display: flex;
  align-items: center;
  border-radius: 8px;
  margin-bottom: 6px;
  padding: 10px 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.chat-list-item.selected { background: #e6f7ff; border: 1.5px solid #1677ff; }
.chat-list-item:hover { background: #f0f5ff; }

.chat-item-avatar {
  width: 32px; height: 32px;
  background: #1677ff20;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin-right: 10px; font-size: 14px;
  color: #1677ff; font-weight: 600; flex-shrink: 0;
}
.chat-item-content { flex: 1; min-width: 0; }
.chat-item-title-row { display: flex; align-items: center; }
.chat-title {
  font-weight: 500; font-size: 14px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.chat-desc {
  color: #999; font-size: 12px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-top: 2px;
}

.chat-content {
  display: flex; flex-direction: column; height: 100%;
  background: #fff; position: relative;
}
.content-header {
  padding: 12px 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex; justify-content: flex-end;
}

.chat-messages {
  flex: 1; overflow-y: auto;
  padding: 24px 16px 120px 16px;
  scrollbar-width: thin; scrollbar-color: #d6dee1 transparent;
}
.chat-messages::-webkit-scrollbar { width: 6px; }
.chat-messages::-webkit-scrollbar-thumb { background: #d6dee1; border-radius: 4px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }

.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  padding: 0 8px;
}

.msg-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
  flex-shrink: 0;
  margin-top: 4px;
}
.msg-avatar.assistant { background: #1677ff; color: #fff; }
.msg-avatar.user { background: #52c41a; color: #fff; }

.msg-body {
  flex: 1; min-width: 0;
}
.msg-role {
  font-size: 13px; font-weight: 500;
  color: #333; margin-bottom: 4px;
}
.msg-content {
  line-height: 1.6;
}
.user-text {
  display: inline-block;
  background: #f0f0f0;
  padding: 8px 14px;
  border-radius: 12px 12px 4px 12px;
  font-size: 15px;
  color: #1e1e1e;
  white-space: pre-wrap;
  word-break: break-word;
  max-width: 100%;
}

.typing-indicator {
  display: flex; gap: 4px; align-items: center;
  margin-top: 8px; padding: 4px 0;
}
.typing-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #1677ff;
  animation: typing-bounce 1.4s infinite ease-in-out;
}
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.chat-input-wrap {
  position: absolute;
  left: 24px; right: 24px; bottom: 20px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 8px 12px;
  z-index: 10;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
</style>
