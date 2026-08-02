# Design QA — homepage How It Works illustrations

## Visual truth

- Approved source assets:
  - `output/imagegen/bookie-how-it-works/set-up-services.png`
  - `output/imagegen/bookie-how-it-works/share-your-link.png`
  - `output/imagegen/bookie-how-it-works/get-booked.png`
- Implementation screenshots:
  - `output/qa/homepage-how-it-works-desktop.png`
  - `output/qa/homepage-how-it-works-cards.png`
- Combined comparison: `output/qa/how-it-works-comparison.png`

## Test state

- Route: `/`
- State: homepage scrolled from the sticky `How it works` navigation link
- Browser viewport: 1265 × 712 CSS pixels
- Source asset dimensions: 1254 × 1254 pixels each
- Delivery format: 720 × 720 WebP assets rendered with responsive `next/image`

## Comparison

The combined comparison places all three approved illustrations above the implemented card section. The implementation preserves the approved subjects, palette, proportions, warm-ivory background, and sequence. The images remain crisp at the card size and do not show the checkerboard artifact from the first generation pass.

The focused card view confirms:

- all three cards align to a consistent grid and height;
- image subjects are centered and uncropped;
- step badges remain readable without obscuring the illustrations;
- heading, description, border, radius, and spacing follow the existing Bookie visual system;
- the sticky homepage header remains visible and functional;
- the `How it works` navigation link reaches the intended section.

## Findings

- P0: none
- P1: none
- P2: none
- P3: the source artwork is raster rather than vector; optimized WebP delivery keeps each asset below 33 KB and remains visually crisp at the implemented size.

## Verification

- `npm run lint`: passed
- `npm run build`: passed
- `git diff --check`: passed
- Local browser visual comparison: passed
- Primary interaction (`How it works` anchor): passed

final result: passed
