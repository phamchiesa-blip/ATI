import { useEffect, useRef, useState } from "react";
import { api, getToken, setToken } from "./api";
import Auth from "./Auth";
import Onboarding from "./Onboarding";
import Browse, { presetBrowse } from "./Browse";
import Taste from "./Taste";
import TrailerModal from "./Trailer";
import Recommend from "./Recommend";
import Detail from "./Detail";
import Toast from "./Toast";
import { Notice, TrailerContext } from "./ui";

const parseRoute = () => {
  const m = window.location.hash.match(/^#\/movie\/(\d+)/);
  return m ? Number(m[1]) : null;
};

export default function App() {
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
  const started = useRef(false);
  const ratedCount = useRef(0);

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
      title: "Muốn lưu gợi ý của bạn?",
      text: "Đăng nhập hoặc đăng ký để giữ lại các phim đã đánh giá cho lần sau.",
      duration: 9000,
      action: { label: "Đăng nhập / Đăng ký", onClick: () => openAuth("register") },
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
      title: `Chào mừng, ${u.name}!`,
      text:
        mode === "register"
          ? "Tài khoản đã sẵn sàng, gợi ý của bạn sẽ được lưu lại."
          : "Rất vui được gặp lại bạn.",
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

  const restart = async () => {
    if (!window.confirm("Xóa các phim đã đánh giá và thể loại đã chọn để bắt đầu lại?")) return;
    await api.resetProfile().catch(() => {});
    setRated({});
    setUser((u) => ({ ...u, onboarded: false }));
    setView("main");
    setRev((v) => v + 1);
    window.location.hash = "";
    notify({ kind: "info", title: "Đã xóa hồ sơ sở thích", text: "Bạn có thể chọn thể loại để bắt đầu lại.", duration: 4000 });
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
        notify({ kind: "error", title: "Chưa lưu được đánh giá", text: "Hãy thử lại sau ít giây.", duration: 4000 });
      }
    }
    setRev((v) => v + 1);
  };

  const toastEl = <Toast toast={toast} onClose={closeToast} />;

  if (booting) return <p className="p-10 text-mute">Đang tải...</p>;
  if (offline || !user) {
    return (
      <main className="mx-auto max-w-md px-5 py-16">
        <Notice
          title="Chưa kết nối được máy chủ"
          action={
            <button
              onClick={() => {
                setBooting(true);
                startSession();
              }}
              className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white"
            >
              Thử lại
            </button>
          }
        >
          Hãy kiểm tra lệnh uvicorn api:app --reload đang chạy.
        </Notice>
      </main>
    );
  }

  if (view === "auth") {
    return (
      <>
        <Auth initialMode={authMode} onBack={() => setView("main")} onDone={authDone} />
        {toastEl}
      </>
    );
  }

  const tabBtn = (id, label, active, onClick) => (
    <button
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
        active ? "bg-ink text-white" : "hover:bg-ink/5"
      }`}
    >
      {label}
    </button>
  );
  const ghost = "rounded-full px-3 py-1.5 font-semibold ring-1 ring-ink/20 hover:bg-ink/5";
  const inMain = view === "main" && !movieId;

  return (
    <TrailerContext.Provider value={setTrailerMovie}>
      <header className="sticky top-0 z-10 border-b border-ink/10 bg-paper/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
          <span className="font-display text-2xl font-extrabold">Gu Phim</span>
          <nav className="flex flex-wrap gap-1">
            {tabBtn("recommend", "Dành cho bạn", inMain && tab === "recommend", () => goTab("recommend"))}
            {tabBtn("browse", "Khám phá", inMain && tab === "browse", () => goTab("browse"))}
            {tabBtn("taste", "Gu của bạn", inMain && tab === "taste", () => goTab("taste"))}
            {tabBtn("genres", user.onboarded ? "Đổi thể loại" : "Chọn thể loại", view === "genres", () => {
              setView("genres");
              if (window.location.hash) window.location.hash = "";
            })}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-3 text-sm">
            {user.guest ? (
              <>
                <span className="rounded-full bg-lemon/60 px-3 py-1 font-semibold">Khách</span>
                <button onClick={() => openAuth("login")} className={ghost}>
                  Đăng nhập
                </button>
                <button
                  onClick={() => openAuth("register")}
                  className="rounded-full bg-cobalt px-4 py-1.5 font-semibold text-white hover:bg-cobalt/90"
                >
                  Đăng ký
                </button>
              </>
            ) : (
              <>
                <span className="text-mute">Xin chào, {user.name}</span>
                <button onClick={restart} className={ghost}>
                  Làm lại từ đầu
                </button>
                <button onClick={logout} className={ghost}>
                  Đăng xuất
                </button>
              </>
            )}
          </div>
        </div>
      </header>

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
      ) : tab === "taste" ? (
        <Taste rev={rev} onBrowse={() => goTab("browse")} />
      ) : (
        <Browse rated={rated} onRate={rate} />
      )}

      <TrailerModal movie={trailerMovie} onClose={() => setTrailerMovie(null)} />
      {toastEl}
    </TrailerContext.Provider>
  );
}