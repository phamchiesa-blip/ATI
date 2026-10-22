// Mọi lời gọi tới backend nằm ở đây. Đổi địa chỉ API bằng biến VITE_API_URL nếu cần.
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "gu-phim-token";

export const OFFLINE_MSG =
  "Chưa kết nối được máy chủ. Hãy kiểm tra lệnh uvicorn api:app --reload đang chạy.";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) =>
  t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Lỗi");
    this.status = status;
    this.detail = detail;
  }
}

async function req(path, opts = {}) {
  const token = getToken();
  let res;
  try {
    res = await fetch(BASE + path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    throw new ApiError(0, OFFLINE_MSG);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // Phiên hết hạn: xóa token và báo cho App quay về trang đăng nhập
    if (res.status === 401 && token && !path.startsWith("/api/auth/")) {
      setToken(null);
      window.dispatchEvent(new Event("auth-expired"));
    }
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

const post = (path, data) => req(path, { method: "POST", body: JSON.stringify(data) });

export const api = {
  // Tài khoản (khách cũng là một tài khoản tạm; đăng ký sẽ nâng cấp tài khoản khách)
  guest: async () => {
    const r = await post("/api/auth/guest", {});
    setToken(r.token);
    return r.user;
  },
  register: async (email, password, name, accept_terms) => {
    const r = await post("/api/auth/register", { email, password, name, accept_terms });
    setToken(r.token);
    return r.user;
  },
  login: async (email, password) => {
    const r = await post("/api/auth/login", { email, password });
    setToken(r.token);
    return r.user;
  },
  me: () => req("/api/auth/me"),
  logout: () => post("/api/auth/logout", {}),

  // Phim
  genres: () => req("/api/genres"),
  showcase: (n = 12) => req(`/api/showcase?n=${n}`),
  movies: (params = {}) => {
    const q = new URLSearchParams({ page_size: 24 });
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") q.set(k, v);
    });
    return req(`/api/movies?${q}`);
  },
  suggest: (q) => req(`/api/suggest?q=${encodeURIComponent(q)}`),
  trailer: (id) => req(`/api/movies/${id}/trailer`),
  movie: (id) => req(`/api/movies/${id}`),
  similar: (id, k = 8) => req(`/api/movies/${id}/similar?k=${k}`),

  // Hồ sơ sở thích
  getOnboarding: () => req("/api/onboarding"),
  onboarding: (genres, favorite_movie_ids = []) =>
    post("/api/onboarding", { genres, favorite_movie_ids }),
  feedback: (movie_id, action) => post("/api/feedback", { movie_id, action }),
  recommendations: (k = 13, mode = "proposed") => req(`/api/recommendations?k=${k}&mode=${mode}`),
  history: () => req("/api/history"),
  resetProfile: () => req("/api/me/profile", { method: "DELETE" }),
};