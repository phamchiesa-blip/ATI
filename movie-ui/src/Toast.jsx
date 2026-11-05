import { AnimatePresence, motion } from "framer-motion";
import { Info, PartyPopper, TriangleAlert, X } from "lucide-react";
import { useLang } from "./i18n";

const ICONS = { welcome: PartyPopper, info: Info, error: TriangleAlert, warning: TriangleAlert };

// Thông báo nhỏ góc dưới bên phải. Thanh phía dưới chạy ngược trong `duration` ms
// rồi tự đóng; người dùng cũng có thể bấm X để đóng sớm.
export default function Toast({ toast, onClose }) {
  const { tr } = useLang();
  const kind = toast?.kind ?? "info";
  const Icon = ICONS[kind] ?? Info;
  const tint = kind === "error" || kind === "warning" ? "text-coral" : "text-cobalt";
  const bar = kind === "error" || kind === "warning" ? "bg-coral" : "bg-cobalt";

  return (
    <div className="pointer-events-none fixed right-5 bottom-5 left-5 z-50 sm:left-auto sm:w-96">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            role={kind === "error" ? "alert" : "status"}
            aria-live="polite"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ duration: 0.22 }}
            className="pointer-events-auto relative overflow-hidden rounded-2xl bg-white p-4 shadow-xl ring-1 ring-ink/10"
          >
            <div className="flex items-start gap-3">
              <Icon size={20} className={`mt-0.5 shrink-0 ${tint}`} />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{toast.title}</p>
                {toast.text && <p className="mt-0.5 text-sm text-mute">{toast.text}</p>}
                {toast.actions ? (
                  <div className="mt-3 flex items-center gap-2">
                    {toast.actions.map((act, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          if (act.onClick) act.onClick();
                          onClose(toast.id);
                        }}
                        className={
                          act.primary
                            ? "cursor-pointer rounded-full bg-coral px-3.5 py-1 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-coral/90"
                            : "cursor-pointer rounded-full bg-ink/5 px-3.5 py-1 text-xs font-semibold text-ink transition-colors hover:bg-ink/10"
                        }
                      >
                        {act.label}
                      </button>
                    ))}
                  </div>
                ) : toast.action ? (
                  <button
                    onClick={() => {
                      toast.action.onClick();
                      onClose(toast.id);
                    }}
                    className="mt-2 cursor-pointer text-sm font-semibold text-cobalt underline underline-offset-4"
                  >
                    {toast.action.label}
                  </button>
                ) : null}
              </div>
              <button
                aria-label={tr("Đóng thông báo", "Close notification")}
                onClick={() => onClose(toast.id)}
                className="cursor-pointer rounded-full p-1 text-mute hover:bg-ink/5"
              >
                <X size={16} />
              </button>
            </div>
            <motion.span
              aria-hidden
              initial={{ scaleX: 1 }}
              animate={{ scaleX: 0 }}
              transition={{ duration: (toast.duration ?? 5000) / 1000, ease: "linear" }}
              className={`absolute inset-x-0 bottom-0 h-1 origin-left ${bar}`}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
