# Equipment Catalog Audit

Date: 2026-06-22

Scope: online consistency pass for `telescope_catalog_seed.csv`, `eyepiece_catalog_seed.csv`, and `barlow_catalog_seed.csv`.

## Sources Checked

- Celestron official product pages and Shopify product endpoints:
  - `https://www.celestron.com/products/omni-4-mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-6-mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-9-mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-12mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-15-mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-32-mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-40-mm-eyepiece-125in`
  - `https://www.celestron.com/products/omni-56mm-eyepiece-2in`
  - `https://www.celestron.com/products/8-24mm-zoom-eyepiece-125in`
  - `https://www.celestron.com/products/omni-2x-barlow-lens-125in`
  - `https://www.celestron.com/products/x-cel-lx-2x-barlow-lens-125in`
  - `https://www.celestron.com/products/x-cel-lx-3x-barlow-lens-125in`
  - `https://www.celestron.com/products/luminos-25x-barlow-lens-2in`
- Baader official backend catalog endpoint for Hyperion Zoom and Hyperion Zoom Barlow:
  - `https://backend.baader-planetarium.com/graphql`
  - `https://www.baader-planetarium.com/en/downloads/dl/file/id/356/product/3117/description_and_recommended_accessories_for_the_hyperion_universal_zoom_mark_iv.pdf`
- Vendor search/product pages for previously flagged rows where direct confirmation was attempted:
  - Bresser Messier NT-150S/750
  - Orion StarBlast 4.5 Astro
  - Sky-Watcher Evostar 80ED DS-Pro
  - William Optics Zenithstar 61 II
  - Omegon MightyMak 90/127

## Corrections Applied

- Removed historical placeholder rows marked `Catalog seed entry`.
- Removed unresolved `To verify by market revision` rows for Omegon MightyMak 90/127 because no primary source could be confirmed in this pass.
- Removed duplicate telescope rows that shared identical brand/specs with a more complete manufacturer-catalog row:
  - Bresser Messier NT-150S
  - Orion StarBlast 4.5
  - Sky-Watcher Evostar 80ED
  - William Optics Zenithstar 61
- Removed unverified eyepiece placeholder rows with incomplete barrel data:
  - Bresser SPL 26 mm
  - Omegon Redline 15 mm
  - William Optics Swan 20 mm
- Removed duplicate Barlow placeholder rows with missing barrel data.
- Updated Celestron Omni Plossl apparent fields from the official specifications:
  - 4, 6, 9, 12, 15 mm: 50 deg
  - 32 mm: 48 deg
  - 40 mm: 40 deg
  - 56 mm: 47 deg
- Added Celestron Omni Plossl 40 mm and 56 mm rows from official product pages.
- Added zoom AFOV ranges for Baader Hyperion Zoom and Celestron 8-24 mm Zoom.
- Normalized Celestron Barlow model names to the official product titles.

## Remaining Data Notes

- Rows marked `Specs encoded in model name` remain intentionally present. Their core aperture/focal-length values are encoded in the product name, but they should still be checked against current regional product revisions before being treated as purchase-grade specifications.
- This pass did not attempt a complete manufacturer-by-manufacturer certification of every row. It removed known legacy placeholders and corrected rows where primary manufacturer pages were reachable and clear.
