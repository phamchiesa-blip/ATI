import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { api } from "./api";
import { Poster } from "./ui";

// Dùng khi chưa tải được phim ngẫu nhiên từ máy chủ
const FALLBACK = [
  { title: "Inception", genres: ["Science Fiction", "Action"], release_year: 2010 },
  { title: "Up", genres: ["Animation", "Family"], release_year: 2009 },
  { title: "Se7en", genres: ["Crime", "Thriller"], release_year: 1995 },
  { title: "Amélie", genres: ["Comedy", "Romance"], release_year: 2001 },
  { title: "Whiplash", genres: ["Drama", "Music"], release_year: 2014 },
  { title: "Alien", genres: ["Horror", "Science Fiction"], release_year: 1979 },
];

const toGroups = (items) => {
  const out = [];
  for (let i = 0; i + 2 < items.length; i += 3) out.push(items.slice(i, i + 3));
  return out;
};

// 3 poster ngẫu nhiên: hiện dần từ khoảng trống và trượt lên, vài giây sau đổi sang bộ khác.
export default function Showcase() {
  const [list, setList] = useState(null);
  const [step, setStep] = useState(0);
  const calm = useReducedMotion();

  useEffect(() => {
    let off = false;
    api
      .showcase(12)
      .then((r) => !off && setList(r.items.length >= 3 ? r.items : FALLBACK))
      .catch(() => !off && setList(FALLBACK));
    return () => {
      off = true;
    };
  }, []);

  const groups = list ? toGroups(list) : [];
  useEffect(() => {
    if (groups.length < 2) return;
    const t = setInterval(() => setStep((s) => (s + 1) % groups.length), 5000);
    return () => clearInterval(t);
  }, [groups.length]);

  const parent = {
    hidden: {},
    show: { transition: { staggerChildren: 0.18 } },
    exit: { transition: { staggerChildren: 0.06 } },
  };
  const child = {
    hidden: { opacity: 0, y: calm ? 0 : 48 },
    show: { opacity: 1, y: 0, transition: { duration: 1, ease: [0.22, 1, 0.36, 1] } },
    exit: { opacity: 0, y: calm ? 0 : -28, transition: { duration: 0.5 } },
  };

  return (
    <div className="mt-10 max-w-md" aria-hidden>
      {groups.length === 0 ? (
        <div className="aspect-[3/2.4]" />
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            variants={parent}
            initial="hidden"
            animate="show"
            exit="exit"
            className="grid grid-cols-3 gap-3"
          >
            {groups[step % groups.length].map((m, i) => (
              <motion.div key={m.movie_id ?? m.title} variants={child} style={{ marginTop: i === 1 ? 24 : 0 }}>
                <Poster movie={m} />
              </motion.div>
            ))}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}