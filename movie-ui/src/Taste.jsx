import { useEffect, useMemo, useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { api } from "./api";
import { Notice, toneOf } from "./ui";

const top = (list, pick, n) => {
  const counts = {};
  list.forEach((m) => [].concat(pick(m) ?? []).forEach((x) => (counts[x] = (counts[x] ?? 0) + 1)));
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
};

function Row({ m }) {
  const [bg] = toneOf(m.genres?.[0]);
  return (
    <li>
      <a href={`#/movie/${m.movie_id}`} className="flex items-center gap-3 rounded-xl bg-white p-3 hover:bg-ink/5">
        <span aria-hidden className="size-8 shrink-0 rounded-lg" style={{ background: bg }} />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold">{m.title}</span>
          <span className="block truncate text-xs text-mute">
            {[m.release_year, m.genres?.slice(0, 2).join(", ")].filter(Boolean).join(" · ")}
          </span>
        </span>
      </a>
    </li>
  );
}

// Trang "Gu của bạn": tổng hợp từ lịch sử Thích / Không thích
export default function Taste({ rev, onBrowse }) {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(false);

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
      <h1 className="font-display text-4xl font-extrabold">Gu của bạn</h1>
      <p className="mt-2 text-mute">Tổng hợp từ những phim bạn đã bấm Thích hoặc Không thích.</p>

      <div className="mt-8">
        {error && <Notice title="Không tải được dữ liệu">Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.</Notice>}
        {stats && stats.likes.length + stats.dislikes.length === 0 && (
          <Notice
            title="Bạn chưa đánh giá phim nào"
            action={
              <button onClick={onBrowse} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                Khám phá phim
              </button>
            }
          >
            Bấm Thích hoặc Không thích ở vài bộ phim, gu của bạn sẽ hiện ở đây.
          </Notice>
        )}
        {stats && stats.likes.length + stats.dislikes.length > 0 && (
          <>
            <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
              <section className="rounded-3xl bg-white p-6">
                <h2 className="font-display text-2xl font-extrabold">Thể loại bạn hay Thích</h2>
                {stats.genres.length === 0 ? (
                  <p className="mt-3 text-mute">Chưa có phim nào được Thích.</p>
                ) : (
                  <ul className="mt-4 grid gap-3">
                    {stats.genres.map(([g, n]) => (
                      <li key={g}>
                        <div className="flex justify-between text-sm font-semibold">
                          <span>{g}</span>
                          <span className="text-mute">{n} phim</span>
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
                    <span className="text-sm text-mute">phim đã Thích</span>
                  </p>
                  <p>
                    <span className="block font-display text-4xl font-extrabold">{stats.dislikes.length}</span>
                    <span className="text-sm text-mute">phim không thích</span>
                  </p>
                </div>
                {stats.directors.length > 0 && (
                  <>
                    <h2 className="mt-6 font-display text-lg font-extrabold">Đạo diễn quen thuộc</h2>
                    <ul className="mt-2 grid gap-1 text-sm">
                      {stats.directors.map(([d, n]) => (
                        <li key={d} className="flex justify-between">
                          <span>{d}</span>
                          <span className="text-mute">{n} phim</span>
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
                  <ThumbsUp size={20} className="text-cobalt" /> Đã Thích
                </h2>
                <ul className="mt-3 grid gap-2">{stats.likes.map((m) => <Row key={m.movie_id} m={m} />)}</ul>
              </section>
              <section>
                <h2 className="flex items-center gap-2 font-display text-2xl font-extrabold">
                  <ThumbsDown size={20} /> Không thích
                </h2>
                <ul className="mt-3 grid gap-2">{stats.dislikes.map((m) => <Row key={m.movie_id} m={m} />)}</ul>
              </section>
            </div>
          </>
        )}
      </div>
    </main>
  );
}