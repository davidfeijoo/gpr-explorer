# Geopolitical Risk Index Explorer

Interactive front end for the GDELT-based geopolitical risk index (MSc thesis, DTU).
Built with Vite + React + Recharts. Deploys as a static site (no server).

## What's live vs. in development

**Live — computed from the real GDELT GKG series (2015-02-18 -> 2026-05-24, 4,096 daily obs):**
- Kinetic-pillar index = share of G20 articles tagging any selected curated theme
- Theme selection across the 9 curated kinetic themes (exact, via the precomputed OR-combination matrix)
- Rolling window (1-90 day moving average)
- Normalization (raw / z-score / min-max / percentile)
- Pin-baseline comparison, CSV upload of your own series

**In development — shown as clearly labeled demos:**
- Per-source country / outlet selection (published series aggregates all G20 outlets)
- Sub-daily (hourly / 15-min) resolution
- Hybrid & Geoeconomic pillars and weighted multi-pillar blending
- Exact Caldara & Iacoviello (2022) comparison (needs the per-source data cube)

## Data
The app reads two static JSON files from `public/data/`:
- `index.json` (~0.3 MB) - dates, daily article totals, all-9-theme index, per-theme counts. Loaded on first paint.
- `combos.json` (~10 MB) - the 511 OR-combination counts so any theme subset recomputes exactly in the browser. Lazily fetched.

Regenerate them from the thesis backend after updates:
```bash
python scripts/export_data.py /path/to/dev2/gpr_index public/data
```
(Requires pandas + pyarrow.)

## Run locally
```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production build into dist/
npm run preview
```

## Deploy to Vercel
Vercel-ready (`vercel.json`: framework=vite, output=dist).
1. Push this folder to a GitHub repo.
2. Vercel -> New Project -> import the repo (auto-detects Vite) -> Deploy.

Or via CLI:
```bash
npm i -g vercel
vercel --prod
```
No backend or env vars needed; `public/data/*.json` are static assets.
