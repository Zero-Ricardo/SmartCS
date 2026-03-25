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
  id: string;
  role: SenderRole;
  content: string;
  createdAt: string;
  pending?: boolean;
  feedback?: "up" | "down";
  card?: ChatCard;
  citations?: Citation[];
  error?: string;
}

export interface ChatSnapshot {
  sessionId: string | null;
  messages: ChatMessage[];
}
