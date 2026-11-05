/**
 * context/AppContexts.js
 * ----------------------
 * Clean Architecture - Application Context Layer.
 * Chua cac React Context dung chung giua cac tang giao dien:
 *   - LangContext (da ngon ngu VI / EN)
 *   - TrailerContext (mo popup trailer)
 *   - WatchlistContext (trang thai danh sach Xem sau)
 */
import { createContext, useContext } from "react";

const LANG_KEY = "gu-phim-lang";

export const getInitialLang = () => {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    return saved === "en" ? "en" : "vi";
  } catch {
    return "vi";
  }
};

export const saveLang = (lang) => {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    /* ignore */
  }
};

export const LangContext = createContext({
  lang: "vi",
  setLang: () => {},
  tr: (vi, _en) => vi,
});

export function useLang() {
  return useContext(LangContext);
}

export const TrailerContext = createContext(() => {});

export const WatchlistContext = createContext({
  saved: new Set(),
  toggle: () => {},
});

