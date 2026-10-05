import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "@/locales/en/common.json";
import th from "@/locales/th/common.json";

export const SUPPORTED_LANGUAGES = ["th", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

// A UI preference only — never a token (CLAUDE.md 6 forbids tokens in storage).
const LANGUAGE_KEY = "radius-manager.language";

function storedLanguage(): Language {
  try {
    const value = localStorage.getItem(LANGUAGE_KEY);
    return value === "th" || value === "en" ? value : "en";
  } catch {
    return "en";
  }
}

export function changeLanguage(language: Language): void {
  void i18n.changeLanguage(language);
  try {
    localStorage.setItem(LANGUAGE_KEY, language);
  } catch {
    // Storage unavailable (private mode) — the choice just won't persist.
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    th: { common: th },
    en: { common: en },
  },
  lng: storedLanguage(),
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
