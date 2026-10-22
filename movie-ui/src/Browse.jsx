import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "./api";
import { GRID, MovieCard, Notice, useDebounced } from "./ui";

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
  { id: "", label: "Mọi năm" },
  { id: "2020", label: "Từ 2020", from: 2020 },
  { id: "2010", label: "2010 - 2019", from: 2010, to: 2019 },
  { id: "2000", label: "2000 - 2009", from: 2000, to: 2009 },
  { id: "1990", label: "1990 - 1999", from: 1990, to: 1999 },
  { id: "old", label: "Trước 1990", to: 1989 },
];
const RATINGS = [
  { id: "", label: "Mọi điểm" },
  { id: "6", label: "Từ 6 điểm" },
  { id: "7", label: "Từ 7 điểm" },
  { id: "8", label: "Từ 8 điểm" },
];
const SORTS = [
  { id: "popularity", label: "Phổ biến nhất" },
  { id: "rating", label: "Điểm cao nhất" },
  { id: "newest", label: "Mới nhất" },
  { id: "oldest", label: "Cũ nhất" },
  { id: "title", label: "Tên A - Z" },
];
const PEOPLE_LABEL = {
  director: "Đạo diễn",
  actor: "Diễn viên",
  voice: "Lồng tiếng",
  keyword: "Từ khóa",
};
const GROUPS = [
  ["movies", "Phim"],
  ["director", "Đạo diễn"],
  ["actor", "Diễn viên"],
  ["voice", "Lồng tiếng"],
  ["keyword", "Từ khóa"],
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
    return GROUPS.flatMap(([kind, label]) =>
      (sug[kind] ?? []).map((it) => ({
        kind,
        label,
        text: it.title ?? it.name,
        hint: kind === "movies" ? (it.release_year ?? "") : `${it.count} phim`,
        id: it.movie_id,
      }))
    );
  }, [sug]);
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
        <span className="sr-only">Tìm phim, đạo diễn, diễn viên hoặc từ khóa</span>
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
          placeholder="Tìm phim, đạo diễn, diễn viên, từ khóa..."
          className="w-full rounded-full bg-white py-2.5 pr-10 pl-11 ring-1 ring-ink/15 focus:ring-2 focus:ring-cobalt focus:outline-none"
        />
        {value && (
          <button
            type="button"
            aria-label="Xóa nội dung tìm kiếm"
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

  const active = [
    ...f.genres.map((g) => ({ key: `g-${g}`, label: g, clear: () => toggleGenre(g) })),
    ...["director", "actor", "voice", "keyword"]
      .filter((k) => f[k])
      .map((k) => ({ key: k, label: `${PEOPLE_LABEL[k]}: ${f[k]}`, clear: () => set({ [k]: "" }) })),
    ...(f.years ? [{ key: "years", label: YEARS.find((x) => x.id === f.years).label, clear: () => set({ years: "" }) }] : []),
    ...(f.rating ? [{ key: "rating", label: `Từ ${f.rating} điểm`, clear: () => set({ rating: "" }) }] : []),
    ...(dq.trim() ? [{ key: "q", label: `"${dq.trim()}"`, clear: () => set({ query: "" }) }] : []),
  ];

  const chip = (on) =>
    `rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
      on ? "bg-ink text-white" : "bg-white ring-1 ring-ink/15 hover:bg-ink/5"
    }`;

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">Khám phá phim</h1>

      <div className="mt-6 flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center">
        <SearchBox
          value={f.query}
          onChange={(v) => set({ query: v })}
          onPick={(kind, name) => set({ [kind]: name, query: "" })}
        />
        <select aria-label="Năm phát hành" value={f.years} onChange={(e) => set({ years: e.target.value })} className={selectCls}>
          {YEARS.map((y) => (
            <option key={y.id} value={y.id}>
              {y.label}
            </option>
          ))}
        </select>
        <select aria-label="Điểm đánh giá" value={f.rating} onChange={(e) => set({ rating: e.target.value })} className={selectCls}>
          {RATINGS.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
        <select aria-label="Sắp xếp" value={f.sort} onChange={(e) => set({ sort: e.target.value })} className={`${selectCls} md:ml-auto`}>
          {SORTS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button className={chip(f.genres.length === 0)} onClick={() => set({ genres: [] })}>
          Tất cả
        </button>
        {genreList.map((g) => (
          <button key={g.name} aria-pressed={f.genres.includes(g.name)} className={chip(f.genres.includes(g.name))} onClick={() => toggleGenre(g.name)}>
            {g.name}
          </button>
        ))}
      </div>

      <div className="mt-5 flex min-h-8 flex-wrap items-center gap-2 text-sm">
        {state === "ok" && <span className="font-semibold">{total.toLocaleString("vi-VN")} phim</span>}
        {active.map((a) => (
          <span key={a.key} className="inline-flex items-center gap-1 rounded-full bg-cobalt/10 py-1 pr-1 pl-3 font-medium text-cobalt">
            {a.label}
            <button aria-label={`Bỏ lọc ${a.label}`} onClick={a.clear} className="rounded-full p-1 hover:bg-cobalt/15">
              <X size={14} />
            </button>
          </span>
        ))}
        {active.length > 0 && (
          <button onClick={() => setF({ ...DEFAULTS })} className="font-semibold underline underline-offset-4">
            Xóa tất cả
          </button>
        )}
      </div>

      <div className="mt-6">
        {state === "error" && (
          <Notice title="Không tải được danh sách phim">Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.</Notice>
        )}
        {state === "ok" && items.length === 0 && (
          <Notice
            title="Không có phim nào khớp"
            action={
              <button onClick={() => setF({ ...DEFAULTS })} className="mt-6 rounded-full bg-cobalt px-6 py-2.5 font-semibold text-white">
                Xóa bộ lọc
              </button>
            }
          >
            Thử bỏ bớt bộ lọc, hoặc gõ tên phim, đạo diễn, diễn viên để xem gợi ý.
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
                  Đang hiện {items.length} / {total.toLocaleString("vi-VN")} phim
                </p>
                <button onClick={more} className="rounded-full bg-white px-8 py-3 font-semibold ring-1 ring-ink/20 hover:bg-ink/5">
                  Xem thêm phim
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}