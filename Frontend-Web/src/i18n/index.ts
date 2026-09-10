import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import de from "./de/translation.json";

/**
 * Single-language setup for now — only German ships. Resources are bundled
 * directly (no http backend/lazy loading) so translations resolve
 * synchronously on first render, in both the app and tests. Adding a
 * language later is just another `resources` entry plus a language
 * switch — no restructuring of call sites.
 */
void i18n.use(initReactI18next).init({
  resources: {
    de: { translation: de },
  },
  lng: "de",
  fallbackLng: "de",
  interpolation: {
    escapeValue: false, // React already escapes rendered text.
  },
});

export default i18n;
