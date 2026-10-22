import { useContext, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Play } from "lucide-react";
import { api } from "./api";
import { CardButtons, GRID, Notice, PosterLink, PosterTile, Rating, RateButtons, TrailerContext } from "./ui";

const reasonText = (m) =>
  m.match_percent == null
    ? "Được nhiều người yêu thích"
    : m.reasons?.length
      ? `Vì bạn thích ${m.reasons.join(", ")}`
      : "Có nội dung gần với những phim bạn đã chọn";

const PARTS = [
  ["cosine", "Giống gu của bạn"],
  ["rating", "Điểm đánh giá"],
  ["popularity", "Độ phổ biến"],
  ["newness", "Độ mới"],
  ["neural", "AI học từ Thích / Không thích"],
];

// Các thành phần cấu thành điểm gợi ý (module Ranking), thang 0-100 so với các phim ứng viên
function Breakdown({ data }) {
  return (
    <ul className="mt-2 grid gap-2">
      {PARTS.filter(([k]) => data[k] != null).map(([k, label]) => {
        const v = Math.round(data[k] * 100);
        return (
          <li key={k}>
            <div className="flex justify-between text-xs">
              <span>{label}</span>
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

function Hero({ movie, status, onRate }) {
  const openTrailer = useContext(TrailerContext);
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
              {g}
            </span>
          ))}
        </div>
        <p className="mt-4 line-clamp-4 leading-relaxed text-mute">{movie.overview}</p>
        <p className="mt-4 text-sm font-medium">{reasonText(movie)}</p>

        <div className="mt-5 flex flex-wrap items-start gap-x-10 gap-y-4">
          {movie.match_percent != null ? (
            <p className="flex items-baseline gap-2">
              <span className="font-display text-5xl font-extrabold text-cobalt">{movie.match_percent}%</span>
              <span className="text-sm text-mute">độ hợp</span>
            </p>
          ) : (
            <Rating value={movie.vote_average} />
          )}
          {movie.breakdown && (
            <div className="min-w-56 flex-1">
              <p className="text-sm font-semibold">Vì sao gợi ý phim này?</p>
              <Breakdown data={movie.breakdown} />
            </div>
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button
            onClick={() => openTrailer(movie)}
            className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 font-semibold text-white hover:bg-ink/85"
          >
            <Play size={16} className="fill-white" /> Xem trailer
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
function Ticket({ movie, min, max, status, onRate }) {
  const [why, setWhy] = useState(false);
  const personal = movie.match_percent != null;
  const width = max === min ? 100 : 35 + ((movie.match_percent - min) / (max - min)) * 65;
  return (
    <article>
      <PosterTile movie={movie} status={status} onRate={onRate} className="rounded-b-none" />
      <div className="relative rounded-b-xl bg-white p-3 ring-1 ring-ink/10">
        <span className="absolute inset-x-3 top-0 border-t border-dashed border-ink/30" />
        <span className="absolute top-0 -left-2 size-4 -translate-y-1/2 rounded-full bg-paper" />
        <span className="absolute top-0 -right-2 size-4 -translate-y-1/2 rounded-full bg-paper" />
        {personal ? (
          <>
            <p className="mt-1 flex items-baseline justify-between">
              <span className="font-display text-xl font-extrabold text-cobalt">{movie.match_percent}%</span>
              <span className="text-xs text-mute">độ hợp</span>
            </p>
            <div className="mt-1 h-1.5 rounded-full bg-ink/10">
              <div className="h-full rounded-full bg-cobalt" style={{ width: `${width}%` }} />
            </div>
          </>
        ) : (
          <p className="mt-1">
            <Rating value={movie.vote_average} />
          </p>
        )}
        <p className="mt-2 text-xs leading-snug text-mute">{reasonText(movie)}</p>
        {movie.breakdown && (
          <>
            <button
              onClick={() => setWhy((v) => !v)}
              aria-expanded={why}
              className="mt-2 text-xs font-semibold text-cobalt underline underline-offset-4"
            >
              {why ? "Ẩn chi tiết" : "Vì sao gợi ý?"}
            </button>
            {why && <Breakdown data={movie.breakdown} />}
          </>
        )}
      </div>
      <div className="mt-3">
        <CardButtons movie={movie} />
      </div>
    </article>
  );
}

const MODES = [
  ["proposed", "Đề xuất (Ranking + AI)"],
  ["baseline", "Baseline (chỉ cosine)"],
];

export default function Recommend({ rev, rated, onRate, onPickGenres, onBrowse }) {
  const [items, setItems] = useState([]);
  const [personalized, setPersonalized] = useState(true);
  const [mode, setMode] = useState("proposed");
  const [state, setState] = useState("loading");

  useEffect(() => {
    let off = false;
    api
      .recommendations(13, mode)
      .then((r) => {
        if (off) return;
        setItems(r.items);
        setPersonalized(r.personalized);
        setState("ok");
      })
      .catch(() => !off && setState("error"));
    return () => {
      off = true;
    };
  }, [rev, mode]);

  const [hero, ...rest] = items;
  const pcts = rest.map((m) => m.match_percent).filter((p) => p != null);
  const min = Math.min(...pcts);
  const max = Math.max(...pcts);

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-extrabold">
            {personalized ? "Dành cho bạn" : "Đang được yêu thích"}
          </h1>
          <p className="mt-2 text-mute">
            {personalized
              ? "Danh sách tự cập nhật mỗi khi bạn bấm Thích hoặc Không thích."
              : "Những phim nổi tiếng và được đánh giá cao."}
          </p>
        </div>
        {personalized && (
          <div>
            <div role="group" aria-label="Cách gợi ý" className="inline-flex rounded-full bg-white p-1 ring-1 ring-ink/15">
              {MODES.map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setMode(id)}
                  aria-pressed={mode === id}
                  className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
                    mode === id ? "bg-ink text-white" : "hover:bg-ink/5"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-2 max-w-sm text-xs text-mute">
              {mode === "baseline"
                ? "Chỉ xếp theo độ giống nội dung, không tính điểm đánh giá, độ phổ biến, độ mới hay AI."
                : "Kết hợp độ giống nội dung với điểm đánh giá, độ phổ biến, độ mới và AI học từ Thích / Không thích."}
            </p>
          </div>
        )}
      </div>

      {state === "ok" && !personalized && (
        <div className="mt-6 flex flex-wrap items-center gap-4 rounded-2xl bg-white p-5 ring-1 ring-ink/10">
          <p className="min-w-60 flex-1">
            <strong>Muốn gợi ý riêng cho bạn?</strong> Chọn thể loại bạn thích, hoặc bấm Thích / Không
            thích vài phim bên dưới.
          </p>
          <button onClick={onPickGenres} className="rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white hover:bg-cobalt/90">
            Chọn thể loại
          </button>
        </div>
      )}

      <div className="mt-8">
        {state === "loading" && <div className="h-96 animate-pulse rounded-3xl bg-ink/10" />}
        {state === "error" && (
          <Notice title="Không tải được gợi ý">Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.</Notice>
        )}
        {state === "ok" && !hero && (
          <Notice
            title="Bạn đã xem hết gợi ý hiện có"
            action={
              <button onClick={onBrowse} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                Khám phá thêm phim
              </button>
            }
          >
            Hãy Thích vài phim mới để hệ thống hiểu bạn rõ hơn.
          </Notice>
        )}
        {state === "ok" && hero && (
          <>
            <Hero movie={hero} status={rated[hero.movie_id]} onRate={onRate} />
            <ul className={`mt-12 ${GRID}`}>
              <AnimatePresence initial={false} mode="popLayout">
                {rest.map((m) => (
                  <motion.li key={m.movie_id} layout exit={{ opacity: 0, scale: 0.94 }} transition={{ duration: 0.25 }}>
                    <Ticket movie={m} min={min} max={max} status={rated[m.movie_id]} onRate={onRate} />
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