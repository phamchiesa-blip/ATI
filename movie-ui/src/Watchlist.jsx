import { GRID, MovieCard, Notice } from "./ui";
import { useLang } from "./i18n";

const savedOn = (m, lang, tr) =>
  m.added_at
    ? `${tr("Lưu ngày", "Saved on")} ${new Date(m.added_at * 1000).toLocaleDateString(lang === "en" ? "en-US" : "vi-VN")}`
    : undefined;

// Trang "Xem sau": danh sách phim đã lưu. Lưu phim không làm đổi gợi ý của bạn.
export default function Watchlist({ items, rated, onRate, onBrowse }) {
  const { lang, tr } = useLang();
  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">{tr("Xem sau", "Watchlist")}</h1>
      <p className="mt-2 text-mute">
        {tr(
          "Những phim bạn đã lưu. Lưu phim chỉ để nhớ, không ảnh hưởng đến gợi ý như Thích / Không thích.",
          "Movies you saved for later. Saving a movie is just a bookmark and does not affect recommendations like Like / Dislike."
        )}
      </p>
      <div className="mt-8">
        {items.length === 0 ? (
          <Notice
            title={tr("Chưa có phim nào", "Your watchlist is empty")}
            action={
              <button onClick={onBrowse} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                {tr("Khám phá phim", "Explore Movies")}
              </button>
            }
          >
            {tr(
              "Bấm biểu tượng đánh dấu ở góc trên bên phải poster để lưu phim vào đây.",
              "Click the bookmark icon at the top-right corner of any poster to save movies here."
            )}
          </Notice>
        ) : (
          <div className={GRID}>
            {items.map((m) => (
              <MovieCard
                key={m.movie_id}
                movie={m}
                note={savedOn(m, lang, tr)}
                status={rated[m.movie_id]}
                onRate={onRate}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
