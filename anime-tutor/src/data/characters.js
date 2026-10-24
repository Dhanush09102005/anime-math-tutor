// Central character registry.
// Both CharacterSelect.jsx and SessionHeader.jsx import from here.
// characterCards re-exports from assets so there's one source of truth
// for both the metadata (name, title, flavor, active) and the images.

export { characterCards } from "../assets/characters/index.js";

export const CHARACTERS = [
  {
    id:     "kakashi",
    name:   "Kakashi Hatake",
    title:  "Copy Ninja",
    flavor: "Laid-back, perceptive, quietly raises the bar",
    active: true,
  },
  {
    id:     "sukuna",
    name:   "Ryomen Sukuna",
    title:  "King of Curses",
    flavor: "Contemptuous, imperious — respect is earned through results",
    active: true,
  },
  {
    id:     "makima",
    name:   "Makima",
    title:  "Control Devil",
    flavor: "Serene, calculating, subtly unsettling",
    active: true,
  },
  {
    id:     "goku",
    name:   "Son Goku",
    title:  "Saiyan Raised on Earth",
    flavor: "Enthusiastic, training-obsessed, genuinely can't understand giving up",
    active: true,
  },
];
