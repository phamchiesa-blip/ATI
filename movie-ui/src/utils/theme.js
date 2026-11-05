/**
 * utils/theme.js
 * --------------
 * Bang mau poster theo the loai, grid layout chuan va helper tao duong dan phim.
 */
export const TONES = {
  Action: ["#FF7A59", "#2A0E06"],
  Adventure: ["#FFC83D", "#2B2200"],
  Animation: ["#6FD6C6", "#052B26"],
  Comedy: ["#FFE26B", "#312900"],
  Crime: ["#8EA2FF", "#0E1856"],
  Documentary: ["#9AD0EC", "#082A3D"],
  Drama: ["#F6A6C1", "#3A0F22"],
  Family: ["#B7E36B", "#1E2D06"],
  Fantasy: ["#C3A6FF", "#1F0F4D"],
  History: ["#D9B77E", "#2E2108"],
  Horror: ["#FF5D5D", "#2A0707"],
  Music: ["#FF9FD2", "#3A0A26"],
  Mystery: ["#7C6BD6", "#FFFFFF"],
  Romance: ["#FFB3C7", "#44101F"],
  "Science Fiction": ["#5B7CFF", "#FFFFFF"],
  Thriller: ["#3B4A6B", "#FFFFFF"],
  War: ["#A89F8A", "#1E1A10"],
  Western: ["#E39B5B", "#2E1505"],
};

const FALLBACK = ["#CBD5E1", "#0F172A"];

export const toneOf = (genre) => TONES[genre] ?? FALLBACK;

export const GRID =
  "grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6";

export const movieHref = (m) => `#/movie/${m.movie_id}`;

