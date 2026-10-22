import { useEffect, useState } from "react";
import { ArrowLeft, Check } from "lucide-react";
import { api, OFFLINE_MSG } from "./api";
import { toneOf } from "./ui";

// Màn hình chọn thể loại yêu thích. Mở từ nút "Chọn thể loại" trên thanh đầu trang.
export default function Onboarding({ onDone, onCancel }) {
  const [genres, setGenres] = useState([]);
  const [picked, setPicked] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .genres()
      .then((g) => setGenres(g.filter((x) => x.count >= 50)))
      .catch(() => setError(OFFLINE_MSG));
    api.getOnboarding().then((r) => setPicked(r.genres)).catch(() => {});
  }, []);

  const toggle = (g) =>
    setPicked((p) => (p.includes(g) ? p.filter((x) => x !== g) : [...p, g]));

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await api.onboarding(picked);
      onDone();
    } catch (e) {
      setError(e.status === 0 ? OFFLINE_MSG : "Chưa lưu được lựa chọn. Hãy thử lại.");
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-5 py-10 md:py-14">
      <button
        onClick={onCancel}
        className="inline-flex items-center gap-2 text-sm font-semibold hover:text-cobalt"
      >
        <ArrowLeft size={16} /> Quay lại
      </button>
      <h1 className="mt-6 font-display text-4xl leading-tight font-extrabold md:text-6xl">
        Bạn thích phim
        <br />
        kiểu nào?
      </h1>
      <p className="mt-4 max-w-xl text-lg text-mute">
        Chọn vài thể loại để nhận gợi ý riêng. Những phim bạn đã Thích hoặc Không thích vẫn được giữ
        lại khi bạn đổi thể loại.
      </p>

      <fieldset className="mt-10">
        <legend className="text-sm font-semibold">Thể loại yêu thích</legend>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {genres.map(({ name: g }) => {
            const on = picked.includes(g);
            const [bg, fg] = toneOf(g);
            return (
              <button
                key={g}
                type="button"
                aria-pressed={on}
                onClick={() => toggle(g)}
                style={on ? { background: bg, color: fg } : undefined}
                className="flex items-center justify-between gap-2 rounded-2xl bg-white px-4 py-5 text-left font-display text-lg font-bold ring-1 ring-ink/10 transition-colors hover:ring-ink/30"
              >
                <span className="flex items-center gap-2">
                  {!on && <span className="size-3 rounded-full" style={{ background: bg }} aria-hidden />}
                  {g}
                </span>
                {on && <Check size={20} aria-hidden />}
              </button>
            );
          })}
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="mt-6 text-coral">
          {error}
        </p>
      )}

      <div className="mt-10 flex items-center gap-4">
        <button
          onClick={submit}
          disabled={picked.length === 0 || busy}
          className="rounded-full bg-cobalt px-8 py-3 font-semibold text-white transition-colors hover:bg-cobalt/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Đang lưu..." : "Lưu và xem gợi ý"}
        </button>
        <span className="text-sm text-mute">
          {picked.length === 0 ? "Chọn ít nhất 1 thể loại" : `Đã chọn ${picked.length}`}
        </span>
      </div>
    </main>
  );
}