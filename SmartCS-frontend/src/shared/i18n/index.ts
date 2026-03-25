import { computed, ref } from "vue";
import type { AppLocale } from "@/shared/i18n/messages";
import { i18nMessages } from "@/shared/i18n/messages";

const LOCALE_KEY = "taoke-locale";
const fallbackLocale: AppLocale = "zh-CN";

const detectLocale = (): AppLocale => {
  const saved = localStorage.getItem(LOCALE_KEY) as AppLocale | null;
  if (saved === "zh-CN" || saved === "en-US") {
    return saved;
  }
  if (navigator.language === "en-US") {
    return "en-US";
  }
  return fallbackLocale;
};

const locale = ref<AppLocale>(detectLocale());

export const useI18n = () => {
  const t = (key: string) => i18nMessages[locale.value][key] ?? key;
  const setLocale = (next: AppLocale) => {
    locale.value = next;
    localStorage.setItem(LOCALE_KEY, next);
  };
  return {
    locale: computed(() => locale.value),
    setLocale,
    t
  };
};
