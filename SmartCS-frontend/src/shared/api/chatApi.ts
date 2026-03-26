import type { AppLocale } from "@/shared/i18n/messages";
import type { ChatCard } from "@/shared/types/chat";

// 关键：使用相对路径，让 nginx 反向代理到后端
// 本地开发时 VITE_API_BASE_URL=http://localhost:8000
// 生产环境 VITE_API_BASE_URL 为空，使用相对路径 /
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "";
const INTERNAL_SECRET = (import.meta.env.VITE_INTERNAL_SECRET as string | undefined)?.trim() || "your-internal-secret-key";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export interface SendMessageParams {
  content: string;
  visitorId: string;
  sessionId: string | null;
  pageContext: string;
  locale: AppLocale;
  userMessageId: string;    // 前端生成的用户消息 ID
  aiMessageId: string;      // 前端预分配的 AI 消息 ID
}

export interface Citation {
  source: string;
  doc_title: string;
  score: number;
}

export interface StreamHandler {
  onToken: (token: string) => void;
  onCard: (card: ChatCard) => void;
  onSession: (sessionId: string) => void;
  onCitations: (citations: Citation[]) => void;
  onDone: () => void;
  onError: () => void;
}

export interface StreamResult {
  sessionId: string | null;
}

interface BackendSession {
  id: string;
}

const buildHeaders = (accept = "application/json") => {
  if (!INTERNAL_SECRET) {
    throw new Error("缺少 VITE_INTERNAL_SECRET 配置");
  }
  return {
    "Content-Type": "application/json",
    Accept: accept,
    "X-Internal-Secret": INTERNAL_SECRET
  };
};

const parseEventBlock = (block: string) => {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (!line.startsWith("data:")) {
      continue;
    }
    let payload = line.slice(5);
    if (payload.startsWith(" ")) {
      payload = payload.slice(1);
    }
    dataLines.push(payload);
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: dataLines.join("\n")
  };
};

const resolveLatestSessionId = async (visitorId: string): Promise<string | null> => {
  const response = await fetch(`${API_BASE_URL}/internal/chat/sessions?guest_id=${encodeURIComponent(visitorId)}`, {
    method: "GET",
    headers: buildHeaders()
  });
  if (!response.ok) {
    return null;
  }
  const sessions = (await response.json()) as unknown;
  if (!Array.isArray(sessions)) {
    return null;
  }
  const latest = sessions[0] as BackendSession | undefined;
  if (!latest || typeof latest.id !== "string") {
    return null;
  }
  return latest.id;
};

export const sendMessageStream = async (params: SendMessageParams, handlers: StreamHandler) => {
  let doneDispatched = false;
  const requestSessionId = params.sessionId && UUID_PATTERN.test(params.sessionId) ? params.sessionId : null;

  try {
    const response = await fetch(`${API_BASE_URL}/internal/chat/stream`, {
      method: "POST",
      headers: buildHeaders("text/event-stream"),
      body: JSON.stringify({
        query: params.content,
        guest_id: params.visitorId,
        session_id: requestSessionId,
        user_message_id: params.userMessageId,
        ai_message_id: params.aiMessageId
      })
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP_${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });

      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const parsed = parseEventBlock(block.trim());
        if (!parsed) {
          continue;
        }
        // session 事件：获取 session_id，不输出到聊天框
        if (parsed.event === "session") {
          try {
            const data = JSON.parse(parsed.data);
            if (data.session_id) {
              handlers.onSession(data.session_id);
            }
          } catch {}
          continue;
        }
        // citations 事件：获取引用来源，不输出到聊天框
        if (parsed.event === "citations") {
          try {
            const citations = JSON.parse(parsed.data);
            if (Array.isArray(citations)) {
              handlers.onCitations(citations);
            }
          } catch {}
          continue;
        }
        // done 事件
        if (parsed.data === "[DONE]") {
          doneDispatched = true;
          handlers.onDone();
          continue;
        }
        // 普通文本块（event === "message"）
        if (parsed.data) {
          handlers.onToken(parsed.data);
        }
      }
    }

    if (!doneDispatched) {
      handlers.onDone();
    }

    const resolvedSessionId = requestSessionId ?? (await resolveLatestSessionId(params.visitorId));
    return { sessionId: resolvedSessionId } satisfies StreamResult;
  } catch {
    handlers.onError();
    return { sessionId: requestSessionId } satisfies StreamResult;
  }
};


/**
 * 提交消息反馈（有用/无用）
 */
export const submitFeedback = async (messageId: string, feedbackType: "up" | "down", reason?: string): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/internal/chat/feedback`, {
      method: "POST",
      headers: buildHeaders(),
      body: JSON.stringify({
        message_id: messageId,
        feedback_type: feedbackType,
        reason: reason
      })
    });

    if (!response.ok) {
      return false;
    }

    const result = await response.json();
    return result.success === true;
  } catch {
    return false;
  }
};
