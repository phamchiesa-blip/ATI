import { createContext, useContext, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { Bookmark, Play, Star, ThumbsDown, ThumbsUp } from "lucide-react";
import { translateBackendText, useLang } from "./i18n";
import { api } from "./api";

// Tóm tắt phim theo ngôn ngữ đang chọn (tiếng Việt được dịch ở backend, cache lại ở client)
const overviewCache = new Map();
export function useOverview(movie) {
  const { lang } = useLang();
  const id = movie?.movie_id ?? movie?.id;
  const original = movie?.overview || "";
  const preset = movie?.overview_vi || null; // bản dịch sẵn backend gửi kèm
  const key = `${id}:${lang}`;
  const pick = () => (lang !== "vi" || !original ? original : preset ?? overviewCache.get(key) ?? null);
  const [text, setText] = useState(pick);
  useEffect(() => {
    const now = pick();
    setText(now);
    if (now !== null) return;
    let off = false;
    api
      .overview(id, "vi")
      .then((r) => {
        overviewCache.set(key, r.overview);
        if (!off) setText(r.overview);
      })
      .catch(() => !off && setText(original));
    return () => {
      off = true;
    };
  }, [key, original, preset]);
  return text; // null = đang dịch
}

export function Overview({ movie, className }) {
  const text = useOverview(movie);
  if (text === null) {
    return (
      <div className={className} aria-busy="true">
        <div className="animate-pulse space-y-2 py-1">
          <div className="h-3 w-full rounded bg-ink/10" />
          <div className="h-3 w-11/12 rounded bg-ink/10" />
          <div className="h-3 w-4/5 rounded bg-ink/10" />
        </div>
      </div>
    );
  }
  return <p className={className}>{text}</p>;
}

// Màu poster theo thể loại: [nền, chữ]
export const TONES = {
  Action: ["#FF7A59", "#2A0E06"],
  Adventure: ["#FFC83D", "#2B2200"],
  Animation: ["#6FD6C6", "#052B26"],
  Comedy: ["#FFE26B", "#312900"],
  Crime: ["#8EA2FF", "#0E1856"],
  Documentary: ["#9AD0EC", "#082A3D"],
  Drama: ["#F6A6C1", "#3A0F22"],
  Family: ["#B7E36B", "#1E2D06"],
  Fantasy: ["#C3A6FF", "#1F0F4D"],
  History: ["#D9B77E", "#2E2108"],
  Horror: ["#FF5D5D", "#2A0707"],
  Music: ["#FF9FD2", "#3A0A26"],
  Mystery: ["#7C6BD6", "#FFFFFF"],
  Romance: ["#FFB3C7", "#44101F"],
  "Science Fiction": ["#5B7CFF", "#FFFFFF"],
  Thriller: ["#3B4A6B", "#FFFFFF"],
  War: ["#A89F8A", "#1E1A10"],
  Western: ["#E39B5B", "#2E1505"],
};
const FALLBACK = ["#CBD5E1", "#0F172A"];
export const toneOf = (genre) => TONES[genre] ?? FALLBACK;

// Lưới phim: 2 cột trên điện thoại, tới 6 cột trên màn hình lớn
export const GRID =
  "grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6";

export function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

// Mở popup trailer từ bất kỳ thẻ phim nào (App cung cấp hàm này)
export const TrailerContext = createContext(() => {});

// Danh sách "Xem sau": App cung cấp tập phim đã lưu và hàm bật/tắt
export const WatchlistContext = createContext({ saved: new Set(), toggle: () => {} });

export function SaveButton({ movie }) {
  const { saved, toggle } = useContext(WatchlistContext);
  const { tr } = useLang();
  const on = saved.has(movie.movie_id);
  const label = on ? tr("Bỏ khỏi Xem sau", "Remove from Watchlist") : tr("Lưu vào Xem sau", "Save to Watchlist");
  return (
    <button
      onClick={() => toggle(movie)}
      aria-pressed={on}
      aria-label={label}
      title={label}
      className={`flex size-9 items-center justify-center rounded-full shadow-md transition-colors ${
        on ? "bg-lemon text-ink" : "bg-white text-ink hover:bg-paper"
      }`}
    >
      <Bookmark size={18} className={on ? "fill-current" : ""} />
    </button>
  );
}

export const movieHref = (m) => `#/movie/${m.movie_id}`;

// Có poster_url (TMDB) thì hiện ảnh thật; chưa có thì dùng poster chữ theo màu thể loại.
// `inset`: chừa chỗ phía dưới cho hai nút Thích / Không thích đặt đè lên poster.
export function Poster({ movie, size = "md", showTitle = true, inset = false, className = "" }) {
  const { tr } = useLang();
  if (movie.poster_url) {
    return (
      <img
        src={movie.poster_url}
        alt={tr(`Poster phim ${movie.title}`, `${movie.title} poster`)}
        loading="lazy"
        className={`aspect-[2/3] w-full rounded-xl bg-ink/10 object-cover ${className}`}
      />
    );
  }
  const [bg, fg] = toneOf(movie.genres?.[0]);
  const [bg2] = movie.genres?.[1] ? toneOf(movie.genres[1]) : [bg];
  const big = size === "lg";
  return (
    <div
      role="img"
      aria-label={tr(`Poster phim ${movie.title}`, `${movie.title} poster`)}
      className={`flex aspect-[2/3] w-full flex-col justify-between overflow-hidden rounded-xl ${
        big ? "p-5" : "p-3"
      } ${inset ? "pb-14" : ""} ${className}`}
      style={{ background: `linear-gradient(160deg, ${bg} 55%, ${bg2})`, color: fg }}
    >
      <span
        className="font-display leading-none font-extrabold opacity-30"
        style={{ fontSize: big ? "5rem" : "2rem" }}
      >
        {movie.release_year ?? ""}
      </span>
      <div>
        {showTitle && (
          <h3
            className={`font-display leading-[0.95] font-extrabold tracking-tight ${
              big ? "text-4xl" : "line-clamp-4 text-base"
            }`}
          >
            {movie.title}
          </h3>
        )}
        <p className={`${showTitle ? "mt-1.5" : ""} ${big ? "text-base" : "text-[11px]"} opacity-75`}>
          {movie.genres?.slice(0, big ? 3 : 2).join(", ")}
        </p>
      </div>
    </div>
  );
}

// Hai nút lớn (dùng ở trang chi tiết và khung nổi bật)
export function RateButtons({ status, onRate }) {
  const { tr } = useLang();
  if (status) {
    return (
      <motion.p
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`inline-flex items-center gap-2 text-sm font-semibold ${
          status === "like" ? "text-cobalt" : "text-mute"
        }`}
      >
        {status === "like" ? <ThumbsUp size={16} /> : <ThumbsDown size={16} />}
        {status === "like" ? tr("Bạn đã thích", "You liked this") : tr("Bạn đã bỏ qua", "You passed on this")}
      </motion.p>
    );
  }
  const base =
    "inline-flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-2 text-sm font-semibold transition-colors";
  return (
    <div className="flex gap-2">
      <motion.button
        whileTap={{ scale: 0.92 }}
        onClick={() => onRate("like")}
        className={`${base} bg-cobalt text-white hover:bg-cobalt/90`}
      >
        <ThumbsUp size={16} /> {tr("Thích", "Like")}
      </motion.button>
      <motion.button
        whileTap={{ scale: 0.92 }}
        onClick={() => onRate("dislike")}
        className={`${base} bg-white text-ink ring-1 ring-ink/15 hover:bg-ink/5`}
      >
        <ThumbsDown size={16} /> {tr("Không thích", "Dislike")}
      </motion.button>
    </div>
  );
}

// Hai nút tròn nhỏ đặt ở góc trái dưới của ô phim
export function RateIcons({ status, onRate }) {
  const { tr } = useLang();
  const locked = !!status;
  const btn = (action, Icon, label, activeCls) => {
    const active = status === action;
    return (
      <motion.button
        whileTap={locked ? undefined : { scale: 0.85 }}
        disabled={locked}
        aria-label={active ? `${label} (${tr("đã chọn", "selected")})` : label}
        aria-pressed={active}
        title={label}
        onClick={() => onRate(action)}
        className={`flex size-9 items-center justify-center rounded-full shadow-md transition-colors ${
          active ? activeCls : "bg-white text-ink"
        } ${locked && !active ? "opacity-40" : "hover:bg-paper"}`}
      >
        <Icon size={18} className={active ? "fill-current" : ""} />
      </motion.button>
    );
  };
  return (
    <div className="flex gap-2">
      {btn("like", ThumbsUp, tr("Thích", "Like"), "bg-cobalt text-white")}
      {btn("dislike", ThumbsDown, tr("Không thích", "Dislike"), "bg-ink text-white")}
    </div>
  );
}

export function Rating({ value }) {
  if (value == null) return null;
  return (
    <span className="inline-flex items-center gap-1 text-sm font-semibold">
      <Star size={14} className="fill-lemon stroke-ink" />
      {Number(value).toFixed(1)}
    </span>
  );
}

// Hai nút dưới ô phim: xem trailer (popup) và trang chi tiết
export function CardButtons({ movie }) {
  const openTrailer = useContext(TrailerContext);
  const { tr } = useLang();
  return (
    <div className="grid grid-cols-2 gap-2">
      <button
        onClick={() => openTrailer(movie)}
        className="inline-flex items-center justify-center gap-1.5 rounded-full bg-ink px-2 py-2 text-xs font-semibold text-white transition-colors hover:bg-ink/85"
      >
        <Play size={12} className="fill-white" /> Trailer
      </button>
      <a
        href={movieHref(movie)}
        className="inline-flex items-center justify-center rounded-full bg-white px-2 py-2 text-xs font-semibold ring-1 ring-ink/20 transition-colors hover:bg-ink/5"
      >
        {tr("Chi tiết", "Details")}
      </a>
    </div>
  );
}

export function PosterLink({ movie, ...props }) {
  const { tr } = useLang();
  return (
    <a href={movieHref(movie)} aria-label={tr(`Xem chi tiết ${movie.title}`, `View details for ${movie.title}`)} className="block">
      <Poster movie={movie} {...props} />
    </a>
  );
}

// Poster bấm được + hai icon Thích / Không thích ở góc trái dưới
export function PosterTile({ movie, status, onRate, className = "" }) {
  return (
    <div className="relative">
      <PosterLink movie={movie} inset className={className} />
      <div className="absolute bottom-2.5 left-2.5">
        <RateIcons status={status} onRate={(a) => onRate(movie, a)} />
      </div>
      <div className="absolute top-2.5 right-2.5">
        <SaveButton movie={movie} />
      </div>
    </div>
  );
}

// Popup xem nhanh khi rê chuột: hiện sau 0,35 giây, tự chọn bên trái/phải cho vừa màn hình
export function useHoverPreview() {
  const ref = useRef(null);
  const timer = useRef(0);
  const [pos, setPos] = useState(null);

  const hide = () => {
    clearTimeout(timer.current);
    setPos(null);
  };
  const show = () => {
    if (!window.matchMedia("(hover: hover)").matches) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      if (!ref.current) return;
      const r = ref.current.getBoundingClientRect();
      const W = 340;
      const H = 320;
      const fitsRight = r.right + 12 + W <= window.innerWidth - 8;
      setPos({
        left: fitsRight ? r.right + 12 : Math.max(8, r.left - 12 - W),
        top: Math.min(Math.max(8, r.top), Math.max(8, window.innerHeight - H - 8)),
      });
    }, 350);
  };

  useEffect(() => {
    if (!pos) return;
    const close = () => setPos(null);
    window.addEventListener("scroll", close, { passive: true });
    return () => window.removeEventListener("scroll", close);
  }, [pos]);
  useEffect(() => () => clearTimeout(timer.current), []);

  return { ref, pos, show, hide };
}

export function HoverPreview({ movie, pos }) {
  const { tr } = useLang();
  if (!pos) return null;
  return createPortal(
    <motion.div
      aria-hidden
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.15 }}
      className="pointer-events-none fixed z-40 flex w-[340px] gap-4 rounded-2xl bg-white p-4 shadow-2xl ring-1 ring-ink/10"
      style={{ left: pos.left, top: pos.top }}
    >
      <div className="w-24 shrink-0">
        <Poster movie={movie} showTitle={false} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-display text-lg leading-tight font-extrabold">{movie.title}</p>
        <p className="mt-1 flex items-center gap-3 text-sm text-mute">
          {movie.release_year && <span>{movie.release_year}</span>}
          <Rating value={movie.vote_average} />
        </p>
        <p className="mt-1.5 text-xs font-medium">{movie.genres?.join(", ")}</p>
        <Overview movie={movie} className="mt-2 line-clamp-5 text-xs leading-relaxed text-mute" />
        {movie.director && (
          <p className="mt-2 text-xs">
            <span className="text-mute">{tr("Đạo diễn ", "Director ")}</span>
            {movie.director}
          </p>
        )}
        {movie.cast?.length > 0 && (
          <p className="mt-1 line-clamp-2 text-xs">
            <span className="text-mute">{tr("Diễn viên ", "Cast ")}</span>
            {movie.cast.slice(0, 4).join(", ")}
          </p>
        )}
      </div>
    </motion.div>,
    document.body
  );
}

// Thẻ phim trong lưới: poster + icon Thích/Không thích, điểm, nút Trailer/Chi tiết, popup khi rê chuột
export function MovieCard({ movie, status, onRate, note }) {
  const { ref, pos, show, hide } = useHoverPreview();
  const { lang } = useLang();
  const displayNote = note ? translateBackendText(note, lang) : undefined;
  return (
    <article
      ref={ref}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) hide();
      }}
      className="flex flex-col gap-2.5"
    >
      <PosterTile movie={movie} status={status} onRate={onRate} />
      <div className="min-w-0">
        {movie.poster_url && <h3 className="truncate text-sm font-semibold">{movie.title}</h3>}
        <div className="mt-0.5 flex items-center gap-3">
          <Rating value={movie.vote_average} />
          {movie.release_year && <span className="text-xs text-mute">{movie.release_year}</span>}
        </div>
        {displayNote && <p className="mt-0.5 text-xs font-semibold text-cobalt">{displayNote}</p>}
      </div>
      <CardButtons movie={movie} />
      <HoverPreview movie={movie} pos={pos} />
    </article>
  );
}

export function Notice({ title, children, action }) {
  return (
    <div className="mx-auto max-w-md rounded-2xl bg-white p-8 text-center">
      <h2 className="font-display text-2xl font-extrabold">{title}</h2>
      <p className="mt-2 text-mute">{children}</p>
      {action}
    </div>
  );
}
