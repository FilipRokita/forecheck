# Design

The page is dark, technical and data-first: the answer first (the verdict), then the evidence. It follows the mockup made for
this project, which has a desktop and a phone artboard (https://claude.ai/artifact/EzTJVKrAF5whUPeE5NuU16). The numbers in the
mockup were examples and are not used.

## Tokens

All colours are tokens in `src/app/globals.css` and are used through Tailwind (`bg-surface`, `text-fg-muted`, and so on). No
component holds a raw colour.

| Token | Value | Use |
| :--- | :--- | :--- |
| `bg` | `#0b0c0e` | Page |
| `surface` | `#121417` | Cards |
| `surface-raised` | `#1c2025` | Pressed controls, mobile rows |
| `border` / `border-strong` | `#24272d` / `#2e323a` | Hairlines |
| `fg` | `#e8eaed` | Text |
| `fg-soft` | `#c4c9d1` | Body copy in cards |
| `fg-muted` | `#98a0ab` | Secondary text, axes |
| `highlight` | `#15221f` | The winning row |
| `model-icon` | `#8aa4ff` | ICON |
| `model-ecmwf` | `#6ee7c8` | ECMWF, and the focus ring |
| `model-gfs` | `#f2b36a` | GFS |
| `warn`, `warn-bg`, `warn-border` | amber | "Sample data" and "Limited history" badges |

Type: Inter for text and JetBrains Mono for numbers, both bundled with `@fontsource-variable` (no request to a font service, so
the page's content security policy allows only its own origin). Numbers use a decimal point and no thousands separator.

## Layout

| | Desktop | Phone |
| :--- | :--- | :--- |
| Station | A button that opens a centred list | The same button, full width. The list is a bottom sheet |
| Quantity, period | Two segmented controls in a row | Stacked. Quantity scrolls sideways if it must |
| Verdict | A one-sentence summary, then three cards in a row | The same, cards stacked |
| Horizon chart | Wide bars | The same, narrower bars |
| Ranking | A table | A card per model |
| Comparison | A map of Poland (it stays in view) beside a table | The map above the same table, rows 48 px tall |

Both have the same features. Nothing is hidden on a phone.

## Motion and feedback

Everything that can be clicked shows it: a pointer cursor, a hover state and a small press effect. All of it is plain CSS
(tokens and keyframes in `src/app/globals.css`), with no animation library.

- Cards rise in one after another. Chart bars grow from zero, and a tooltip names the value of the bar under the pointer.
- The verdict numbers count up once when they appear.
- The winning model's card has a faint glow in its colour. The station list slides in over a blurred page.
- Skeletons shimmer. Changing the quantity or the period shows them, because the figures would be read in the wrong unit.
  Changing the station keeps the old figures on screen, dimmed, until the new ones arrive: they name their station, so they
  cannot be mistaken for the new one. The header stays on top on larger screens, blurred.
- The logo in the header is the one from the README, drawn in the page's own font. Pressing it scrolls smoothly back to the top.
- Every animation stops when the system asks for reduced motion.

The header has a GitHub icon that links to the repository. On a phone the header is one row (the export button is an icon, and the GitHub icon is left out because the footer links the repository) and the quantity and period controls lose their captions,
so the verdict starts higher.

## The station map

Each station is a dot in the colour of its best model, and the open station pulses. Pressing a dot opens that station, and
the pointer shows a station's name. The outline of Poland is [Natural Earth](https://www.naturalearthdata.com/) (public
domain), simplified, and lives in `src/lib/poland.ts` with the function that places a station on it.

The map is a second way in to what the table already says, so it is hidden from assistive technology and the table is the
accessible version.

## Accessibility

- Real `<button>`, `<a>`, `<table>`, `<dialog>`. The station list is a native modal dialog: focus is trapped, Escape closes it,
  and focus returns to the button that opened it.
- Touch targets are at least 44 px on a phone.
- Selection is exposed (`aria-pressed`, `aria-current`), not only coloured.
- The three models are told apart by name, by position (always ICON, ECMWF, GFS in the same order) and by colour, never by
  colour alone. The legend names them, and the chart has a table with the same numbers.
- Text contrast is at least 4.5:1. The weakest pairing, `fg-muted` on `highlight`, is 6.2:1, and `fg-muted` on `surface` is 7.0:1. A test computes every text pairing from the real tokens (`tests/unit/test_design_tokens.py`).
- Structural accessibility is checked with axe-core in the dashboard test. Colour contrast is covered by the token test above, because
  axe-core needs a real browser engine for it.
- The Polish legal notices carry `lang="pl"`.

## Honesty in the interface

- A "Sample data" badge shows while demo scores are in the database.
- A "Limited history: N scored days" badge shows whenever the period's window is not yet full.
- "Scored through" always says how far scoring has got.
- Where there is not enough data, the page says "Too early" or "too few days" instead of showing a figure it cannot stand
  behind.
