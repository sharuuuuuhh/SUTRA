# DESIGN.md &bull; Sutra Design System & Motion Specification

Sutra's visual identity avoids generic SaaS templates in favor of a warm, tactile **editorial notebook aesthetic**. The brand motif is the **yellow highlighter pen**, symbolizing the transition from dense, overwhelming notes to crisp, exam-ready clarity.

---

## 🎨 Color Palette & Tokens

| Token | Hex | Role | Usage |
|---|---|---|---|
| `--color-paper` | `#F4F6F1` | Background Canvas | Page background with subtle dotted grid overlay |
| `--color-paper-2` | `#E9EDE4` | Surface Elevation | Card containers, dropzones, timeline tracks |
| `--color-sheet` | `#FFFFFF` | Paper Sheet | Elevated notebook sheets, modal bodies, reading canvas |
| `--color-ink` | `#101A2E` | Deep Navy Ink | Primary typography, headers, high-contrast borders |
| `--color-ink-muted` | `#4B5565` | Secondary Ink | Paragraph copy, metadata, secondary controls |
| `--color-cobalt` | `#2446F5` | Primary Action | Buttons, active navigation pills, progress bar |
| `--color-highlighter` | `#FFE14D` | Brand Highlight | Selective keyphrase accents, sticky notes, badges |
| `--color-margin-red` | `#E5484D` | Annotation Red | Gaps, corrections, high-probability exam tags |

---

## ✍️ Typography & Scale

- **Headlines**: `Bricolage Grotesque` (700 / 800 weight, sentence case, $-0.025\text{em}$ tracking).
- **Body**: `IBM Plex Sans` ($17\text{px} / 1.6\text{em}$ line height, clear legibility for mathematical and technical reading).
- **Code & Meta**: `IBM Plex Mono` ($13.5\text{px}$, course codes, token stamps, file chips).

---

## 📐 Shape & Geometry

- **Sheets & Cards**: `6px` radius (emulating real trimmed paper sheets).
- **Buttons & Inputs**: `10px` radius (tactile, rounded interactive controls).
- **Modals & Large Panels**: `24px` radius (prominent structural framing).

---

## 🎬 Anime.js Motion Plan (7 Choreographed Behaviors)

### 1. Page Load Orchestration
- **Headline Mask Reveal**: Each line of the hero headline rises out of an `overflow: hidden` bounding box via `translateY: [100%, 0%]` with a $140\text{ms}$ stagger.
- **Paper Sheet Drop**: The hero paper sheet lands with a soft elastic settle (`rotate: [-5, -2.5]deg`).
- **Highlighter Sweep**: Yellow highlight spans expand horizontally (`scaleX: [0, 1]`, `transformOrigin: left`).

### 2. Signature Moment (340vh Pinned Transformation)
- Section height is locked to $340\text{vh}$ with a sticky $100\text{vh}$ stage.
- A paused `anime.timeline({ autoplay: false })` is synchronized directly to scroll offset via `.seek()`:
  - **Scroll 0% &rarr; 33%**: Highlights illuminate across Coffman condition phrases in the raw lecture notes.
  - **Scroll 33% &rarr; 66%**: Filler text dims to $16\%$ opacity; raw paper steps back ($0.94$ scale).
  - **Scroll 66% &rarr; 100%**: The clean "Deadlock, in plain words" sheet slides into foreground ($60\text{px} \to 0\text{px}$), and its structural blocks stagger in.
  - A three-stage caption bar dynamically highlights the active step.

### 3. Parallax Drift
- Mockups and paper sheets drift along the Y-axis as the user scrolls.
- Calculated from the parent element's bounding box using native CSS `translate: 0px Ypx` (avoiding CSS `transform` jitter).

### 4. Entrance Reveals (IntersectionObserver)
- Feature rows and comparison blocks fade and rise into view ($28\text{px} \to 0\text{px}$) upon crossing the $15\%$ viewport threshold.
- Probability bars fill smoothly to their calibrated widths ($88\%$, $65\%$, $42\%$).

### 5. Vertical Steps Timeline
- In the "Three steps" section, a cobalt indicator line scales vertically (`scaleY: 0 \to 1`, `transformOrigin: top`) in proportion to the section's scroll traversal.

### 6. Chrome & Navigation Transitions
- Top cobalt progress indicator mirrors total document scroll progress ($0\% \to 100\%$).
- Sticky navigation bar activates a blurred backdrop glassmorphism state (`backdrop-filter: blur(12px)`) once scrolled past $12\text{px}$.

### 7. Performance & Accessibility
- All scroll handlers are throttled through `window.requestAnimationFrame` with `{ passive: true }` listeners.
- The `prefers-reduced-motion` media query immediately activates the `.rm` class, showing final states without animation delay.
