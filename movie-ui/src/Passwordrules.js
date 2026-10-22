// Quy tắc mật khẩu: phải khớp với password_problems() trong api.py.
const COMMON = new Set([
  "12345678", "123456789", "1234567890", "11111111", "00000000", "123123123",
  "password", "password1", "password123", "passw0rd", "qwerty123", "qwertyuiop",
  "abc12345", "abcd1234", "iloveyou", "admin123", "letmein123", "welcome1",
  "matkhau123", "12345678a", "1q2w3e4r", "dragon123", "monkey123", "football1",
]);

export const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
const LABELS = ["Rất yếu", "Yếu", "Trung bình", "Khá", "Mạnh"];

export function checkPassword(pw, email = "") {
  const local = email.split("@")[0].toLowerCase();
  const rules = [
    { id: "len", label: "Ít nhất 8 ký tự", ok: pw.length >= 8 && pw.length <= 128 },
    { id: "mix", label: "Có cả chữ cái và chữ số", ok: /\p{L}/u.test(pw) && /\p{Nd}/u.test(pw) },
    {
      id: "common",
      label: "Không quá phổ biến hoặc quá đơn giản",
      ok: pw.length > 0 && !COMMON.has(pw.toLowerCase()) && new Set(pw).size >= 4,
    },
    {
      id: "email",
      label: "Không chứa phần đầu của email",
      ok: pw.length > 0 && !(local.length >= 3 && pw.toLowerCase().includes(local)),
    },
  ];
  const valid = rules.every((r) => r.ok);
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/\p{Ll}/u.test(pw) && /\p{Lu}/u.test(pw)) score++;
  if (/[^\p{L}\p{Nd}]/u.test(pw)) score++;
  if (!valid) score = Math.min(score, 1);
  return { rules, valid, score, label: pw ? LABELS[score] : "" };
}