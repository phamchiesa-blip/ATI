import { useEffect, useMemo, useState } from "react";
import { ThumbsDown, ThumbsUp, X } from "lucide-react";
import { api } from "./services/apiClient";
import { Notice } from "./components/MovieCard";
import { toneOf } from "./utils/theme";
import { useLang } from "./context/AppContexts";
import { genreLabel } from "./utils/i18nHelpers";

const top = (list, pick, n) => {
  const counts = {};
  list.forEach((m) => [].concat(pick(m) ?? []).forEach((x) => (counts[x] = (counts[x] ?? 0) + 1)));
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
};

function Row({ m, onRemove, removeLabel, lang }) {
  const [bg] = toneOf(m.genres?.[0]);
  const genreStr = m.genres?.slice(0, 2).map((g) => genreLabel(g, lang)).join(", ");
  return (
    <li className="group flex items-center gap-2 rounded-xl bg-white pr-2 hover:bg-ink/5">
      <a href={`#/movie/${m.movie_id}`} className="flex min-w-0 flex-1 items-center gap-3 p-3">
        <span aria-hidden className="size-8 shrink-0 rounded-lg" style={{ background: bg }} />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold">{m.title}</span>
          <span className="block truncate text-xs text-mute">
            {[m.release_year, genreStr].filter(Boolean).join(" · ")}
          </span>
        </span>
      </a>
      <button
        type="button"
        onClick={() => onRemove(m)}
        title={removeLabel}
        aria-label={`${removeLabel}: ${m.title}`}
        className="inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-xs font-semibold text-mute ring-1 ring-ink/15 transition-colors hover:bg-coral hover:text-white hover:ring-coral"
      >
        <X size={14} /> <span className="hidden sm:inline">{removeLabel}</span>
      </button>
    </li>
  );
}

// Trang "Gu của bạn": tổng hợp từ lịch sử Thích / Không thích
export default function Taste({ rev, onBrowse, onUnrate }) {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(false);
  const { lang, tr } = useLang();

  const remove = (m) => {
    setItems((list) => list.filter((x) => x.movie_id !== m.movie_id));
    onUnrate?.(m);
  };

  useEffect(() => {
    api
      .history()
      .then((r) => setItems(r.items))
      .catch(() => setError(true));
  }, [rev]);

  const stats = useMemo(() => {
    if (!items) return null;
    const likes = items.filter((m) => m.action === "like");
    const dislikes = items.filter((m) => m.action === "dislike");
    return {
      likes,
      dislikes,
      genres: top(likes, (m) => m.genres, 6),
      directors: top(likes, (m) => m.director, 4).filter(([, n]) => n >= 2),
    };
  }, [items]);

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">{tr("Gu của bạn", "Your Taste")}</h1>
      <p className="mt-2 text-mute">
        {tr(
          "Tổng hợp từ những phim bạn đã bấm Thích hoặc Không thích.",
          "Summarized from the movies you have Liked or Disliked."
        )}
      </p>

      <div className="mt-8">
        {error && (
          <Notice title={tr("Không tải được dữ liệu", "Could not load data")}>
            {tr(
              "Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.",
              "Please check that the API server is running and reload the page."
            )}
          </Notice>
        )}
        {stats && stats.likes.length + stats.dislikes.length === 0 && (
          <Notice
            title={tr("Bạn chưa đánh giá phim nào", "You haven't rated any movies yet")}
            action={
              <button onClick={onBrowse} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                {tr("Khám phá phim", "Explore Movies")}
              </button>
            }
          >
            {tr(
              "Bấm Thích hoặc Không thích ở vài bộ phim, gu của bạn sẽ hiện ở đây.",
              "Click Like or Dislike on a few movies and your taste profile will appear here."
            )}
          </Notice>
        )}
        {stats && stats.likes.length + stats.dislikes.length > 0 && (
          <>
            <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
              <section className="rounded-3xl bg-white p-6">
                <h2 className="font-display text-2xl font-extrabold">
                  {tr("Thể loại bạn hay Thích", "Your Top Liked Genres")}
                </h2>
                {stats.genres.length === 0 ? (
                  <p className="mt-3 text-mute">{tr("Chưa có phim nào được Thích.", "No liked movies yet.")}</p>
                ) : (
                  <ul className="mt-4 grid gap-3">
                    {stats.genres.map(([g, n]) => (
                      <li key={g}>
                        <div className="flex justify-between text-sm font-semibold">
                          <span>{genreLabel(g, lang)}</span>
                          <span className="text-mute">
                            {n} {tr("phim", "movies")}
                          </span>
                        </div>
                        <div className="mt-1 h-2.5 rounded-full bg-ink/10">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${(n / stats.genres[0][1]) * 100}%`, background: toneOf(g)[0] }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="rounded-3xl bg-white p-6">
                <div className="flex gap-8">
                  <p>
                    <span className="block font-display text-4xl font-extrabold text-cobalt">{stats.likes.length}</span>
                    <span className="text-sm text-mute">{tr("phim đã Thích", "liked movies")}</span>
                  </p>
                  <p>
                    <span className="block font-display text-4xl font-extrabold">{stats.dislikes.length}</span>
                    <span className="text-sm text-mute">{tr("phim không thích", "disliked movies")}</span>
                  </p>
                </div>
                {stats.directors.length > 0 && (
                  <>
                    <h2 className="mt-6 font-display text-lg font-extrabold">
                      {tr("Đạo diễn quen thuộc", "Favorite Directors")}
                    </h2>
                    <ul className="mt-2 grid gap-1 text-sm">
                      {stats.directors.map(([d, n]) => (
                        <li key={d} className="flex justify-between">
                          <span>{d}</span>
                          <span className="text-mute">
                            {n} {tr("phim", "movies")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>
            </div>

            <div className="mt-8 grid gap-8 md:grid-cols-2">
              <section>
                <h2 className="flex items-center gap-2 font-display text-2xl font-extrabold">
                  <ThumbsUp size={20} className="text-cobalt" /> {tr("Đã Thích", "Liked")}
                </h2>
                <ul className="mt-3 grid gap-2">{stats.likes.map((m) => <Row key={m.movie_id} m={m} onRemove={remove} removeLabel={tr("Bỏ thích", "Unlike")} lang={lang} />)}</ul>
              </section>
              <section>
                <h2 className="flex items-center gap-2 font-display text-2xl font-extrabold">
                  <ThumbsDown size={20} /> {tr("Không thích", "Disliked")}
                </h2>
                <ul className="mt-3 grid gap-2">{stats.dislikes.map((m) => <Row key={m.movie_id} m={m} onRemove={remove} removeLabel={tr("Bỏ không thích", "Remove dislike")} lang={lang} />)}</ul>
              </section>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
