/**
 * i18n.js (Barrel Re-export)
 * --------------------------
 * Re-export tu tang context/AppContexts.js va utils/i18nHelpers.js.
 */
export { getInitialLang, saveLang, LangContext, useLang } from "./context/AppContexts";
export { GENRE_MAP_VI, genreLabel, translateBackendText } from "./utils/i18nHelpers";
