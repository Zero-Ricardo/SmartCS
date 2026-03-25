<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ChatDotRound, Close, Download, MagicStick, Upload, UserFilled, Delete, DocumentCopy, ChatSquare, Link, TopRight } from "@element-plus/icons-vue";
import { useClipboard, useNetwork, useDraggable } from "@vueuse/core";
import dayjs from "dayjs";
import { useChatStore } from "@/entities/chat/model/useChatStore";
import { useI18n } from "@/shared/i18n";
import { sendMessageStream } from "@/shared/api/chatApi";
import type { ChatMessage } from "@/shared/types/chat";
import { toRichHtml } from "@/shared/utils/richText";

const store = useChatStore();
const { t, locale, setLocale } = useI18n();
const { copy } = useClipboard();
const { isOnline } = useNetwork();

const opened = ref(false);
const input = ref("");
const streaming = ref(false);
const errorText = ref("");
const messageListRef = ref<HTMLElement>();
const preloadHistory = ref<ChatMessage[]>([]);

const workTime = computed(() => {
  const hour = dayjs().hour();
  return hour >= 9 && hour < 18;
});

const statusText = computed(() => (workTime.value ? t("aiServiceOn") : t("aiServiceOff")));
const quickPrompts = computed(() => [t("prompt1"), t("prompt2"), t("prompt3"), t("prompt4")]);

const connectionLabel = computed(() => {
  if (!isOnline.value || store.connectionState === "OFFLINE") {
    return t("offline");
  }
  if (store.connectionState === "RECONNECTING") {
    return t("reconnecting");
  }
  if (streaming.value) {
    return t("thinking");
  }
  return t("online");
});

const connectionVariant = computed(() => {
  if (!isOnline.value || store.connectionState === "OFFLINE") {
    return "offline";
  }
  if (store.connectionState === "RECONNECTING") {
    return "reconnecting";
  }
  if (streaming.value) {
    return "thinking";
  }
  return "online";
});

const panelMessages = computed(() => [...preloadHistory.value, ...store.messages]);

const ensureBottom = async () => {
  await nextTick();
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
  }
};

const openWidget = async () => {
  opened.value = true;
  await ensureBottom();
};

const closeWidget = () => {
  opened.value = false;
};

const pushUserMessage = (text: string) => {
  const payload: Omit<ChatMessage, "id" | "createdAt"> = { role: "user", content: text };
  if (store.quotedMessage) {
    payload.content = `> ${store.quotedMessage}\n\n${text}`;
    store.clearQuote();
  }
  
  return store.appendMessage(payload);
};

const pushAiContainer = () => {
  return store.appendMessage({
    role: store.serviceMode === "AI" ? "ai" : "human",
    content: "",
    pending: true
  });
};

const sendMessage = async (preset?: string) => {
  const content = (preset ?? input.value).trim();
  if (!content || streaming.value) {
    return;
  }
  errorText.value = "";
  pushUserMessage(content);
  input.value = "";
  streaming.value = true;
  store.setConnection("RECONNECTING");
  const aiId = pushAiContainer();
  await ensureBottom();

  const streamResult = await sendMessageStream(
    {
      content,
      visitorId: store.visitorId,
      sessionId: store.sessionId,
      pageContext: "training-home",
      locale: locale.value
    },
    {
      onToken(token) {
        const current = store.messages.find((item) => item.id === aiId)?.content ?? "";
        store.patchMessage(aiId, { content: `${current}${token}` });
        ensureBottom();
      },
      onCard(card) {
        store.patchMessage(aiId, { card });
      },
      onSession(sessionId) {
        if (sessionId && sessionId !== store.sessionId) {
          store.setSessionId(sessionId);
        }
      },
      onCitations(citations) {
        store.patchMessage(aiId, { citations });
      },
      onDone() {
        store.patchMessage(aiId, { pending: false });
        store.setConnection("ONLINE");
        streaming.value = false;
      },
      onError() {
        store.patchMessage(aiId, { pending: false, error: "NETWORK_ERROR" });
        store.setConnection("OFFLINE");
        errorText.value = "NETWORK_ERROR";
        streaming.value = false;
      }
    }
  );
  await ensureBottom();
};

const onEnter = (event: KeyboardEvent) => {
  if (!event.shiftKey) {
    event.preventDefault();
    void sendMessage();
  }
};

const exportChat = async () => {
  try {
    const content = panelMessages.value
      .map((message) => `[${dayjs(message.createdAt).format("YYYY-MM-DD HH:mm:ss")}] ${message.role}: ${message.content}`)
      .join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `chat-${dayjs().format("YYYYMMDD-HHmmss")}.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch {
    await copy(panelMessages.value.map((item) => `${item.role}: ${item.content}`).join("\n"));
    ElMessage.warning(t("exportFallback"));
  }
};

const useEmoji = (emoji: string) => {
  input.value += emoji;
};

const onFiles = async (files: FileList | null) => {
  if (!files || files.length === 0) {
    return;
  }
  const first = files[0];
  const text = `${t("upload")}：${first.name}`;
  await sendMessage(text);
};

const onPaste = async (event: ClipboardEvent) => {
  const item = Array.from(event.clipboardData?.items ?? []).find((entry) => entry.type.startsWith("image/"));
  if (!item) {
    return;
  }
  const file = item.getAsFile();
  if (!file) {
    return;
  }
  await sendMessage(`${t("upload")}：pasted-image.png`);
};

const onScroll = () => {
  if (!messageListRef.value || messageListRef.value.scrollTop > 24) {
    return;
  }
  if (!store.canLoadOlder) {
    return;
  }
  preloadHistory.value = [...store.loadOlder(8), ...preloadHistory.value];
};

const transferHuman = () => {
  if (!workTime.value) {
    ElMessage.info(t("transferDisabled"));
    return;
  }
  store.switchMode("HUMAN");
  ElMessage.success(t("transferHuman"));
};

const toggleServiceMode = () => {
  if (store.serviceMode === "AI") {
    transferHuman();
    return;
  }
  store.switchMode("AI");
  ElMessage.success(t("backToAiSuccess"));
};

const modeToggleLabel = computed(() => (store.serviceMode === "AI" ? t("transferHuman") : t("backToAi")));
const modeToggleDisabled = computed(() => store.serviceMode === "AI" && !workTime.value);

const roleLabel = (role: ChatMessage["role"]) => {
  if (role === "user") {
    return t("roleUser");
  }
  if (role === "ai") {
    return t("roleAi");
  }
  if (role === "human") {
    return t("roleHuman");
  }
  return t("roleSystem");
};

const avatarText = (role: ChatMessage["role"]) => {
  if (role === "user") {
    return "我";
  }
  if (role === "ai") {
    return "AI";
  }
  if (role === "human") {
    return "人";
  }
  return "S";
};

const formatTime = (iso: string) => {
  const d = dayjs(iso);
  if (!d.isValid()) {
    return "";
  }
  return d.format("HH:mm");
};

const copyAndToast = async (value: string) => {
  await copy(value);
  ElMessage.success(t("copySuccess"));
};

const quoteMessage = (text: string) => {
  // Filter out any quoted parts (e.g., lines starting with >) to prevent nested quoting
  const cleanText = text.split('\n').filter(line => !line.startsWith('>')).join('\n').trim();
  store.setQuote(cleanText);
  nextTick(() => {
    const el = document.querySelector(".composer-input textarea") as HTMLTextAreaElement;
    if (el) el.focus();
  });
};

const handleDeleteMessage = (id: string) => {
  ElMessageBox.confirm(
    "确定要删除这条消息吗？删除后将无法恢复。",
    "删除确认",
    {
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).then(() => {
    store.deleteMessage(id);
    ElMessage.success("消息已删除");
  }).catch(() => {
    // cancelled
  });
};

const renderMessage = (content: string) => toRichHtml(content);

const chatPanelRef = ref<HTMLElement | null>(null);
const chatHeaderRef = ref<HTMLElement | null>(null);

const { x, y } = useDraggable(chatPanelRef, {
  initialValue: { 
    x: window.innerWidth > 980 ? window.innerWidth - 980 - 24 : 24, 
    y: window.innerHeight > 760 ? window.innerHeight - 760 - 24 : 24 
  }, // initial bottom right position based on panel dimensions
  handle: chatHeaderRef,
});

const panelStyle = computed(() => {
  return {
    left: `${x.value}px`,
    top: `${y.value}px`,
  };
});

onMounted(() => {
  const restored = store.restore();
  if (!restored) {
    store.appendMessage({
      role: "system",
      content: t("aboutContent")
    });
  }
});
</script>

<template>
  <div class="chat-widget">
    <button v-if="!opened" class="entry-button" @click="openWidget">{{ t("chatEntry") }}</button>
    <section v-else ref="chatPanelRef" class="chat-panel" :style="panelStyle">
      <header ref="chatHeaderRef" class="chat-header" style="cursor: move;">
        <div class="title-wrap">
          <h3>{{ t("chatTitle") }}</h3>
          <div class="status-line">
            <span class="status-text">{{ statusText }}</span>
            <span class="connection-pill" :class="`variant-${connectionVariant}`">
              <span class="connection-dot" aria-hidden="true"></span>
              <span class="connection-text">{{ connectionLabel }}</span>
            </span>
          </div>
        </div>
        <div class="actions">
          <el-select :model-value="locale" size="small" style="width: 96px" @change="setLocale">
            <el-option label="中文" value="zh-CN" />
            <el-option label="EN" value="en-US" />
          </el-select>
          <el-button
            type="primary"
            plain
            size="small"
            :disabled="modeToggleDisabled"
            @click="toggleServiceMode"
          >
            <el-icon style="margin-right: 6px">
              <component :is="store.serviceMode === 'AI' ? UserFilled : ChatDotRound" />
            </el-icon>
            {{ modeToggleLabel }}
          </el-button>
          <el-button class="tool-btn header-close" text circle aria-label="close" @click="closeWidget">
            <el-icon>
              <Close />
            </el-icon>
          </el-button>
        </div>
      </header>

      <div class="chat-body">
        <div class="left-pane">
          <div class="prompt-row">
            <el-tag
              v-for="item in quickPrompts"
              :key="item"
              class="prompt-tag"
              @click="sendMessage(item)"
            >
              {{ item }}
            </el-tag>
          </div>
          <div ref="messageListRef" class="message-list" @scroll="onScroll">
            <article v-for="message in panelMessages" :key="message.id" class="message" :class="`role-${message.role}`">
              <div v-if="message.role !== 'system'" class="avatar" :data-role="message.role">
                {{ avatarText(message.role) }}
              </div>
              <div class="message-main">
                <div class="meta">
                  <span class="role-label">{{ roleLabel(message.role) }}</span>
                  <span class="time">{{ formatTime(message.createdAt) }}</span>
                </div>
                <div class="bubble">
                  <span v-if="message.pending" class="typing-indicator">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                  </span>
                  <span v-else v-html="renderMessage(message.content)" />
                </div>
                <div v-if="message.card?.type === 'contact_card'" class="card-inline">
                  <div class="card-grid">
                    <div class="card-field">
                      <span class="card-k">{{ t("wechat") }}</span>
                      <span class="card-v">{{ message.card.wechat }}</span>
                    </div>
                    <div class="card-field">
                      <span class="card-k">{{ t("phone") }}</span>
                      <span class="card-v">{{ message.card.phone }}</span>
                    </div>
                  </div>
                  <div class="card-actions">
                    <el-button size="small" @click="copyAndToast(message.card.wechat)">{{ t("copyWechat") }}</el-button>
                    <el-button size="small" @click="copyAndToast(message.card.phone)">{{ t("copyPhone") }}</el-button>
                    <el-popover trigger="hover" width="200">
                      <template #reference>
                        <el-button size="small">{{ t("qrCode") }}</el-button>
                      </template>
                      <img class="qr-img" :src="message.card.qrcodeUrl" :alt="t('qrCode')">
                    </el-popover>
                  </div>
                </div>
                <div v-if="message.role === 'ai'" class="feedback-row">
                  <div class="feedback-left">
                    <el-button
                      text
                      size="small"
                      :type="message.feedback === 'up' ? 'primary' : undefined"
                      @click="store.setFeedback(message.id, 'up')"
                    >
                      {{ t("useful") }}
                    </el-button>
                    <el-button
                      text
                      size="small"
                      :type="message.feedback === 'down' ? 'danger' : undefined"
                      @click="store.setFeedback(message.id, 'down')"
                    >
                      {{ t("useless") }}
                    </el-button>
                  </div>
                  <div class="msg-actions">
                    <el-tooltip content="引用" placement="top">
                      <el-button class="action-btn" text circle size="small" @click="quoteMessage(message.content)">
                        <el-icon><ChatSquare /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="复制" placement="top">
                      <el-button class="action-btn" text circle size="small" @click="copyAndToast(message.content)">
                        <el-icon><DocumentCopy /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="删除" placement="top">
                      <el-button class="action-btn" text circle size="small" @click="handleDeleteMessage(message.id)">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>
                <!-- 引用来源 -->
                <div v-if="message.citations?.length" class="citations-row">
                  <div class="citations-header">
                    <el-icon><Link /></el-icon>
                    <span>参考来源</span>
                  </div>
                  <div class="citations-list">
                    <a
                      v-for="(citation, index) in message.citations"
                      :key="index"
                      :href="citation.source"
                      target="_blank"
                      class="citation-item"
                      :title="citation.doc_title"
                    >
                      <span class="citation-index">{{ index + 1 }}</span>
                      <span class="citation-title">{{ citation.doc_title }}</span>
                      <el-icon class="citation-link"><TopRight /></el-icon>
                    </a>
                  </div>
                </div>
                <div v-if="message.error" class="error-actions">
                  <el-button text type="danger" size="small" @click="sendMessage(message.content)">{{ t("retry") }}</el-button>
                </div>
              </div>
            </article>
            <p v-if="errorText" class="error-line">{{ errorText }}</p>
          </div>
          <div class="composer-box">
            <div v-show="store.quotedMessage" class="quote-preview">
              <div class="quote-content">{{ store.quotedMessage }}</div>
              <el-icon class="quote-close" @click="store.clearQuote()"><Close /></el-icon>
            </div>
            <el-input
              v-model="input"
              type="textarea"
              :rows="3"
              :placeholder="t('placeholder')"
              @keydown.enter="onEnter"
              @paste="onPaste"
              class="composer-input"
            />
            <div class="composer-row">
              <div class="toolbar">
                <el-tooltip :content="t('toolEmoji')" placement="top">
                  <el-popover trigger="click" width="180">
                    <template #reference>
                      <el-button class="tool-btn" text circle aria-label="emoji">
                        <el-icon>
                          <MagicStick />
                        </el-icon>
                      </el-button>
                    </template>
                    <div class="emoji-list">
                      <button @click="useEmoji('😀')">😀</button>
                      <button @click="useEmoji('👍')">👍</button>
                      <button @click="useEmoji('📚')">📚</button>
                    </div>
                  </el-popover>
                </el-tooltip>
                <el-tooltip :content="t('toolUpload')" placement="top">
                  <label class="tool-btn upload-label" aria-label="upload">
                    <el-icon>
                      <Upload />
                    </el-icon>
                    <input type="file" @change="onFiles(($event.target as HTMLInputElement).files)">
                  </label>
                </el-tooltip>
                <el-tooltip :content="t('toolExport')" placement="top">
                  <el-button class="tool-btn" text circle aria-label="export" @click="exportChat">
                    <el-icon>
                      <Download />
                    </el-icon>
                  </el-button>
                </el-tooltip>
              </div>
              <el-button type="primary" :loading="streaming" @click="sendMessage()">{{ t("send") }}</el-button>
            </div>
          </div>
        </div>

        <aside class="right-pane">
          <template v-if="store.serviceMode === 'AI'">
            <el-card class="side-card" shadow="never">
              <template #header>
                <span class="side-title">{{ t("aboutTitle") }}</span>
              </template>
              <p class="side-text">{{ t("aboutContent") }}</p>
            </el-card>
            <el-card class="side-card" shadow="never">
              <template #header>
                <span class="side-title">{{ t("faqTitle") }}</span>
              </template>
              <ul class="side-list">
                <li>{{ t("faq1") }}</li>
                <li>{{ t("faq2") }}</li>
                <li>{{ t("faq3") }}</li>
              </ul>
            </el-card>
          </template>
          <template v-else>
            <el-card class="side-card" shadow="never">
              <template #header>
                <span class="side-title">{{ t("agentCard") }}</span>
              </template>
              <div class="agent-card">
                <div class="agent-avatar">人</div>
                <div class="agent-meta">
                  <p class="agent-line"><span class="agent-k">{{ t("agentName") }}</span><span class="agent-v">李晨</span></p>
                  <p class="agent-line"><span class="agent-k">{{ t("agentNo") }}</span><span class="agent-v">CS-2048</span></p>
                </div>
              </div>
              <div class="agent-actions">
                <el-button size="small" @click="copyAndToast('taoke-consult')">{{ t("copyWechat") }}</el-button>
                <el-button size="small" @click="copyAndToast('400-800-9000')">{{ t("copyPhone") }}</el-button>
                <el-popover trigger="hover" width="220">
                  <template #reference>
                    <el-button size="small">{{ t("qrCode") }}</el-button>
                  </template>
                  <img
                    class="qr-img"
                    src="https://dummyimage.com/180x180/ff5a00/ffffff.png&text=Taoke+CS"
                    :alt="t('qrCode')"
                  >
                </el-popover>
              </div>
            </el-card>
          </template>
        </aside>
      </div>
    </section>
  </div>
</template>
