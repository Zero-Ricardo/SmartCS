export type ServiceMode = "AI" | "HUMAN";
export type SenderRole = "user" | "ai" | "human" | "system";
export type ConnectionState = "ONLINE" | "RECONNECTING" | "OFFLINE";

export type ContactCard = {
  type: "contact_card";
  wechat: string;
  phone: string;
  qrcodeUrl: string;
};

export type CsatCard = {
  type: "csat_card";
  sessionId: string;
  scale: 5;
};

export type ChatCard = ContactCard | CsatCard;

export interface Citation {
  source: string;
  doc_title: string;
  score: number;
}

export interface ChatMessage {
  id: string;                    // 消息 ID（前端生成，后端使用）
  role: SenderRole;
  content: string;
  createdAt: string;
  pending?: boolean;
  feedback?: "up" | "down";
  card?: ChatCard;
  citations?: Citation[];
  error?: string;
  originalContent?: string;      // 用户原始发送的内容，用于重试
  userMessageId?: string;        // 对应的用户消息 ID，用于重试
}

export interface ChatSnapshot {
  sessionId: string | null;
  messages: ChatMessage[];
}
