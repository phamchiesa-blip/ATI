/**
 * App.jsx (Clean Architecture Root Container)
 * -------------------------------------------
 * Dieu phoi trang thai phien nguoi dung, ngon ngu, giao dien sang/toi va dinh tuyen trang.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { api, getToken, setToken } from "./services/apiClient";
import {
  getInitialLang,
  LangContext,
  saveLang,
  TrailerContext,
  WatchlistContext,
} from "./context/AppContexts";
import { Footer, Navbar, ThemeLangControls } from "./components/Navbar";
import { Notice } from "./components/MovieCard";
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

const parseRoute = () => {
  const m = window.location.hash.match(/^#\/movie\/(\d+)/);
  return m ? Number(m[1]) : null;
};

export default function App() {
  const [lang, setLangState] = useState(getInitialLang);
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);
  const [offline, setOffline] = useState(false);
  const [view, setView] = useState("main"); // main | auth | genres
  const [authMode, setAuthMode] = useState("login");
  const [tab, setTab] = useState("recommend");
  const [movieId, setMovieId] = useState(parseRoute);
  const [rated, setRated] = useState({});
  const [rev, setRev] = useState(0);
  const [toast, setToast] = useState(null);
  const [trailerMovie, setTrailerMovie] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
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
    } catch {
      /* ignore */
    }
  }, [theme]);
  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  const notify = (t) => setToast({ id: Date.now() + Math.random(), duration: 5000, ...t });
  const closeToast = (id) => setToast((t) => (t && t.id === id ? null : t));

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

  useEffect(() => {
    const h = () => {
      setUser(null);
      setRated({});
      startSession();
    };
    window.addEventListener("auth-expired", h);
    return () => window.removeEventListener("auth-expired", h);
  }, []);

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

  const openBrowse = (patch) => {
    presetBrowse(patch);
    goTab("browse");
  };

  const openAuth = (mode) => {
    setAuthMode(mode);
    setView("auth");
  };

  const nudge = () =>
    notify({
      kind: "info",
      title: tr("Muốn lưu gợi ý của bạn?", "Want to save your recommendations?"),
      text: tr(
        "Đăng nhập hoặc đăng ký để giữ lại các phim đã đánh giá cho lần sau.",
        "Sign in or register to keep your rated movies for next time."
      ),
      duration: 9000,
      action: {
        label: tr("Đăng nhập / Đăng ký", "Sign in / Register"),
        onClick: () => openAuth("register"),
      },
    });

  const authDone = (u, mode) => {
    if (u.id !== user?.id) setRated({});
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
        text: tr(
          "Đã có lỗi xảy ra, vui lòng thử lại sau.",
          "An error occurred, please try again later."
        ),
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
        title:
          prev === "dislike"
            ? tr("Đã bỏ Không thích", "Removed dislike")
            : tr("Đã bỏ Thích", "Removed like"),
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

  const toggleSave = async (movie) => {
    const was = saved.has(movie.movie_id);
    setWatchlist((w) =>
      was
        ? w.filter((m) => m.movie_id !== movie.movie_id)
        : [{ ...movie, added_at: Date.now() / 1000 }, ...w]
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

  const toastEl = <Toast toast={toast} onClose={closeToast} />;

  if (booting) return <p className="p-10 text-mute">{tr("Đang tải...", "Loading...")}</p>;
  if (offline || !user) {
    return (
      <LangContext.Provider value={{ lang, setLang, tr }}>
        <main className="mx-auto max-w-md px-5 py-16">
          <div className="mb-4 flex justify-end gap-2">
            <ThemeLangControls theme={theme} toggleTheme={toggleTheme} toggleLang={toggleLang} />
          </div>
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
        <div className="mx-auto flex max-w-6xl justify-end gap-2 px-5 pt-4">
          <ThemeLangControls theme={theme} toggleTheme={toggleTheme} toggleLang={toggleLang} />
        </div>
        <Auth initialMode={authMode} onBack={() => setView("main")} onDone={authDone} />
        {toastEl}
      </LangContext.Provider>
    );
  }

  return (
    <LangContext.Provider value={{ lang, setLang, tr }}>
      <WatchlistContext.Provider value={{ saved, toggle: toggleSave }}>
        <TrailerContext.Provider value={setTrailerMovie}>
          <div className="flex min-h-screen flex-col">
            <Navbar
              user={user}
              view={view}
              tab={tab}
              movieId={movieId}
              watchlistCount={watchlist.length}
              theme={theme}
              toggleTheme={toggleTheme}
              toggleLang={toggleLang}
              goTab={goTab}
              onPickGenres={() => {
                setView("genres");
                if (window.location.hash) window.location.hash = "";
              }}
              openAuth={openAuth}
              restart={restart}
              logout={logout}
            />

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
                <Watchlist
                  items={watchlist}
                  rated={rated}
                  onRate={rate}
                  onBrowse={() => goTab("browse")}
                />
              ) : tab === "eval" ? (
                <Evaluation />
              ) : tab === "taste" ? (
                <Taste rev={rev} onBrowse={() => goTab("browse")} onUnrate={unrate} />
              ) : (
                <Browse rated={rated} onRate={rate} />
              )}
            </div>

            <Footer onOpenEval={() => goTab("eval")} />
          </div>

          <TrailerModal movie={trailerMovie} onClose={() => setTrailerMovie(null)} />
          {toastEl}
        </TrailerContext.Provider>
      </WatchlistContext.Provider>
    </LangContext.Provider>
  );
}
