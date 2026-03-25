import { computed, ref } from "vue";
import { defineStore } from "pinia";
import dayjs from "dayjs";
import type { ChatMessage, ChatSnapshot, ConnectionState, ServiceMode } from "@/shared/types/chat";
import { ensureVisitorId } from "@/shared/utils/visitor";

const STORAGE_KEY = "taoke-chat-snapshot";

const createId = () => crypto.randomUUID?.() ?? `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export const useChatStore = defineStore("chat", () => {
  const visitorId = ref(ensureVisitorId());
  const sessionId = ref<string | null>(null);
  const serviceMode = ref<ServiceMode>("AI");
  const connectionState = ref<ConnectionState>("ONLINE");
  const messages = ref<ChatMessage[]>([]);
  const historyIndex = ref(0);
  const quotedMessage = ref<string>("");

  const setQuote = (text: string) => {
    quotedMessage.value = text;
  };

  const clearQuote = () => {
    quotedMessage.value = "";
  };

  const appendMessage = (payload: Omit<ChatMessage, "id" | "createdAt">) => {
    const message: ChatMessage = {
      id: createId(),
      createdAt: dayjs().toISOString(),
      ...payload
    };
    messages.value.push(message);
    persist();
    return message.id;
  };

  const patchMessage = (id: string, updater: Partial<ChatMessage>) => {
    const target = messages.value.find((item) => item.id === id);
    if (!target) {
      return;
    }
    Object.assign(target, updater);
    persist();
  };

  const setFeedback = (id: string, feedback: "up" | "down") => {
    patchMessage(id, { feedback });
  };

  const deleteMessage = (id: string) => {
    const index = messages.value.findIndex((item) => item.id === id);
    if (index !== -1) {
      messages.value.splice(index, 1);
      persist();
    }
  };

  const switchMode = (mode: ServiceMode) => {
    serviceMode.value = mode;
    persist();
  };

  const setConnection = (state: ConnectionState) => {
    connectionState.value = state;
  };

  const setSessionId = (value: string | null) => {
    sessionId.value = value;
    persist();
  };

  const persist = () => {
    const snapshot: ChatSnapshot = {
      sessionId: sessionId.value,
      messages: messages.value
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  };

  const restore = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return false;
      }
      const snapshot = JSON.parse(raw) as ChatSnapshot;
      sessionId.value = typeof snapshot.sessionId === "string" ? snapshot.sessionId : null;
      messages.value = Array.isArray(snapshot.messages) ? snapshot.messages : [];
      historyIndex.value = messages.value.length;
      return true;
    } catch {
      return false;
    }
  };

  const clear = () => {
    messages.value = [];
    sessionId.value = null;
    localStorage.removeItem(STORAGE_KEY);
  };

  const canLoadOlder = computed(() => historyIndex.value > 0);

  const loadOlder = (pageSize = 10) => {
    const start = Math.max(0, historyIndex.value - pageSize);
    const chunk = messages.value.slice(start, historyIndex.value);
    historyIndex.value = start;
    return chunk;
  };

  return {
    visitorId,
    sessionId,
    serviceMode,
    connectionState,
    messages,
    appendMessage,
    patchMessage,
    setFeedback,
    deleteMessage,
    switchMode,
    setConnection,
    setSessionId,
    restore,
    clear,
    canLoadOlder,
    loadOlder,
    quotedMessage,
    setQuote,
    clearQuote
  };
});
