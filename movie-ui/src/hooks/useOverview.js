/**
 * hooks/useOverview.js
 * --------------------
 * Custom hook tai va cache ban dich tom tat phim (overview) theo ngon ngu hien tai.
 */
import { useEffect, useState } from "react";
import { useLang } from "../context/AppContexts";
import { api } from "../services/apiClient";

const overviewCache = new Map();

export function useOverview(movie) {
  const { lang } = useLang();
  const id = movie?.movie_id ?? movie?.id;
  const original = movie?.overview || "";
  const preset = movie?.overview_vi || null;
  const key = `${id}:${lang}`;
  const pick = () => (lang !== "vi" || !original ? original : preset ?? overviewCache.get(key) ?? null);
  const [text, setText] = useState(pick);

  useEffect(() => {
    const now = pick();
    setText(now);
    if (now !== null) return;
    let off = false;
    api
      .overview(id, "vi")
      .then((r) => {
        overviewCache.set(key, r.overview);
        if (!off) setText(r.overview);
      })
      .catch(() => !off && setText(original));
    return () => {
      off = true;
    };
  }, [key, original, preset]);

  return text; // null = dang dich
}

