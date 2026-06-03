import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/common.json";
import ko from "./locales/ko/common.json";
import ja from "./locales/ja/common.json";
import zh from "./locales/zh/common.json";

// Figma copy is English — pin the UI language to English.
void i18n.use(initReactI18next).init({
  resources: {
    en: { common: en },
    ko: { common: ko },
    ja: { common: ja },
    zh: { common: zh },
  },
  lng: "en",
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
