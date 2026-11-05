import { useState } from "react";
import { ArrowLeft, Check, Circle, Eye, EyeOff } from "lucide-react";
import { api, OFFLINE_MSG } from "./services/apiClient";
import { checkPassword, EMAIL_RE } from "./utils/passwordRules";
import Showcase from "./Showcase";
import { useLang } from "./context/AppContexts";

const inputCls =
  "mt-2 w-full rounded-xl bg-white px-4 py-3 ring-1 ring-ink/15 focus:ring-2 focus:ring-cobalt focus:outline-none";
const BAR = ["bg-coral", "bg-coral", "bg-lemon", "bg-cobalt", "bg-cobalt"];

export default function Auth({ initialMode = "login", onBack, onDone }) {
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", terms: false });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { lang, tr } = useLang();
  const isLogin = mode === "login";
  const set = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const pw = checkPassword(form.password, form.email, lang);
  const name = form.name.trim().replace(/\s+/g, " ");
  const emailOk = EMAIL_RE.test(form.email.trim());
  const nameOk = name.length >= 2 && name.length <= 30;
  const match = form.confirm !== "" && form.confirm === form.password;
  const canSubmit = isLogin
    ? form.email.trim() !== "" && form.password !== ""
    : emailOk && nameOk && pw.valid && match && form.terms;

  const switchMode = () => {
    setMode(isLogin ? "register" : "login");
    setError("");
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit || busy) return;
    setBusy(true);
    setError("");
    try {
      const user = isLogin
        ? await api.login(form.email, form.password)
        : await api.register(form.email.trim(), form.password, name, form.terms);
      onDone(user, mode);
    } catch (err) {
      setError(
        err.status === 0
          ? OFFLINE_MSG
          : typeof err.detail === "string"
            ? err.detail
            : tr("Thông tin chưa hợp lệ, hãy kiểm tra lại.", "Invalid information, please check again.")
      );
      setBusy(false);
    }
  };

  const eye = (
    <button
      type="button"
      onClick={() => setShow((v) => !v)}
      aria-label={show ? tr("Ẩn mật khẩu", "Hide password") : tr("Hiện mật khẩu", "Show password")}
      className="absolute top-1/2 right-3 -translate-y-1/2 rounded-full p-1.5 text-mute hover:bg-ink/5"
    >
      {show ? <EyeOff size={18} /> : <Eye size={18} />}
    </button>
  );

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 py-8">
      <button onClick={onBack} className="inline-flex items-center gap-2 text-sm font-semibold hover:text-cobalt">
        <ArrowLeft size={16} /> {tr("Tiếp tục với tư cách khách", "Continue as guest")}
      </button>

      <div className="mt-8 grid items-center gap-12 md:grid-cols-2 md:py-8">
        <section>
          <p className="font-display text-2xl font-extrabold">Gu Phim</p>
          <h1 className="mt-6 font-display text-4xl leading-tight font-extrabold md:text-6xl">
            {tr("Phim hợp gu bạn,", "Movies that match your taste,")}
            <br />
            {tr("chọn trong vài phút.", "picked in minutes.")}
          </h1>
          <p className="mt-4 max-w-md text-lg text-mute">
            {tr(
              "Tài khoản giúp lưu lại những phim bạn đã đánh giá và gợi ý riêng cho bạn ở lần sau.",
              "An account saves your rated movies and personalized recommendations for next time."
            )}
          </p>
          <Showcase />
        </section>

        <form onSubmit={submit} noValidate className="rounded-3xl bg-white p-8 md:p-10">
          <h2 className="font-display text-3xl font-extrabold">
            {isLogin ? tr("Đăng nhập", "Sign In") : tr("Tạo tài khoản", "Create Account")}
          </h2>

          {!isLogin && (
            <label className="mt-6 block">
              <span className="text-sm font-semibold">{tr("Tên hiển thị", "Display Name")}</span>
              <input
                value={form.name}
                onChange={set("name")}
                maxLength={30}
                autoComplete="nickname"
                placeholder={tr("Ví dụ: Meobeo", "e.g., Alex")}
                className={inputCls}
              />
              <span className="mt-1 block text-xs text-mute">
                {tr("Từ 2 đến 30 ký tự", "2 to 30 characters")}
              </span>
            </label>
          )}

          <label className="mt-5 block">
            <span className="text-sm font-semibold">Email</span>
            <input
              type="email"
              value={form.email}
              onChange={set("email")}
              autoComplete="email"
              aria-invalid={!isLogin && form.email !== "" && !emailOk}
              className={inputCls}
            />
            {!isLogin && form.email !== "" && !emailOk && (
              <span className="mt-1 block text-xs text-coral">
                {tr("Email chưa đúng định dạng", "Invalid email format")}
              </span>
            )}
          </label>

          <label className="mt-5 block">
            <span className="text-sm font-semibold">{tr("Mật khẩu", "Password")}</span>
            <span className="relative block">
              <input
                type={show ? "text" : "password"}
                value={form.password}
                onChange={set("password")}
                autoComplete={isLogin ? "current-password" : "new-password"}
                aria-describedby={isLogin ? undefined : "pw-rules"}
                className={`${inputCls} pr-12`}
              />
              {eye}
            </span>
          </label>

          {!isLogin && (
            <>
              <div id="pw-rules" className="mt-3" aria-live="polite">
                <div className="flex items-center gap-3">
                  <div className="flex flex-1 gap-1" aria-hidden>
                    {[0, 1, 2, 3].map((i) => (
                      <span
                        key={i}
                        className={`h-1.5 flex-1 rounded-full ${
                          form.password && i < Math.max(pw.score, 1) ? BAR[pw.score] : "bg-ink/10"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="w-20 text-right text-xs font-semibold">{pw.label}</span>
                </div>
                <ul className="mt-3 grid gap-1.5 text-sm">
                  {pw.rules.map((r) => (
                    <li key={r.id} className={`flex items-center gap-2 ${r.ok ? "text-cobalt" : "text-mute"}`}>
                      {r.ok ? <Check size={15} /> : <Circle size={15} />}
                      {r.label}
                    </li>
                  ))}
                </ul>
              </div>

              <label className="mt-5 block">
                <span className="text-sm font-semibold">{tr("Nhập lại mật khẩu", "Confirm Password")}</span>
                <input
                  type={show ? "text" : "password"}
                  value={form.confirm}
                  onChange={set("confirm")}
                  autoComplete="new-password"
                  aria-invalid={form.confirm !== "" && !match}
                  className={inputCls}
                />
                {form.confirm !== "" && !match && (
                  <span className="mt-1 block text-xs text-coral">
                    {tr("Mật khẩu nhập lại chưa khớp", "Passwords do not match")}
                  </span>
                )}
              </label>

              <label className="mt-5 flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={form.terms}
                  onChange={set("terms")}
                  className="mt-1 size-4 accent-cobalt"
                />
                <span className="text-mute">
                  {tr(
                    "Tôi đồng ý để Gu Phim lưu email và lịch sử Thích / Không thích của tôi nhằm cá nhân hóa gợi ý.",
                    "I agree to let Gu Phim store my email and Like / Dislike history to personalize recommendations."
                  )}
                </span>
              </label>
            </>
          )}

          {error && (
            <p role="alert" className="mt-5 text-coral">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={!canSubmit || busy}
            className="mt-6 w-full rounded-full bg-cobalt py-3 font-semibold text-white transition-colors hover:bg-cobalt/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy
              ? tr("Đang xử lý...", "Processing...")
              : isLogin
                ? tr("Đăng nhập", "Sign In")
                : tr("Đăng ký", "Sign Up")}
          </button>

          <p className="mt-6 text-center text-sm text-mute">
            {isLogin ? tr("Chưa có tài khoản?", "Don't have an account?") : tr("Đã có tài khoản?", "Already have an account?")}{" "}
            <button
              type="button"
              onClick={switchMode}
              className="font-semibold text-cobalt underline underline-offset-4"
            >
              {isLogin ? tr("Đăng ký", "Sign Up") : tr("Đăng nhập", "Sign In")}
            </button>
          </p>
        </form>
      </div>
    </main>
  );
}
