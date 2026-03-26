const VISITOR_KEY = "taoke-visitor-id";

const randomId = () => {
  const cryptoId = crypto?.randomUUID?.();
  if (cryptoId) {
    return cryptoId;
  }
  return `visitor-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export const ensureVisitorId = (): string => {
  try {
    const existing = localStorage.getItem(VISITOR_KEY);
    if (existing) {
      return existing;
    }
    const nextId = randomId();
    localStorage.setItem(VISITOR_KEY, nextId);
    return nextId;
  } catch {
    return randomId();
  }
};
