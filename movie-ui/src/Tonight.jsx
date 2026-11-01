import { useContext, useEffect, useState } from "react";
import { Bookmark, Play, Shuffle } from "lucide-react";
import { api, OFFLINE_MSG } from "./api";
import { MovieCard, Notice, PosterLink, RateButtons, TrailerContext, WatchlistContext, toneOf } from "./ui";

function Pick({ movie, status, onRate, onNext }) {
  const openTrailer = useContext(TrailerContext);
  const { saved, toggle } = useContext(WatchlistContext);
  const on = saved.has(movie.movie_id);
  return (
    <section className="grid gap-8 rounded-3xl bg-white p-6 md:grid-cols-[260px_1fr] md:p-10">
      <PosterLink movie={movie} size="lg" showTitle={false} />
      <div className="max-w-xl">
        <p className="text-sm font-semibold text-cobalt">{movie.why}</p>
        <h2 className="mt-2 font-display text-4xl leading-tight font-extrabold md:text-5xl">
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
        {movie.director && <p className="mt-3 text-sm">Đạo diễn {movie.director}</p>}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={() => openTrailer(movie)}
            className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 font-semibold text-white hover:bg-ink/85"
          >
            <Play size={16} className="fill-white" /> Xem trailer
          </button>
          <button
            onClick={() => toggle(movie)}
            aria-pressed={on}
            className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 font-semibold ring-1 ring-ink/20 hover:bg-ink/5"
          >
            <Bookmark size={16} className={on ? "fill-current" : ""} /> {on ? "Đã lưu" : "Xem sau"}
          </button>
          <button
            onClick={onNext}
            className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-semibold ring-1 ring-cobalt/40 text-cobalt hover:bg-cobalt/5"
          >
            <Shuffle size={16} /> Đổi phim khác
          </button>
        </div>
        <div className="mt-5 max-w-sm">
          <RateButtons status={status} onRate={(a) => onRate(movie, a)} />
        </div>
      </div>
    </section>
  );
}

// "Tối nay xem gì?": chọn tâm trạng và thời gian rảnh, nhận một phim để xem ngay
export default function Tonight({ rated, onRate }) {
  const [options, setOptions] = useState(null);
  const [mood, setMood] = useState("");
  const [time, setTime] = useState("any");
  const [queue, setQueue] = useState(null); // danh sách phim đã nhận, hiển thị từng phim
  const [cursor, setCursor] = useState(0);
  const [done, setDone] = useState(false); // hết phim phù hợp
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .tonightOptions()
      .then(setOptions)
      .catch(() => setError(OFFLINE_MSG));
  }, []);

  const fetchMore = async (exclude) => {
    const r = await api.tonight(mood, time, exclude);
    setNote(
      time !== "any" && !r.runtime_filter_applied
        ? "Chưa lọc được theo thời lượng vì thiếu dữ liệu thời lượng phim (cần file CSV gốc)."
        : ""
    );
    return r.items;
  };

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const items = await fetchMore([]);
      setQueue(items);
      setCursor(0);
      setDone(items.length === 0);
    } catch (e) {
      setError(e.status === 0 ? OFFLINE_MSG : "Chưa chọn được phim. Hãy thử lại.");
    }
    setBusy(false);
  };

  const next = async () => {
    const nextIndex = cursor + 1;
    if (nextIndex + 4 >= queue.length && !done) {
      try {
        const more = await fetchMore(queue.map((m) => m.movie_id));
        if (more.length === 0) setDone(true);
        else setQueue((q) => [...q, ...more]);
      } catch {
        /* giữ nguyên danh sách hiện có */
      }
    }
    if (nextIndex < queue.length) setCursor(nextIndex);
  };

  const pick = queue?.[cursor];
  const others = queue ? queue.slice(cursor + 1, cursor + 5) : [];

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">Tối nay xem gì?</h1>
      <p className="mt-2 max-w-2xl text-mute">
        Chọn tâm trạng và thời gian rảnh, hệ thống chọn giúp bạn một phim. Tâm trạng được đổi sang thể loại
        theo quy tắc cố định (không phải mô hình học); nếu bạn đã có gu, phim hợp gu sẽ được xếp trước.
      </p>

      {options && (
        <div className="mt-8 rounded-3xl bg-white p-6 md:p-8">
          <h2 className="text-sm font-semibold">Bạn đang cảm thấy thế nào?</h2>
          <div role="radiogroup" aria-label="Tâm trạng" className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {options.moods.map((m) => {
              const on = mood === m.id;
              const [bg, fg] = toneOf(m.genres[0]);
              return (
                <button
                  key={m.id}
                  role="radio"
                  aria-checked={on}
                  onClick={() => setMood(m.id)}
                  style={on ? { background: bg, color: fg } : undefined}
                  className="rounded-2xl bg-paper px-4 py-4 text-left ring-1 ring-ink/10 transition-colors hover:ring-ink/30"
                >
                  <span className="block font-display text-lg font-bold">{m.label}</span>
                  <span className="mt-0.5 block text-xs opacity-70">{m.genres.join(", ")}</span>
                </button>
              );
            })}
          </div>

          <h2 className="mt-6 text-sm font-semibold">Bạn có bao nhiêu thời gian?</h2>
          <div role="radiogroup" aria-label="Thời gian" className="mt-3 flex flex-wrap gap-2">
            {options.times.map((t) => (
              <button
                key={t.id}
                role="radio"
                aria-checked={time === t.id}
                onClick={() => setTime(t.id)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
                  time === t.id ? "bg-ink text-white" : "bg-white ring-1 ring-ink/15 hover:bg-ink/5"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <button
            onClick={start}
            disabled={!mood || busy}
            className="mt-8 rounded-full bg-cobalt px-8 py-3 font-semibold text-white transition-colors hover:bg-cobalt/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "Đang chọn..." : "Chọn phim cho tôi"}
          </button>
          {!mood && <span className="ml-3 text-sm text-mute">Hãy chọn một tâm trạng</span>}
        </div>
      )}

      {error && (
        <p role="alert" className="mt-6 text-coral">
          {error}
        </p>
      )}
      {note && <p className="mt-4 text-sm text-mute">{note}</p>}

      <div className="mt-8">
        {queue && !pick && (
          <Notice title="Chưa có phim phù hợp">
            Không còn phim nào khớp tâm trạng và thời gian này. Hãy thử đổi tâm trạng hoặc chọn "Không giới hạn".
          </Notice>
        )}
        {pick && (
          <>
            <Pick movie={pick} status={rated[pick.movie_id]} onRate={onRate} onNext={next} />
            {others.length > 0 && (
              <section className="mt-10">
                <h2 className="font-display text-2xl font-extrabold">Lựa chọn khác</h2>
                <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
                  {others.map((m) => (
                    <MovieCard key={m.movie_id} movie={m} note={m.runtime ? `${m.runtime} phút` : undefined} status={rated[m.movie_id]} onRate={onRate} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}