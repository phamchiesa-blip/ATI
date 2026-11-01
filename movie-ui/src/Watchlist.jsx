import { GRID, MovieCard, Notice } from "./ui";

const savedOn = (m) =>
  m.added_at ? `Lưu ngày ${new Date(m.added_at * 1000).toLocaleDateString("vi-VN")}` : undefined;

// Trang "Xem sau": danh sách phim đã lưu. Lưu phim không làm đổi gợi ý của bạn.
export default function Watchlist({ items, rated, onRate, onBrowse }) {
  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">Xem sau</h1>
      <p className="mt-2 text-mute">
        Những phim bạn đã lưu. Lưu phim chỉ để nhớ, không ảnh hưởng đến gợi ý như Thích / Không thích.
      </p>
      <div className="mt-8">
        {items.length === 0 ? (
          <Notice
            title="Chưa có phim nào"
            action={
              <button onClick={onBrowse} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                Khám phá phim
              </button>
            }
          >
            Bấm biểu tượng đánh dấu ở góc trên bên phải poster để lưu phim vào đây.
          </Notice>
        ) : (
          <div className={GRID}>
            {items.map((m) => (
              <MovieCard key={m.movie_id} movie={m} note={savedOn(m)} status={rated[m.movie_id]} onRate={onRate} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}