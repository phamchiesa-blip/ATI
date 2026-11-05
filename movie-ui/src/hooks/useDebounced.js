/**
 * hooks/useDebounced.js
 * ---------------------
 * Custom hook tri hoan gia tri (debounce) khi nguoi dung go tim kiem.
 */
import { useEffect, useState } from "react";

export function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

