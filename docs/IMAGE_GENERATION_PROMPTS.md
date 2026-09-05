# NightScope Category Artwork - Generation Record

Date: 2026-09-05. Source introduction: 1.46.11.

The user explicitly approved Python resizing/compression. The final 16 JPEGs
are installed in `astro_viewer/resources/images/categories/` (614,168 bytes
combined). Original PNG copies remain in ignored
`build/object-imagery-1.46.11/originals/`; they are not application resources.
`IMAGE_ASSET_MANIFEST.json` records original and final SHA-256 identities.

Normalization: Pillow 12.3.0, RGB, LANCZOS resize from 1254 x 1254 to 512 x 512,
no crop, JPEG quality 92, optimized/progressive encoding, chroma subsampling 0.
There is no generative editing, colour adjustment, sharpening or added content
in this step. The 16 final images were visually checked together at 240 and
92 pixels; disposable contact sheets and the local conversion helper are in
`build/object-imagery-1.46.11/`.

Mode: built-in image-generation tool; no CLI/API fallback was used. One distinct
call per category. The generated galaxy is the style reference for the other
15 assets, not a photograph or an input target to preserve. Originals remain in
the generating environment; only normalized application assets belong in
`astro_viewer/resources/images/categories/`. Generation is not deterministic;
these prompts record the design, not a promise of byte-identical regeneration.

Every category was visually reviewed for recognizability, family consistency,
quiet margins and absence of a named-target identity. The UI explicitly labels
these as AI-generated category illustrations. They are not scientifically
verified depictions, nor are their relative scales or colours measurements.
A galaxy-system illustration is generic: three drawn members do not assert
that the selected catalogue pair has a third member. Likewise the galaxy
symbol does not assert spiral morphology for every selected galaxy.

## Prompt Set

### galaxy

Application asset: `galaxy.jpg`.
Original generation output: `exec-cf5931e2-a105-429e-a700-c1b4b9a4657e.png`.

```text
Use case: scientific-educational. Asset type: one square category illustration for the NightScope astronomy desktop app, designed to remain legible at 64 px and attractive at 512 px. Primary request: a beautiful, restrained scientific editorial illustration representing the category GALAXY, not a photograph of any named celestial object. Subject: one luminous galaxy seen at a moderate oblique angle, coherent delicate spiral structure around a softly glowing warm ivory core, subtle blue-grey dust and star-forming detail; no companion galaxies. Style/medium: polished hand-rendered astronomical illustration, precise soft painterly detail, no cartoon outlines, no infographic framing, not a telescope-photo imitation. Composition: centered isolated subject occupying roughly two-thirds of a square canvas, generous quiet margins. Backdrop: completely plain very dark charcoal #111319, no background starfield or gradient in the corners. Restrained ivory, cool steel blue and faint teal highlights, controlled luminosity rather than dazzling white bloom. No text, labels, signatures, watermark, border, frame, UI, planets or decorative space scenery. Deliver one finished compact square image, ideally 512 x 512 pixels.
```

### galaxy_system

Application asset: `galaxy_system.jpg`.
Original generation output: `exec-2a9f41ec-58fd-4954-a1f7-cbd0505b53d0.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: GALAXY SYSTEM. A small balanced gathering of three separate distant galaxies at different apparent inclinations: a restrained ivory elliptical glow, a cool oblique spiral, and a smaller near-edge-on galaxy. Clear dark gaps between their halos, no connecting lines or forced collision bridges. This represents a category encompassing pairs, triplets and groups, not a specific observed configuration. Entire group in central two-thirds of square with the same understated painterly detail.
```

### open_cluster

Application asset: `open_cluster.jpg`.
Original generation output: `exec-569e414c-ef0e-4b3f-9555-3dd1807cd609.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: OPEN STAR CLUSTER. A loose irregular gathering of around 25 individually distinguishable ivory and pale blue stellar points, varied brightness, wide dark gaps between stars, a few fainter members; no central unresolved luminous ball, no gas or nebulosity, no connecting lines. The star group fills the middle two-thirds of the square. Stars are point-like with subtle natural soft glints, not large cartoon star shapes.
```

### globular_cluster

Application asset: `globular_cluster.jpg`.
Original generation output: `exec-35d06607-5c66-4b20-b607-7f357ca6392c.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: GLOBULAR STAR CLUSTER. A round densely populated ball of hundreds of tiny warm ivory and pale blue stellar points, smoothly concentrated toward a luminous but finely resolved center and thinning naturally toward the edges. Clearly spherical distribution, not spiral, no gas, no flat disc. The cluster fills the middle two-thirds of the square.
```

### nebula

Application asset: `nebula.jpg`.
Original generation output: `exec-3a0d2667-d434-4514-8981-bcbd6fe869d0.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: DIFFUSE NEBULA, a category-level gas-cloud illustration. An irregular soft cloud of faint luminous blue-grey and ivory interstellar gas, delicate overlapping wisps and dark translucent dust veils, several subtle embedded stellar points. No ring, central shell, spiral structure or identifiable named target. Centered airy asymmetric silhouette, quiet dark margins.
```

### emission_nebula

Application asset: `emission_nebula.jpg`.
Original generation output: `exec-e88a48dc-c9b0-433b-8f04-36fb264ed8fc.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: EMISSION NEBULA / H II REGION. An irregular billowing interstellar cloud with softly luminous restrained rose-copper hydrogen emission, dark dusty filaments and small bright blue-white illuminating young stars. Delicate internal lacework, a few teal highlights, clearly diffuse gaseous boundaries and generous dark margins. No expanding circular shell, no planetary ring, no identifiable named nebula.
```

### reflection_nebula

Application asset: `reflection_nebula.jpg`.
Original generation output: `exec-2af876db-e175-4772-8f3e-7a4adad37c3a.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: REFLECTION NEBULA. A delicate irregular fan of cool blue-grey interstellar dust illuminated around two tiny bright blue-white stellar points. Soft flowing dust veils, faint darker dust lanes, graceful asymmetric shape on the same very dark charcoal backdrop. The reflected blue glow is the defining feature. No reddish emission cloud, ring or globular central ball.
```

### dark_nebula

Application asset: `dark_nebula.jpg`.
Original generation output: `exec-7519d6d3-b68c-425f-8fbf-200a153f824e.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: DARK NEBULA. An irregular opaque interstellar dust-cloud silhouette clearly blocking a restrained field of small ivory and blue stellar points behind it. The cloud itself is non-luminous charcoal-black, with fine irregular edges and faint dusty rim scattering. Maintain the reference's quiet dark outer margins; place the denser background stars behind the central cloud only so the obscuration is legible. No bright glowing nebula, no cartoon horse shape or identifiable named target.
```

### planetary_nebula

Application asset: `planetary_nebula.jpg`.
Original generation output: `exec-87ca07e1-cc2a-42ac-9021-b399aae35071.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: PLANETARY NEBULA. One delicate oval shell of expelled stellar gas around a tiny central white stellar point. Translucent blue-teal inner shell with a restrained copper-red outer rim and a clearly darker central cavity, softly feathered wisps and a physically coherent thin gaseous shell. It must look like a luminous gas shell, never a planet or solid ring. Fully contained at the center of the square with generous dark margins, no galaxy or busy background starfield.
```

### nebula_cluster

Application asset: `nebula_cluster.jpg`.
Original generation output: `exec-04acbc0e-2077-4eca-a57d-27ca8cbee203.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: NEBULA WITH OPEN STAR CLUSTER. A visibly loose gathering of around twenty individually resolved small young blue-white stars embedded in a softly glowing irregular cloud of muted copper-rose emission gas and cool blue dust. Make both the discrete open-cluster stars and gaseous nebula distinctly readable at small sizes; no dense spherical cluster, no central ring or spiral. Keep the whole grouping centered with clear quiet margins.
```

### supernova_remnant

Application asset: `supernova_remnant.jpg`.
Original generation output: `exec-6b94e47f-66a5-40be-b0dd-ed89a4bf1d13.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: SUPERNOVA REMNANT. Delicate shredded interstellar filaments tracing a large irregular incomplete expanding shell, a few long curved wisps and broken overlapping arcs of muted copper and blue-teal glowing gas, darker hollow interior, no central stellar point. Clearly filamentary and ragged rather than the smooth compact oval of a planetary nebula. The entire shell fits comfortably in the central two-thirds of the image.
```

### asterism

Application asset: `asterism.jpg`.
Original generation output: `exec-79871309-b058-4880-b8fa-c18ea49a4f40.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: ASTERISM. A sparse chance alignment of seven prominent white and cool blue point-like stars in an easily recognizable loose angular arc with one branching pair, plus very few faint field stars. No connecting lines, no gas, no dense cluster, no unresolved glow. A balanced grouping with dark gaps and generous margins, not a named real constellation or star pattern. Match the same polished subtle stellar glints of the reference style.
```

### star_cloud

Application asset: `star_cloud.jpg`.
Original generation output: `exec-ce076aab-2f76-4289-9aa9-285fedab945d.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: a Milky Way star cloud, a broad irregular window onto a wonderfully rich field of individually resolved distant stars, many tiny cool white and warm ivory points with subtle granular unresolved background starlight. The density gently rises across an elongated diagonal central region, not a compact round central nucleus. No galaxy outline, no gaseous nebula, no bright isolated dominant star, no globular-cluster ball. Restrained dark margins, astronomically suggestive painted star field.
```

### star

Application asset: `star.jpg`.
Original generation output: `exec-3eea84ef-7dc3-4837-9e11-30b98c640a14.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: a single luminous distant star seen as an unresolved point of light, placed in the center of a nearly black sparse sky. Modest fine blue-white star glint and a very restrained soft halo give it presence at small sizes. Just a few much fainter background stars. Not a resolved sun sphere, no visible stellar surface, no gas, no planets, no galaxy, no companion bright star. Same quiet polished illustrative style as the reference.
```

### double_star

Application asset: `double_star.jpg`.
Original generation output: `exec-1e8b969f-38ee-4394-8c2c-1d6d9ea26a8f.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: an optical double star, two clearly separated unresolved points of starlight near the center, one slightly brighter warm ivory and the other cooler blue-white, diagonally separated enough to remain distinct in a small thumbnail. Restrained elegant fine glints, minimal soft light. A few much fainter background stars. No connecting lines, no orbit, no transfer stream, no shared glowing envelope: this illustration must not assert that the pair is gravitationally bound. No resolved star spheres or nebula.
```

### unclassified

Application asset: `unclassified.jpg`.
Original generation output: `exec-16342392-ff70-4d2e-ba8b-f3626ca7047c.png`.

```text
Use case: scientific-educational. Generate one new square NightScope category illustration, not a photograph of a named target. Input image 1 is a STYLE REFERENCE ONLY: match its restrained polished astronomical painting, delicate detail, controlled luminosity, centered composition, generous dark margins and unobtrusive near-black charcoal background. Replace its subject completely as specified below; do not include a galaxy unless specified. Intended for thumbnails and 512 px detail cards. No text, labels, border, frame, watermark, logo, UI or unrelated scenery. Keep the background quiet and the subject clear at thumbnail size.
Subject: a neutral unidentified catalogue field in a dark sky, with a small sparse scattering of modest distant white and muted blue stars. At the center leave quiet empty dark sky, subtly indicated by four tiny discreet light-gray curved optical finder corner marks, separated and not a complete enclosing border. It conveys a catalogue position still without a known visual category. No prominent target shape, no galaxy, nebula, cluster, bright dominant single star, solar body, invented fuzzy object, text, letters, question mark, numbers or panel. The finder marks should be subtle painted details, not a full UI overlay. Match the restrained astronomical illustration family.
```
