import { AnimatePresence, motion } from "framer-motion";
import { Info, PartyPopper, TriangleAlert, X } from "lucide-react";

const ICONS = { welcome: PartyPopper, info: Info, error: TriangleAlert };

// Thông báo nhỏ góc dưới bên phải. Thanh phía dưới chạy ngược trong `duration` ms
// rồi tự đóng; người dùng cũng có thể bấm X để đóng sớm.
export default function Toast({ toast, onClose }) {
  const kind = toast?.kind ?? "info";
  const Icon = ICONS[kind] ?? Info;
  const tint = kind === "error" ? "text-coral" : "text-cobalt";
  const bar = kind === "error" ? "bg-coral" : "bg-cobalt";

  return (
    <div className="pointer-events-none fixed right-5 bottom-5 left-5 z-50 sm:left-auto sm:w-96">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            role="status"
            aria-live="polite"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.25 }}
            className="pointer-events-auto overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-ink/10"
          >
            <div className="flex items-start gap-3 p-4">
              <Icon size={22} className={`mt-0.5 shrink-0 ${tint}`} aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{toast.title}</p>
                {toast.text && <p className="mt-0.5 text-sm text-mute">{toast.text}</p>}
                {toast.action && (
                  <button
                    onClick={() => {
                      toast.action.onClick();
                      onClose(toast.id);
                    }}
                    className="mt-2 text-sm font-semibold text-cobalt underline underline-offset-4"
                  >
                    {toast.action.label}
                  </button>
                )}
              </div>
              <button
                aria-label="Đóng thông báo"
                onClick={() => onClose(toast.id)}
                className="rounded-full p-1 text-mute hover:bg-ink/5"
              >
                <X size={16} />
              </button>
            </div>
            <motion.div
              className={`h-1 ${bar}`}
              initial={{ width: "100%" }}
              animate={{ width: "0%" }}
              transition={{ duration: (toast.duration ?? 5000) / 1000, ease: "linear" }}
              onAnimationComplete={() => onClose(toast.id)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}