---
name: Logo-matched colour theme
description: EduCheck AI's theme is matched to the VERISM logo — midnight navy, electric aqua, ice-blue glow, circuit teal. Never hardcode colours.
type: design
---
The user asked for a light-blue theme, then asked for it to match their uploaded logo (the "VERISM" cyber-owl crest). The theme now follows that logo:

- Brand colours taken from the logo: deep midnight navy `#081D33` (text, primary buttons), electric aqua/cyan `#00F2FE` and `#1AE5D9` (glow accents, matched-phrase highlight, secondary accent), ice-blue `#E0FFFF` (soft fills), deep circuit teal `#0C6E77` (links, active states, solid accent buttons).
- Surfaces stay light: pale ice-blue paper, near-white cards, navy text.
- Status meanings: amber = waiting on the teacher, teal-green = approved/healthy, coral = similarity or integrity flag. These stay warm/red so they never read as brand accents.
- Matched phrases in submissions use an aqua highlight, never the browser's yellow `<mark>`.
- All colours are semantic tokens in `src/styles.css`; components use token classes only — never hex values or utilities like `bg-white`/`text-white`.
- Token names are legacy: `lav` is the lead brand accent (now aqua-teal), `blue` the brighter secondary aqua. Names are kept so component markup stays untouched.
- Tone classes (`soft-*`, `icon-*`, `tone-*`, `chart-*`, `bar-*`, `dot-*`) are written by hand in a components layer because they are assembled at runtime and Tailwind's scanner never sees them. New tone values need entries there too.
