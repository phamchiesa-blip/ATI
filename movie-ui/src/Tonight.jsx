import { useContext, useEffect, useState } from "react";
import { AlertCircle, Bookmark, MessageSquare, Play, Plus, RotateCcw, Send, Shuffle, Sparkles, SlidersHorizontal, X } from "lucide-react";
import { api } from "./services/apiClient";
import { MovieCard, Notice } from "./components/MovieCard";
import { Overview, PosterLink, RateButtons } from "./components/Poster";
import { GRID, toneOf } from "./utils/theme";
import { TrailerContext, WatchlistContext, useLang } from "./context/AppContexts";
import { genreLabel, translateBackendText } from "./utils/i18nHelpers";

const FOLLOWUP_CHIPS = [
  { labelVi: "Nhẹ nhàng hơn nữa", labelEn: "Lighter mood", text: "Cho mình cái nhẹ nhàng hơn nữa" },
  { labelVi: "Kịch tính hơn", labelEn: "More thrilling", text: "Cho mình phim kịch tính, hồi hộp hơn" },
  { labelVi: "Phim mới hơn (từ 2012)", labelEn: "Newer movies (from 2012)", text: "Chọn phim mới hơn gần đây" },
  { labelVi: "Phim ngắn (< 100 phút)", labelEn: "Short movies (< 100m)", text: "Chọn phim ngắn dưới 100 phút" },
  { labelVi: "Bỏ Kinh dị & Tâm lý nặng", labelEn: "No Horror & heavy Drama", text: "Tránh kinh dị và tâm lý bi kịch" },
];

const QUICK_SUG_EN = {
  chill: "Lighthearted & relaxing for the weekend",
  light: "Lighthearted & relaxing, no horror",
  mindblow: "Mind-bending sci-fi like Inception",
  family: "Fun family animation",
  thriller: "Gripping crime & mystery thriller",
  thrill: "Suspenseful crime thriller under 2 hours",
  romance: "Emotional & romantic",
  action_new: "2010s epic action & adventure",
  action90s: "90s action blockbusters",
};

const MOOD_EN = {
  happy: "Fun & lighthearted",
  thrill: "Thrilling & suspenseful",
  touching: "Touching & emotional",
  excited: "Exciting & epic",
  scary: "Scary & spooky",
  dreamy: "Dreamy & magical",
  romantic: "Romantic",
  think: "Thought-provoking",
};

const TIME_EN = {
  short: "Under 100 min",
  medium: "Around 2 hours",
  any: "Any length",
};

const INITIAL_VISIBLE_RECOMMENDATIONS = 8;
const RECOMMENDATION_PAGE_SIZE = 6;

// Store a UI error code rather than the raw API message. The API currently
// returns Vietnamese detail strings, so rendering them directly mixes the two
// languages whenever the visitor switches to English.
function errorText(kind, tr) {
  if (kind === "offline") {
    return tr(
      "Chưa kết nối được máy chủ. Hãy kiểm tra máy chủ API rồi thử lại.",
      "Could not connect to the server. Please check that the API is running and try again."
    );
  }
  if (kind === "unrecognized") {
    return tr(
      "Hệ thống chưa hiểu yêu cầu tìm phim của bạn. Vui lòng mô tả tâm trạng, thể loại, thời kỳ hoặc tên phim cụ thể.",
      "We could not understand your movie request. Please describe a mood, genre, era, or a specific movie."
    );
  }
  return tr("Chưa chọn được phim. Hãy thử lại.", "Could not pick a movie. Please try again.");
}

function Pick({ movie, status, onRate, onNext, hasNext }) {
  const openTrailer = useContext(TrailerContext);
  const { saved, toggle } = useContext(WatchlistContext);
  const { lang, tr } = useLang();
  const on = saved.has(movie.movie_id);
  const displayWhy = translateBackendText(movie.why, lang);
  return (
    <section className="grid gap-8 rounded-3xl bg-white p-6 ring-1 ring-ink/10 md:grid-cols-[260px_1fr] md:p-10">
      <PosterLink movie={movie} size="lg" showTitle={false} />
      <div className="max-w-xl">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-cobalt">{displayWhy}</p>
          {movie.match_percent != null && (
            <span className="rounded-full bg-cobalt/10 px-2.5 py-0.5 text-xs font-bold text-cobalt">
              {movie.match_percent}% {tr("độ hợp", "match")}
            </span>
          )}
        </div>
        <h2 className="mt-2 font-display text-4xl leading-tight font-extrabold md:text-5xl">
          <a href={`#/movie/${movie.movie_id}`} className="hover:text-cobalt">
            {movie.title}
          </a>
        </h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {movie.genres.map((g) => (
            <span key={g} className="rounded-full bg-paper px-3 py-1 text-sm font-medium">
              {genreLabel(g, lang)}
            </span>
          ))}
          {movie.release_year && (
            <span className="rounded-full bg-ink/5 px-3 py-1 text-sm text-mute">{movie.release_year}</span>
          )}
          {movie.runtime && (
            <span className="rounded-full bg-ink/5 px-3 py-1 text-sm text-mute">
              {movie.runtime} {tr("phút", "min")}
            </span>
          )}
        </div>
        <Overview movie={movie} className="mt-4 line-clamp-4 leading-relaxed text-mute" />
        {movie.director && (
          <p className="mt-3 text-sm">
            {tr("Đạo diễn", "Director")} {movie.director}
          </p>
        )}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={() => openTrailer(movie)}
            className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 font-semibold text-white hover:bg-ink/85"
          >
            <Play size={16} className="fill-white" /> {tr("Xem trailer", "Watch trailer")}
          </button>
          <button
            onClick={() => toggle(movie)}
            aria-pressed={on}
            className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 font-semibold ring-1 ring-ink/20 hover:bg-ink/5"
          >
            <Bookmark size={16} className={on ? "fill-current" : ""} />{" "}
            {on ? tr("Đã lưu", "Saved") : tr("Xem sau", "Watchlist")}
          </button>
          {hasNext && (
            <button
              onClick={onNext}
              className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-semibold text-cobalt ring-1 ring-cobalt/40 hover:bg-cobalt/5"
            >
              <Shuffle size={16} /> {tr("Đổi phim khác", "Next movie")}
            </button>
          )}
        </div>
        <div className="mt-5 max-w-sm">
          <RateButtons status={status} onRate={(a) => onRate(movie, a)} />
        </div>
      </div>
    </section>
  );
}

// Khung hiển thị "Mình hiểu bạn muốn: ... · Tránh: ..." cho phép sửa/bỏ/thêm thể loại trực tiếp
function IntentBanner({ intent, genreLabels, onUpdateIntent }) {
  const [addingWant, setAddingWant] = useState(false);
  const [addingAvoid, setAddingAvoid] = useState(false);
  const { lang, tr } = useLang();

  if (!intent) return null;

  const genreMap = Object.fromEntries(
    (genreLabels || []).map((g) => [g.id, genreLabel(g.id, lang)])
  );
  const wanted = intent.wanted_genres || [];
  const avoid = intent.avoid_genres || [];
  const simMovies = intent.similar_movies || [];

  const removeWanted = (g) => {
    onUpdateIntent({
      ...intent,
      wanted_genres: wanted.filter((x) => x !== g),
    });
  };

  const addWanted = (g) => {
    setAddingWant(false);
    if (!g || wanted.includes(g)) return;
    onUpdateIntent({
      ...intent,
      wanted_genres: [...wanted, g],
      avoid_genres: avoid.filter((x) => x !== g),
    });
  };

  const removeAvoid = (g) => {
    onUpdateIntent({
      ...intent,
      avoid_genres: avoid.filter((x) => x !== g),
    });
  };

  const addAvoid = (g) => {
    setAddingAvoid(false);
    if (!g || avoid.includes(g)) return;
    onUpdateIntent({
      ...intent,
      avoid_genres: [...avoid, g],
      wanted_genres: wanted.filter((x) => x !== g),
    });
  };

  const removeSimilar = (mid) => {
    onUpdateIntent({
      ...intent,
      similar_movie_ids: simMovies.filter((m) => m.movie_id !== mid).map((m) => m.movie_id),
    });
  };

  const clearYear = () => {
    onUpdateIntent({
      ...intent,
      year_from: null,
      year_to: null,
    });
  };

  const clearRuntime = () => {
    onUpdateIntent({
      ...intent,
      max_runtime: null,
    });
  };

  const clearKeyword = () => {
    onUpdateIntent({
      ...intent,
      matched_keywords: [],
      matched_keyword_display: "",
    });
  };

  return (
    <div className="mt-6 rounded-2xl bg-cobalt/5 p-4 ring-1 ring-cobalt/20 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-display text-base font-extrabold text-ink md:text-lg">
          {translateBackendText(intent.summary_line, lang)}
        </p>
        <span className="rounded-full bg-white px-3 py-0.5 text-xs font-semibold text-mute ring-1 ring-ink/10">
          {intent.parser_source === "llm"
            ? tr("Phân tích bằng AI", "Understood by AI")
            : tr("Phân tích nhanh", "Quick match")}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold text-mute">{tr("Muốn xem:", "Want:")}</span>
        {wanted.map((g) => (
          <span
            key={g}
            className="inline-flex items-center gap-1 rounded-full bg-cobalt px-3 py-1 font-semibold text-white"
          >
            {genreMap[g] || g}
            <button
              type="button"
              onClick={() => removeWanted(g)}
              title={tr(`Bỏ thể loại ${genreMap[g] || g}`, `Remove ${genreMap[g] || g}`)}
              className="rounded-full p-0.5 hover:bg-white/20"
            >
              <X size={12} />
            </button>
          </span>
        ))}
        {simMovies.map((m) => (
          <span
            key={m.movie_id}
            className="inline-flex items-center gap-1 rounded-full bg-ink px-3 py-1 font-semibold text-white"
          >
            {tr("Giống:", "Similar to:")} {m.title}
            <button
              type="button"
              onClick={() => removeSimilar(m.movie_id)}
              title={tr(`Bỏ giống ${m.title}`, `Remove ${m.title}`)}
              className="rounded-full p-0.5 hover:bg-white/20"
            >
              <X size={12} />
            </button>
          </span>
        ))}
        {(intent.year_from || intent.year_to) && (
          <span className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 font-semibold text-ink ring-1 ring-ink/15">
            {tr("Năm:", "Year:")} {intent.year_from || "..."}–{intent.year_to || tr("nay", "now")}
            <button type="button" onClick={clearYear} className="rounded-full p-0.5 hover:bg-ink/10">
              <X size={12} />
            </button>
          </span>
        )}
        {intent.max_runtime && (
          <span className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 font-semibold text-ink ring-1 ring-ink/15">
            &le; {intent.max_runtime} {tr("phút", "min")}
            <button type="button" onClick={clearRuntime} className="rounded-full p-0.5 hover:bg-ink/10">
              <X size={12} />
            </button>
          </span>
        )}
        {intent.matched_keyword_display && (
          <span className="inline-flex items-center gap-1 rounded-full bg-lemon px-3 py-1 font-semibold text-ink ring-1 ring-ink/15">
            {tr("Từ khóa:", "Keyword:")} {intent.matched_keyword_display}
            <button
              type="button"
              onClick={clearKeyword}
              title={tr(`Bỏ từ khóa ${intent.matched_keyword_display}`, `Remove keyword ${intent.matched_keyword_display}`)}
              className="rounded-full p-0.5 hover:bg-ink/10"
            >
              <X size={12} />
            </button>
          </span>
        )}

        {addingWant ? (
          <select
            aria-label={tr("Thêm thể loại muốn xem", "Add wanted genre")}
            autoFocus
            defaultValue=""
            onChange={(e) => addWanted(e.target.value)}
            onBlur={() => setAddingWant(false)}
            className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold ring-1 ring-cobalt"
          >
            <option value="" disabled>
              {tr("+ Chọn thể loại...", "+ Select genre...")}
            </option>
            {(genreLabels || [])
              .filter((g) => !wanted.includes(g.id))
              .map((g) => (
                <option key={g.id} value={g.id}>
                  {genreLabel(g.id, lang)}
                </option>
              ))}
          </select>
        ) : (
          <button
            type="button"
            onClick={() => setAddingWant(true)}
            className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-1 font-semibold text-cobalt ring-1 ring-cobalt/30 hover:bg-cobalt/10"
          >
            <Plus size={12} /> {tr("Thêm thể loại", "Add genre")}
          </button>
        )}

        <span className="ml-2 font-semibold text-mute">{tr("· Tránh:", "· Avoid:")}</span>
        {avoid.map((g) => (
          <span
            key={g}
            className="inline-flex items-center gap-1 rounded-full bg-coral/15 px-3 py-1 font-semibold text-coral ring-1 ring-coral/30"
          >
            {genreMap[g] || g}
            <button
              type="button"
              onClick={() => removeAvoid(g)}
              title={tr(`Bỏ tránh ${genreMap[g] || g}`, `Remove ${genreMap[g] || g}`)}
              className="rounded-full p-0.5 hover:bg-coral/20"
            >
              <X size={12} />
            </button>
          </span>
        ))}

        {addingAvoid ? (
          <select
            aria-label={tr("Thêm thể loại muốn tránh", "Add avoided genre")}
            autoFocus
            defaultValue=""
            onChange={(e) => addAvoid(e.target.value)}
            onBlur={() => setAddingAvoid(false)}
            className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold ring-1 ring-coral"
          >
            <option value="" disabled>
              {tr("+ Tránh thể loại...", "+ Avoid genre...")}
            </option>
            {(genreLabels || [])
              .filter((g) => !avoid.includes(g.id))
              .map((g) => (
                <option key={g.id} value={g.id}>
                  {genreLabel(g.id, lang)}
                </option>
              ))}
          </select>
        ) : (
          <button
            type="button"
            onClick={() => setAddingAvoid(true)}
            className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-1 font-semibold text-mute ring-1 ring-ink/15 hover:bg-ink/5"
          >
            <Plus size={12} /> {tr("Thêm loại trừ", "Add exclusion")}
          </button>
        )}
      </div>
      <p className="mt-2 text-xs text-mute">
        {tr(
          "Hiểu sai ý bạn? Hãy bấm × hoặc + Thêm ở trên để chỉnh lại ngay, hoặc gõ câu tiếp theo bên dưới.",
          "Misunderstood? Click × or + Add above to adjust directly, or type a follow-up message below."
        )}
      </p>
    </div>
  );
}

// "Hôm nay xem gì?": Gợi ý phim qua hội thoại (Conversational Recommender) + Chọn nhanh theo nút
export default function Tonight({ rated, onRate }) {
  const [options, setOptions] = useState(null);
  const [tabMode, setTabMode] = useState("chat"); // "chat" | "buttons"
  const { lang, tr } = useLang();

  // State cho chế độ Chat Bot
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState([]); // [{ userText, summary, count, isFollowup }]
  const [currentIntent, setCurrentIntent] = useState(null);
  const [useLlm, setUseLlm] = useState(true);

  // State cho chế độ chọn nút truyền thống (giữ lại làm tùy chọn phụ)
  const [mood, setMood] = useState("");
  const [time, setTime] = useState("any");

  // Danh sách kết quả chung
  const [queue, setQueue] = useState(null);
  const [cursor, setCursor] = useState(0);
  const [visibleRecommendationCount, setVisibleRecommendationCount] = useState(INITIAL_VISIBLE_RECOMMENDATIONS);
  const [done, setDone] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const localizedError = errorText(error, tr);

  useEffect(() => {
    api
      .tonightOptions()
      .then(setOptions)
      .catch(() => setError("offline"));
  }, []);

  // Gửi câu hỏi vào Chat Bot
  const sendChat = async (textToSend, overrideIntent = null) => {
    const msg = (textToSend ?? input).trim();
    if (!msg && !overrideIntent) return;
    setBusy(true);
    setError("");
    try {
      const r = await api.tonightChat({
        message: msg,
        previous_intent: currentIntent,
        intent_override: overrideIntent,
        exclude: [],
        top_n: 24,
        use_llm: useLlm,
      });
      setCurrentIntent(r.intent);
      setQueue(r.items);
      setCursor(0);
      setVisibleRecommendationCount(INITIAL_VISIBLE_RECOMMENDATIONS);
      setDone(r.items.length === 0);
      setNote(
        r.intent?.max_runtime && !r.runtime_filter_applied
          ? tr(
              "Chưa lọc được theo thời lượng vì thiếu dữ liệu thời lượng phim (cần file CSV gốc).",
              "Runtime filter not applied because movie runtime data is missing (requires original CSV)."
            )
          : ""
      );
      if (msg) {
        setTurns((prev) => [
          ...prev,
          {
            userText: msg,
            summary: r.intent.summary_line,
            count: r.items.length,
            isFollowup: r.intent.is_followup,
          },
        ]);
        setInput("");
      } else if (overrideIntent) {
        setTurns((prev) => [
          ...prev,
          {
            userText: tr("(Đã chỉnh trực tiếp bộ lọc thể loại)", "(Adjusted genre filters directly)"),
            summary: r.intent.summary_line,
            count: r.items.length,
            isFollowup: true,
          },
        ]);
      }
    } catch (e) {
      setError(
        e.status === 0 ? "offline" : "unrecognized"
      );
      setQueue(null);
      setCurrentIntent(null);
    }
    setBusy(false);
  };

  // Xử lý khi người dùng sửa tag trực tiếp trên thanh "Mình hiểu bạn muốn..."
  const handleUpdateIntent = (patchedIntent) => {
    sendChat("", {
      wanted_genres: patchedIntent.wanted_genres,
      avoid_genres: patchedIntent.avoid_genres,
      similar_movie_ids:
        patchedIntent.similar_movie_ids ??
        (patchedIntent.similar_movies || []).map((m) => m.movie_id),
      matched_keywords: patchedIntent.matched_keywords,
      matched_keyword_display: patchedIntent.matched_keyword_display,
      year_from: patchedIntent.year_from,
      year_to: patchedIntent.year_to,
      max_runtime: patchedIntent.max_runtime,
    });
  };

  const resetChat = () => {
    setTurns([]);
    setCurrentIntent(null);
    setQueue(null);
    setCursor(0);
    setVisibleRecommendationCount(INITIAL_VISIBLE_RECOMMENDATIONS);
    setNote("");
    setError("");
    setInput("");
  };

  // Chế độ nút bấm cũ
  const fetchMoreButtons = async (exclude) => {
    const r = await api.tonight(mood, time, exclude);
    setNote(
      time !== "any" && !r.runtime_filter_applied
        ? tr(
            "Chưa lọc được theo thời lượng vì thiếu dữ liệu thời lượng phim (cần file CSV gốc).",
            "Runtime filter not applied because movie runtime data is missing (requires original CSV)."
          )
        : ""
    );
    return r.items;
  };

  const startButtons = async () => {
    setBusy(true);
    setError("");
    try {
      const items = await fetchMoreButtons([]);
      setCurrentIntent(null);
      setQueue(items);
      setCursor(0);
      setVisibleRecommendationCount(INITIAL_VISIBLE_RECOMMENDATIONS);
      setDone(items.length === 0);
    } catch (e) {
      setError(
        e.status === 0 ? "offline" : "request"
      );
    }
    setBusy(false);
  };

  const next = async () => {
    const nextIndex = cursor + 1;
    if (tabMode === "buttons" && nextIndex + 4 >= queue.length && !done) {
      try {
        const more = await fetchMoreButtons(queue.map((m) => m.movie_id));
        if (more.length === 0) setDone(true);
        else setQueue((q) => [...q, ...more]);
      } catch {
        /* giữ nguyên danh sách hiện có */
      }
    }
    if (nextIndex < queue.length) setCursor(nextIndex);
    else setCursor(0);
  };

  const pick = queue?.[cursor];
  const others = queue ? queue.filter((_, index) => index !== cursor) : [];
  const suggestions = options?.quick_suggestions || [];

  return (
    <main className="mx-auto max-w-[1500px] px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-extrabold">
            {tr("Hôm nay bạn muốn xem gì?", "What do you want to watch today?")}
          </h1>
        </div>

        <div
          role="group"
          aria-label={tr("Chế độ chọn phim", "Movie selection mode")}
          className="inline-flex rounded-full bg-white p-1 ring-1 ring-ink/15"
        >
          <button
            onClick={() => setTabMode("chat")}
            aria-pressed={tabMode === "chat"}
            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
              tabMode === "chat" ? "bg-ink text-white" : "hover:bg-ink/5"
            }`}
          >
            <MessageSquare size={15} /> {tr("Trò chuyện tìm phim", "Chat Recommender")}
          </button>
          <button
            onClick={() => setTabMode("buttons")}
            aria-pressed={tabMode === "buttons"}
            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
              tabMode === "buttons" ? "bg-ink text-white" : "hover:bg-ink/5"
            }`}
          >
            <SlidersHorizontal size={15} /> {tr("Chọn theo tâm trạng", "Pick by Mood")}
          </button>
        </div>
      </div>

      {tabMode === "chat" ? (
        <section className="mt-6 rounded-3xl bg-white p-6 ring-1 ring-ink/10 md:p-8">
          {/* Lịch sử các lượt hội thoại ngắn gọn */}
          {turns.length > 0 && (
            <div className="mb-5 space-y-2.5 border-b border-ink/10 pb-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider text-mute uppercase">
                  {tr(
                    `Hội thoại đang diễn ra (${turns.length} lượt)`,
                    `Active conversation (${turns.length} ${turns.length === 1 ? "turn" : "turns"})`
                  )}
                </span>
                <button
                  type="button"
                  onClick={resetChat}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-cobalt hover:underline"
                >
                  <RotateCcw size={13} /> {tr("Bắt đầu cuộc trò chuyện mới", "Start new conversation")}
                </button>
              </div>
              <ul className="max-h-44 space-y-2 overflow-y-auto pr-1 text-sm">
                {turns.map((t, idx) => (
                  <li key={idx} className="flex flex-col gap-1 rounded-2xl bg-paper px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-ink px-2 py-0.5 text-[11px] font-bold text-white">
                        {tr("Bạn", "You")}
                      </span>
                      <span className="font-medium text-ink">{t.userText}</span>
                    </div>
                    <p className="text-xs text-cobalt">
                      → {translateBackendText(t.summary, lang)} (
                      {tr(`${t.count} phim phù hợp`, `${t.count} matching movies`)})
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Ô nhập câu hỏi */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendChat(input);
            }}
            className="flex flex-col gap-3 sm:flex-row"
          >
            <label className="relative flex-1">
              <span className="sr-only">
                {tr("Hôm nay bạn muốn xem gì?", "What do you want to watch today?")}
              </span>
              <Sparkles size={18} className="absolute top-1/2 left-4 -translate-y-1/2 text-cobalt" />
              <input
                type="text"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  if (error) setError("");
                }}
                disabled={busy}
                placeholder={
                  turns.length > 0
                    ? tr(
                        "Gõ tiếp để tinh chỉnh (VD: “cho mình cái nhẹ hơn nữa”, “tránh kinh dị”, “từ năm 2010”)...",
                        "Type a follow-up to refine (e.g., “something lighter”, “no horror”, “from 2010”)..."
                      )
                    : tr(
                        "Hôm nay bạn muốn xem gì? (VD: “phim hài nhẹ nhàng thư giãn, tránh kinh dị” hoặc “giống Inception”)...",
                        "What do you want to watch? (e.g., “lighthearted comedy, no horror” or “like Inception”)..."
                      )
                }
                className="w-full rounded-full bg-paper py-3.5 pr-4 pl-11 text-sm font-medium ring-1 ring-ink/15 focus:ring-2 focus:ring-cobalt focus:outline-none"
              />
            </label>
            <button
              type="submit"
              disabled={!input.trim() || busy}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-cobalt px-7 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-cobalt/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={16} />
              {busy
                ? tr("Đang phân tích...", "Analyzing...")
                : turns.length > 0
                  ? tr("Tinh chỉnh", "Refine")
                  : tr("Tìm phim ngay", "Find Movies")}
            </button>
          </form>

          {/* Thông báo lỗi khi không nhận diện được yêu cầu */}
          {error && tabMode === "chat" && (
            <div
              role="alert"
              className="mt-4 flex items-start gap-3 rounded-2xl bg-coral/10 p-4 text-sm font-medium text-coral ring-1 ring-coral/25"
            >
              <AlertCircle size={20} className="mt-0.5 shrink-0 text-coral" />
              <div className="min-w-0 flex-1">
                <p className="font-bold text-coral">
                  {tr("Không nhận diện được yêu cầu", "Could not recognize request")}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-ink/80">{localizedError}</p>
              </div>
              <button
                type="button"
                onClick={() => setError("")}
                className="rounded-lg px-2 py-1 text-xs font-semibold text-coral/70 transition-colors hover:bg-coral/10 hover:text-coral"
                aria-label={tr("Đóng thông báo lỗi", "Close error message")}
              >
                ✕
              </button>
            </div>
          )}

          {/* Gợi ý bấm nhanh (khi mới vào) hoặc gợi ý tinh chỉnh nhiều lượt (khi đã có kết quả) */}
          {turns.length === 0 ? (
            <div className="mt-4">
              <p className="text-xs font-semibold text-mute">{tr("Gợi ý bấm nhanh:", "Quick suggestions:")}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    disabled={busy}
                    onClick={() => sendChat(s.prompt)}
                    className="rounded-full bg-paper px-3.5 py-1.5 text-xs font-semibold text-ink ring-1 ring-ink/10 transition-colors hover:bg-cobalt/10 hover:text-cobalt hover:ring-cobalt/30"
                  >
                    {lang === "en" ? QUICK_SUG_EN[s.id] || s.label : s.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-4">
              <p className="text-xs font-semibold text-mute">
                {tr("Tinh chỉnh tiếp câu vừa rồi (nhiều lượt hội thoại):", "Follow-up refinements (multi-turn):")}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {FOLLOWUP_CHIPS.map((c) => (
                  <button
                    key={c.labelVi}
                    type="button"
                    disabled={busy}
                    onClick={() => sendChat(c.text)}
                    className="rounded-full bg-paper px-3.5 py-1.5 text-xs font-semibold text-ink ring-1 ring-ink/10 transition-colors hover:bg-cobalt/10 hover:text-cobalt hover:ring-cobalt/30"
                  >
                    + {tr(c.labelVi, c.labelEn)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Tùy chọn bật/tắt LLM API nếu máy chủ có cấu hình key */}
          {options?.llm_available && (
            <div className="mt-4 flex items-center gap-2 text-xs text-mute">
              <input
                id="toggle-llm"
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                className="accent-cobalt"
              />
              <label htmlFor="toggle-llm">
                {tr(
                  "Dùng AI để hiểu câu bạn gõ chính xác hơn",
                  "Use AI to better understand what you type"
                )}
              </label>
            </div>
          )}

          {/* Dòng "Mình hiểu bạn muốn: ... · Tránh: ..." kèm nút chỉnh sửa trực tiếp */}
          <IntentBanner
            intent={currentIntent}
            genreLabels={options?.genre_labels}
            onUpdateIntent={handleUpdateIntent}
          />
        </section>
      ) : (
        options && (
          <div className="mt-6 rounded-3xl bg-white p-6 ring-1 ring-ink/10 md:p-8">
            <h2 className="text-sm font-semibold">{tr("Bạn đang cảm thấy thế nào?", "How are you feeling?")}</h2>
            <div
              role="radiogroup"
              aria-label={tr("Tâm trạng", "Mood")}
              className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
            >
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
                    <span className="block font-display text-lg font-bold">
                      {lang === "en" ? MOOD_EN[m.id] || m.label : m.label}
                    </span>
                    <span className="mt-0.5 block text-xs opacity-70">
                      {m.genres.map((g) => genreLabel(g, lang)).join(", ")}
                    </span>
                  </button>
                );
              })}
            </div>

            <h2 className="mt-6 text-sm font-semibold">
              {tr("Bạn có bao nhiêu thời gian?", "How much time do you have?")}
            </h2>
            <div role="radiogroup" aria-label={tr("Thời gian", "Time available")} className="mt-3 flex flex-wrap gap-2">
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
                  {lang === "en" ? TIME_EN[t.id] || t.label : t.label}
                </button>
              ))}
            </div>

            <button
              onClick={startButtons}
              disabled={!mood || busy}
              className="mt-8 rounded-full bg-cobalt px-8 py-3 font-semibold text-white transition-colors hover:bg-cobalt/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? tr("Đang chọn...", "Picking...") : tr("Chọn phim cho tôi", "Pick a movie for me")}
            </button>
            {!mood && <span className="ml-3 text-sm text-mute">{tr("Hãy chọn một tâm trạng", "Please select a mood")}</span>}
          </div>
        )
      )}

      {error && tabMode === "buttons" && (
        <p role="alert" className="mt-6 text-coral">
          {localizedError}
        </p>
      )}
      {note && <p className="mt-4 text-sm text-mute">{note}</p>}

      <div className="mt-8">
        {queue && !pick && (
          <Notice title={tr("Chưa có phim phù hợp", "No matching movies")}>
            {tr(
              "Không tìm thấy phim nào khớp toàn bộ điều kiện hiện tại. Hãy thử bỏ bớt một thể loại hoặc điều kiện lọc ở trên.",
              "No movies match all current criteria. Try removing a genre or filter condition above."
            )}
          </Notice>
        )}
        {pick && (
          <>
            <Pick
              movie={pick}
              status={rated[pick.movie_id]}
              onRate={onRate}
              onNext={next}
              hasNext={queue.length > 1}
            />
            {others.length > 0 && (
              <section className="mt-10">
                <h2 className="font-display text-2xl font-extrabold">
                  {tr(
                    `Danh sách gợi ý phù hợp khác (${others.length} phim)`,
                    `Other matching recommendations (${others.length} movies)`
                  )}
                </h2>
                <div className={`mt-4 ${GRID}`}>
                  {others.slice(0, visibleRecommendationCount).map((m) => (
                    <MovieCard
                      key={m.movie_id}
                      movie={m}
                      note={m.why || (m.runtime ? `${m.runtime} ${tr("phút", "min")}` : undefined)}
                      status={rated[m.movie_id]}
                      onRate={onRate}
                    />
                  ))}
                </div>
                {visibleRecommendationCount < others.length && (
                  <div className="mt-8 text-center">
                    <button
                      type="button"
                      onClick={() =>
                        setVisibleRecommendationCount((count) =>
                          Math.min(count + RECOMMENDATION_PAGE_SIZE, others.length)
                        )
                      }
                      className="rounded-full bg-white px-6 py-2.5 text-sm font-semibold text-cobalt ring-1 ring-cobalt/30 transition-colors hover:bg-cobalt/10"
                    >
                      {tr(
                        `Xem thêm ${Math.min(RECOMMENDATION_PAGE_SIZE, others.length - visibleRecommendationCount)} phim`,
                        `Show ${Math.min(RECOMMENDATION_PAGE_SIZE, others.length - visibleRecommendationCount)} more movies`
                      )}
                    </button>
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
