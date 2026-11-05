import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "./api";
import { GRID, MovieCard, Notice, useDebounced } from "./ui";
import { useLang } from "./i18n";

const KEY = "gu-phim-browse";
const DEFAULTS = {
  query: "",
  genres: [],
  director: "",
  actor: "",
  voice: "",
  keyword: "",
  years: "",
  rating: "",
  sort: "popularity",
};

const YEARS = [
  { id: "", labelVi: "Mọi năm", labelEn: "All years" },
  { id: "2020", labelVi: "Từ 2020", labelEn: "2020 & newer", from: 2020 },
  { id: "2010", labelVi: "2010 - 2019", labelEn: "2010 - 2019", from: 2010, to: 2019 },
  { id: "2000", labelVi: "2000 - 2009", labelEn: "2000 - 2009", from: 2000, to: 2009 },
  { id: "1990", labelVi: "1990 - 1999", labelEn: "1990 - 1999", from: 1990, to: 1999 },
  { id: "old", labelVi: "Trước 1990", labelEn: "Before 1990", to: 1989 },
];
const RATINGS = [
  { id: "", labelVi: "Mọi điểm", labelEn: "All ratings" },
  { id: "6", labelVi: "Từ 6 điểm", labelEn: "6+ rating" },
  { id: "7", labelVi: "Từ 7 điểm", labelEn: "7+ rating" },
  { id: "8", labelVi: "Từ 8 điểm", labelEn: "8+ rating" },
];
const SORTS = [
  { id: "popularity", labelVi: "Phổ biến nhất", labelEn: "Most popular" },
  { id: "rating", labelVi: "Điểm cao nhất", labelEn: "Highest rated" },
  { id: "newest", labelVi: "Mới nhất", labelEn: "Newest" },
  { id: "oldest", labelVi: "Cũ nhất", labelEn: "Oldest" },
  { id: "title", labelVi: "Tên A - Z", labelEn: "Title A - Z" },
];
const PEOPLE_LABEL = {
  director: ["Đạo diễn", "Director"],
  actor: ["Diễn viên", "Actor"],
  voice: ["Lồng tiếng", "Voice cast"],
  keyword: ["Từ khóa", "Keyword"],
};
const GROUPS = [
  ["movies", "Phim", "Movies"],
  ["director", "Đạo diễn", "Directors"],
  ["actor", "Diễn viên", "Actors"],
  ["voice", "Lồng tiếng", "Voice Cast"],
  ["keyword", "Từ khóa", "Keywords"],
];

const loadFilters = () => {
  try {
    return { ...DEFAULTS, ...JSON.parse(sessionStorage.getItem(KEY)) };
  } catch {
    return DEFAULTS;
  }
};

// Dùng từ trang chi tiết: bấm tên đạo diễn / diễn viên / từ khóa là sang Khám phá với bộ lọc đó
export function presetBrowse(patch) {
  sessionStorage.setItem(KEY, JSON.stringify({ ...DEFAULTS, ...patch }));
}

function SearchBox({ value, onChange, onPick }) {
  const [open, setOpen] = useState(false);
  const [sug, setSug] = useState(null);
  const [active, setActive] = useState(-1);
  const box = useRef(null);
  const dv = useDebounced(value, 200);
  const { tr } = useLang();

  useEffect(() => {
    if (dv.trim().length < 2) {
      setSug(null);
      return;
    }
    let off = false;
    api
      .suggest(dv.trim())
      .then((r) => {
        if (off) return;
        setSug(r);
        setActive(-1);
      })
      .catch(() => {});
    return () => {
      off = true;
    };
  }, [dv]);

  useEffect(() => {
    const h = (e) => box.current && !box.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const options = useMemo(() => {
    if (!sug) return [];
    return GROUPS.flatMap(([kind, labelVi, labelEn]) =>
      (sug[kind] ?? []).map((it) => ({
        kind,
        label: tr(labelVi, labelEn),
        text: it.title ?? it.name,
        hint: kind === "movies" ? (it.release_year ?? "") : `${it.count} ${tr("phim", "movies")}`,
        id: it.movie_id,
      }))
    );
  }, [sug, tr]);
  const showList = open && options.length > 0;

  const pick = (o) => {
    setOpen(false);
    if (o.kind === "movies") window.location.hash = `#/movie/${o.id}`;
    else onPick(o.kind, o.text);
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown" && options.length) {
      e.preventDefault();
      setOpen(true);
      setActive((a) => (a + 1) % options.length);
    } else if (e.key === "ArrowUp" && options.length) {
      e.preventDefault();
      setActive((a) => (a <= 0 ? options.length - 1 : a - 1));
    } else if (e.key === "Enter" && showList && active >= 0) {
      e.preventDefault();
      pick(options[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={box} className="relative w-full md:w-[28rem]">
      <label className="relative block">
        <span className="sr-only">
          {tr("Tìm phim, đạo diễn, diễn viên hoặc từ khóa", "Search movies, directors, actors, or keywords")}
        </span>
        <Search size={18} className="absolute top-1/2 left-4 -translate-y-1/2 text-mute" />
        <input
          role="combobox"
          aria-expanded={showList}
          aria-controls="search-list"
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `opt-${active}` : undefined}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={tr("Tìm phim, đạo diễn, diễn viên, từ khóa...", "Search movies, directors, actors, keywords...")}
          className="w-full rounded-full bg-white py-2.5 pr-10 pl-11 ring-1 ring-ink/15 focus:ring-2 focus:ring-cobalt focus:outline-none"
        />
        {value && (
          <button
            type="button"
            aria-label={tr("Xóa nội dung tìm kiếm", "Clear search input")}
            onClick={() => {
              onChange("");
              setSug(null);
            }}
            className="absolute top-1/2 right-3 -translate-y-1/2 rounded-full p-1 text-mute hover:bg-ink/5"
          >
            <X size={16} />
          </button>
        )}
      </label>

      {showList && (
        <ul
          id="search-list"
          role="listbox"
          className="absolute z-20 mt-2 max-h-96 w-full overflow-auto rounded-2xl bg-white p-2 shadow-xl ring-1 ring-ink/10"
        >
          {options.map((o, i) => (
            <Fragment key={`${o.kind}-${o.text}-${i}`}>
              {(i === 0 || options[i - 1].kind !== o.kind) && (
                <li role="presentation" className="px-3 pt-2 pb-1 text-xs font-semibold text-mute">
                  {o.label}
                </li>
              )}
              <li
                id={`opt-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(o);
                }}
                onMouseEnter={() => setActive(i)}
                className={`flex cursor-pointer items-center justify-between gap-3 rounded-xl px-3 py-2 ${
                  i === active ? "bg-paper" : ""
                }`}
              >
                <span className="truncate">{o.text}</span>
                <span className="shrink-0 text-xs text-mute">{o.hint}</span>
              </li>
            </Fragment>
          ))}
        </ul>
      )}
    </div>
  );
}

const selectCls = "rounded-full bg-white px-3 py-2 text-sm font-medium ring-1 ring-ink/15";

export default function Browse({ rated, onRate }) {
  const [f, setF] = useState(loadFilters);
  const [genreList, setGenreList] = useState([]);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [state, setState] = useState("loading");
  const dq = useDebounced(f.query);
  const { lang, tr } = useLang();
  const set = (patch) => setF((prev) => ({ ...prev, ...patch }));

  useEffect(() => {
    sessionStorage.setItem(KEY, JSON.stringify(f));
  }, [f]);

  useEffect(() => {
    api.genres().then((g) => setGenreList(g.filter((x) => x.count >= 50))).catch(() => {});
  }, []);

  const params = (pageNo) => {
    const y = YEARS.find((x) => x.id === f.years);
    return {
      query: dq.trim(),
      genres: f.genres.join(","),
      director: f.director,
      actor: f.actor,
      voice: f.voice,
      keyword: f.keyword,
      year_from: y?.from,
      year_to: y?.to,
      min_rating: f.rating,
      sort: f.sort,
      page: pageNo,
    };
  };

  const filterKey = [dq, f.genres.join(), f.director, f.actor, f.voice, f.keyword, f.years, f.rating, f.sort].join("|");
  useEffect(() => {
    let off = false;
    setState("loading");
    api
      .movies(params(1))
      .then((r) => {
        if (off) return;
        setItems(r.items);
        setTotal(r.total);
        setPage(1);
        setState("ok");
      })
      .catch(() => !off && setState("error"));
    return () => {
      off = true;
    };
  }, [filterKey]);

  const more = async () => {
    try {
      const r = await api.movies(params(page + 1));
      setItems((i) => [...i, ...r.items]);
      setPage(page + 1);
    } catch {
      setState("error");
    }
  };

  const toggleGenre = (g) =>
    set({ genres: f.genres.includes(g) ? f.genres.filter((x) => x !== g) : [...f.genres, g] });

  const yearEntry = YEARS.find((x) => x.id === f.years);
  const active = [
    ...f.genres.map((g) => ({ key: `g-${g}`, label: g, clear: () => toggleGenre(g) })),
    ...["director", "actor", "voice", "keyword"]
      .filter((k) => f[k])
      .map((k) => ({
        key: k,
        label: `${tr(PEOPLE_LABEL[k][0], PEOPLE_LABEL[k][1])}: ${f[k]}`,
        clear: () => set({ [k]: "" }),
      })),
    ...(f.years && yearEntry
      ? [{ key: "years", label: tr(yearEntry.labelVi, yearEntry.labelEn), clear: () => set({ years: "" }) }]
      : []),
    ...(f.rating
      ? [{ key: "rating", label: tr(`Từ ${f.rating} điểm`, `${f.rating}+ rating`), clear: () => set({ rating: "" }) }]
      : []),
    ...(dq.trim() ? [{ key: "q", label: `"${dq.trim()}"`, clear: () => set({ query: "" }) }] : []),
  ];

  const chip = (on) =>
    `rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
      on ? "bg-ink text-white" : "bg-white ring-1 ring-ink/15 hover:bg-ink/5"
    }`;

  const localeStr = lang === "en" ? "en-US" : "vi-VN";

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">{tr("Khám phá phim", "Explore Movies")}</h1>

      <div className="mt-6 flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center">
        <SearchBox
          value={f.query}
          onChange={(v) => set({ query: v })}
          onPick={(kind, name) => set({ [kind]: name, query: "" })}
        />
        <select
          aria-label={tr("Năm phát hành", "Release year")}
          value={f.years}
          onChange={(e) => set({ years: e.target.value })}
          className={selectCls}
        >
          {YEARS.map((y) => (
            <option key={y.id} value={y.id}>
              {tr(y.labelVi, y.labelEn)}
            </option>
          ))}
        </select>
        <select
          aria-label={tr("Điểm đánh giá", "Rating")}
          value={f.rating}
          onChange={(e) => set({ rating: e.target.value })}
          className={selectCls}
        >
          {RATINGS.map((r) => (
            <option key={r.id} value={r.id}>
              {tr(r.labelVi, r.labelEn)}
            </option>
          ))}
        </select>
        <select
          aria-label={tr("Sắp xếp", "Sort by")}
          value={f.sort}
          onChange={(e) => set({ sort: e.target.value })}
          className={`${selectCls} md:ml-auto`}
        >
          {SORTS.map((s) => (
            <option key={s.id} value={s.id}>
              {tr(s.labelVi, s.labelEn)}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button className={chip(f.genres.length === 0)} onClick={() => set({ genres: [] })}>
          {tr("Tất cả", "All")}
        </button>
        {genreList.map((g) => (
          <button
            key={g.name}
            aria-pressed={f.genres.includes(g.name)}
            className={chip(f.genres.includes(g.name))}
            onClick={() => toggleGenre(g.name)}
          >
            {g.name}
          </button>
        ))}
      </div>

      <div className="mt-5 flex min-h-8 flex-wrap items-center gap-2 text-sm">
        {state === "ok" && (
          <span className="font-semibold">
            {total.toLocaleString(localeStr)} {tr("phim", "movies")}
          </span>
        )}
        {active.map((a) => (
          <span
            key={a.key}
            className="inline-flex items-center gap-1 rounded-full bg-cobalt/10 py-1 pr-1 pl-3 font-medium text-cobalt"
          >
            {a.label}
            <button
              aria-label={tr(`Bỏ lọc ${a.label}`, `Remove filter ${a.label}`)}
              onClick={a.clear}
              className="rounded-full p-1 hover:bg-cobalt/15"
            >
              <X size={14} />
            </button>
          </span>
        ))}
        {active.length > 0 && (
          <button onClick={() => setF({ ...DEFAULTS })} className="font-semibold underline underline-offset-4">
            {tr("Xóa tất cả", "Clear all")}
          </button>
        )}
      </div>

      <div className="mt-6">
        {state === "error" && (
          <Notice title={tr("Không tải được danh sách phim", "Could not load movies")}>
            {tr(
              "Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.",
              "Please check that the API server is running and reload the page."
            )}
          </Notice>
        )}
        {state === "ok" && items.length === 0 && (
          <Notice
            title={tr("Không có phim nào khớp", "No matching movies")}
            action={
              <button
                onClick={() => setF({ ...DEFAULTS })}
                className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white"
              >
                {tr("Xóa bộ lọc", "Clear filters")}
              </button>
            }
          >
            {tr(
              "Thử bỏ bớt bộ lọc, hoặc gõ tên phim, đạo diễn, diễn viên để xem gợi ý.",
              "Try removing some filters, or type a movie title, director, or actor to see suggestions."
            )}
          </Notice>
        )}
        {state === "loading" && (
          <div className={GRID}>
            {Array.from({ length: 12 }, (_, i) => (
              <div key={i} className="aspect-[2/3] animate-pulse rounded-xl bg-ink/10" />
            ))}
          </div>
        )}
        {state === "ok" && items.length > 0 && (
          <>
            <div className={GRID}>
              {items.map((m) => (
                <MovieCard key={m.movie_id} movie={m} status={rated[m.movie_id]} onRate={onRate} />
              ))}
            </div>
            {items.length < total && (
              <div className="mt-10 text-center">
                <p className="mb-3 text-sm text-mute">
                  {tr(
                    `Đang hiện ${items.length} / ${total.toLocaleString(localeStr)} phim`,
                    `Showing ${items.length} of ${total.toLocaleString(localeStr)} movies`
                  )}
                </p>
                <button
                  onClick={more}
                  className="rounded-full bg-white px-8 py-3 font-semibold ring-1 ring-ink/20 hover:bg-ink/5"
                >
                  {tr("Xem thêm phim", "Load more movies")}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
