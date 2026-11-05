/**
 * components/Poster.jsx
 * ---------------------
 * Component hien thi poster phim (anh TMDB hoac poster mau theo the loai),
 * kem SaveButton, RateButtons, RateIcons, Rating va CardButtons.
 */
import { useContext } from "react";
import { motion } from "framer-motion";
import { Bookmark, Play, Star, ThumbsDown, ThumbsUp } from "lucide-react";
import { TrailerContext, WatchlistContext, useLang } from "../context/AppContexts";
import { genreLabel } from "../utils/i18nHelpers";
import { movieHref, toneOf } from "../utils/theme";
import { useOverview } from "../hooks/useOverview";

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

export function SaveButton({ movie }) {
  const { saved, toggle } = useContext(WatchlistContext);
  const { tr } = useLang();
  const on = saved.has(movie.movie_id);
  const label = on
    ? tr("Bỏ khỏi Xem sau", "Remove from Watchlist")
    : tr("Lưu vào Xem sau", "Save to Watchlist");
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

export function Poster({ movie, size = "md", showTitle = true, inset = false, className = "" }) {
  const { lang, tr } = useLang();
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
          {movie.genres?.slice(0, big ? 3 : 2).map((g) => genreLabel(g, lang)).join(", ")}
        </p>
      </div>
    </div>
  );
}

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
        {status === "like"
          ? tr("Bạn đã thích", "You liked this")
          : tr("Bạn đã bỏ qua", "You passed on this")}
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
    <a
      href={movieHref(movie)}
      aria-label={tr(`Xem chi tiết ${movie.title}`, `View details for ${movie.title}`)}
      className="block"
    >
      <Poster movie={movie} {...props} />
    </a>
  );
}

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

