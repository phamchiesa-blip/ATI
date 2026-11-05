/**
 * ui.jsx (Barrel Re-export)
 * -------------------------
 * Tap hop cac UI primitives, hooks, context va theme utilities tu cac tang Clean Architecture:
 *   - context/AppContexts.js
 *   - hooks/useDebounced.js, hooks/useOverview.js, hooks/useHoverPreview.js
 *   - utils/theme.js
 *   - components/Poster.jsx, components/MovieCard.jsx
 */
export { TrailerContext, WatchlistContext } from "./context/AppContexts";
export { TONES, toneOf, GRID, movieHref } from "./utils/theme";
export { useDebounced } from "./hooks/useDebounced";
export { useOverview } from "./hooks/useOverview";
export { useHoverPreview } from "./hooks/useHoverPreview";
export {
  Overview,
  SaveButton,
  Poster,
  RateButtons,
  RateIcons,
  Rating,
  CardButtons,
  PosterLink,
  PosterTile,
} from "./components/Poster";
export { HoverPreview, MovieCard, Notice } from "./components/MovieCard";
