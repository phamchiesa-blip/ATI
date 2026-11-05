/**
 * components/Navbar.jsx
 * ---------------------
 * Thanh dieu huong tren cung (Header) va chan trang (Footer) cua ung dung Gu Phim.
 */
import { Globe, Moon, Sun } from "lucide-react";
import { useLang } from "../context/AppContexts";

export function ThemeLangControls({ theme, toggleTheme, toggleLang }) {
  const { lang, tr } = useLang();
  return (
    <>
      <button
        type="button"
        onClick={toggleTheme}
        title={theme === "dark" ? tr("Chế độ sáng", "Light mode") : tr("Chế độ tối", "Dark mode")}
        aria-label={
          theme === "dark"
            ? tr("Chuyển sang chế độ sáng", "Switch to light mode")
            : tr("Chuyển sang chế độ tối", "Switch to dark mode")
        }
        className="inline-flex items-center justify-center rounded-full bg-white p-2 ring-1 ring-ink/20 transition-colors hover:bg-cobalt hover:text-white hover:ring-cobalt"
      >
        {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
      </button>
      <button
        type="button"
        onClick={toggleLang}
        title={tr(
          "Chuyển sang Tiếng Anh (Switch to English)",
          "Chuyển sang Tiếng Việt (Switch to Vietnamese)"
        )}
        aria-label={tr("Đổi ngôn ngữ sang Tiếng Anh", "Switch language to Vietnamese")}
        className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-bold ring-1 ring-ink/20 transition-colors hover:bg-cobalt hover:text-white hover:ring-cobalt"
      >
        <Globe size={14} />
        <span>{lang === "vi" ? "VI · EN" : "EN · VI"}</span>
      </button>
    </>
  );
}

export function Navbar({
  user,
  view,
  tab,
  movieId,
  watchlistCount,
  theme,
  toggleTheme,
  toggleLang,
  goTab,
  onPickGenres,
  openAuth,
  restart,
  logout,
}) {
  const { tr } = useLang();
  const inMain = view === "main" && !movieId;
  const ghost = "rounded-full px-3 py-1.5 font-semibold ring-1 ring-ink/20 hover:bg-ink/5";

  const tabBtn = (id, label, active, onClick) => (
    <button
      key={id}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`shrink-0 whitespace-nowrap rounded-full px-3 py-2 text-sm font-semibold transition-colors xl:px-4 ${
        active ? "bg-ink text-white" : "hover:bg-ink/5"
      }`}
    >
      {label}
    </button>
  );

  return (
    <header className="sticky top-0 z-10 border-b border-ink/10 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1500px] items-center gap-x-4 px-5 py-3 xl:gap-x-6">
        <span className="shrink-0 whitespace-nowrap font-display text-2xl font-extrabold">
          Gu Phim
        </span>
        <nav className="flex min-w-0 flex-nowrap gap-1 overflow-x-auto [scrollbar-width:none]">
          {tabBtn(
            "recommend",
            tr("Dành cho bạn", "For You"),
            inMain && tab === "recommend",
            () => goTab("recommend")
          )}
          {tabBtn("browse", tr("Khám phá", "Explore"), inMain && tab === "browse", () =>
            goTab("browse")
          )}
          {tabBtn(
            "tonight",
            tr("Hôm nay xem gì?", "What to Watch?"),
            inMain && tab === "tonight",
            () => goTab("tonight")
          )}
          {tabBtn(
            "watch",
            `${tr("Xem sau", "Watchlist")}${watchlistCount ? ` (${watchlistCount})` : ""}`,
            inMain && tab === "watch",
            () => goTab("watch")
          )}
          {tabBtn("taste", tr("Gu của bạn", "Your Taste"), inMain && tab === "taste", () =>
            goTab("taste")
          )}
          {tabBtn(
            "genres",
            user.onboarded
              ? tr("Đổi thể loại", "Change Genres")
              : tr("Chọn thể loại", "Pick Genres"),
            view === "genres",
            onPickGenres
          )}
        </nav>
        <div className="ml-auto flex shrink-0 flex-nowrap items-center gap-2 whitespace-nowrap text-sm">
          <ThemeLangControls theme={theme} toggleTheme={toggleTheme} toggleLang={toggleLang} />
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
  );
}

export function Footer({ onOpenEval }) {
  const { tr } = useLang();
  return (
    <footer className="mx-auto mt-16 w-full max-w-[1500px] border-t border-ink/10 px-5 py-8 text-xs text-mute">
      <p>
        {tr(
          "Dữ liệu phim và hình ảnh từ TMDB. Sản phẩm này dùng TMDB API nhưng không được TMDB chứng nhận hay bảo trợ.",
          "Movie data and images from TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB."
        )}
      </p>
      <button onClick={onOpenEval} className="mt-2 font-semibold underline underline-offset-4">
        {tr("Đánh giá hệ thống", "System Evaluation")}
      </button>
    </footer>
  );
}

