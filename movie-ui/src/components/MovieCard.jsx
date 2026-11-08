/**
 * components/MovieCard.jsx
 * ------------------------
 * The phim trong luoi hien thi (MovieCard), kem popup xem nhanh (HoverPreview) va khung thong bao (Notice).
 */
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { useLang } from "../context/AppContexts";
import { genreLabel, translateBackendText } from "../utils/i18nHelpers";
import { useHoverPreview } from "../hooks/useHoverPreview";
import { CardButtons, Overview, Poster, PosterTile, Rating } from "./Poster";

export function HoverPreview({ movie, pos }) {
  const { lang, tr } = useLang();
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
        <p className="mt-1.5 text-xs font-medium">
          {movie.genres?.map((g) => genreLabel(g, lang)).join(", ")}
        </p>
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
      className="flex h-full flex-col gap-2.5"
    >
      <PosterTile movie={movie} status={status} onRate={onRate} />
      <div className="min-h-14 min-w-0">
        {movie.poster_url && <h3 className="truncate text-sm font-semibold">{movie.title}</h3>}
        <div className="mt-0.5 flex items-center gap-3">
          <Rating value={movie.vote_average} />
          {movie.release_year && <span className="text-xs text-mute">{movie.release_year}</span>}
        </div>
        {displayNote && <p className="mt-0.5 text-xs font-semibold text-cobalt">{displayNote}</p>}
      </div>
      <div className="mt-auto">
        <CardButtons movie={movie} />
      </div>
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

