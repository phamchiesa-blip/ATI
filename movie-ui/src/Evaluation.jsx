import { useEffect, useState } from "react";
import { api } from "./api";
import { Notice } from "./ui";
import { useLang } from "./i18n";

const KIND_COLOR = {
  reference: "#CBD5E1",
  baseline: "#56607a",
  tier1: "#2f4bff",
  tier2old: "#8EA2FF",
  tier2new: "#FFC83D",
  other: "#94A3B8",
};

const RANKER_EN = {
  "0a_Random": "Random",
  "0b_Popular": "Most Popular",
  "1_Baseline": "Baseline (cosine only)",
  "2_Tier1": "Tier 1 (Ranking)",
  "3_Tier2_Old": "Tier 2 Old (probability)",
  "3_Tier2_New": "Tier 2 New (normalized logit)",
};

const SCENARIO_EN = {
  ALL: "Overall",
  onboarding_only: "Genres only",
  interactions_m1: "Liked 1 movie",
  interactions_m3: "Liked 3 movies",
  interactions_m5: "Liked 5 movies",
  interactions_m10: "Liked 10 movies",
};

const METRIC_HINT_EN = {
  precision_at_10: "Among the top 10 recommended movies, the fraction that truly matches the simulated user's taste.",
  hit_rate_at_10: "Fraction of simulated users who get at least 1 matching movie in the top 10.",
  recall_at_10: "Out of all matching movies in the catalog, the fraction found in the top 10 (naturally low because hundreds of movies match).",
  recall_at_50: "Same as Recall@10, but measured in the top 50 recommendations.",
  f1_at_10: "Harmonic mean balancing Precision@10 and Recall@10.",
};

const fmt = (metric, v) =>
  v == null ? "–" : metric === "hit_rate_at_10" ? `${(v * 100).toFixed(1)}%` : v.toFixed(3);

function Bar({ label, value, std, max, color, text, strong }) {
  const pct = value == null ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <li className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 sm:grid-cols-[14rem_1fr_8rem]">
      <span className={`truncate text-sm ${strong ? "font-semibold" : ""}`}>{label}</span>
      <span className="h-3 rounded-full bg-ink/10" aria-hidden>
        <span className="block h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </span>
      <span className="text-right text-sm tabular-nums">
        {text}
        {std != null && <span className="text-xs text-mute"> ±{std.toFixed(2)}</span>}
      </span>
    </li>
  );
}

function Card({ title, children, hint }) {
  return (
    <section className="rounded-3xl bg-white p-6 md:p-8">
      <h2 className="font-display text-2xl font-extrabold">{title}</h2>
      {hint && <p className="mt-1 text-sm text-mute">{hint}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Table({ table }) {
  return (
    <div className="overflow-x-auto rounded-2xl ring-1 ring-ink/10">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{table.heading}</caption>
        <thead>
          <tr>
            {table.header.map((h, i) => (
              <th key={i} scope="col" className="bg-paper px-3 py-2 text-left font-semibold whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i} className="border-t border-ink/10">
              {r.map((c, j) => (
                <td key={j} className="px-3 py-2 whitespace-nowrap">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Notes({ blocks }) {
  return (
    <ol className="grid gap-5">
      {blocks.map((b, i) => (
        <li key={i}>
          <p className="font-semibold">{b.title}</p>
          {b.text && <p className="mt-1 text-sm leading-relaxed text-mute">{b.text}</p>}
          {b.points?.length > 0 && (
            <ul className="mt-1 grid list-disc gap-1.5 pl-5 text-sm leading-relaxed text-mute">
              {b.points.map((p, j) => (
                <li key={j}>{p}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}

// Trang "Đánh giá hệ thống": hiển thị kết quả benchmark mà nhóm xuất ra trong ranking_eval/results/
export default function Evaluation() {
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");
  const [metric, setMetric] = useState("precision_at_10");
  const [scenario, setScenario] = useState("ALL");
  const { lang, tr } = useLang();

  useEffect(() => {
    api
      .evaluation()
      .then((d) => {
        setData(d);
        setState(d.available ? "ok" : "empty");
      })
      .catch(() => setState("error"));
  }, []);

  if (state === "loading")
    return (
      <main className="mx-auto max-w-5xl px-5 py-8">
        <div className="h-96 animate-pulse rounded-3xl bg-ink/10" />
      </main>
    );
  if (state === "error")
    return (
      <main className="mx-auto max-w-5xl px-5 py-12">
        <Notice title={tr("Không tải được kết quả", "Could not load evaluation results")}>
          {tr(
            "Hãy kiểm tra máy chủ API đang chạy rồi tải lại trang.",
            "Please check that the API server is running and reload the page."
          )}
        </Notice>
      </main>
    );
  if (state === "empty")
    return (
      <main className="mx-auto max-w-5xl px-5 py-12">
        <Notice title={tr("Chưa có kết quả đánh giá", "No evaluation results yet")}>
          {tr(
            "Chạy benchmark ở thư mục gốc của repo: python -m ranking_eval.run_benchmark. Kết quả được ghi vào ranking_eval/results/, sau đó tải lại trang này.",
            "Run the benchmark from the repo root: python -m ranking_eval.run_benchmark. Results will be written to ranking_eval/results/, then reload this page."
          )}
        </Notice>
      </main>
    );

  const all = data.summary.ALL ?? {};
  const p10 = (r) => all[r]?.precision_at_10?.mean;
  const cur = data.metrics.find((m) => m.id === metric);
  const scenarioData = data.summary[scenario] ?? {};
  const values = data.rankers.map((r) => scenarioData[r.id]?.[metric]?.mean).filter((v) => v != null);
  const max = metric === "precision_at_10" || metric === "hit_rate_at_10" ? 1 : Math.max(...values, 0.01) * 1.15;
  const paired = data.paired?.rows.find((r) => r[0].includes("Tổng thể") && r[1].includes("Tầng 1 trừ Baseline"));
  const chip = (on) =>
    `rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${on ? "bg-ink text-white" : "bg-paper ring-1 ring-ink/15 hover:bg-ink/5"}`;

  return (
    <main className="mx-auto max-w-5xl px-5 py-8">
      <h1 className="font-display text-4xl font-extrabold">{tr("Đánh giá hệ thống", "System Evaluation")}</h1>
      <p className="mt-2 max-w-3xl text-mute">
        {tr(
          "So sánh các cách gợi ý phim bằng thử nghiệm tự động với những nhóm người dùng giả lập có sở thích rõ ràng (ví dụ người mê khoa học viễn tưởng, người mê hoạt hình gia đình).",
          "Comparing recommendation strategies using automated benchmarks with simulated user personas that have clear preferences (e.g., sci-fi fans, family animation fans)."
        )}
      </p>
      <p className="mt-4 rounded-2xl bg-lemon/40 px-4 py-3 text-sm">
        <strong>{tr("Lưu ý:", "Note:")}</strong>{" "}
        {tr(
          "đây là kết quả mô phỏng, chưa thay thế việc đánh giá với người dùng thật.",
          "these are simulation results and do not replace evaluation with real users."
        )}
        {data.run_info.length > 0 && <span className="text-mute"> {data.run_info[0]}.</span>}
      </p>

      <div className="mt-8 grid gap-6">
        <Card
          title={tr("Tóm tắt", "Summary")}
          hint={tr(
            "Precision@10 tổng thể: trong 10 phim đầu, bao nhiêu phim đúng gu người dùng giả lập.",
            "Overall Precision@10: out of the top 10 movies, how many match the simulated user's taste."
          )}
        >
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["0b_Popular", tr("Chỉ gợi ý phim phổ biến", "Popular movies only")],
              ["1_Baseline", tr("Baseline (chỉ cosine)", "Baseline (cosine only)")],
              ["2_Tier1", tr("Tầng 1 (Ranking)", "Tier 1 (Ranking)")],
            ].map(([id, label]) => (
              <div key={id} className="rounded-2xl bg-paper p-4">
                <p
                  className="font-display text-4xl font-extrabold"
                  style={id === "2_Tier1" ? { color: KIND_COLOR.tier1 } : undefined}
                >
                  {p10(id) != null ? p10(id).toFixed(3) : "–"}
                </p>
                <p className="mt-1 text-sm text-mute">{label}</p>
              </div>
            ))}
          </div>
          {paired && (
            <p className="mt-5 text-sm leading-relaxed">
              {tr("Tầng 1 so với Baseline: chênh lệch", "Tier 1 vs. Baseline: difference")}{" "}
              <strong>{paired[2]}</strong>, {tr("khoảng tin cậy 95%", "95% CI")} {paired[3]}. {paired[5]}.
            </p>
          )}
        </Card>

        <Card
          title={tr("So sánh các cách gợi ý", "Ranker Comparison")}
          hint={lang === "en" ? METRIC_HINT_EN[metric] || cur?.hint : cur?.hint}
        >
          <div className="flex flex-wrap gap-2" role="group" aria-label={tr("Chỉ số", "Metrics")}>
            {data.metrics.map((m) => (
              <button
                key={m.id}
                aria-pressed={metric === m.id}
                onClick={() => setMetric(m.id)}
                className={chip(metric === m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label={tr("Kịch bản", "Scenarios")}>
            {data.scenarios.map((s) => (
              <button
                key={s.id}
                aria-pressed={scenario === s.id}
                onClick={() => setScenario(s.id)}
                className={chip(scenario === s.id)}
              >
                {lang === "en" ? SCENARIO_EN[s.id] || s.label : s.label}
              </button>
            ))}
          </div>
          <ul className="mt-6 grid gap-3">
            {data.rankers.map((r) => {
              const cell = scenarioData[r.id]?.[metric];
              return (
                <Bar
                  key={r.id}
                  label={lang === "en" ? RANKER_EN[r.id] || r.label : r.label}
                  value={cell?.mean}
                  std={cell?.std}
                  max={max}
                  color={KIND_COLOR[r.kind] ?? KIND_COLOR.other}
                  text={fmt(metric, cell?.mean)}
                  strong={r.kind === "tier1"}
                />
              );
            })}
          </ul>
          <p className="mt-4 text-xs text-mute">
            {tr(
              "Số sau dấu ± là độ lệch chuẩn giữa các lượt giả lập. “Ngẫu nhiên” và “Phổ biến nhất” là mốc tham chiếu.",
              "Numbers after ± indicate standard deviation across simulation runs. “Random” and “Most Popular” serve as reference baselines."
            )}
          </p>
        </Card>

        {data.personas.length > 0 && (
          <Card
            title={tr("Theo từng nhóm người dùng giả lập", "By Simulated User Persona")}
            hint={tr(
              "Precision@10 của Baseline và Tầng 1 cho từng nhóm. Δ là mức Tầng 1 hơn (+) hoặc kém (-) Baseline.",
              "Precision@10 of Baseline and Tier 1 per persona. Δ shows how much Tier 1 outperforms (+) or underperforms (-) Baseline."
            )}
          >
            <ul className="grid gap-6">
              {data.personas.map((p) => {
                const base = p.precision["1_Baseline"];
                const t1 = p.precision["2_Tier1"];
                const d = base != null && t1 != null ? t1 - base : null;
                return (
                  <li key={p.id}>
                    <p className="text-sm font-semibold">
                      {p.id} · {p.name}
                      {p.external && (
                        <span
                          className="ml-2 rounded-full bg-paper px-2 py-0.5 text-xs font-medium text-mute"
                          title={tr(
                            "Tiêu chí của nhóm này nằm ngoài dữ liệu vector phim (ví dụ ngôn ngữ, nguồn chuyển thể)",
                            "Criteria for this persona lie outside the movie vector features (e.g., language, adaptation source)"
                          )}
                        >
                          {tr("ngoài vector", "external to vector")}
                        </span>
                      )}
                      {d != null && (
                        <span
                          className={`ml-3 text-xs tabular-nums ${
                            d > 0.005 ? "text-cobalt" : d < -0.005 ? "text-coral" : "text-mute"
                          }`}
                        >
                          Δ {d > 0 ? "+" : ""}
                          {d.toFixed(3)}
                        </span>
                      )}
                    </p>
                    <ul className="mt-2 grid gap-2">
                      <Bar
                        label="Baseline"
                        value={base}
                        max={1}
                        color={KIND_COLOR.baseline}
                        text={fmt("precision_at_10", base)}
                      />
                      <Bar
                        label={tr("Tầng 1 (Ranking)", "Tier 1 (Ranking)")}
                        value={t1}
                        max={1}
                        color={KIND_COLOR.tier1}
                        text={fmt("precision_at_10", t1)}
                      />
                    </ul>
                  </li>
                );
              })}
            </ul>
          </Card>
        )}

        {data.conclusions.length > 0 && (
          <Card title={tr("Nhận định của nhóm", "Team Conclusions")}>
            <Notes blocks={data.conclusions} />
          </Card>
        )}

        {data.paired && (
          <details className="rounded-3xl bg-white p-6 md:p-8">
            <summary className="cursor-pointer font-display text-2xl font-extrabold">
              {tr("Kiểm định thống kê chi tiết", "Detailed Statistical Tests")}
            </summary>
            <p className="mt-2 text-sm text-mute">
              {tr(
                "Chênh lệch Precision@10 theo cặp, khoảng tin cậy 95% bằng bootstrap (đơn vị độc lập là nhóm người dùng giả lập). Nếu khoảng tin cậy không chứa 0 thì chênh lệch có ý nghĩa thống kê.",
                "Paired Precision@10 differences and 95% bootstrap confidence intervals (with simulated user personas as independent units). If the CI excludes 0, the difference is statistically significant."
              )}
            </p>
            <div className="mt-4">
              <Table table={data.paired} />
            </div>
          </details>
        )}

        {data.dislike?.table && (
          <details className="rounded-3xl bg-white p-6 md:p-8">
            <summary className="cursor-pointer font-display text-2xl font-extrabold">{data.dislike.title}</summary>
            <div className="mt-4">
              <Table table={data.dislike.table} />
            </div>
            {data.dislike.notes.length > 0 && (
              <ol className="mt-4 grid list-decimal gap-2 pl-5 text-sm leading-relaxed text-mute">
                {data.dislike.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ol>
            )}
          </details>
        )}

        {data.limitations.length > 0 && (
          <Card title={tr("Hạn chế của cách đánh giá", "Evaluation Limitations")}>
            <Notes blocks={data.limitations} />
          </Card>
        )}
      </div>
    </main>
  );
}
