/**
 * api.js (Barrel Re-export)
 * -------------------------
 * Re-export tu tang services/apiClient.js de dam bao tuong thich nguoc.
 */
export {
  OFFLINE_MSG,
  getToken,
  setToken,
  ApiError,
  api,
} from "./services/apiClient";
