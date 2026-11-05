import { useContext, useEffect, useState } from "react";
import { ArrowLeft, Bookmark, ExternalLink, Play } from "lucide-react";
import { api } from "./services/apiClient";
import { GRID, toneOf } from "./utils/theme";
import { MovieCard, Notice } from "./components/MovieCard";
import { Overview, Poster, Rating, RateButtons } from "./components/Poster";
import { TrailerContext, WatchlistContext, useLang } from "./context/AppContexts";
import { genreLabel } from "./utils/i18nHelpers";

const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const duration = (min, tr) => {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? tr(`${h} giờ ${m} phút`, `${h}h ${m}m`) : tr(`${m} phút`, `${m}m`);
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
  const { tr } = useLang();
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
              title={tr(`Xem phim khác của ${p.name}`, `More movies with ${p.name}`)}
              className="block max-w-full truncate text-left font-semibold hover:text-cobalt"
            >
              {p.name}
            </button>
            {p.character && (
              <span className="block truncate text-sm text-mute">
                {tr(`vai ${p.character}`, `as ${p.character}`)}
              </span>
            )}
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
  const { saved, toggle } = useContext(WatchlistContext);
  const [movie, setMovie] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [state, setState] = useState("loading");
  const { lang, tr } = useLang();

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
        <ArrowLeft size={16} /> {tr("Quay lại", "Back")}
      </button>

      {state === "loading" && <div className="mt-6 h-96 animate-pulse rounded-3xl bg-ink/10" />}
      {state === "missing" && (
        <div className="mt-8">
          <Notice title={tr("Không tìm thấy phim này", "Movie not found")}>
            {tr(
              "Có thể đường dẫn đã sai hoặc phim không còn trong dữ liệu.",
              "The link might be incorrect or the movie is no longer in the catalog."
            )}
          </Notice>
        </div>
      )}
      {state === "error" && (
        <div className="mt-8">
          <Notice title={tr("Không tải được thông tin phim", "Could not load movie details")}>
            {tr(
              "Hãy kiểm tra máy chủ API đang chạy rồi thử lại.",
              "Please check that the API server is running and try again."
            )}
          </Notice>
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
                {movie.runtime && <span>{duration(movie.runtime, tr)}</span>}
                <Rating value={movie.vote_average} />
                {movie.vote_count != null && (
                  <span className="text-mute">
                    {movie.vote_count.toLocaleString(lang === "en" ? "en-US" : "vi-VN")}{" "}
                    {tr("lượt đánh giá", "votes")}
                  </span>
                )}
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {movie.genres.map((g) => (
                  <button
                    key={g}
                    onClick={() => onFilter({ genres: [g] })}
                    className="rounded-full bg-paper px-3 py-1 text-sm font-medium hover:bg-ink/10"
                  >
                    {genreLabel(g, lang)}
                  </button>
                ))}
              </div>

              <Overview movie={movie} className="mt-5 max-w-2xl leading-relaxed text-mute" />

              <dl className="mt-6 grid max-w-2xl gap-x-8 gap-y-4 sm:grid-cols-2">
                <Fact label={tr("Đạo diễn", "Director")}>
                  {movie.director && (
                    <button
                      onClick={() => onFilter({ director: movie.director })}
                      className="underline decoration-ink/30 underline-offset-4 hover:text-cobalt"
                    >
                      {movie.director}
                    </button>
                  )}
                </Fact>
                <Fact label={tr("Biên kịch", "Writers")}>{movie.crew?.writers?.join(", ")}</Fact>
                <Fact label={tr("Âm nhạc", "Music")}>{movie.crew?.composers?.join(", ")}</Fact>
              </dl>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <button
                  onClick={() => openTrailer(movie)}
                  className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 font-semibold text-white transition-colors hover:bg-ink/85"
                >
                  <Play size={16} className="fill-white" /> {tr("Xem trailer", "Watch trailer")}
                </button>
                <button
                  onClick={() => toggle(movie)}
                  aria-pressed={saved.has(movie.movie_id)}
                  className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 font-semibold ring-1 ring-ink/20 transition-colors hover:bg-ink/5"
                >
                  <Bookmark size={16} className={saved.has(movie.movie_id) ? "fill-current" : ""} />
                  {saved.has(movie.movie_id) ? tr("Đã lưu", "Saved") : tr("Xem sau", "Watchlist")}
                </button>
                {movie.homepage && (
                  <a
                    href={movie.homepage}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 text-sm font-semibold underline underline-offset-4"
                  >
                    {tr("Trang chủ phim", "Official Website")} <ExternalLink size={14} />
                  </a>
                )}
                <div className="min-w-60 flex-1 sm:max-w-sm">
                  <RateButtons status={rated[movie.movie_id]} onRate={(a) => onRate(movie, a)} />
                </div>
              </div>
            </div>
          </section>

          {movie.cast_members?.length > 0 && (
            <Section title={tr("Diễn viên", "Cast")}>
              <People
                people={movie.cast_members}
                tone={toneOf(movie.genres[0])}
                onPick={(name) => onFilter({ actor: name })}
              />
            </Section>
          )}
          {movie.voice_cast?.length > 0 && (
            <Section title={tr("Diễn viên lồng tiếng", "Voice Cast")}>
              <People
                people={movie.voice_cast}
                tone={toneOf(movie.genres[0])}
                onPick={(name) => onFilter({ voice: name })}
              />
            </Section>
          )}

          {(movie.companies?.length > 0 ||
            movie.countries?.length > 0 ||
            movie.languages?.length > 0 ||
            movie.budget ||
            movie.revenue) && (
            <Section title={tr("Thông tin thêm", "Additional Information")}>
              <dl className="grid gap-x-8 gap-y-5 rounded-2xl bg-white p-6 sm:grid-cols-2 lg:grid-cols-3">
                <Fact label={tr("Hãng sản xuất", "Production Companies")}>{movie.companies?.join(", ")}</Fact>
                <Fact label={tr("Quốc gia", "Countries")}>{movie.countries?.join(", ")}</Fact>
                <Fact label={tr("Ngôn ngữ", "Languages")}>{movie.languages?.join(", ")}</Fact>
                <Fact label={tr("Kinh phí", "Budget")}>{movie.budget ? money(movie.budget) : null}</Fact>
                <Fact label={tr("Doanh thu", "Revenue")}>{movie.revenue ? money(movie.revenue) : null}</Fact>
              </dl>
              {movie.keywords?.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {movie.keywords.map((k) => (
                    <button
                      key={k}
                      onClick={() => onFilter({ keyword: k })}
                      title={tr("Xem các phim có cùng từ khóa", "Browse movies with this keyword")}
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
            <Section title={tr("Phim tương tự", "Similar Movies")}>
              <div className={GRID}>
                {similar.map((m) => (
                  <MovieCard
                    key={m.movie_id}
                    movie={m}
                    note={tr(`Giống ${m.similarity}%`, `${m.similarity}% similar`)}
                    status={rated[m.movie_id]}
                    onRate={onRate}
                  />
                ))}
              </div>
            </Section>
          )}

          {movie.same_director?.length > 0 && (
            <Section title={tr(`Cùng đạo diễn ${movie.director}`, `More from director ${movie.director}`)}>
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
