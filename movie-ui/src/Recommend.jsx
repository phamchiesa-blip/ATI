import { useContext, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Play } from "lucide-react";
import { api } from "./services/apiClient";
import { GRID } from "./utils/theme";
import { HoverPreview, Notice } from "./components/MovieCard";
import { CardButtons, Overview, PosterLink, PosterTile, Rating, RateButtons } from "./components/Poster";
import { useHoverPreview } from "./hooks/useHoverPreview";
import { TrailerContext, useLang } from "./context/AppContexts";
import { genreLabel } from "./utils/i18nHelpers";

const reasonText = (m, coldStart, tr, lang = "vi", isHero = false) =>
  (coldStart || m.cold_start)
    ? (isHero
        ? tr(
            "Phim đang được yêu thích, hãy bấm Thích/Không thích để hệ thống hiểu gu của bạn",
            "Popular movie — click Like/Dislike so the system learns your taste"
          )
        : tr("Phim đang được yêu thích", "Popular right now"))
    : m.match_percent == null
      ? tr("Được nhiều người yêu thích", "Audience favorite")
      : m.reasons?.length
        ? tr(
            `Vì bạn thích ${m.reasons.map((r) => genreLabel(r, "vi")).join(", ")}`,
            `Because you like ${m.reasons.map((r) => genreLabel(r, "en")).join(", ")}`
          )
        : tr("Có nội dung gần với những phim bạn đã chọn", "Similar content to movies you selected");

const PARTS = [
  ["cosine", "Giống gu của bạn", "Matches your taste"],
  ["rating", "Điểm đánh giá", "Rating score"],
  ["popularity", "Độ phổ biến", "Popularity"],
  ["newness", "Độ mới", "Recency"],
  ["neural", "AI học từ Thích / Không thích", "Online AI learned from Like / Dislike"],
];

// Các thành phần cấu thành điểm gợi ý (module Ranking), thang 0-100 so với các phim ứng viên
function Breakdown({ data, coldStart }) {
  const { tr } = useLang();
  return (
    <ul className="mt-2 grid gap-2">
      {PARTS.filter(([k]) => data[k] != null && (!coldStart || k !== "cosine")).map(([k, labelVi, labelEn]) => {
        const v = Math.round(data[k] * 100);
        return (
          <li key={k}>
            <div className="flex justify-between text-xs">
              <span>{tr(labelVi, labelEn)}</span>
              <span className="text-mute">{v}</span>
            </div>
            <div className="mt-0.5 h-1 rounded-full bg-ink/10">
              <div className="h-full rounded-full bg-cobalt" style={{ width: `${v}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Hero({ movie, status, onRate, coldStart }) {
  const isCold = coldStart || Boolean(movie.cold_start);
  const openTrailer = useContext(TrailerContext);
  const { lang, tr } = useLang();
  return (
    <section className="grid items-center gap-8 rounded-3xl bg-white p-6 md:grid-cols-[280px_1fr] md:p-10">
      <PosterLink movie={movie} size="lg" showTitle={false} />
      <div className="max-w-xl">
        <h2 className="font-display text-4xl leading-tight font-extrabold md:text-5xl">
          <a href={`#/movie/${movie.movie_id}`} className="hover:text-cobalt">
            {movie.title}
          </a>
        </h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {movie.genres.map((g) => (
            <span key={g} className="rounded-full bg-paper px-3 py-1 text-sm font-medium">
              {genreLabel(g, lang)}
            </span>
          ))}
        </div>
        <Overview movie={movie} className="mt-4 line-clamp-4 leading-relaxed text-mute" />
        <p className="mt-4 text-sm font-medium">{reasonText(movie, isCold, tr, lang, true)}</p>

        <div className="mt-5 flex flex-wrap items-start gap-x-10 gap-y-4">
          {!isCold && movie.match_percent != null ? (
            <p className="flex items-baseline gap-2">
              <span className="font-display text-5xl font-extrabold text-cobalt">{movie.match_percent}%</span>
              <span className="text-sm text-mute">{tr("độ hợp", "match")}</span>
            </p>
          ) : (
            <Rating value={movie.vote_average} />
          )}
          {movie.breakdown && (
            <div className="min-w-56 flex-1">
              <p className="text-sm font-semibold">{tr("Vì sao gợi ý phim này?", "Why this recommendation?")}</p>
              <Breakdown data={movie.breakdown} coldStart={isCold} />
            </div>
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button
            onClick={() => openTrailer(movie)}
            className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 font-semibold text-white hover:bg-ink/85"
          >
            <Play size={16} className="fill-white" /> {tr("Xem trailer", "Watch trailer")}
          </button>
          <div className="min-w-60 flex-1 sm:max-w-sm">
            <RateButtons status={status} onRate={(a) => onRate(movie, a)} />
          </div>
        </div>
      </div>
    </section>
  );
}

// Poster + "cuống vé": độ hợp, lý do gợi ý và (nếu có) bảng điểm thành phần
function Ticket({ movie, min, max, status, onRate, coldStart }) {
  const isCold = coldStart || Boolean(movie.cold_start);
  const [why, setWhy] = useState(false);
  const { lang, tr } = useLang();
  const personal = !isCold && movie.match_percent != null;
  const width = max === min ? 100 : 35 + ((movie.match_percent - min) / (max - min)) * 65;
  const { ref, pos, show, hide } = useHoverPreview();

  return (
    <article
      ref={ref}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) hide();
      }}
      className="flex h-full flex-col"
    >
      <PosterTile movie={movie} status={status} onRate={onRate} className="rounded-b-none" />
      <div className="relative flex flex-1 flex-col rounded-b-xl bg-white p-3 ring-1 ring-ink/10">
        <span className="absolute inset-x-3 top-0 border-t border-dashed border-ink/30" />
        <span className="absolute top-0 -left-2 size-4 -translate-y-1/2 rounded-full bg-paper" />
        <span className="absolute top-0 -right-2 size-4 -translate-y-1/2 rounded-full bg-paper" />
        <div className="mt-1 flex min-h-11 flex-col justify-center">
          {personal ? (
            <>
            <p className="mt-1 flex items-baseline justify-between">
              <span className="font-display text-xl font-extrabold text-cobalt">{movie.match_percent}%</span>
              <span className="text-xs text-mute">{tr("độ hợp", "match")}</span>
            </p>
            <div className="mt-1 h-1.5 rounded-full bg-ink/10">
              <div className="h-full rounded-full bg-cobalt" style={{ width: `${width}%` }} />
            </div>
            </>
          ) : (
            <p>
              <Rating value={movie.vote_average} />
            </p>
          )}
        </div>
        <p className="mt-2 min-h-10 line-clamp-2 text-xs leading-snug text-mute">
          {reasonText(movie, isCold, tr, lang, false)}
        </p>
        <div className="mt-2 min-h-7">
          {movie.breakdown && (
            <button
              onClick={() => setWhy((v) => !v)}
              aria-expanded={why}
              className="mt-2 text-xs font-semibold text-cobalt underline underline-offset-4"
            >
              {why ? tr("Ẩn chi tiết", "Hide details") : tr("Vì sao gợi ý?", "Why recommended?")}
            </button>
          )}
          {why && (
            <div className="absolute inset-x-3 top-full z-20 rounded-xl bg-white p-3 shadow-xl ring-1 ring-ink/15">
              <Breakdown data={movie.breakdown} coldStart={isCold} />
            </div>
          )}
        </div>
      </div>
      <div className="mt-3">
        <CardButtons movie={movie} />
      </div>
      <HoverPreview movie={movie} pos={pos} />
    </article>
  );
}

const MODES = [
  ["proposed", "Gợi ý thông minh", "Smart picks"],
  ["baseline", "Phim tương tự", "Similar movies"],
];

export default function Recommend({ rev, rated, onRate, onPickGenres, onBrowse }) {
  const [items, setItems] = useState([]);
  const [personalized, setPersonalized] = useState(true);
  const [coldStart, setColdStart] = useState(false);
  const [mode, setMode] = useState("proposed");
  const [state, setState] = useState("loading");
  const { tr } = useLang();

  useEffect(() => {
    let off = false;
    api
      .recommendations(13, mode)
      .then((r) => {
        if (off) return;
        setItems(r.items);
        setPersonalized(r.personalized);
        setColdStart(Boolean(r.cold_start));
        setState("ok");
      })
      .catch(() => !off && setState("error"));
    return () => {
      off = true;
    };
  }, [rev, mode]);

  const isCold = coldStart || !personalized;
  const [hero, ...rest] = items;
  const pcts = rest.map((m) => m.match_percent).filter((p) => p != null);
  const min = pcts.length ? Math.min(...pcts) : 0;
  const max = pcts.length ? Math.max(...pcts) : 100;

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-extrabold">
            {!isCold ? tr("Dành cho bạn", "For You") : tr("Đang được yêu thích", "Popular Right Now")}
          </h1>
          {isCold && (
            <p className="mt-2 text-mute">
              {tr("Những phim nổi tiếng và được đánh giá cao.", "Well-known and highly rated movies.")}
            </p>
          )}
        </div>
        {!isCold && (
          <div>
            <div role="group" aria-label={tr("Cách gợi ý", "Recommendation mode")} className="inline-flex rounded-full bg-white p-1 ring-1 ring-ink/15">
              {MODES.map(([id, labelVi, labelEn]) => (
                <button
                  key={id}
                  onClick={() => setMode(id)}
                  aria-pressed={mode === id}
                  className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
                    mode === id ? "bg-ink text-white" : "hover:bg-ink/5"
                  }`}
                >
                  {tr(labelVi, labelEn)}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {state === "ok" && isCold && (
        <div className="mt-6 flex flex-wrap items-center gap-4 rounded-2xl bg-white p-5 ring-1 ring-ink/10">
          <p className="min-w-60 flex-1">
            <strong>{tr("Muốn gợi ý riêng cho bạn?", "Want personalized recommendations?")}</strong>{" "}
            {tr(
              "Chọn thể loại bạn thích, hoặc bấm Thích / Không thích vài phim bên dưới.",
              "Pick your favorite genres, or click Like / Dislike on a few movies below."
            )}
          </p>
          <button onClick={onPickGenres} className="rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white hover:bg-cobalt/90">
            {tr("Chọn thể loại", "Pick Genres")}
          </button>
        </div>
      )}

      <div className="mt-8">
        {state === "loading" && <div className="h-96 animate-pulse rounded-3xl bg-ink/10" />}
        {state === "error" && (
          <Notice title={tr("Không tải được gợi ý", "Could not load recommendations")}>
            {tr(
              "Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.",
              "Please check that the API server is running and reload the page."
            )}
          </Notice>
        )}
        {state === "ok" && !hero && (
          <Notice
            title={tr("Bạn đã xem hết gợi ý hiện có", "You have seen all current recommendations")}
            action={
              <button onClick={onBrowse} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                {tr("Khám phá thêm phim", "Explore more movies")}
              </button>
            }
          >
            {tr(
              "Hãy Thích vài phim mới để hệ thống hiểu bạn rõ hơn.",
              "Like a few more movies so the system understands your taste better."
            )}
          </Notice>
        )}
        {state === "ok" && hero && (
          <>
            <Hero movie={hero} status={rated[hero.movie_id]} onRate={onRate} coldStart={isCold} />
            <ul className={`mt-12 ${GRID}`}>
              <AnimatePresence initial={false} mode="popLayout">
                {rest.map((m) => (
                  <motion.li key={m.movie_id} layout exit={{ opacity: 0, scale: 0.94 }} transition={{ duration: 0.25 }}>
                    <Ticket movie={m} min={min} max={max} status={rated[m.movie_id]} onRate={onRate} coldStart={isCold} />
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </>
        )}
      </div>
    </main>
  );
}
