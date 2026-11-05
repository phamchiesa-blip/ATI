/**
 * hooks/useHoverPreview.js
 * ------------------------
 * Custom hook tinh toan vi tri popup xem nhanh khi re chuot vao the phim.
 */
import { useEffect, useRef, useState } from "react";

export function useHoverPreview() {
  const ref = useRef(null);
  const timer = useRef(0);
  const [pos, setPos] = useState(null);

  const hide = () => {
    clearTimeout(timer.current);
    setPos(null);
  };
  const show = () => {
    if (!window.matchMedia("(hover: hover)").matches) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      if (!ref.current) return;
      const r = ref.current.getBoundingClientRect();
      const W = 340;
      const H = 320;
      const fitsRight = r.right + 12 + W <= window.innerWidth - 8;
      setPos({
        left: fitsRight ? r.right + 12 : Math.max(8, r.left - 12 - W),
        top: Math.min(Math.max(8, r.top), Math.max(8, window.innerHeight - H - 8)),
      });
    }, 350);
  };

  useEffect(() => {
    if (!pos) return;
    const close = () => setPos(null);
    window.addEventListener("scroll", close, { passive: true });
    return () => window.removeEventListener("scroll", close);
  }, [pos]);
  useEffect(() => () => clearTimeout(timer.current), []);

  return { ref, pos, show, hide };
}

