import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/common.json";
import ko from "./locales/ko/common.json";
import ja from "./locales/ja/common.json";
import zh from "./locales/zh/common.json";

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { common: en },
      ko: { common: ko },
      ja: { common: ja },
      zh: { common: zh },
    },
    fallbackLng: "en",
    defaultNS: "common",
    interpolation: { escapeValue: false },
    detection: {
      order: ["querystring", "localStorage", "navigator"],
      caches: ["localStorage"],
      lookupQuerystring: "lang",
    },
  });

export default i18n;
