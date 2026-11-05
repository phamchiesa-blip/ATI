import { useEffect, useMemo, useRef, useState } from "react";
import { Globe, Moon, Sun } from "lucide-react";
import { api, getToken, setToken } from "./api";
import Auth from "./Auth";
import Onboarding from "./Onboarding";
import Browse, { presetBrowse } from "./Browse";
import Taste from "./Taste";
import Watchlist from "./Watchlist";
import Tonight from "./Tonight";
import Evaluation from "./Evaluation";
import TrailerModal from "./Trailer";
import Recommend from "./Recommend";
import Detail from "./Detail";
import Toast from "./Toast";
import { Notice, TrailerContext, WatchlistContext } from "./ui";
import { getInitialLang, LangContext, saveLang } from "./i18n";

const parseRoute = () => {
  const m = window.location.hash.match(/^#\/movie\/(\d+)/);
  return m ? Number(m[1]) : null;
};

export default function App() {
  const [lang, setLangState] = useState(getInitialLang);
  const [user, setUser] = useState(null); // luôn có user: khách hoặc tài khoản
  const [booting, setBooting] = useState(true);
  const [offline, setOffline] = useState(false);
  const [view, setView] = useState("main"); // main | auth | genres
  const [authMode, setAuthMode] = useState("login");
  const [tab, setTab] = useState("recommend");
  const [movieId, setMovieId] = useState(parseRoute); // trang chi tiết: #/movie/<id>
  const [rated, setRated] = useState({}); // { movie_id: "like" | "dislike" }
  const [rev, setRev] = useState(0); // tăng lên mỗi lần đánh giá để tải lại gợi ý
  const [toast, setToast] = useState(null);
  const [trailerMovie, setTrailerMovie] = useState(null);
  const [watchlist, setWatchlist] = useState([]); // phim đã lưu "Xem sau"
  const started = useRef(false);
  const ratedCount = useRef(0);

  const setLang = (nextLang) => {
    const val = nextLang === "en" ? "en" : "vi";
    setLangState(val);
    saveLang(val);
  };
  const toggleLang = () => setLang(lang === "vi" ? "en" : "vi");
  const tr = (vi, en) => (lang === "en" ? en : vi);

  const [theme, setTheme] = useState(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light"
  );
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("theme", theme);
    } catch {}
  }, [theme]);
  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  const notify = (t) => setToast({ id: Date.now() + Math.random(), duration: 5000, ...t });
  const closeToast = (id) => setToast((t) => (t && t.id === id ? null : t));

  // Khôi phục phiên cũ, hoặc tạo phiên khách mới để vào xem gợi ý ngay
  const startSession = async () => {
    setOffline(false);
    try {
      let u = null;
      if (getToken()) {
        try {
          u = await api.me();
        } catch (e) {
          if (e.status === 0) throw e;
          setToken(null);
        }
      }
      setUser(u ?? (await api.guest()));
    } catch {
      setOffline(true);
    } finally {
      setBooting(false);
    }
  };

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    startSession();
  }, []);

  // Phiên hết hạn giữa chừng: quay về phiên khách mới
  useEffect(() => {
    const h = () => {
      setUser(null);
      setRated({});
      startSession();
    };
    window.addEventListener("auth-expired", h);
    return () => window.removeEventListener("auth-expired", h);
  }, []);

  // Điều hướng bằng hash để nút Back của trình duyệt hoạt động
  useEffect(() => {
    const h = () => {
      setMovieId(parseRoute());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, []);

  useEffect(() => {
    if (!user) return;
    api
      .history()
      .then((r) => setRated(Object.fromEntries(r.items.map((m) => [m.movie_id, m.action]))))
      .catch(() => {});
  }, [user?.id]);

  useEffect(() => {
    if (!user) {
      setWatchlist([]);
      return;
    }
    api
      .watchlist()
      .then((r) => setWatchlist(r.items))
      .catch(() => {});
  }, [user?.id]);

  const goTab = (id) => {
    setView("main");
    setTab(id);
    if (window.location.hash) window.location.hash = "";
  };

  // Từ trang chi tiết: bấm tên đạo diễn / diễn viên / từ khóa -> Khám phá với bộ lọc đó
  const openBrowse = (patch) => {
    presetBrowse(patch);
    goTab("browse");
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setView("auth");
  };

  // Nhắc khách đăng nhập/đăng ký để lưu gợi ý (thỉnh thoảng, không làm phiền)
  const nudge = () =>
    notify({
      kind: "info",
      title: tr("Muốn lưu gợi ý của bạn?", "Want to save your recommendations?"),
      text: tr(
        "Đăng nhập hoặc đăng ký để giữ lại các phim đã đánh giá cho lần sau.",
        "Sign in or register to keep your rated movies for next time."
      ),
      duration: 9000,
      action: { label: tr("Đăng nhập / Đăng ký", "Sign in / Register"), onClick: () => openAuth("register") },
    });

  const authDone = (u, mode) => {
    if (u.id !== user?.id) setRated({}); // đăng nhập vào tài khoản khác: tải lại lịch sử
    setUser(u);
    setView("main");
    setTab("recommend");
    ratedCount.current = 0;
    setRev((v) => v + 1);
    window.location.hash = "";
    notify({
      kind: "welcome",
      title: tr(`Chào mừng, ${u.name}!`, `Welcome, ${u.name}!`),
      text:
        mode === "register"
          ? tr(
              "Tài khoản đã sẵn sàng, gợi ý của bạn sẽ được lưu lại.",
              "Your account is ready, and your recommendations will be saved."
            )
          : tr("Rất vui được gặp lại bạn.", "Glad to see you again."),
    });
  };

  const logout = async () => {
    await api.logout().catch(() => {});
    setToken(null);
    setUser(null);
    setRated({});
    setView("main");
    window.location.hash = "";
    setBooting(true);
    startSession();
  };

  const executeRestart = async () => {
    try {
      await api.resetProfile();
      setRated({});
      setUser((u) => ({ ...u, onboarded: false }));
      setView("main");
      setRev((v) => v + 1);
      window.location.hash = "";
      notify({
        kind: "info",
        title: tr("Đã làm lại từ đầu", "Profile reset"),
        text: tr(
          "Hồ sơ sở thích đã được xóa. Bạn có thể chọn lại thể loại yêu thích.",
          "Your taste profile has been cleared. You can pick your favorite genres again."
        ),
        duration: 4000,
      });
    } catch {
      notify({
        kind: "error",
        title: tr("Chưa xóa được hồ sơ", "Could not reset profile"),
        text: tr("Đã có lỗi xảy ra, vui lòng thử lại sau.", "An error occurred, please try again later."),
        duration: 4000,
      });
    }
  };

  const restart = () => {
    notify({
      kind: "warning",
      title: tr("Làm lại từ đầu?", "Start over?"),
      text: tr(
        "Xóa các phim đã đánh giá và thể loại đã chọn để bắt đầu lại?",
        "Clear all rated movies and selected genres to start over?"
      ),
      duration: 10000,
      actions: [
        {
          label: tr("Xác nhận làm lại", "Confirm reset"),
          primary: true,
          onClick: executeRestart,
        },
        {
          label: tr("Hủy", "Cancel"),
          onClick: () => {},
        },
      ],
    });
  };

  const rate = async (movie, action) => {
    setRated((r) => ({ ...r, [movie.movie_id]: action }));
    try {
      await api.feedback(movie.movie_id, action);
      if (user?.guest) {
        ratedCount.current += 1;
        const n = ratedCount.current;
        if (n === 3 || (n > 3 && (n - 3) % 6 === 0)) nudge();
      }
    } catch (e) {
      if (e.status !== 409) {
        setRated((r) => {
          const next = { ...r };
          delete next[movie.movie_id];
          return next;
        });
        notify({
          kind: "error",
          title: tr("Chưa lưu được đánh giá", "Could not save rating"),
          text: tr("Hãy thử lại sau ít giây.", "Please try again in a few seconds."),
          duration: 4000,
        });
      }
    }
    setRev((v) => v + 1);
  };

  const unrate = async (movie) => {
    const prev = rated[movie.movie_id];
    setRated((r) => {
      const next = { ...r };
      delete next[movie.movie_id];
      return next;
    });
    try {
      await api.unrate(movie.movie_id);
      notify({
        kind: "info",
        title: prev === "dislike" ? tr("Đã bỏ Không thích", "Removed dislike") : tr("Đã bỏ Thích", "Removed like"),
        text: movie.title,
        duration: 3000,
      });
    } catch (e) {
      if (e.status !== 404) {
        setRated((r) => ({ ...r, [movie.movie_id]: prev }));
        notify({
          kind: "error",
          title: tr("Chưa bỏ được đánh giá", "Could not remove rating"),
          text: tr("Hãy thử lại sau ít giây.", "Please try again in a few seconds."),
          duration: 4000,
        });
      }
    }
    setRev((v) => v + 1);
  };

  const saved = useMemo(() => new Set(watchlist.map((m) => m.movie_id)), [watchlist]);

  // Lưu / bỏ lưu phim: cập nhật giao diện ngay, lỗi thì hoàn lại
  const toggleSave = async (movie) => {
    const was = saved.has(movie.movie_id);
    setWatchlist((w) =>
      was ? w.filter((m) => m.movie_id !== movie.movie_id) : [{ ...movie, added_at: Date.now() / 1000 }, ...w]
    );
    try {
      await (was ? api.removeWatch(movie.movie_id) : api.addWatch(movie.movie_id));
    } catch {
      setWatchlist((w) => (was ? [movie, ...w] : w.filter((m) => m.movie_id !== movie.movie_id)));
      notify({
        kind: "error",
        title: tr("Chưa lưu được", "Could not save"),
        text: tr("Hãy thử lại sau ít giây.", "Please try again in a few seconds."),
        duration: 4000,
      });
    }
  };

  const langBtn = (
    <button
      type="button"
      onClick={toggleLang}
      title={tr("Chuyển sang Tiếng Anh (Switch to English)", "Chuyển sang Tiếng Việt (Switch to Vietnamese)")}
      aria-label={tr("Đổi ngôn ngữ sang Tiếng Anh", "Switch language to Vietnamese")}
      className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-bold ring-1 ring-ink/20 transition-colors hover:bg-cobalt hover:text-white hover:ring-cobalt"
    >
      <Globe size={14} />
      <span>{lang === "vi" ? "VI · EN" : "EN · VI"}</span>
    </button>
  );

  const themeBtn = (
    <button
      type="button"
      onClick={toggleTheme}
      title={theme === "dark" ? tr("Chế độ sáng", "Light mode") : tr("Chế độ tối", "Dark mode")}
      aria-label={theme === "dark" ? tr("Chuyển sang chế độ sáng", "Switch to light mode") : tr("Chuyển sang chế độ tối", "Switch to dark mode")}
      className="inline-flex items-center justify-center rounded-full bg-white p-2 ring-1 ring-ink/20 transition-colors hover:bg-cobalt hover:text-white hover:ring-cobalt"
    >
      {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  );

  const toastEl = <Toast toast={toast} onClose={closeToast} />;

  if (booting) return <p className="p-10 text-mute">{tr("Đang tải...", "Loading...")}</p>;
  if (offline || !user) {
    return (
      <LangContext.Provider value={{ lang, setLang, tr }}>
        <main className="mx-auto max-w-md px-5 py-16">
          <div className="mb-4 flex justify-end gap-2">{themeBtn}{langBtn}</div>
          <Notice
            title={tr("Chưa kết nối được máy chủ", "Cannot connect to server")}
            action={
              <button
                onClick={() => {
                  setBooting(true);
                  startSession();
                }}
                className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white"
              >
                {tr("Thử lại", "Retry")}
              </button>
            }
          >
            {tr(
              "Hãy kiểm tra lệnh uvicorn api:app --reload đang chạy.",
              "Please make sure uvicorn api:app --reload is running."
            )}
          </Notice>
        </main>
      </LangContext.Provider>
    );
  }

  if (view === "auth") {
    return (
      <LangContext.Provider value={{ lang, setLang, tr }}>
        <div className="mx-auto flex max-w-6xl justify-end gap-2 px-5 pt-4">{themeBtn}{langBtn}</div>
        <Auth initialMode={authMode} onBack={() => setView("main")} onDone={authDone} />
        {toastEl}
      </LangContext.Provider>
    );
  }

  const tabBtn = (id, label, active, onClick) => (
    <button
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`shrink-0 whitespace-nowrap rounded-full px-3 py-2 text-sm font-semibold transition-colors xl:px-4 ${
        active ? "bg-ink text-white" : "hover:bg-ink/5"
      }`}
    >
      {label}
    </button>
  );
  const ghost = "rounded-full px-3 py-1.5 font-semibold ring-1 ring-ink/20 hover:bg-ink/5";
  const inMain = view === "main" && !movieId;

  return (
    <LangContext.Provider value={{ lang, setLang, tr }}>
      <WatchlistContext.Provider value={{ saved, toggle: toggleSave }}>
        <TrailerContext.Provider value={setTrailerMovie}>
          <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-10 border-b border-ink/10 bg-paper/90 backdrop-blur">
            <div className="mx-auto flex max-w-[1500px] items-center gap-x-4 px-5 py-3 xl:gap-x-6">
              <span className="shrink-0 whitespace-nowrap font-display text-2xl font-extrabold">Gu Phim</span>
              <nav className="flex min-w-0 flex-nowrap gap-1 overflow-x-auto [scrollbar-width:none]">
                {tabBtn(
                  "recommend",
                  tr("Dành cho bạn", "For You"),
                  inMain && tab === "recommend",
                  () => goTab("recommend")
                )}
                {tabBtn("browse", tr("Khám phá", "Explore"), inMain && tab === "browse", () => goTab("browse"))}
                {tabBtn(
                  "tonight",
                  tr("Hôm nay xem gì?", "What to Watch?"),
                  inMain && tab === "tonight",
                  () => goTab("tonight")
                )}
                {tabBtn(
                  "watch",
                  `${tr("Xem sau", "Watchlist")}${watchlist.length ? ` (${watchlist.length})` : ""}`,
                  inMain && tab === "watch",
                  () => goTab("watch")
                )}
                {tabBtn("taste", tr("Gu của bạn", "Your Taste"), inMain && tab === "taste", () => goTab("taste"))}
                {tabBtn(
                  "genres",
                  user.onboarded ? tr("Đổi thể loại", "Change Genres") : tr("Chọn thể loại", "Pick Genres"),
                  view === "genres",
                  () => {
                    setView("genres");
                    if (window.location.hash) window.location.hash = "";
                  }
                )}
              </nav>
              <div className="ml-auto flex shrink-0 flex-nowrap items-center gap-2 whitespace-nowrap text-sm">
                {themeBtn}
                {langBtn}
                {user.guest ? (
                  <>
                    <span className="rounded-full bg-lemon/60 px-3 py-1 font-semibold">
                      {tr("Khách", "Guest")}
                    </span>
                    <button onClick={() => openAuth("login")} className={ghost}>
                      {tr("Đăng nhập", "Sign In")}
                    </button>
                    <button
                      onClick={() => openAuth("register")}
                      className="rounded-full bg-cobalt px-4 py-1.5 font-semibold text-white hover:bg-cobalt/90"
                    >
                      {tr("Đăng ký", "Sign Up")}
                    </button>
                  </>
                ) : (
                  <>
                    <span className="hidden text-mute 2xl:inline">
                      {tr(`Xin chào, ${user.name.split(" ")[0]}`, `Hi, ${user.name.split(" ")[0]}`)}
                    </span>
                    <button onClick={restart} className={ghost}>
                      {tr("Làm lại từ đầu", "Reset Profile")}
                    </button>
                    <button onClick={logout} className={ghost}>
                      {tr("Đăng xuất", "Sign Out")}
                    </button>
                  </>
                )}
              </div>
            </div>
          </header>

          <div className="flex-1">
          {view === "genres" ? (
            <Onboarding
              onCancel={() => setView("main")}
              onDone={() => {
                setUser((u) => ({ ...u, onboarded: true }));
                setView("main");
                setTab("recommend");
                setRev((v) => v + 1);
                if (user.guest) nudge();
              }}
            />
          ) : movieId ? (
            <Detail key={movieId} id={movieId} rated={rated} onRate={rate} onFilter={openBrowse} />
          ) : tab === "recommend" ? (
            <Recommend
              rev={rev}
              rated={rated}
              onRate={rate}
              onPickGenres={() => setView("genres")}
              onBrowse={() => goTab("browse")}
            />
          ) : tab === "tonight" ? (
            <Tonight rated={rated} onRate={rate} />
          ) : tab === "watch" ? (
            <Watchlist items={watchlist} rated={rated} onRate={rate} onBrowse={() => goTab("browse")} />
          ) : tab === "eval" ? (
            <Evaluation />
          ) : tab === "taste" ? (
            <Taste rev={rev} onBrowse={() => goTab("browse")} onUnrate={unrate} />
          ) : (
            <Browse rated={rated} onRate={rate} />
          )}
          </div>

          <footer className="mx-auto mt-16 w-full max-w-[1500px] border-t border-ink/10 px-5 py-8 text-xs text-mute">
            <p>
              {tr(
                "Dữ liệu phim và hình ảnh từ TMDB. Sản phẩm này dùng TMDB API nhưng không được TMDB chứng nhận hay bảo trợ.",
                "Movie data and images from TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB."
              )}
            </p>
            <button onClick={() => goTab("eval")} className="mt-2 font-semibold underline underline-offset-4">
              {tr("Đánh giá hệ thống", "System Evaluation")}
            </button>
          </footer>
          </div>

          <TrailerModal movie={trailerMovie} onClose={() => setTrailerMovie(null)} />
          {toastEl}
        </TrailerContext.Provider>
      </WatchlistContext.Provider>
    </LangContext.Provider>
  );
}
