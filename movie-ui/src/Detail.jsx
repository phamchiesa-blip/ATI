import { useContext, useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, Play } from "lucide-react";
import { api } from "./api";
import { GRID, MovieCard, Notice, Poster, Rating, RateButtons, TrailerContext, toneOf } from "./ui";

const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const duration = (min) => {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h} giờ ${m} phút` : `${m} phút`;
};

function Section({ title, children }) {
  return (
    <section className="mt-12">
      <h2 className="font-display text-2xl font-extrabold">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function People({ people, tone, onPick }) {
  const [bg, fg] = tone;
  return (
    <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {people.map((p) => (
        <li key={p.name + p.character} className="flex items-center gap-3 rounded-2xl bg-white p-3">
          <span
            aria-hidden
            className="flex size-11 shrink-0 items-center justify-center rounded-full font-display text-lg font-extrabold"
            style={{ background: bg, color: fg }}
          >
            {p.name?.[0]}
          </span>
          <span className="min-w-0">
            <button
              onClick={() => onPick(p.name)}
              title={`Xem phim khác của ${p.name}`}
              className="block max-w-full truncate text-left font-semibold hover:text-cobalt"
            >
              {p.name}
            </button>
            {p.character && <span className="block truncate text-sm text-mute">vai {p.character}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Fact({ label, children }) {
  if (!children || (Array.isArray(children) && children.length === 0)) return null;
  return (
    <div>
      <dt className="text-sm text-mute">{label}</dt>
      <dd className="mt-0.5 font-medium">{children}</dd>
    </div>
  );
}

export default function Detail({ id, rated, onRate, onFilter }) {
  const openTrailer = useContext(TrailerContext);
  const [movie, setMovie] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [state, setState] = useState("loading");

  useEffect(() => {
    let off = false;
    setState("loading");
    setMovie(null);
    setSimilar([]);
    api
      .movie(id)
      .then((m) => {
        if (off) return;
        setMovie(m);
        setState("ok");
      })
      .catch((e) => !off && setState(e.status === 404 ? "missing" : "error"));
    api.similar(id, 8).then((r) => !off && setSimilar(r.items)).catch(() => {});
    return () => {
      off = true;
    };
  }, [id]);

  const back = () => (window.history.length > 1 ? window.history.back() : (window.location.hash = ""));

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <button onClick={back} className="inline-flex items-center gap-2 text-sm font-semibold hover:text-cobalt">
        <ArrowLeft size={16} /> Quay lại
      </button>

      {state === "loading" && <div className="mt-6 h-96 animate-pulse rounded-3xl bg-ink/10" />}
      {state === "missing" && (
        <div className="mt-8">
          <Notice title="Không tìm thấy phim này">Có thể đường dẫn đã sai hoặc phim không còn trong dữ liệu.</Notice>
        </div>
      )}
      {state === "error" && (
        <div className="mt-8">
          <Notice title="Không tải được thông tin phim">Hãy kiểm tra máy chủ API đang chạy rồi thử lại.</Notice>
        </div>
      )}

      {state === "ok" && movie && (
        <>
          <section className="mt-6 grid gap-8 rounded-3xl bg-white p-6 md:grid-cols-[300px_1fr] md:p-10">
            <Poster movie={movie} size="lg" showTitle={false} />
            <div>
              <h1 className="font-display text-4xl leading-tight font-extrabold md:text-6xl">{movie.title}</h1>
              {movie.tagline && <p className="mt-2 text-lg text-mute italic">{movie.tagline}</p>}

              <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
                {movie.release_year && <span className="font-semibold">{movie.release_year}</span>}
                {movie.runtime && <span>{duration(movie.runtime)}</span>}
                <Rating value={movie.vote_average} />
                {movie.vote_count != null && (
                  <span className="text-mute">{movie.vote_count.toLocaleString("vi-VN")} lượt đánh giá</span>
                )}
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {movie.genres.map((g) => (
                  <button
                    key={g}
                    onClick={() => onFilter({ genres: [g] })}
                    className="rounded-full bg-paper px-3 py-1 text-sm font-medium hover:bg-ink/10"
                  >
                    {g}
                  </button>
                ))}
              </div>

              <p className="mt-5 max-w-2xl leading-relaxed text-mute">{movie.overview}</p>

              <dl className="mt-6 grid max-w-2xl gap-x-8 gap-y-4 sm:grid-cols-2">
                <Fact label="Đạo diễn">
                  {movie.director && (
                    <button onClick={() => onFilter({ director: movie.director })} className="underline decoration-ink/30 underline-offset-4 hover:text-cobalt">
                      {movie.director}
                    </button>
                  )}
                </Fact>
                <Fact label="Biên kịch">{movie.crew?.writers?.join(", ")}</Fact>
                <Fact label="Âm nhạc">{movie.crew?.composers?.join(", ")}</Fact>
              </dl>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <button
                  onClick={() => openTrailer(movie)}
                  className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 font-semibold text-white transition-colors hover:bg-ink/85"
                >
                  <Play size={16} className="fill-white" /> Xem trailer
                </button>
                {movie.homepage && (
                  <a
                    href={movie.homepage}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 text-sm font-semibold underline underline-offset-4"
                  >
                    Trang chủ phim <ExternalLink size={14} />
                  </a>
                )}
                <div className="min-w-60 flex-1 sm:max-w-sm">
                  <RateButtons status={rated[movie.movie_id]} onRate={(a) => onRate(movie, a)} />
                </div>
              </div>
            </div>
          </section>

          {movie.cast_members?.length > 0 && (
            <Section title="Diễn viên">
              <People people={movie.cast_members} tone={toneOf(movie.genres[0])} onPick={(name) => onFilter({ actor: name })} />
            </Section>
          )}
          {movie.voice_cast?.length > 0 && (
            <Section title="Diễn viên lồng tiếng">
              <People people={movie.voice_cast} tone={toneOf(movie.genres[0])} onPick={(name) => onFilter({ voice: name })} />
            </Section>
          )}

          {(movie.companies?.length > 0 ||
            movie.countries?.length > 0 ||
            movie.languages?.length > 0 ||
            movie.budget ||
            movie.revenue) && (
            <Section title="Thông tin thêm">
              <dl className="grid gap-x-8 gap-y-5 rounded-2xl bg-white p-6 sm:grid-cols-2 lg:grid-cols-3">
                <Fact label="Hãng sản xuất">{movie.companies?.join(", ")}</Fact>
                <Fact label="Quốc gia">{movie.countries?.join(", ")}</Fact>
                <Fact label="Ngôn ngữ">{movie.languages?.join(", ")}</Fact>
                <Fact label="Kinh phí">{movie.budget ? money(movie.budget) : null}</Fact>
                <Fact label="Doanh thu">{movie.revenue ? money(movie.revenue) : null}</Fact>
              </dl>
              {movie.keywords?.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {movie.keywords.map((k) => (
                    <button
                      key={k}
                      onClick={() => onFilter({ keyword: k })}
                      title="Xem các phim có cùng từ khóa"
                      className="rounded-full bg-white px-3 py-1 text-sm text-mute ring-1 ring-ink/10 hover:text-cobalt hover:ring-cobalt/40"
                    >
                      {k}
                    </button>
                  ))}
                </div>
              )}
            </Section>
          )}

          {similar.length > 0 && (
            <Section title="Phim tương tự">
              <div className={GRID}>
                {similar.map((m) => (
                  <MovieCard
                    key={m.movie_id}
                    movie={m}
                    note={`Giống ${m.similarity}%`}
                    status={rated[m.movie_id]}
                    onRate={onRate}
                  />
                ))}
              </div>
            </Section>
          )}

          {movie.same_director?.length > 0 && (
            <Section title={`Cùng đạo diễn ${movie.director}`}>
              <div className={GRID}>
                {movie.same_director.map((m) => (
                  <MovieCard key={m.movie_id} movie={m} status={rated[m.movie_id]} onRate={onRate} />
                ))}
              </div>
            </Section>
          )}
        </>
      )}
    </main>
  );
}