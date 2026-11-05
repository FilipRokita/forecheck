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
| `model-icon` | `#8aa4ff` | ICON |
| `model-ecmwf` | `#6ee7c8` | ECMWF, and the focus ring |
| `model-gfs` | `#f2b36a` | GFS |
| `warn`, `warn-bg`, `warn-border` | amber | "Sample data" and "Limited history" badges |

Type: Inter for text and JetBrains Mono for numbers, both bundled with `@fontsource-variable` (no request to a font service, so
the page's content security policy allows only its own origin). Numbers use a decimal point and no thousands separator.

## Highlighted rows

The best model's row in the ranking, and the open station's row in the comparison, are washed in that model's colour (a 10%
tint over `surface`, with a 3 px bar of the colour on the left edge). The colour is never a fixed green, so a highlight is
never mistaken for ECMWF unless ECMWF is the model. `modelTint` in `src/lib/models.ts` makes the tint.

## Layout

| | Desktop | Phone |
| :--- | :--- | :--- |
| Station | A button that opens a dropdown under it, with a search box on top | One "Configure" button that shows the choice and opens a drawer from the bottom |
| Quantity, period | Two segmented controls in a row | In the same drawer, with the station: every option is a button, and a choice applies at once |
| Verdict | A one-sentence summary, then three cards in a row | The same, cards stacked |
| Horizon chart | Wide bars | The same, narrower bars |
| Ranking | A table | A card per model |
| Column guide | A window in the middle | A drawer from the bottom, taller so it rarely needs scrolling |
| Comparison | A map of Poland, centred beside a table | The map above the same table |

Both have the same features. Nothing is hidden on a phone.

## Motion and feedback

Everything that can be clicked shows it: a pointer cursor, a hover state and a small press effect. All of it is plain CSS
(tokens and keyframes in `src/app/globals.css`), with no animation library.

- Cards rise in one after another. Chart bars grow from zero, and a tooltip names the value of the bar under the pointer.
- The verdict numbers count up once when they appear.
- The winning model's card has a faint glow in its colour.
- Skeletons shimmer, but only on the first load. Before the first answer the page shows its own shape (the header with the
  logo, the controls and the cards as grey blocks of the same size), not one big block, so nothing moves when it arrives. After that, changing the station, quantity or period never blanks the page:
  the old figures stay until the new ones arrive, a thin line under the header shows that something is loading (only if it
  takes a moment), and then the numbers count from the old value to the new one, the chart bars and the map dots move to
  their new height and colour, and changed words fade in. The highlight in the quantity and period controls slides to the
  button you pressed. Each part is written in the unit and for the period of its
  own answer, so figures that are still on screen are never read in the wrong unit.
- A drawer slides up from the bottom of a phone, and a window on a larger screen fades in. However it is closed (the X, Done,
  a press outside it, Escape), it leaves in the same way: a short slide down, or a fade.
- The header stays on top, blurred.
- Every animation stops when the system asks for reduced motion.

The header has a GitHub icon that links to the repository, placed before the export button. On a phone the header is one row (the export button is an icon, and the logo is a little smaller on the narrowest phones), so the three controls live in the drawer instead of filling the first screen.

## The station map

Each station is a dot in the colour of its best model, and the open station pulses. The pointer shows a station's name. The
map is only to look at: the station is chosen with the picker or from the table. The outline of Poland is
[Natural Earth](https://www.naturalearthdata.com/) (public domain), simplified, and lives in `src/lib/poland.ts` with the
function that places a station on it.

The map repeats what the table says, so it is hidden from assistive technology and the table is the accessible version.

## The column guide

Under the ranking, "What do these columns mean?" opens a window with one raised card per column: the name, which way is
better, the first model's own number in large type, one plain sentence, and a small picture of where that number sits (a bar,
or a scale with a middle mark for bias). It closes with the X, Escape, or a press on the backdrop.

## Accessibility

- Real `<button>`, `<a>`, `<table>`. The station picker is a combobox: the search box takes the focus, the arrow keys move through
  the matches, Enter picks one, and Escape closes the list and returns the focus to the button.
- While a drawer or window is open, the page behind it does not scroll, and the scrolling of the drawer's own content does not
  pass on to the page.
- Touch targets are at least 44 px on a phone.
- Selection is exposed (`aria-pressed`, `aria-selected`, `aria-current`), not only coloured.
- The three models are told apart by name, by position (always ICON, ECMWF, GFS in the same order) and by colour, never by
  colour alone. The legend names them, and the chart has a table with the same numbers that only screen readers get.
- Text contrast is at least 4.5:1. The weakest pairing, `fg-muted` on a row washed in ECMWF's colour, is 5.7:1, and `fg-muted` on `surface-raised` is 6.2:1. A test computes every text pairing from the real tokens (`tests/unit/test_design_tokens.py`).
- Structural accessibility is checked with axe-core in the dashboard test. Colour contrast is covered by the token test above, because
  axe-core needs a real browser engine for it.
- The Polish legal notices carry `lang="pl"`.

## Honesty in the interface

- A "Sample data" badge shows while demo scores are in the database.
- A "Limited history: N scored days" badge shows whenever the period's window is not yet full.
- "Scored through" always says how far scoring has got.
- Where there is not enough data, the page says "Too early" or "too few days" instead of showing a figure it cannot stand
  behind.
