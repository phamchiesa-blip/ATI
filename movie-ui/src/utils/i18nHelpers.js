/**
 * utils/i18nHelpers.js
 * --------------------
 * Bang anh xa the loai phim song ngu (VI / EN) va bo dich chuoi ly do tu Backend.
 */
export const GENRE_MAP_VI = {
  Action: "Hành động",
  Adventure: "Phiêu lưu",
  Animation: "Hoạt hình",
  Comedy: "Hài",
  Crime: "Tội phạm / Hình sự",
  Documentary: "Tài liệu",
  Drama: "Tâm lý / Chính kịch",
  Family: "Gia đình",
  Fantasy: "Kỳ ảo / Phép thuật",
  Foreign: "Phim nước ngoài",
  History: "Lịch sử",
  Horror: "Kinh dị",
  Music: "Âm nhạc",
  Mystery: "Bí ẩn / Trinh thám",
  Romance: "Lãng mạn / Tình cảm",
  "Science Fiction": "Khoa học viễn tưởng",
  "TV Movie": "Phim truyền hình",
  Thriller: "Giật gân / Hồi hộp",
  War: "Chiến tranh",
  Western: "Viễn Tây",
};

export function genreLabel(genre, lang = "vi") {
  if (!genre) return "";
  if (lang === "en") {
    for (const [en, vi] of Object.entries(GENRE_MAP_VI)) {
      if (
        vi.toLowerCase() === String(genre).toLowerCase() ||
        en.toLowerCase() === String(genre).toLowerCase()
      ) {
        return en;
      }
    }
    return genre;
  }
  return GENRE_MAP_VI[genre] ?? genre;
}

const VI_TO_EN_PHRASES = [
  // Thong bao loi Chatbot & Backend
  [
    "Hệ thống chưa hiểu yêu cầu tìm phim của bạn. Vui lòng mô tả tâm trạng, thể loại (hài, hành động...), thời kỳ hoặc tên phim cụ thể (VD: “giống Inception”).",
    "The system could not understand your movie request. Please describe your mood, preferred genre (comedy, action...), time period, or a specific movie title (e.g., “like Inception”).",
  ],
  [
    'Hệ thống chưa hiểu yêu cầu tìm phim của bạn. Vui lòng mô tả tâm trạng, thể loại (hài, hành động...), thời kỳ hoặc tên phim cụ thể (VD: "giống Inception").',
    'The system could not understand your movie request. Please describe your mood, preferred genre (comedy, action...), time period, or a specific movie title (e.g., "like Inception").',
  ],
  [
    "Hệ thống chưa hiểu yêu cầu tìm phim của bạn.",
    "The system could not understand your movie request.",
  ],
  [
    "Vui lòng mô tả tâm trạng, thể loại (hài, hành động...), thời kỳ hoặc tên phim cụ thể (VD: “giống Inception”).",
    "Please describe your mood, preferred genre (comedy, action...), time period, or a specific movie title (e.g., “like Inception”).",
  ],
  [
    'Vui lòng mô tả tâm trạng, thể loại (hài, hành động...), thời kỳ hoặc tên phim cụ thể (VD: "giống Inception").',
    'Please describe your mood, preferred genre (comedy, action...), time period, or a specific movie title (e.g., "like Inception").',
  ],
  [
    "Hãy nhập yêu cầu hoặc chọn một gợi ý nhanh",
    "Please enter a request or select a quick suggestion",
  ],
  [
    "Chưa chọn được phim. Hãy thử lại.",
    "Could not pick a movie. Please try again.",
  ],
  [
    "Tâm trạng không hợp lệ",
    "Invalid mood selection",
  ],
  [
    "Không tìm thấy phim",
    "Movie not found",
  ],
  [
    "Chưa kết nối được máy chủ. Hãy kiểm tra lệnh uvicorn api:app --reload đang chạy.",
    "Could not connect to the server. Please check that 'uvicorn api:app --reload' is running.",
  ],
  ["Mình hiểu bạn muốn:", "I understand you want:"],
  ["dưới 18 tuổi", "for under 18"],
  ["dành cho 18+", "for 18+"],
  ["dành cho trên 18 tuổi", "for 18+"],
  ["khán giả 18+", "18+ audience"],
  ["phù hợp dưới 18 tuổi", "suitable for under 18"],
  ["Chưa xác định được yêu cầu tìm phim", "Could not identify movie search criteria"],
  ["Phim hay được đánh giá cao", "Highly rated movies"],
  [" · Tránh: ", " · Avoid: "],
  ["Hành động", "Action"],
  ["Phiêu lưu", "Adventure"],
  ["Hoạt hình", "Animation"],
  ["Tội phạm / Hình sự", "Crime"],
  ["Tài liệu", "Documentary"],
  ["Tâm lý / Chính kịch", "Drama"],
  ["Gia đình", "Family"],
  ["Kỳ ảo / Phép thuật", "Fantasy"],
  ["Phim nước ngoài", "Foreign"],
  ["Lịch sử", "History"],
  ["Kinh dị", "Horror"],
  ["Âm nhạc", "Music"],
  ["Bí ẩn / Trinh thám", "Mystery"],
  ["Lãng mạn / Tình cảm", "Romance"],
  ["Khoa học viễn tưởng", "Science Fiction"],
  ["Phim truyền hình", "TV Movie"],
  ["Giật gân / Hồi hộp", "Thriller"],
  ["Chiến tranh", "War"],
  ["Viễn Tây", "Western"],
  ["Hài", "Comedy"],
  ["nhẹ nhàng, thư giãn", "lighthearted, relaxing"],
  ["vui vẻ, hài hước", "fun, hilarious"],
  ["hồi hộp, căng thẳng", "thrilling, suspenseful"],
  ["xoắn não, suy ngẫm", "mind-bending, thought-provoking"],
  ["buồn, cảm động, sâu lắng", "emotional, touching"],
  ["phấn khích, mãn nhãn, hoành tráng", "exciting, epic"],
  ["rùng rợn, ám ảnh, đen tối", "scary, dark"],
  ["lãng mạn, ngọt ngào", "romantic, sweet"],
  ["mơ mộng, kỳ ảo", "dreamy, magical"],
  ["truyền cảm hứng, nghị lực", "inspiring"],
  ["nhẹ nhàng hơn", "lighter"],
  ["kịch tính hơn", "more thrilling"],
  ["Nội dung gần với ", "Similar to "],
  ["Đúng chất ", "Matches "],
  ["Hợp tâm trạng ", "Fits mood "],
  ["Từ khóa: ", "Keyword: "],
  ["từ khóa ", "keyword "],
  ["chủ đề ", "topic "],
  ["Phát hành năm ", "Released in "],
  ["từ năm ", "from "],
  ["trước năm ", "before "],
  ["năm ", "year "],
  ["dưới ", "under "],
  [" phút", " min"],
  ["giống ", "like "],
  ["đạo diễn ", "director "],
  ["Đạo diễn ", "Director "],
  ["diễn viên ", "actor "],
  ["Có ", "Starring "],
  ["hợp hồ sơ sở thích của bạn", "matches your taste profile"],
  ["hợp gu của bạn", "matches your taste"],
  ["hợp gu ", "matches your "],
  [" của bạn", " taste"],
  ["Được đánh giá cao", "Highly rated"],
  ["Được nhiều khán giả yêu thích", "Audience favorite"],
  ["được nhiều người yêu thích", "popular choice"],
];

export function translateBackendText(text, lang) {
  if (!text || lang !== "en") return text;
  let out = String(text);

  // Xu ly uu tien cho thong bao loi nhan dien yeu cau chatbot
  if (
    out.includes("chưa hiểu yêu cầu tìm phim") ||
    out.includes("chua hieu yeu cau tim phim")
  ) {
    return "The system could not understand your movie request. Please describe your mood, preferred genre (comedy, action...), time period, or a specific movie title (e.g., “like Inception”).";
  }

  for (const [vi, en] of VI_TO_EN_PHRASES) {
    out = out.split(vi).join(en);
  }
  return out;
}

