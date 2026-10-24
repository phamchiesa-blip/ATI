import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, X } from "lucide-react";
import { api } from "./api";

const MESSAGES = {
  no_key:
    "Chưa cấu hình TMDB API key nên chưa nhúng được trailer ngay trong trang. Bạn vẫn có thể xem trên YouTube.",
  not_found: "Chưa tìm thấy trailer cho phim này trong TMDB. Bạn có thể thử tìm trên YouTube.",
  unavailable: "Không lấy được trailer lúc này. Bạn có thể thử tìm trên YouTube.",
};

// Popup trailer: bấm ra ngoài, bấm X hoặc nhấn Esc để đóng
export default function TrailerModal({ movie, onClose }) {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  const closeRef = useRef(null);

  useEffect(() => {
    if (!movie) return;
    setData(null);
    setFailed(false);
    let off = false;
    api
      .trailer(movie.movie_id)
      .then((d) => !off && setData(d))
      .catch(() => !off && setFailed(true));
    return () => {
      off = true;
    };
  }, [movie]);

  useEffect(() => {
    if (!movie) return;
    const previous = document.activeElement;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previous?.focus?.();
    };
  }, [movie, onClose]);

  const searchUrl = data?.search_url
    ? data.search_url
    : movie
      ? `https://www.youtube.com/results?search_query=${encodeURIComponent(`${movie.title} official trailer`)}`
      : "#";

  return (
    <AnimatePresence>
      {movie && (
        <motion.div
          key="trailer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/75 p-4"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={`Trailer ${movie.title}`}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-2xl"
          >
            <div className="flex items-center gap-3 px-5 py-3">
              <h2 className="min-w-0 flex-1 truncate font-display text-lg font-extrabold">
                {movie.title}
                {movie.release_year ? ` (${movie.release_year})` : ""}
              </h2>
              <button
                ref={closeRef}
                onClick={onClose}
                aria-label="Đóng trailer"
                className="rounded-full p-2 hover:bg-ink/5"
              >
                <X size={20} />
              </button>
            </div>

            {data?.key ? (
              <div className="aspect-video bg-black">
                <iframe
                  className="size-full"
                  src={`https://www.youtube-nocookie.com/embed/${data.key}?autoplay=1&rel=0`}
                  title={`Trailer ${movie.title}`}
                  allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                  allowFullScreen
                />
              </div>
            ) : (
              <div className="flex aspect-video flex-col items-center justify-center gap-4 bg-paper p-8 text-center">
                {!data && !failed ? (
                  <p className="text-mute">Đang tìm trailer...</p>
                ) : (
                  <>
                    <p className="max-w-md text-mute">
                      {failed ? MESSAGES.unavailable : (MESSAGES[data.reason] ?? MESSAGES.not_found)}
                    </p>
                    <a
                      href={searchUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 font-semibold text-white hover:bg-ink/85"
                    >
                      Tìm trên YouTube <ExternalLink size={16} />
                    </a>
                  </>
                )}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}