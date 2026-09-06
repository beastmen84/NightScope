"""Update multilingual content packs through reviewed, placeholder-safe machine translation."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import OrderedDict
from functools import cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from astro_viewer.app.services.localization import content_key  # noqa: E402
from tools.translation_provider import GoogleTranslator  # noqa: E402


DATA_DIR = PROJECT_ROOT / "astro_viewer" / "data"
TRANSLATIONS_DIR = PROJECT_ROOT / "astro_viewer" / "translations"
OBJECT_FIELDS = ("short_description", "observing_notes", "best_seen")
TRANSLATION_CHUNK_LIMIT = 4_000
SEPARATOR = "\n[NIGHTSCOPE_SPLIT_0001]\n"

_ENGLISH_CONTENT_OVERRIDES = {
    ("objects", "venus", "short_description"): (
        "Venus dominates twilight with an almost unreal brightness. Through a "
        "telescope it shows no surface detail because it is covered by dense "
        "clouds, but it reveals elegant phases similar to the Moon's. It is also "
        "an excellent urban target: its value lies in following how its shape and "
        "apparent diameter change over the months. When high in the sky, it "
        "handles moderate magnification well."
    ),
    ("objects", "neptune", "short_description"): (
        "Neptune is a subtle and remote target. At the eyepiece it appears as a "
        "tiny blue disk that can remain almost stellar in small instruments, but "
        "knowing that the light comes from the outermost major planet in the "
        "Solar System gives the observation a particular sense of scale. The real "
        "achievement is identifying it with certainty and distinguishing it from "
        "the field stars."
    ),
    ("objects", "messier-M12", "short_description"): (
        "M12 is a globular cluster in Ophiuchus. It is less concentrated and more "
        "open than M10; modern studies suggest that it lost many low-mass stars "
        "during repeated passages through the Galaxy."
    ),
    ("objects", "messier-M12", "curiosity_text"): (
        "M12 appears to have lost many low-mass stars. During repeated passages "
        "through the Milky Way's disk, galactic tides may have stripped as many "
        "as a million low-mass stars from the cluster."
    ),
    ("objects", "messier-M17", "observing_notes"): (
        "For M17, record the effects of the filter and magnification separately; "
        "its integrated magnitude is 6.0 and its reference extent is 11′."
    ),
    ("objects", "messier-M20", "short_description"): (
        "M20, the Trifid Nebula, is a region in Sagittarius that combines "
        "emission and reflection nebulosity, dark lanes, and a young star cluster. "
        "It is a difficult visual target, but under a good sky it has a unique "
        "appearance."
    ),
    ("objects", "messier-M22", "short_description"): (
        "M22 is one of the brightest and most spectacular globular clusters "
        "visible from mid-northern latitudes. It is large, relatively loosely "
        "concentrated, and easier to resolve than many similar clusters, especially "
        "when high above the horizon. In a medium-aperture telescope it can fill "
        "the field with stars and shows a less compact core than M13."
    ),
    ("objects", "messier-M22", "observing_notes"): (
        "Observe it near culmination at medium magnification; its broad, rich outer "
        "regions deserve a field of view that is not too narrow."
    ),
    ("objects", "messier-M42", "short_description"): (
        "M42, the Great Orion Nebula, is the most spectacular star-forming region "
        "readily visible from the Northern Hemisphere. Even from a city it shows "
        "a bright core around the Trapezium; under dark skies, wings, arcs, and "
        "dark regions extend far beyond the center. It offers detail at both low "
        "and high magnification."
    ),
    ("objects", "messier-M48", "short_description"): (
        "M48 is an open cluster in Hydra. It is large, bright, and often "
        "overlooked. At low magnification it shows a broad, loose structure that "
        "is well suited to winter or spring skies."
    ),
    ("objects", "messier-M78", "observing_notes"): (
        "Transparency is crucial: observe it without narrowband filters, at low "
        "magnification, and under a dark sky."
    ),
    ("objects", "messier-M84", "short_description"): (
        "M84 is variously classified as an elliptical or lenticular galaxy in "
        "the Virgo Cluster. Old starlight dominates its body, but the center "
        "harbors a supermassive black hole; Hubble images also reveal warped "
        "dust lanes."
    ),
    ("objects", "messier-M84", "curiosity_text"): (
        "M84 lies in Markarian's Chain and hosts an active nucleus. A relativistic "
        "jet emerges from the region of its central black hole, although it is far "
        "less conspicuous than the jet from nearby M87."
    ),
    ("objects", "messier-M86", "short_description"): (
        "M86 is a Virgo galaxy with a classification intermediate between "
        "elliptical and lenticular. Observing it with M84 and the other members "
        "of Markarian's Chain gives the impression of crossing an entire galaxy "
        "cluster."
    ),
    ("objects", "messier-M109", "short_description"): (
        "M109 is a barred spiral galaxy in Ursa Major, close to Phecda. It is not "
        "showy, but it is relatively easy to locate, and its central bar makes its "
        "structure interesting to examine."
    ),
    ("objects", "caldwell-C51", "short_description"): (
        "C51 (IC 1613) is an irregular galaxy in Cetus. It is extended and has "
        "very low surface brightness: first look for its faint overall glow, then "
        "scan the outer regions with averted vision. It covers about 12′ × 11′, "
        "so magnitude 9.0 must be interpreted as an integrated brightness."
    ),
    ("objects", "caldwell-C51", "observing_notes"): (
        "C51 covers about 12′ × 11′: preserve dark adaptation, use a wide field, "
        "and examine the edges with averted vision."
    ),
    ("objects", "caldwell-C53", "short_description"): (
        "C53 (NGC 3115), the Spindle Galaxy, is a lenticular galaxy in Sextans. "
        "It has a smooth, concentrated glow without visible arms; the useful "
        "detail is the gradient from the core to the outer halo. Magnitude 9.1 "
        "describes the whole object, while its 8′ × 3′ extent helps estimate the "
        "actual surface contrast."
    ),
    ("objects", "caldwell-C80", "short_description"): (
        "C80, NGC 5139, Omega Centauri, is the largest and brightest globular "
        "cluster in the Milky Way. To the naked eye it can resemble a fuzzy star; "
        "through a telescope it becomes an enormous mass of stars, broader and "
        "less concentrated than many other globular clusters. From low northern "
        "latitudes, observe it near culmination. Its 36′ apparent extent calls "
        "for a wide field, while greater aperture resolves more stars."
    ),
    ("objects", "caldwell-C80", "observing_notes"): (
        "Use a field wide enough to contain the entire cluster, then apply medium "
        "magnification to resolve its broad stellar outskirts."
    ),
    ("objects", "messier-M16", "observing_notes"): (
        "For M16 (Eagle Nebula), integrated magnitude 6.4, alternate between "
        "direct and averted vision while keeping the same exit pupil so the "
        "comparison remains reliable."
    ),
    ("objects", "messier-M26", "observing_notes"): (
        "M26 is about 14′ wide and has integrated magnitude 8.0; examine the "
        "cluster as a whole before evaluating its closest stellar pairs."
    ),
    ("objects", "messier-M56", "short_description"): (
        "M56 is a globular cluster in Lyra, between Lyra and Cygnus in a region "
        "already rich in targets. It is a subtle globular cluster that rewards "
        "patient observation rather than a quick glance."
    ),
    ("objects", "messier-M76", "observing_notes"): (
        "For M76 (Little Dumbbell Nebula), integrated magnitude 10.1, alternate "
        "between direct and averted vision while keeping the same exit pupil so "
        "the comparison remains reliable."
    ),
    ("objects", "caldwell-C1", "observing_notes"): (
        "Use a medium field under dark skies; increase magnification moderately "
        "to separate the many faint stars from the background."
    ),
    ("objects", "caldwell-C4", "observing_notes"): (
        "For C4 (NGC 7023 - Iris Nebula), integrated magnitude 6.8, alternate "
        "between direct and averted vision while keeping the same exit pupil so "
        "the comparison remains reliable."
    ),
    ("objects", "caldwell-C10", "observing_notes"): (
        "For C10 (NGC 663), integrated magnitude 7.1, start with a field wider "
        "than 16′; narrow it only if component separation improves."
    ),
    ("objects", "caldwell-C22", "observing_notes"): (
        "For C22 (NGC 7662 - Blue Snowball Nebula), integrated magnitude 9.2, "
        "alternate between direct and averted vision while keeping the same exit "
        "pupil so the comparison remains reliable."
    ),
    ("objects", "caldwell-C28", "observing_notes"): (
        "For C28 (NGC 752), integrated magnitude 5.7, start with a field wider "
        "than 50′; narrow it only if component separation improves."
    ),
    ("objects", "caldwell-C46", "observing_notes"): (
        "For C46 (NGC 2261 - Hubble's Variable Nebula), integrated magnitude "
        "10.0, alternate between direct and averted vision while keeping the "
        "same exit pupil so the comparison remains reliable."
    ),
    ("objects", "caldwell-C53", "observing_notes"): (
        "For C53 (NGC 3115 - Spindle Galaxy), magnitude 9.1 and dimensions "
        "8′ x 3′ must be considered together: surface contrast determines how "
        "much of the galaxy becomes visible."
    ),
    ("objects", "caldwell-C55", "observing_notes"): (
        "For C55 (NGC 7009 - Saturn Nebula), integrated magnitude 8.3, use its "
        "2.5′ x 1′ dimensions to keep the entire nebula in view before narrowing "
        "the field."
    ),
    ("objects", "caldwell-C58", "observing_notes"): (
        "For C58 (NGC 2360), integrated magnitude 7.2, start with a field wider "
        "than 13′; narrow it only if component separation improves."
    ),
    ("objects", "caldwell-C109", "observing_notes"): (
        "For C109 (NGC 3195), use its 0.6′ size to keep the entire nebula in view "
        "before narrowing the field."
    ),
    ("catalogue_objects", "caldwell-C13", "name"): "NGC 457 - Owl Cluster",
    ("catalogue_objects", "caldwell-C38", "name"): "NGC 4565 - Needle Galaxy",
    ("catalogue_objects", "caldwell-C53", "name"): "NGC 3115 - Spindle Galaxy",
    ("equipment_filters", "astronomik::uhc-e", "notes"): (
        "Moderate bandpass suitable for small apertures."
    ),
    ("equipment_filters", "baader::oiii super-g 9 nm", "notes"): (
        "Narrow OIII filter for medium to large apertures."
    ),
    ("equipment_filters", "baader::fringe killer", "notes"): (
        "Reduces chromatic aberration in achromatic refractors."
    ),
    ("equipment_reducers", "starizona::sct corrector iv::0.63", "notes"): (
        "Photographic focal reducer and corrector for classic SCTs."
    ),
    (
        "equipment_reducers",
        "starizona::night owl sct reducer-corrector::0.4",
        "connection",
    ): "2-inch body",
    (
        "equipment_reducers",
        "starizona::night owl sct reducer-corrector::0.4",
        "notes",
    ): "Fast photographic focal reducer for small sensors.",
    ("equipment_reducers", "william optics::flat 73r::0.8", "notes"): (
        "Dedicated focal reducer and field flattener."
    ),
    ("equipment_reducers", "william optics::ultra flat 91::0.79", "notes"): (
        "Dedicated focal reducer with a corrected field."
    ),
    ("equipment_reducers", "william optics::ultra flat 132::0.79", "notes"): (
        "Dedicated focal reducer with a corrected field."
    ),
    ("equipment_reducers", "william optics::ultra flat 156::0.79", "notes"): (
        "Dedicated focal reducer with a corrected field."
    ),
    (
        "equipment_reducers",
        "sky-watcher::0.85x reducer-corrector ed80::0.85",
        "connection",
    ): "M48 camera side",
    (
        "equipment_reducers",
        "sky-watcher::0.85x reducer-corrector ed100::0.85",
        "connection",
    ): "M48 camera side",
    (
        "equipment_reducers",
        "sky-watcher::0.85x reducer-corrector ed120::0.85",
        "connection",
    ): "M48 camera side",
}

_ENGLISH_TELESCOPE_LABELS = {
    "optical_type": {
        "refractor": "Refractor",
    },
    "mount_type": {
        "altazimuth": "Altazimuth",
        "Dobson": "Dobsonian",
        "Dobson tabletop": "Tabletop Dobsonian",
        "equatorial": "Equatorial",
        "equatorial CG-4": "CG-4 equatorial",
    },
}

_ENGLISH_OBJECT_TEXT_REPLACEMENTS = (
    ("multi-billion-dollar age", "multi-billion-year age"),
    ("planetary mixer", "planetary nebula"),
    ("discreet and not immediate", "subtle and not immediately obvious"),
    ("With a wide shot both can fit into the same frame.", "A wide field of view can include both galaxies."),
    ("before narrowing the frame.", "before narrowing the field."),
    ("it records central concentration", "record central concentration"),
    ("magnitude 6.3 is built in:", "with integrated magnitude 6.3:"),
    ("the dark sky counts more than the magnification", "dark-sky quality matters more than magnification"),
    ("the design of the group counts above all", "the overall pattern of the group matters most"),
    ("The figure of ", "The integrated magnitude of "),
    (" magnitudes concerns the entire object", " describes the entire object"),
    (
        "The first reading concerns the nucleus, orientation and shape of the halo",
        "Start by examining the nucleus, orientation, and shape of the halo",
    ),
    ("with more aperture and stable seeing", "with a larger aperture and steady seeing"),
    ("then move up with stable seeing", "then increase magnification when the seeing is steady"),
    ("the central star is sought without easy expectations", "the central star remains challenging"),
    ("increase moderately on M81", "increase magnification moderately on M81"),
    ("The rod and arms", "The bar and arms"),
    ("acquired in a fusion", "acquired through a merger"),
    ("trace of that ancient fusion", "trace of that ancient merger"),
    ("rejuvenated by fusions or transfers", "rejuvenated by mergers or transfers"),
    ("it initially preserves a field wider than", "start with a field wider than"),
    ("initially retains a field wider than", "start with a field wider than"),
    ("it initially retains a wider field of", "start with a field wider than"),
    ("before increasing.", "before increasing magnification."),
    ("before boosting.", "before increasing magnification."),
    ("before brightening.", "before increasing magnification."),
    ("Markarian Range", "Markarian's Chain"),
    ("superficial details", "surface details"),
    ("dark fractures in the disc", "dark lanes in the disk"),
    ("how much collisions", "how collisions"),
    ("appear behind her", "appear behind it"),
    ("constellation Bootes", "constellation Boötes"),
    ("name it Trifida.", "name it the Trifid Nebula."),
    ("exit pupil so the comparison", "exit pupil, so the comparison"),
    ("becomes sharp and the edge", "becomes sharp, and the edge"),
    ("noticeably deformed and the nucleus", "noticeably deformed, and the nucleus"),
    ("In Lepus it appears", "In Lepus, it appears"),
    ("At first it looks", "At first, it looks"),
    ("bright core and the dotted edge", "bright core and the granular outer region"),
    (
        "so aperture and sky impact differently.",
        "so both aperture and sky quality affect how much detail is visible.",
    ),
)

_SPANISH_CONTENT_REPLACEMENTS = (
    ("binoculares", "prismáticos"),
    ("Binoculares", "Prismáticos"),
    ("Clúster", "Cúmulo"),
    ("clúster", "cúmulo"),
    ("Racimo", "Cúmulo"),
    ("racimo", "cúmulo"),
    ("ampliación", "aumento"),
    ("Ampliación", "Aumento"),
    ("ampliaciones", "aumentos"),
    ("Ampliaciones", "Aumentos"),
    ("campo verdadero", "campo real"),
    ("Campo verdadero", "Campo real"),
    ("una visión estable", "un seeing estable"),
    ("Una visión estable", "Un seeing estable"),
    ("la visión estable", "el seeing estable"),
    ("La visión estable", "El seeing estable"),
    ("con buena visión", "con buen seeing"),
    ("visión estable", "seeing estable"),
    ("visión constante", "seeing estable"),
    ("visión sea estable", "seeing sea estable"),
    ("buena visión", "buen seeing"),
    ("la seeing", "el seeing"),
    ("una seeing", "un seeing"),
    ("Ver decide casi todo.", "El seeing lo decide casi todo."),
    ("BordeHD", "EdgeHD"),
    ("bordeHD", "EdgeHD"),
    (
        "Caja de cambios dedicada con rango correcto.",
        "Reductor focal dedicado con campo corregido.",
    ),
    (
        "caja de cambios dedicada con rango correcto.",
        "reductor focal dedicado con campo corregido.",
    ),
    ("Clúster abierto", "Cúmulo abierto"),
    ("clúster abierto", "cúmulo abierto"),
    ("Grupo abierto", "Cúmulo abierto"),
    ("grupo abierto", "cúmulo abierto"),
    ("Clúster de torres de enfriamiento", "Cúmulo de la Torre de Refrigeración"),
    ("Cúmulo de torres de enfriamiento", "Cúmulo de la Torre de Refrigeración"),
    ("Rose Cluster", "Cúmulo de la Rosa"),
    ("Butterfly Cluster", "Cúmulo de la Mariposa"),
    ("Wild Duck Cluster", "Cúmulo del Pato Salvaje"),
    ("Webb's Cross Cluster", "Cúmulo de la Cruz de Webb"),
    ("Jellyfish Cluster", "Cúmulo de la Medusa"),
    ("Pinwheel Galaxy", "Galaxia del Molinete"),
    ("Shoe-Buckle Cluster", "Cúmulo de la Hebilla"),
    ("Pinwheel Cluster", "Cúmulo del Molinete"),
    ("Starfish Cluster", "Cúmulo de la Estrella de Mar"),
    ("Pyramid Cluster", "Cúmulo de la Pirámide"),
    ("Beehive Cluster", "Cúmulo del Pesebre"),
    ("Heart Cluster", "Cúmulo con Forma de Corazón"),
    ("Scorpion Cluster", "Cúmulo del Escorpión"),
    ("Spectre Cluster", "Cúmulo del Espectro"),
    ("King Cobra", "Cobra Real"),
    ("Golden Eye Cluster", "Cúmulo del Ojo Dorado"),
    ("Angelfish Cluster", "Cúmulo del Pez Ángel"),
    ("Phantom Galaxy", "Galaxia Fantasma"),
    ("Little Dumbbell", "Pequeña Mancuerna"),
    ("Southern Pinwheel Galaxy", "Galaxia del Molinete Austral"),
    ("Squid Galaxy", "Galaxia del Calamar"),
    ("Carabin Galaxy", "Galaxia de Carabin"),
    ("Mirror Galaxy", "Galaxia del Espejo"),
    ("Surfboard Galaxy", "Galaxia de la Tabla de Surf"),
    ("Vacuum Cleaner Galaxy", "Galaxia de la Aspiradora"),
    ("Andromeda Satellite #1", "Satélite de Andrómeda n.º 1"),
    ("Andromeda Satellite #2", "Satélite de Andrómeda n.º 2"),
    ("Fireworks Galaxy", "Galaxia de los Fuegos Artificiales"),
    ("Owl Cluster", "Cúmulo del Búho"),
    ("Silver Needle Galaxy", "Galaxia de la Aguja Plateada"),
    ("Whale Galaxy", "Galaxia de la Ballena"),
    ("Needle Galaxy", "Galaxia de la Aguja"),
    ("Barnard Galaxy", "Galaxia de Barnard"),
    ("Caroline Cluster", "Cúmulo de Caroline"),
    ("Escultor Galaxy", "Galaxia del Escultor"),
    ("Omicron Velorum Cluster", "Cúmulo de Ómicron Velorum"),
    ("Cluster S Normae", "Cúmulo de S Normae"),
    ("Jewel Box Cluster", "Cúmulo del Joyero"),
    ("Lambda Centauri Cluster", "Cúmulo de Lambda Centauri"),
    ("Tau Canis Majoris Cluster", "Cúmulo de Tau Canis Majoris"),
    ("Little Beehive Cluster", "Cúmulo de la Pequeña Colmena"),
    ("Black Eye Galaxy", "Galaxia del Ojo Negro"),
    ("Spindle Galaxy", "Galaxia del Huso"),
    ("Civetta Cluster", "Cúmulo del Búho"),
    ("visualización directa y evitada", "visión directa y periférica"),
    ("visualización directa y desviada", "visión directa y periférica"),
    ("visión evitada", "visión periférica"),
    ("una visualización limpia y agradable", "una observación limpia y agradable"),
    ("Coma Berenices", "Cabellera de Berenice"),
    ("Coma di Berenice", "Cabellera de Berenice"),
    ("Coma Berenice", "Cabellera de Berenice"),
    ("Berenice Coma", "Cabellera de Berenice"),
    ("la aumento", "el aumento"),
    ("una aumento", "un aumento"),
    ("de la aumento", "del aumento"),
    ("la globular", "el cúmulo globular"),
    ("una globular", "un cúmulo globular"),
    ("Es globular", "Es un cúmulo globular"),
    ("Es un globular", "Es un cúmulo globular"),
    ("Se trata de un globular", "Se trata de un cúmulo globular"),
    ("un pequeño globular", "un pequeño cúmulo globular"),
    ("un globular muy", "un cúmulo globular muy"),
    ("una inusual globular", "un cúmulo globular inusual"),
    ("una magnífica globular", "un magnífico cúmulo globular"),
    ("muchas otras globulares", "muchos otros cúmulos globulares"),
    ("muchas globulares", "muchos cúmulos globulares"),
    ("otras globulares", "otros cúmulos globulares"),
    ("futuros globulares", "futuros cúmulos globulares"),
    ("globular adquirido", "cúmulo globular adquirido"),
    ("cúmulo globular compacta", "cúmulo globular compacto"),
    ("cúmulo globular remota", "cúmulo globular remoto"),
    ("cúmulo globular suelta", "cúmulo globular suelto"),
    ("cúmulo globular relativamente rica", "cúmulo globular relativamente rico"),
    ("cúmulo globular rica", "cúmulo globular rico"),
    ("relativamente desenfocado", "relativamente poco concentrado"),
    ("muchos grupos similares", "muchos cúmulos similares"),
    ("a medida que aumenta el aumento", "al subir el aumento"),
    ("suele tener mayores poderes que", "suele admitir más aumento que"),
    ("es un planeta brillante", "es una nebulosa planetaria brillante"),
    ("muchas estrellas globulares", "muchos cúmulos globulares"),
    ("estrellas solubles", "estrellas resolubles"),
    (
        "la apertura y el cielo impactan de manera diferente",
        "la apertura y la calidad del cielo influyen de forma distinta",
    ),
    ("La preparación de campo", "La preparación del campo"),
    ("comienza desde una extensión", "parte de una extensión"),
    ("comienza en una extensión", "parte de una extensión"),
    ("En el ocular se debe buscar en una escala de", "En el ocular debe buscarse una extensión de"),
    ("Satélite Andrómeda #1", "Satélite de Andrómeda n.º 1"),
    ("Satélite Andrómeda #2", "Satélite de Andrómeda n.º 2"),
    ("Andrómeda Satellite #2", "Satélite de Andrómeda n.º 2"),
    ("Triángulo/Galaxia Molinete", "Galaxia del Triángulo o del Molinete"),
    ("Flickering Globular", "Cúmulo Globular Parpadeante"),
    ("Intergalactic Wanderer", "Vagabundo Intergaláctico"),
    ("La galaxia Surfboard", "Esta galaxia"),
    ("Cúmulo cruzado de Webb", "Cúmulo de la Cruz de Webb"),
    ("Cúmulo de mariposas", "Cúmulo de la Mariposa"),
    ("Cúmulo Pirámide", "Cúmulo de la Pirámide"),
    ("Nebulosa Dumbbell", "Nebulosa de la Mancuerna"),
    ("Nebulosa Cocoon", "Nebulosa del Capullo"),
    ("Nebulosa Bola de Nieve Azul", "Nebulosa de la Bola de Nieve Azul"),
    ("Nebulosa de la Estrella Flamígera", "Nebulosa de la Estrella Llameante"),
    ("Galaxias Antenas", "Galaxias de las Antenas"),
    ("Galaxia Aguja", "Galaxia de la Aguja"),
    ("Galaxia Ojo de Gato", "Galaxia del Ojo de Gato"),
    ("M77 (Ballena A", "M77 (Cetus A"),
    ("Velas", "Vela"),
    ("al aumentar la potencia", "al subir el aumento"),
    ("aumente el aumento", "suba el aumento"),
    (
        "cuando la visión permite aumentar el aumento",
        "cuando el seeing permite subir el aumento",
    ),
    ("textura de la estrella", "textura estelar"),
    ("Galaxia Sombrero", "Galaxia del Sombrero"),
    ("Sombrero tiene", "La Galaxia del Sombrero tiene"),
    ("Nebulosa Quilla", "Nebulosa de Carina"),
    ("Antenna Galaxies", "Galaxias de las Antenas"),
    ("Tarantula", "Tarántula"),
    ("cúmulo de discos abiertos", "cúmulo abierto"),
    ("capturar la textura", "apreciar la textura"),
    ("un campo bien oscurecido", "un campo con el fondo bien oscuro"),
    (
        "determinan gran parte de la representación",
        "determinan en gran medida su visibilidad",
    ),
    ("requiere un campo consistente con su escala", "requiere un campo acorde con su escala"),
    (
        "dos puntos de datos que deben leerse junto con",
        "dos datos que deben valorarse junto con",
    ),
    (
        "dos puntos de datos que se pueden leer junto con",
        "dos datos que deben valorarse junto con",
    ),
    ("qué tan prominente", "hasta qué punto"),
    ("sólo", "solo"),
    ("sólo reducirlo si", "redúzcalo solo si"),
    ("reducirlo sólo si", "redúzcalo solo si"),
    (
        "primer eje de verificación y condensación central",
        "compruebe primero el eje principal y la condensación central",
    ),
    (
        "verifique el primer eje y la condensación central",
        "compruebe primero el eje principal y la condensación central",
    ),
    ("para que la comparación siga siendo confiable", "para que la comparación siga siendo fiable"),
    ("coordenadas confiables", "coordenadas fiables"),
    ("antes de impulsarse", "antes de aumentar"),
    ("antes de iluminarse", "antes de aumentar"),
    ("en el mismo marco", "en el mismo campo visual"),
    ("cúmulo cúmulo globular", "cúmulo globular"),
    ("grupo Leone", "Grupo de Leo"),
    ("bulto central", "bulbo central"),
    ("bulto estelar", "bulbo estelar"),
    ("el núcleo del M96", "el núcleo de M96"),
    ("Cisne Loop", "Bucle del Cisne"),
    ("Andrómeda Satélite #1", "Satélite de Andrómeda n.º 1"),
    ("Andrómeda Satélite #2", "Satélite de Andrómeda n.º 2"),
    ("grupo estelar compacto lo que", "cúmulo estelar compacto, lo que"),
    (
        "cuánto se ha barajado el grupo",
        "cuánto se ha mezclado dinámicamente el cúmulo",
    ),
    ("Léelo primero", "Examínelo primero"),
    ("Alternar visión", "Alterne la visión"),
    ("y conservar el que no extingue", "y conserve el que no apague"),
    ("dentro de Rosetta", "en el interior de la Nebulosa Roseta"),
    ("La cavidad central de Rosetta", "La cavidad central de la Nebulosa Roseta"),
    ("cuando quieres ver", "cuando se quiere observar"),
    ("lo que estás observando", "lo que se está observando"),
    ("punto de estrella", "punto estelar"),
    ("Proyectada hacia el centro de la Vía Láctea", "Proyectado hacia el centro de la Vía Láctea"),
    ("Con un aumento reducido", "Con poco aumento"),
    ("campo mediano", "campo medio"),
    ("aumente moderadamente el aumento", "suba el aumento con moderación"),
    ("cuando el cielo está bien", "cuando las condiciones son buenas"),
    ("de la M20", "de M20"),
    ("de la M37", "de M37"),
    ("de la M38", "de M38"),
    ("El M39", "M39"),
    ("Está destinado a prismáticos", "Es ideal para prismáticos"),
    ("bajo el cielo oscuro", "bajo un cielo oscuro"),
    ("M33 (Triángulo/Galaxia del Molinete)", "M33 (Galaxia del Triángulo o del Molinete)"),
    ("La galaxia Triángulo", "La Galaxia del Triángulo"),
    ("M36 (Molinillo de viento)", "M36 (Cúmulo del Molinete)"),
    ("Utilice la extensión 29′", "Utilice la extensión de 29′"),
    ("Debajo de Sirio, el M41", "Al sur de Sirio, M41"),
    ("Obsérvelos con prismáticos", "Obsérvelas con prismáticos"),
    ("el puente hacia el compañero", "el puente hacia la compañera"),
    ("Galaxia Girasol", "Galaxia del Girasol"),
    ("La galaxia Black Eye", "La Galaxia del Ojo Negro"),
    ("Leo Triplet", "Triplete de Leo"),
    ("Triple Leo", "Triplete de Leo"),
    ("Triplete Leo", "Triplete de Leo"),
    ("Cúmulo en forma de corazón", "Cúmulo con Forma de Corazón"),
    ("Pequeña Nebulosa Mancuerna", "Nebulosa de la Pequeña Mancuerna"),
    ("Molinillo del Sur", "Molinete Austral"),
    ("Cadena Markarian", "Cadena de Markarian"),
    ("Cordillera Markarian", "Cadena de Markarian"),
    ("Markarian Range", "Cadena de Markarian"),
    ("Observarlo junto con M84", "Observarla junto con M84"),
    ("Visualmente es sobrio", "Visualmente es sobria"),
    ("Telescopio Event Horizon", "Event Horizon Telescope"),
    ("Localizarlo con confianza", "Localizarla con seguridad"),
    (
        "A simple vista es una de las galaxias más simples de Lebreles",
        "Visualmente es una de las galaxias más fáciles de Lebreles",
    ),
    ("del grupo Leo", "del Grupo de Leo"),
    ("para destacarse de", "para destacar frente a"),
    ("es un planeta grande y tenue", "es una nebulosa planetaria grande y tenue"),
    ("No perdona los cielos despejados", "No perdona los cielos brillantes"),
    ("Desde el ocular", "En el ocular"),
    ("Visto desde el ocular", "En el ocular"),
    ("Cúmulo de Crucifijos", "Cúmulo del Crucifijo"),
    ("Hoggi", "Hodierna"),
    ("ésta", "esta"),
    ("El polvo de cisne", "El polvo de Cisne"),
    ("más distantes insertados", "más distantes incluidos"),
    ("Cork y Butterfly", "Corcho y Mariposa"),
    ("emisiones de combustible tan intensas", "emisiones tan intensas"),
    ("prototipo de Seyferts tipo 2", "prototipo de las galaxias Seyfert de tipo 2"),
    ("El sobrevuelo de M81", "El encuentro cercano con M81"),
    ("incorporadas al pasado", "incorporadas en el pasado"),
    ("a pesar de parecer casi como", "aunque parece"),
    ("El núcleo del M96", "El núcleo de M96"),
    ("disco cercano al borde", "disco visto casi de canto"),
    ("chorros adheridos", "chorros asociados"),
    ("acorde a su escala", "acorde con su escala"),
    ("y deja que", "y deje que"),
    ("La estrella facilita señalar", "La estrella facilita la localización"),
    ("; con filtro OIII", "; con un filtro OIII"),
    ("observe en qué aumento", "observe con qué aumento"),
    ("El perfil del C45", "El perfil de C45"),
    ("a lo largo de todo el 5,9′ del diámetro", "a lo largo de sus 5,9′ de diámetro"),
    ("asociada con la Roseta", "asociada a la Nebulosa Roseta"),
    ("La roseta cubre", "La Nebulosa Roseta cubre"),
    ("segmentos de anillo alrededor del campo", "segmentos del anillo alrededor del cúmulo"),
    ("En el campo, C51 se extiende 12′ x 11′", "En el campo, C51 abarca 12′ x 11′"),
    ("antes de aumentar el aumento", "antes de subir el aumento"),
    ("hacer que se note sorprendentemente", "hacerla destacar de forma sorprendente"),
    ("Nebulosa de los Insectos", "Nebulosa del Insecto"),
    (
        "leer la cavidad ovalada y central",
        "apreciar la forma ovalada y la cavidad central",
    ),
    ("comenzar a convertirse en estrellas", "empezar a resolverse en estrellas"),
    ("cúmulos sumergidos", "cúmulos inmersos"),
    ("Obsérvelo bajo un cielo muy oscuro", "Obsérvela bajo un cielo muy oscuro"),
    ("afiliación física", "pertenencia física"),
    ("casi sin gas y con formación estelar reciente", "casi sin gas ni formación estelar reciente"),
    ("evolución completamente aburrida", "historia evolutiva sencilla"),
    ("rastro negro", "franja oscura"),
    ("un compañero menor", "una galaxia compañera menor"),
    ("un análogo de canto", "un análogo visto de canto"),
    ("centro del cúmulo Perseo", "centro del Cúmulo de Perseo"),
    ("la concha filamentosa", "la envoltura filamentosa"),
    ("una instantánea avanzada de", "una imagen de una fase avanzada de"),
    (", perspectiva que crea", ", una perspectiva que crea"),
    ("la escoba de bruja", "la Escoba de la Bruja"),
    ("se ve aún más cerca del borde", "se ve todavía más de canto"),
    ("las estrellas más viejas normales", "las estrellas normales más antiguas"),
    ("galaxia enana del grupo local", "galaxia enana del Grupo Local"),
    (
        "queda poco gas cerca para tragar",
        "queda poco gas cercano que pueda acrecer",
    ),
    ("galaxias Antenas", "Galaxias de las Antenas"),
    ("el par de antenas", "las Galaxias de las Antenas"),
    ("galaxia barrada cercana al borde", "galaxia barrada vista casi de canto"),
    ("telescopio Webb", "telescopio espacial James Webb"),
    (
        "cúmulo joven en extinción interestelar no uniforme",
        "cúmulo joven afectado por una extinción interestelar desigual",
    ),
    ("su compañero visible", "su compañera visible"),
    ("años, cantidad suficiente", "años, tiempo suficiente"),
    ("El Jewel Box", "El Cúmulo del Joyero"),
    ("Muchos giran rápidamente", "Muchas giran rápidamente"),
    ("convirtiendo una matriz en", "convirtiendo esta alineación en"),
    ("El Coalsack", "El Saco de Carbón"),
    ("polvo de Coalsack", "polvo del Saco de Carbón"),
    ("Galaxia Espiral hinchada", "Galaxia Espiral Hinchada"),
    ("galaxia espiral hinchada", "Galaxia Espiral Hinchada"),
    (
        "están orbitados por un planeta apodado Matusalén",
        "alrededor de los cuales orbita un planeta apodado Matusalén",
    ),
    ("No fue reconocido hasta 1964", "No se reconoció hasta 1964"),
    ("edad multimillonaria del sistema", "edad de miles de millones de años del sistema"),
    (
        "resolvió la nebulosidad a simple vista en unas cuarenta estrellas",
        "resolvió en unas cuarenta estrellas la nebulosidad visible a simple vista",
    ),
    ("M47 se consideró perdida", "M47 se consideró perdido"),
    ("Una gigante roja muy obvia", "Una gigante roja muy evidente"),
    ("durante decenas de miles de años luz", "a lo largo de decenas de miles de años luz"),
    ("más distantes insertados por Messier", "más distantes incluidos por Messier"),
    ("incorporadas al pasado", "incorporadas en el pasado"),
    ("disco cercano al borde", "disco visto casi de canto"),
    ("difícil de alcanzar", "difícil de detectar"),
    ("el centro del cúmulo Perseo", "el centro del Cúmulo de Perseo"),
    ("un compañero menor", "una galaxia compañera menor"),
    ("una instantánea avanzada", "una imagen de una fase avanzada"),
    ("una galaxia enana del grupo local", "una galaxia enana del Grupo Local"),
    ("las dos galaxias Antenas", "las dos Galaxias de las Antenas"),
    ("una galaxia barrada cercana al borde", "una galaxia barrada vista casi de canto"),
    ("la compañera visible", "la estrella compañera visible"),
    ("Sus pequeñas dimensiones y su contraste relativamente alto lo hacen adecuado", "Sus pequeñas dimensiones y su contraste relativamente alto la hacen adecuada"),
    ("mejores objetos planetarios", "mejores nebulosas planetarias"),
    ("los suburbios grandes y ricos", "la periferia extensa y rica"),
    ("análisis de conglomerados", "recorrido por cúmulos"),
    ("fusión de dos conglomerados antiguos", "fusión de dos cúmulos antiguos"),
    ("Sirius", "Sirio"),
    ("Estrella cenital", "Zenith Star"),
    ("Diamante Negro", "Black Diamond"),
    ("Diamante negro", "Black Diamond"),
    ("Hilo EdgeHD", "Rosca EdgeHD"),
    ("EdgeHD 14 hilos", "Rosca EdgeHD 14"),
    ("Sistema deflector SCT", "Sistema de bafle SCT"),
    ("Ritchey-Chretien", "Ritchey-Chrétien"),
    (
        "Accesorio de fotografía ópticamente adaptado.",
        "Accesorio fotográfico adaptado ópticamente.",
    ),
    ("suelta y suelta", "abierta y dispersa"),
    ("Schmidt-Cassegrain Meade y la SCT clásica", "SCT clásicos de Meade"),
)

_SPANISH_TELESCOPE_LABELS = {
    "optical_type": {
        "radiocontrol": "Ritchey-Chrétien",
        "refractor petzval": "Refractor Petzval",
        "refractor": "Refractor",
        "catadióptrico": "Catadióptrico",
        "Newton": "Newtoniano",
    },
    "mount_type": {
        "Altazimut": "Altazimutal",
        "Altazimut Ir a": "Altazimutal GoTo",
        "CG-4 ecuatorial": "Ecuatorial CG-4",
        "dobsoniano": "Dobson",
        "Dobsoniano de mesa": "Dobson de sobremesa",
        "Dobsoniano plegable": "Dobson plegable",
        "ecuatorial": "Ecuatorial",
        "Empuje Dobsoniano": "Dobson PushTo",
        "Ir a la bifurcación": "Horquilla GoTo",
        "PushTo altazimutal": "Altazimutal PushTo",
    },
}

_SPANISH_BEST_SEEN = {
    "Alargamientos máximos": "Máximas elongaciones",
    "Alrededor de la oposición": "En torno a la oposición",
    "Anochecer o amanecer según elongación": (
        "Al anochecer o al amanecer, según la elongación"
    ),
    "Cuando supera los 30 grados de altitud": (
        "Cuando supere los 30 grados de altitud"
    ),
    "Durante el día, utilizando un filtro solar de apertura total certificado": (
        "Durante el día, con un filtro solar certificado de apertura completa"
    ),
    "invierno": "Invierno",
    "primavera": "Primavera",
    "primavera y verano": "Primavera y verano",
    "Todas las fases excepto Luna Llena": (
        "Todas las fases excepto la Luna llena"
    ),
    "verano y otoño": "Verano y otoño",
}

_SPANISH_CATALOGUE_NAMES = {
    "messier-M1": "Nebulosa del Cangrejo",
    "messier-M4": "Cúmulo globular de la Araña",
    "messier-M5": "Cúmulo de la Rosa",
    "messier-M6": "Cúmulo de la Mariposa",
    "messier-M7": "Cúmulo de Ptolomeo",
    "messier-M8": "Nebulosa de la Laguna",
    "messier-M11": "Cúmulo del Pato Salvaje",
    "messier-M13": "Gran cúmulo de Hércules",
    "messier-M15": "Gran cúmulo de Pegaso",
    "messier-M16": "Nebulosa del Águila",
    "messier-M17": (
        "Nebulosa Omega, del Cisne, de la Herradura, de la Langosta o de la "
        "Marca de Verificación"
    ),
    "messier-M18": "Cúmulo del Cisne Negro",
    "messier-M20": "Nebulosa Trífida",
    "messier-M21": "Cúmulo de la Cruz de Webb",
    "messier-M22": "Gran cúmulo de Sagitario",
    "messier-M24": "Pequeña Nube Estelar de Sagitario",
    "messier-M27": "Nebulosa de la Mancuerna",
    "messier-M29": "Cúmulo de la Torre de Refrigeración",
    "messier-M30": "Cúmulo de la Medusa",
    "messier-M31": "Galaxia de Andrómeda",
    "messier-M32": "Satélite de Andrómeda n.º 1",
    "messier-M33": "Galaxia del Triángulo o del Molinete",
    "messier-M34": "Cúmulo Espiral",
    "messier-M35": "Cúmulo de la Hebilla",
    "messier-M36": "Cúmulo del Molinete",
    "messier-M37": "Cúmulo de Sal y Pimienta",
    "messier-M38": "Cúmulo de la Estrella de Mar",
    "messier-M39": "Cúmulo de la Pirámide",
    "messier-M40": "Winnecke 4",
    "messier-M41": "Cúmulo de la Pequeña Colmena",
    "messier-M42": "Gran Nebulosa de Orión",
    "messier-M43": "Nebulosa de De Mairan",
    "messier-M44": "Cúmulo del Pesebre o Praesepe",
    "messier-M45": "Pléyades, Siete Hermanas o Subaru",
    "messier-M50": "Cúmulo con Forma de Corazón",
    "messier-M51": "Galaxia del Remolino",
    "messier-M52": "Cúmulo del Escorpión",
    "messier-M55": "Cúmulo del Espectro",
    "messier-M57": "Nebulosa del Anillo",
    "messier-M61": "Galaxia Espiral Hinchada",
    "messier-M62": "Cúmulo Globular Parpadeante",
    "messier-M63": "Galaxia del Girasol",
    "messier-M64": "Galaxia del Ojo Negro",
    "messier-M65": "Triplete de Leo",
    "messier-M66": "Triplete de Leo",
    "messier-M67": "Cobra Real o Cúmulo del Ojo Dorado",
    "messier-M71": "Cúmulo del Pez Ángel",
    "messier-M74": "Galaxia Fantasma",
    "messier-M76": "Nebulosa de la Pequeña Mancuerna",
    "messier-M77": "Cetus A o Galaxia del Calamar",
    "messier-M81": "Galaxia de Bode",
    "messier-M82": "Galaxia del Cigarro",
    "messier-M83": "Galaxia del Molinete Austral",
    "messier-M87": "Virgo A",
    "messier-M90": "Galaxia de Carabin",
    "messier-M93": "Critter Cluster",
    "messier-M94": "Ojo de Cocodrilo o Galaxia del Ojo de Gato",
    "messier-M97": "Nebulosa del Búho",
    "messier-M99": "Rueda de Santa Catalina",
    "messier-M100": "Galaxia del Espejo",
    "messier-M101": "Galaxia del Molinete",
    "messier-M102": "Galaxia del Huso",
    "messier-M104": "Galaxia del Sombrero",
    "messier-M107": "Cúmulo del Crucifijo",
    "messier-M108": "Galaxia de la Tabla de Surf",
    "messier-M109": "Galaxia de la Aspiradora",
    "messier-M110": "Satélite de Andrómeda n.º 2",
    "caldwell-C4": "NGC 7023 - Nebulosa Iris",
    "caldwell-C6": "NGC 6543 - Nebulosa del Ojo de Gato",
    "caldwell-C9": "Sh2-155 - Nebulosa de la Cueva",
    "caldwell-C11": "NGC 7635 - Nebulosa de la Burbuja",
    "caldwell-C12": "NGC 6946 - Galaxia de los Fuegos Artificiales",
    "caldwell-C13": "NGC 457 - Cúmulo del Búho",
    "caldwell-C14": "NGC 869/884 - Doble Cúmulo de Perseo",
    "caldwell-C15": "NGC 6826 - Nebulosa Parpadeante",
    "caldwell-C19": "IC 5146 - Nebulosa del Capullo",
    "caldwell-C20": "NGC 7000 - Nebulosa de América del Norte",
    "caldwell-C22": "NGC 7662 - Nebulosa de la Bola de Nieve Azul",
    "caldwell-C24": "NGC 1275 - Perseo A",
    "caldwell-C25": "NGC 2419 - Vagabundo Intergaláctico",
    "caldwell-C26": "NGC 4244 - Galaxia de la Aguja Plateada",
    "caldwell-C27": "NGC 6888 - Nebulosa Creciente",
    "caldwell-C31": "IC 405 - Nebulosa de la Estrella Llameante",
    "caldwell-C32": "NGC 4631 - Galaxia de la Ballena",
    "caldwell-C33": "NGC 6992/6995 - Nebulosa del Velo Oriental",
    "caldwell-C34": "NGC 6960 - Nebulosa del Velo Occidental",
    "caldwell-C38": "NGC 4565 - Galaxia de la Aguja",
    "caldwell-C41": "Híades",
    "caldwell-C46": "NGC 2261 - Nebulosa Variable de Hubble",
    "caldwell-C49": "NGC 2237-2239 - Nebulosa Roseta",
    "caldwell-C53": "NGC 3115 - Galaxia del Huso",
    "caldwell-C55": "NGC 7009 - Nebulosa de Saturno",
    "caldwell-C57": "NGC 6822 - Galaxia de Barnard",
    "caldwell-C59": "NGC 3242 - Fantasma de Júpiter",
    "caldwell-C60": "NGC 4038 - Galaxias de las Antenas",
    "caldwell-C61": "NGC 4039 - Galaxias de las Antenas",
    "caldwell-C63": "NGC 7293 - Nebulosa de la Hélice",
    "caldwell-C64": "NGC 2362 - Cúmulo de Tau Canis Majoris",
    "caldwell-C65": "NGC 253 - Galaxia del Escultor",
    "caldwell-C68": "NGC 6729 - Nebulosa R Coronae Australis",
    "caldwell-C69": "NGC 6302 - Nebulosa del Insecto",
    "caldwell-C77": "NGC 5128 - Centaurus A",
    "caldwell-C85": "IC 2391 - Cúmulo de Ómicron Velorum",
    "caldwell-C89": "NGC 6087 - Cúmulo de S Normae",
    "caldwell-C92": "NGC 3372 - Nebulosa de Carina",
    "caldwell-C94": "NGC 4755 - Cúmulo del Joyero",
    "caldwell-C99": "Nebulosa Saco de Carbón",
    "caldwell-C100": "IC 2944 - Cúmulo de Lambda Centauri",
    "caldwell-C102": "IC 2602 - Pléyades del Sur",
    "caldwell-C103": "NGC 2070 - Nebulosa de la Tarántula",
    "caldwell-C106": "NGC 104 - 47 Tucanae",
}

_SPANISH_CONTENT_OVERRIDES = {
    ("objects", "messier-M2", "curiosity_text"): (
        "M2 reúne alrededor de 150.000 estrellas en una esfera antigua, formada "
        "hace unos 13.000 millones de años. Sus regiones más densas ocupan un "
        "volumen que, a escala galáctica, resulta extremadamente compacto."
    ),
    ("objects", "messier-M7", "short_description"): (
        "M7 (Cúmulo de Ptolomeo) es un cúmulo abierto de Escorpio, conocido "
        "desde la Antigüedad. Llena el campo de estrellas; al culminar bajo "
        "sobre el horizonte, solo se muestra en todo su esplendor cuando el "
        "horizonte sur está despejado y el cielo es transparente."
    ),
    ("objects", "messier-M7", "curiosity_text"): (
        "M7 ya fue descrito por Ptolomeo en el siglo II como una nebulosidad "
        "cerca del aguijón de Escorpio. Es el objeto Messier más austral y uno "
        "de los pocos de los que consta una observación tan antigua."
    ),
    ("objects", "messier-M9", "curiosity_text"): (
        "M9 se encuentra inusualmente cerca del centro galáctico. La gravedad "
        "de la Vía Láctea ha deformado su estructura y lo ha hecho menos "
        "esférico que muchos otros cúmulos globulares de las regiones exteriores "
        "del halo."
    ),
    ("objects", "messier-M13", "short_description"): (
        "M13, el Gran Cúmulo de Hércules, es el cúmulo globular más famoso del "
        "cielo boreal. Incluso con instrumentos pequeños aparece como una esfera "
        "luminosa bien definida; con aperturas medias y buen seeing, la periferia "
        "se resuelve en innumerables estrellas y pueden aparecer finas cadenas "
        "oscuras, incluida la llamada Hélice. Es uno de los mejores objetos para "
        "comprender cuánto importan la apertura, el enfoque y la paciencia."
    ),
    ("objects", "messier-M13", "observing_notes"): (
        "Céntrelo con poco aumento y aumente progresivamente; busque primero la "
        "resolución en el borde y solo después estructuras más finas en el núcleo."
    ),
    ("objects", "messier-M14", "short_description"): (
        "M14 es un cúmulo globular en Ofiuco. Resulta menos inmediato que los "
        "globulares más famosos, pero contiene una enorme población estelar; "
        "requiere oscuridad y paciencia para separarlo del fondo del cielo."
    ),
    ("objects", "messier-M22", "short_description"): (
        "M22 es uno de los cúmulos globulares más brillantes y espectaculares "
        "visibles desde latitudes medias del norte. Es grande, relativamente "
        "poco concentrado y se resuelve con más facilidad que muchos cúmulos "
        "similares, especialmente cerca de la culminación. Con un telescopio "
        "mediano puede llenar el campo de estrellas y muestra un núcleo menos "
        "compacto que M13."
    ),
    ("objects", "messier-M22", "observing_notes"): (
        "Obsérvelo durante la culminación con aumentos medios; su periferia "
        "extensa y rica merece un campo que no sea demasiado estrecho."
    ),
    ("objects", "messier-M23", "short_description"): (
        "M23 es un cúmulo abierto grande y rico en Sagitario, inmerso en la Vía "
        "Láctea estival. Se aprecia mejor dejando un margen de cielo a su "
        "alrededor, sin forzar demasiado el aumento."
    ),
    ("objects", "messier-M25", "short_description"): (
        "M25 es un cúmulo abierto de Sagitario. Es brillante y disperso, con "
        "suficientes estrellas para que su estructura resulte evidente de "
        "inmediato; en el campo también destaca una variable cefeida."
    ),
    ("objects", "messier-M26", "observing_notes"): (
        "M26 mide aproximadamente 14′ y tiene una magnitud integrada de 8,0; "
        "examine primero el cúmulo en su conjunto y después sus pares estelares "
        "más cerrados."
    ),
    ("objects", "messier-M29", "short_description"): (
        "M29 (Cúmulo de la Torre de Refrigeración) es un cúmulo abierto en "
        "Cisne. Es pequeño y queda parcialmente oculto por el polvo de la Vía "
        "Láctea; no destaca por el número de estrellas, pero se encuentra en una "
        "región estival muy agradable de explorar."
    ),
    ("objects", "messier-M30", "short_description"): (
        "M30 (Cúmulo de la Medusa) es un cúmulo globular de Capricornio. Es "
        "compacto y queda bajo sobre el horizonte desde muchas latitudes, con "
        "un núcleo brillante y prolongaciones estelares que solo aparecen "
        "cuando el cielo acompaña."
    ),
    ("objects", "messier-M30", "curiosity_text"): (
        "En M30 hay dos secuencias distintas de rezagadas azules. Una parece "
        "producida por colisiones estelares durante el colapso del núcleo; la "
        "otra, por transferencia de materia en sistemas binarios."
    ),
    ("objects", "messier-M39", "short_description"): (
        "M39 (Cúmulo de la Pirámide) es un cúmulo abierto de Cisne. Está muy "
        "disperso y resulta más apropiado para prismáticos que para un telescopio "
        "de campo estrecho. Su encanto reside en la sencillez: unas pocas "
        "estrellas brillantes en una región estival muy rica."
    ),
    ("objects", "messier-M48", "observing_notes"): (
        "Para M48, con 30′ de diámetro y magnitud integrada 5,5, elija un campo "
        "que deje un margen de cielo alrededor del cúmulo antes de aumentar."
    ),
    ("objects", "messier-M44", "short_description"): (
        "M44, el Cúmulo del Pesebre, es un cúmulo abierto grande y cercano, "
        "visible a simple vista como una mancha luminosa bajo un cielo oscuro. "
        "Con prismáticos se convierte en un amplio campo de estrellas dispersas, "
        "con pares y pequeños grupos repartidos por un área mayor que la Luna "
        "llena. Un telescopio de focal larga puede mostrar solo una parte."
    ),
    ("objects", "messier-M44", "observing_notes"): (
        "Prefiera prismáticos o telescopios de campo muy amplio; mantenga todo "
        "el cúmulo dentro del campo visual."
    ),
    ("objects", "messier-M50", "short_description"): (
        "M50 (Cúmulo con Forma de Corazón) es un cúmulo abierto compacto en "
        "Unicornio, descrito a menudo por su silueta en forma de corazón. No es "
        "uno de los objetos Messier más famosos, pero ofrece una observación "
        "limpia y agradable."
    ),
    ("objects", "messier-M53", "short_description"): (
        "M53 es un cúmulo globular de la Cabellera de Berenice. Es remoto y "
        "compacto, cercano a la estrella Diadema. No resulta tan espectacular "
        "como M13, pero posee una elegancia serena y un núcleo muy definido."
    ),
    ("objects", "messier-M55", "short_description"): (
        "M55 (Cúmulo del Espectro) es un cúmulo globular de Sagitario. Es grande "
        "y relativamente poco concentrado: menos denso que muchos otros, pero "
        "muy hermoso cuando el cielo austral está limpio y transparente."
    ),
    ("objects", "messier-M54", "curiosity_text"): (
        "Probablemente M54 no pertenezca al halo original de la Vía Láctea: "
        "reside en el núcleo de la Galaxia Enana Elíptica de Sagitario, que "
        "nuestra galaxia está incorporando. Por tanto, sería un cúmulo globular "
        "adquirido mediante una fusión."
    ),
    ("objects", "messier-M57", "short_description"): (
        "M57, la Nebulosa del Anillo, es una nebulosa planetaria compacta y de "
        "alto brillo superficial en Lira. Incluso con telescopios pequeños "
        "aparece como un anillo diminuto o un disco perforado; al aumentar la "
        "magnificación, el centro más oscuro se define y el borde muestra un "
        "brillo desigual. La estrella central es mucho más difícil y requiere "
        "gran abertura y condiciones excelentes."
    ),
    ("objects", "messier-M57", "observing_notes"): (
        "Céntrela con poco aumento y aumente la magnificación cuando el seeing "
        "sea estable; un filtro OIII acentúa el anillo, pero la estrella central "
        "sigue siendo difícil."
    ),
    ("objects", "messier-M70", "short_description"): (
        "M70 es un cúmulo globular de Sagitario. Es compacto y difícil, cercano "
        "a la zona donde se descubrió el cometa Hale-Bopp. Es un objeto para "
        "cielos transparentes, no para una noche urbana."
    ),
    ("objects", "messier-M70", "observing_notes"): (
        "Para evaluar M70, con magnitud integrada 7,9, compare su perfil de 8′ "
        "con dos aumentos y conserve el que no haga desaparecer el halo."
    ),
    ("objects", "messier-M68", "short_description"): (
        "M68 es un cúmulo globular en Hidra, a menudo bajo y poco evidente. "
        "Cuando el horizonte sur es bueno, muestra un núcleo compacto en un "
        "campo bastante aislado."
    ),
    ("objects", "messier-M71", "short_description"): (
        "M71 (Cúmulo del Pez Ángel) es un cúmulo globular en Flecha. Es un objeto "
        "ambiguo y fascinante, a medio camino entre un globular poco concentrado "
        "y un cúmulo muy denso. En el campo estelar de Flecha aparece como una "
        "condensación granulada."
    ),
    ("objects", "messier-M74", "short_description"): (
        "M74 (Galaxia Fantasma) es una galaxia espiral en Piscis. Es grande, se "
        "observa de frente y tiene un brillo superficial bajo. Es fotogénica, "
        "pero visualmente solo recompensa los cielos realmente oscuros."
    ),
    ("objects", "messier-M79", "short_description"): (
        "M79 es un cúmulo globular de Liebre. Es un objeto invernal inusual, "
        "alejado de los campos estivales clásicos de la Vía Láctea. Bajo Orión "
        "aparece compacto y sorprendente."
    ),
    ("objects", "messier-M79", "curiosity_text"): (
        "M79 se encuentra en el lado del cielo opuesto al centro galáctico, una "
        "ubicación inusual para un cúmulo globular. Su órbita ha dado pie a la "
        "hipótesis de que fue adquirido durante la fusión con una galaxia enana."
    ),
    ("objects", "messier-M81", "short_description"): (
        "M81 es una galaxia espiral grande, brillante y bien definida de la Osa "
        "Mayor. En el ocular muestra un núcleo nítido dentro de un halo ovalado; "
        "sus brazos son tenues y difíciles, pero el contraste con la cercana M82 "
        "convierte a la pareja en uno de los campos extragalácticos más bellos "
        "del cielo. Un campo visual amplio puede abarcar ambas galaxias."
    ),
    ("objects", "messier-M82", "observing_notes"): (
        "Obsérvela primero junto a M81; después utilice un aumento medio y visión "
        "desviada para buscar bandas oscuras en el disco."
    ),
    ("objects", "messier-M90", "short_description"): (
        "M90 (Galaxia de Carabin) es una gran galaxia espiral del Cúmulo de "
        "Virgo, con un movimiento peculiar respecto a la Vía Láctea. En el "
        "ocular resulta delicada, pero su perfil alargado ayuda a reconocerla."
    ),
    ("objects", "messier-M92", "short_description"): (
        "M92 es un cúmulo globular de Hércules. Es magnífico, aunque a menudo "
        "queda eclipsado por la fama de M13. De aspecto más compacto y antiguo, "
        "merece una visita siempre que Hércules esté alto en el cielo."
    ),
    ("objects", "messier-M104", "short_description"): (
        "M104, la Galaxia del Sombrero, es una espiral vista casi de canto, con "
        "un gran bulbo central y una marcada banda de polvo. Incluso cuando la "
        "banda no se distingue directamente, el núcleo brillante y el perfil "
        "muy alargado le confieren un aspecto característico. Su baja "
        "declinación desde muchas localidades boreales aconseja observarla cerca "
        "de la culminación."
    ),
    ("objects", "messier-M104", "curiosity_text"): (
        "La Galaxia del Sombrero posee un sistema inusualmente rico de unos dos "
        "mil cúmulos globulares, casi diez veces más que la Vía Láctea. La banda "
        "de polvo oculta un disco estelar dentro de un halo enorme."
    ),
    ("objects", "messier-M102", "short_description"): (
        "M102 (Galaxia del Huso) es una galaxia lenticular de Dragón. Se ve de "
        "canto, delgada y atravesada por una franja de polvo que le confiere un "
        "aspecto elegante en las imágenes. Visualmente es compacta pero "
        "inconfundible."
    ),
    ("objects", "messier-M105", "short_description"): (
        "M105 es una galaxia elíptica de Leo y la mayor elíptica del catálogo "
        "Messier perteneciente al Grupo de Leo. Visualmente es sencilla, pero "
        "revela un entorno galáctico rico y compacto."
    ),
    ("objects", "messier-M108", "short_description"): (
        "M108 (Galaxia de la Tabla de Surf) es una galaxia espiral barrada en "
        "la Osa Mayor. Es una espiral larga, estrecha y vista de canto, situada "
        "cerca de la Nebulosa del Búho en el cielo. Constituye una buena prueba "
        "para la visión desviada."
    ),
    ("objects", "caldwell-C6", "observing_notes"): (
        "Utilice aumentos medios o altos con un seeing estable; pruebe un filtro "
        "OIII para el disco, pero observe también sin filtro para evaluar el "
        "color y buscar la estrella central."
    ),
    ("objects", "caldwell-C14", "short_description"): (
        "C14, el Doble Cúmulo de Perseo, comprende NGC 869 y NGC 884, dos "
        "cúmulos abiertos jóvenes y próximos entre sí en el cielo. Ya se ven a "
        "simple vista como una mancha alargada; con prismáticos se despliegan en "
        "dos concentraciones estelares separadas por un rico puente. El campo "
        "completo es más espectacular que cada cúmulo por separado. Su escala "
        "aparente es de 30′ + 30′; una magnitud integrada de 4,3 no basta para "
        "describir su visibilidad en el ocular."
    ),
    ("objects", "caldwell-C27", "observing_notes"): (
        "Utilice poco aumento y un filtro OIII; localice primero el arco más "
        "brillante y después recorra lentamente el resto del anillo."
    ),
    ("objects", "caldwell-C50", "short_description"): (
        "C50 (NGC 2244) es un cúmulo abierto de Unicornio. Obsérvelo primero en "
        "conjunto, atendiendo a su concentración central y a las figuras "
        "geométricas que forman sus estrellas más brillantes. Su diámetro "
        "aparente es de 24′; la magnitud integrada de 4,8 no basta para indicar "
        "hasta qué punto destacará en el ocular."
    ),
    ("objects", "caldwell-C55", "short_description"): (
        "C55 (NGC 7009) es una nebulosa planetaria de Acuario. Es compacta y "
        "posee un alto brillo superficial: la comparación con estrellas cercanas "
        "y la respuesta a un filtro OIII ayudan a identificarla. En el ocular "
        "debe buscarse una extensión de 2,5′/1′; el brillo total corresponde a "
        "una magnitud integrada de 8,3."
    ),
    ("objects", "caldwell-C56", "short_description"): (
        "C56 (NGC 246) es una nebulosa planetaria de Ballena. Es compacta y "
        "posee un alto brillo superficial: la comparación con estrellas cercanas "
        "y la respuesta a un filtro OIII ayudan a identificarla. Su extensión "
        "aparente es de 3,8′ y su magnitud integrada, 8,0."
    ),
    ("objects", "caldwell-C59", "short_description"): (
        "C59 (NGC 3242) es una nebulosa planetaria de Hidra. Su forma se aprecia "
        "mejor alternando la visión directa y la desviada, en busca de un disco, "
        "un anillo o una estructura interna irregular. Su escala aparente es de "
        "0,3′/21′ y su magnitud integrada, 8,6."
    ),
    ("objects", "caldwell-C60", "observing_notes"): (
        "Para C60 (NGC 4038 - Galaxias de las Antenas), con una extensión de "
        "2,6′ x 1,8′, compruebe primero el eje principal y la condensación "
        "central; la magnitud 11,3 no expresa por sí sola el brillo superficial."
    ),
    ("objects", "caldwell-C66", "curiosity_text"): (
        "NGC 5694 es un cúmulo globular remoto e inusualmente compacto, ligado "
        "débilmente a las regiones exteriores de la Vía Láctea. Algunas de sus "
        "propiedades químicas y dinámicas sugieren que se originó en una galaxia "
        "enana posteriormente absorbida."
    ),
    ("objects", "caldwell-C71", "curiosity_text"): (
        "NGC 2477 es tan rico y concentrado que parece un cúmulo globular, pese "
        "a ser un cúmulo abierto del disco galáctico. Reúne cientos de estrellas "
        "en diferentes etapas de evolución posteriores a la secuencia principal."
    ),
    ("objects", "caldwell-C74", "short_description"): (
        "C74, NGC 3132, la Nebulosa del Anillo Sur, es una nebulosa planetaria "
        "brillante en Vela. Muestra un disco ovalado con una región central más "
        "oscura y una estrella brillante proyectada cerca del centro; la "
        "estrella que realmente origina la nebulosa es una compañera más débil. "
        "Es una de las mejores nebulosas planetarias del cielo austral. Su escala "
        "aparente es de 0,8′; una magnitud integrada de 8,2 no describe por sí "
        "sola lo que resultará visible en el ocular."
    ),
    ("objects", "caldwell-C80", "short_description"): (
        "C80, NGC 5139, Omega Centauri, es el cúmulo globular más grande y "
        "brillante de la Vía Láctea. A simple vista puede parecer una estrella "
        "borrosa; en el telescopio se convierte en una enorme masa estelar, más "
        "extensa y menos concentrada que muchos otros cúmulos globulares. Desde "
        "latitudes septentrionales bajas debe observarse cerca de la "
        "culminación. Su extensión aparente es de 36′ y su magnitud integrada, "
        "3,6."
    ),
    ("objects", "caldwell-C92", "short_description"): (
        "C92, NGC 3372, la Nebulosa de Carina, es una gigantesca región de "
        "formación estelar del cielo austral. Alrededor de Eta Carinae se "
        "entrelazan zonas luminosas, cúmulos y profundas bandas oscuras; a "
        "simple vista y con prismáticos ya impresiona bajo un buen cielo. Su "
        "extensión requiere pocos aumentos. NGC 3372 combina una extensión "
        "aparente de 120′ x 120′ con una magnitud integrada de 6,2, por lo que "
        "la abertura y la calidad del cielo influyen de forma distinta."
    ),
    ("objects", "caldwell-C92", "curiosity_text"): (
        "Eta Carinae, dentro de la Nebulosa de Carina, sobrevivió a la Gran "
        "Erupción del siglo XIX. El episodio expulsó la Nebulosa del Homúnculo "
        "y convirtió brevemente a la estrella en una de las más brillantes del "
        "cielo."
    ),
    ("objects", "caldwell-C103", "short_description"): (
        "C103 (NGC 2070) es una nebulosa de la constelación de Dorado. Alterne "
        "la visión directa y la desviada para seguir bordes, zonas oscuras y "
        "condensaciones, manteniendo suficientes estrellas de referencia en el "
        "campo. En el ocular debe buscarse una extensión de 40′ x 25′; el brillo "
        "total corresponde a una magnitud integrada de 1,0."
    ),
    ("objects", "caldwell-C103", "curiosity_text"): (
        "La Nebulosa de la Tarántula es la región de formación estelar más "
        "grande del Grupo Local. Si estuviera a la distancia de la Nebulosa de "
        "Orión, proyectaría sombras; en sus proximidades también explotó la "
        "supernova SN 1987A."
    ),
    ("objects", "neptune", "observing_notes"): (
        "Utilice una carta celeste actualizada o un sistema de apuntado preciso; "
        "después aumente la magnificación para comprobar que aparece un pequeño "
        "disco y no un simple punto estelar."
    ),
    ("objects", "messier-M18", "short_description"): (
        "M18 (Cúmulo del Cisne Negro) es un cúmulo abierto de Sagitario. Es "
        "pequeño y discreto, y suele observarse al pasar de M17 a M24; su valor "
        "reside en el riquísimo contexto estelar de Sagitario."
    ),
    ("objects", "messier-M65", "short_description"): (
        "M65 (Triplete de Leo) es una galaxia espiral barrada de Leo y una de "
        "las tres integrantes del famoso triplete. Delgada y ordenada, ofrece "
        "su mejor aspecto cuando se observa junto a M66 y NGC 3628 en el mismo "
        "recorrido."
    ),
    ("objects", "messier-M109", "short_description"): (
        "M109 (Galaxia de la Aspiradora) es una galaxia espiral barrada de la "
        "Osa Mayor, situada cerca de Phecda. No es llamativa, pero su localización "
        "resulta agradable y la barra central le confiere interés estructural."
    ),
    ("objects", "caldwell-C1", "short_description"): (
        "C1, NGC 188, es uno de los cúmulos abiertos más antiguos conocidos y "
        "se encuentra cerca del polo norte celeste, en Cefeo. Es rico pero "
        "discreto, formado por estrellas relativamente débiles que componen un "
        "cúmulo extenso y de aspecto granulado. Su posición circumpolar permite "
        "observarlo durante gran parte del año desde latitudes septentrionales. "
        "NGC 188 abarca unos 14′ y tiene una magnitud integrada de 8,1; ambos "
        "datos deben valorarse junto con el contraste del fondo."
    ),
    ("objects", "caldwell-C1", "observing_notes"): (
        "Utilice un campo de amplitud media bajo cielos oscuros; aumente "
        "moderadamente la magnificación para separar del fondo sus numerosas "
        "estrellas débiles."
    ),
    ("objects", "caldwell-C2", "curiosity_text"): (
        "La estrella central de NGC 40 es una Wolf-Rayet muy caliente que expulsa "
        "material a gran velocidad. El viento reciente choca con capas más "
        "lentas expulsadas anteriormente y da forma a la envoltura irregular de "
        "la nebulosa."
    ),
    ("objects", "caldwell-C34", "short_description"): (
        "C34, NGC 6960, es la parte occidental de la Nebulosa del Velo y cruza "
        "visualmente la estrella 52 Cygni. La estrella facilita la localización, "
        "pero puede perjudicar la adaptación a la oscuridad; con un filtro OIII, "
        "la nebulosa aparece como un arco fino e irregular que rebasa el campo. "
        "Es uno de los remanentes de supernova más espectaculares a la vista. El "
        "perfil observable puede ser menor que los 70′ x 6′ catalogados si el "
        "fondo del cielo reduce el contraste de los filamentos."
    ),
    ("objects", "caldwell-C41", "short_description"): (
        "C41, las Híades, es el cúmulo abierto más cercano al Sistema Solar y "
        "forma la característica V que dibuja la cabeza de Tauro. Aldebarán se "
        "proyecta sobre el grupo, pero no pertenece físicamente a él. El cúmulo "
        "es demasiado grande para la mayoría de los telescopios y se aprecia "
        "mejor a simple vista o con prismáticos de campo amplio. Su magnitud "
        "integrada es 1,0 y su extensión, 330′."
    ),
    ("objects", "caldwell-C41", "observing_notes"): (
        "Obsérvelo a simple vista o con prismáticos; evite grandes aumentos y "
        "utilice Aldebarán como estrella de referencia."
    ),
    ("objects", "caldwell-C55", "observing_notes"): (
        "Para C55 (NGC 7009 - Nebulosa de Saturno), con magnitud integrada 8,3, "
        "utilice sus dimensiones de 2,5′ x 1′ para mantener toda la nebulosa a "
        "la vista antes de estrechar el campo."
    ),
    ("objects", "caldwell-C74", "observing_notes"): (
        "Utilice aumentos medios o altos y compare la vista con y sin filtro OIII "
        "para apreciar la forma ovalada y la cavidad central."
    ),
    ("objects", "caldwell-C80", "observing_notes"): (
        "Utilice un campo lo bastante amplio para abarcarlo por completo y "
        "aumentos medios para resolver su vasta periferia estelar."
    ),
    ("objects", "caldwell-C31", "curiosity_text"): (
        "AE Aurigae, la estrella que ilumina la Nebulosa de la Estrella "
        "Llameante, es una fugitiva expulsada de la región de Orión hace millones "
        "de años. Su paso actual por una nube que no la originó es casual."
    ),
    ("objects", "caldwell-C36", "curiosity_text"): (
        "En el disco de NGC 4559 hay una fuente de rayos X ultraluminosa, "
        "demasiado intensa para una binaria estelar normal. Puede albergar un "
        "agujero negro que acreta materia de una compañera situada en una región "
        "de estrellas jóvenes."
    ),
    ("objects", "caldwell-C40", "curiosity_text"): (
        "En NGC 3626 el gas gira en sentido contrario a la mayoría de las "
        "estrellas. La explicación más probable es que adquirió material de una "
        "galaxia compañera, un encuentro que permanece registrado en la dinámica "
        "del disco."
    ),
    ("objects", "caldwell-C56", "curiosity_text"): (
        "La estrella central de la Nebulosa Calavera pertenece a un sistema "
        "triple jerárquico. Las otras componentes, invisibles con instrumentos "
        "pequeños, pueden haber influido en las cavidades y en la geometría no "
        "esférica del gas expulsado."
    ),
    ("objects", "caldwell-C61", "curiosity_text"): (
        "NGC 4039 forma con NGC 4038 las Galaxias de las Antenas. En la zona de "
        "solapamiento, la compresión del gas ha encendido miles de cúmulos "
        "estelares jóvenes, algunos destinados a convertirse en futuros cúmulos "
        "globulares."
    ),
    ("objects", "caldwell-C90", "curiosity_text"): (
        "La estrella central de NGC 2867 es una Wolf-Rayet rica en carbono y "
        "oxígeno. Su espectro revela material producido en las capas internas "
        "durante fases avanzadas de la evolución estelar, antes de ser expulsado "
        "para formar la nebulosa."
    ),
    ("objects", "caldwell-C91", "curiosity_text"): (
        "NGC 3532 fue el primer objetivo fotografiado por el Telescopio Espacial "
        "Hubble, en mayo de 1990. Aquellas primeras imágenes aparecieron borrosas "
        "y ayudaron a revelar el defecto del espejo, corregido después durante "
        "una misión de mantenimiento."
    ),
    ("objects", "caldwell-C93", "curiosity_text"): (
        "NGC 6752 presenta suficientes huecos entre sus estrellas para que en "
        "imágenes profundas aparezcan galaxias mucho más lejanas detrás del "
        "cúmulo. El campo superpone así objetos separados por distancias cósmicas "
        "enormes."
    ),
    ("objects", "caldwell-C98", "curiosity_text"): (
        "NGC 4609 se proyecta sobre la Nebulosa Saco de Carbón, mucho más cercana. "
        "El polvo oscuro absorbe y enrojece la luz del cúmulo situado detrás, "
        "convirtiendo esta alineación en una herramienta para medir la extinción."
    ),
    ("objects", "caldwell-C106", "curiosity_text"): (
        "En 47 Tucanae las estrellas más masivas migran hacia el centro, mientras "
        "que las más ligeras se desplazan hacia el exterior. La distribución de "
        "las rezagadas azules funciona como un reloj dinámico que permite medir "
        "la evolución interna del cúmulo."
    ),
    ("objects", "caldwell-C81", "curiosity_text"): (
        "NGC 6352 es un cúmulo globular relativamente rico en metales, asociado "
        "a las regiones internas de la Galaxia. Su química difiere de la de los "
        "cúmulos globulares pobres en elementos pesados que pueblan el halo "
        "remoto."
    ),
    ("objects", "caldwell-C106", "short_description"): (
        "C106, NGC 104, 47 Tucanae, es uno de los cúmulos globulares más "
        "brillantes y espectaculares del cielo. Muestra un núcleo muy denso "
        "rodeado por un gran halo de estrellas resolubles, con una apariencia "
        "más concentrada y regular que Omega Centauri. Su proximidad aparente a "
        "la Pequeña Nube de Magallanes crea un campo extraordinario. El perfil "
        "observable puede ser menor que los 31′ catalogados si el fondo de cielo "
        "reduce el contraste; la magnitud total es 4,0."
    ),
    ("catalogue_objects", "messier-M71", "description"): (
        "M71 (NGC 6838) - Cúmulo globular en Flecha."
    ),
    ("catalogue_objects", "caldwell-C99", "description"): (
        "C99 - Nebulosa oscura en la Cruz del Sur."
    ),
}

_SPANISH_EDITORIAL_REPLACEMENTS = (
    ("entre visión directa y periférica", "entre la visión directa y la periférica"),
    ("la visión directa y la desviada", "la visión directa y la periférica"),
    ("visión directa y la desviada", "visión directa y la periférica"),
    ("visualización directa y desviada", "visión directa y periférica"),
    ("visión directa y desviada", "visión directa y periférica"),
    ("visión directa y periférica", "visión directa y la periférica"),
    ("aumente moderadamente la magnificación", "suba el aumento con moderación"),
    ("aumente la magnificación moderadamente", "suba el aumento con moderación"),
    ("al aumentar la magnificación", "al subir el aumento"),
    ("aumentar la magnificación", "subir el aumento"),
    ("aumente la magnificación", "suba el aumento"),
    ("contraste de la superficie", "brillo superficial"),
    ("brillo de la superficie", "brillo superficial"),
    ("brillo de su superficie", "brillo superficial"),
    ("campo de amplitud media", "campo medio"),
    ("cielo muy despejado", "cielo muy oscuro y transparente"),
    ("Cúmulo con forma de corazón", "Cúmulo con Forma de Corazón"),
    ("Cúmulo en espiral", "Cúmulo Espiral"),
    ("Cúmulo del Corazón", "Cúmulo con Forma de Corazón"),
    ("Errante Intergaláctico", "Vagabundo Intergaláctico"),
    ("globulares Messier", "cúmulos globulares de Messier"),
    ("Cúmulo Crucifijo", "Cúmulo del Crucifijo"),
    ("catálogo Messier", "catálogo de Messier"),
    ("visión desviada", "visión periférica"),
    ("cielo despejado", "cielo oscuro"),
    ("Cúmulo Critter", "Critter Cluster"),
    ("Nebulosa Hélice", "Nebulosa de la Hélice"),
    ("nodos cometarios", "nudos cometarios"),
    ("200.000 kelvin", "200.000 K"),
    ("Esta combinación lo hace fotogénico", "Esta combinación la hace fotogénica"),
    ("enorme pero casi inactivo", "enorme, pero casi inactivo"),
    ("compacta pero inconfundible", "compacta, pero inconfundible"),
    ("hermosa pero baja", "hermosa, pero baja"),
    ("Es rico pero discreto", "Es rico, pero discreto"),
    ("Probablemente ", "Probablemente, "),
    ("Visualmente ", "Visualmente, "),
    ("magnificaciones", "aumentos"),
    ("magnificación", "aumento"),
    ("Sistema Solar", "sistema solar"),
    ("aberturas", "aperturas"),
    ("abertura", "apertura"),
    ("Grupo Leo", "Grupo de Leo"),
    ("Zorra", "Vulpecula"),
)

_SPANISH_EDITORIAL_OVERRIDES = {
    ("objects", "mercury", "short_description"): (
        "Mercurio es un desafío más que un espectáculo. Siempre permanece cerca "
        "del Sol y ofrece ventanas breves, a poca altura sobre el horizonte, "
        "justo antes del amanecer o después del atardecer. En el telescopio "
        "aparece pequeño y a menudo afectado por la turbulencia, pero distinguir "
        "su fase resulta gratificante. Elegir el momento adecuado importa más "
        "que la apertura del instrumento."
    ),
    ("objects", "jupiter", "observing_notes"): (
        "Obsérvelo cuando esté alto sobre el horizonte; un seeing estable y los "
        "aumentos medios suelen ofrecer más detalle que forzar el aumento máximo."
    ),
    ("objects", "messier-M4", "curiosity_text"): (
        "M4 alberga el sistema PSR B1620-26, formado por un púlsar y una enana "
        "blanca orbitados por un planeta apodado Matusalén. Con una edad estimada "
        "de más de 12.000 millones de años, es uno de los planetas más antiguos "
        "conocidos."
    ),
    ("objects", "messier-M3", "curiosity_text"): (
        "En M3 se han catalogado más de 270 estrellas variables, una cifra "
        "excepcional para un cúmulo globular. Muchas son variables RR Lyrae; su "
        "luminosidad característica permite utilizarlas como candelas estándar "
        "para medir distancias dentro de la Vía Láctea."
    ),
    ("objects", "messier-M7", "curiosity_text"): (
        "M7 ya fue descrito por Ptolomeo en el siglo II como una nebulosidad "
        "cerca del aguijón de Escorpio. Es el objeto Messier más austral y uno "
        "de los pocos con una observación documentada desde la Antigüedad."
    ),
    ("objects", "messier-M12", "short_description"): (
        "M12 es un cúmulo globular de Ofiuco, menos concentrado y más abierto "
        "que M10. Los estudios modernos sugieren que perdió muchas estrellas "
        "de baja masa durante sus pasos por el disco de la Galaxia."
    ),
    ("objects", "messier-M12", "curiosity_text"): (
        "M12 parece haber perdido gran parte de sus estrellas de baja masa. "
        "Durante los repetidos pasos a través del disco de la Vía Láctea, las "
        "mareas galácticas podrían haber arrancado del cúmulo hasta un millón "
        "de ellas."
    ),
    ("objects", "messier-M17", "observing_notes"): (
        "En M17 (Nebulosa Omega, del Cisne, de la Herradura, de la Langosta o "
        "de la Marca de Verificación), registre por separado el efecto del "
        "filtro y del aumento; su magnitud integrada es 6,0 y su extensión de "
        "referencia, 11′."
    ),
    ("objects", "messier-M21", "short_description"): (
        "M21 (Cúmulo de la Cruz de Webb) es un cúmulo abierto de Sagitario y el "
        "pequeño compañero estelar de la Nebulosa Trífida. Aunque es menos "
        "famoso, aporta variedad al campo y completa el recorrido por la región "
        "de M20."
    ),
    ("objects", "messier-M22", "curiosity_text"): (
        "M22 fue reconocido por Abraham Ihle en 1665 y es el primer cúmulo "
        "globular descubierto. Mucho más tarde se comprobó que también contiene "
        "una rara nebulosa planetaria e indicios de múltiples generaciones "
        "estelares."
    ),
    ("objects", "messier-M24", "short_description"): (
        "M24 (Pequeña Nube Estelar de Sagitario) es una nube estelar de la Vía "
        "Láctea situada en Sagitario. No es un único cúmulo, sino una ventana "
        "brillante hacia las regiones internas de la Galaxia. Es ideal para "
        "prismáticos y aumentos bajos."
    ),
    ("objects", "messier-M36", "short_description"): (
        "M36 (Cúmulo del Molinete) es un cúmulo abierto de Auriga. Es el más "
        "compacto de los tres grandes cúmulos de la constelación, brillante y "
        "fácil de reconocer. Constituye un buen punto de partida para un "
        "recorrido invernal por M36, M37 y M38."
    ),
    ("objects", "messier-M37", "curiosity_text"): (
        "M37 es el más rico de los tres cúmulos de Messier en Auriga y contiene "
        "varias gigantes rojas. Su presencia indica una edad mayor que la de la "
        "cercana M36, dominada por estrellas azules jóvenes."
    ),
    ("objects", "messier-M38", "short_description"): (
        "M38 (Cúmulo de la Estrella de Mar) es un cúmulo abierto de Auriga. "
        "Presenta una estructura grande e irregular, descrita a menudo como una "
        "estrella de mar. Está menos concentrado que M37, pero resulta muy "
        "agradable en campos amplios."
    ),
    ("objects", "messier-M38", "curiosity_text"): (
        "No muy lejos de M38 aparece NGC 1907, más pequeño y compacto. Las "
        "mediciones de sus movimientos indican que ambos cúmulos atraviesan la "
        "misma región, pero no se formaron como una pareja ligada "
        "gravitacionalmente."
    ),
    ("objects", "messier-M39", "curiosity_text"): (
        "M39 está tan cerca y disperso que solo reúne una treintena de miembros "
        "confirmados en un campo muy extenso. Su forma triangular destaca mejor "
        "con poco aumento y un campo visual amplio."
    ),
    ("objects", "messier-M40", "short_description"): (
        "M40 (Winnecke 4) es una doble óptica de la Osa Mayor. Es una curiosidad "
        "histórica del catálogo: un aparente par de estrellas, no un objeto de "
        "cielo profundo. Vale la pena observarlo para comprender la finalidad "
        "práctica del catálogo original de Messier."
    ),
    ("objects", "messier-M45", "short_description"): (
        "M45, las Pléyades, es un cúmulo abierto joven y cercano, dominado por "
        "estrellas azules muy brillantes. A simple vista muestra el conocido "
        "pequeño grupo; con prismáticos aparecen decenas de componentes y el "
        "conjunto adquiere una profundidad notable. La nebulosidad de reflexión "
        "se aprecia sobre todo en fotografía; visualmente requiere un cielo muy "
        "oscuro y transparente."
    ),
    ("objects", "messier-M50", "curiosity_text"): (
        "Una gigante roja muy evidente contrasta con las estrellas azul-blancas "
        "de M50. El conjunto recibió el sobrenombre de Cúmulo con Forma de "
        "Corazón por la figura que dibujan sus miembros más brillantes."
    ),
    ("objects", "messier-M51", "short_description"): (
        "M51, la Galaxia del Remolino, es una espiral vista casi de frente que "
        "interactúa con su compañera NGC 5195. En instrumentos pequeños pueden "
        "distinguirse dos núcleos inmersos en un halo común; bajo cielos oscuros "
        "y con aperturas medias, los brazos aparecen como variaciones arqueadas "
        "de brillo y puede percibirse el puente hacia la compañera. Es uno de "
        "los mejores objetivos para intentar distinguir visualmente una "
        "estructura espiral."
    ),
    ("objects", "messier-M57", "curiosity_text"): (
        "La Nebulosa del Anillo no es un simple anillo plano. Las "
        "reconstrucciones tridimensionales describen una estructura semejante "
        "a un barril o una rosquilla, observada casi a lo largo de su eje."
    ),
    ("objects", "messier-M58", "short_description"): (
        "M58 es una galaxia espiral barrada del Cúmulo de Virgo. Visualmente es "
        "discreta: en el ocular suele mostrar un núcleo definido dentro de un "
        "halo tenue, mientras que la barra requiere condiciones excelentes."
    ),
    ("objects", "messier-M59", "short_description"): (
        "M59 es una galaxia elíptica del Cúmulo de Virgo. No ofrece detalles "
        "obvios en el ocular, pero cobra interés cuando se observa como parte "
        "del rico campo de galaxias de la región."
    ),
    ("objects", "messier-M61", "curiosity_text"): (
        "M61 ha albergado numerosas supernovas observadas, más que la mayoría "
        "de las galaxias del catálogo de Messier. Su núcleo activo y sus "
        "regiones de formación estelar revelan un sistema todavía muy dinámico."
    ),
    ("objects", "messier-M63", "curiosity_text"): (
        "Una delgada corriente de estrellas envuelve M63 a lo largo de decenas "
        "de miles de años luz. Es el remanente de una galaxia enana desgarrada "
        "y absorbida, una antigua fusión aún visible en la periferia de la "
        "Galaxia del Girasol."
    ),
    ("objects", "messier-M69", "curiosity_text"): (
        "M69 se encuentra entre los cúmulos globulares más ricos en elementos "
        "pesados del catálogo de Messier. Su posición en el bulbo galáctico "
        "indica un entorno de formación diferente al de los cúmulos pobres en "
        "metales del halo."
    ),
    ("objects", "messier-M73", "short_description"): (
        "M73 es un asterismo de cuatro estrellas en Acuario, más curioso que "
        "espectacular. Su presencia en el catálogo recuerda el carácter "
        "práctico y observacional del trabajo de Messier."
    ),
    ("objects", "messier-M75", "curiosity_text"): (
        "M75 posee uno de los núcleos más concentrados entre los cúmulos "
        "globulares del catálogo de Messier. La luminosidad crece rápidamente "
        "hacia el centro, donde la densidad estelar es mucho mayor que en el "
        "halo exterior."
    ),
    ("objects", "messier-M78", "observing_notes"): (
        "La transparencia es crucial; obsérvela sin filtros de banda estrecha, "
        "con poco aumento y bajo un cielo oscuro."
    ),
    ("objects", "messier-M84", "short_description"): (
        "M84 se clasifica en distintas fuentes como galaxia elíptica o lenticular "
        "del Cúmulo de Virgo. La luz de estrellas viejas domina su cuerpo, pero "
        "el centro alberga un agujero negro supermasivo; las imágenes del Hubble "
        "también revelan bandas de polvo deformadas."
    ),
    ("objects", "messier-M84", "curiosity_text"): (
        "M84 se encuentra en la Cadena de Markarian y alberga un núcleo activo. "
        "Un chorro relativista emerge de la región del agujero negro central, "
        "aunque resulta mucho menos llamativo que el del cercano M87."
    ),
    ("objects", "messier-M86", "short_description"): (
        "M86 es una galaxia de Virgo cuya clasificación se debate entre el tipo "
        "elíptico y el lenticular. Forma parte de la Cadena de Markarian; "
        "observarla junto a M84 y las galaxias cercanas transmite la sensación "
        "de recorrer un cúmulo entero."
    ),
    ("objects", "messier-M88", "curiosity_text"): (
        "M88 se precipita hacia el centro del Cúmulo de Virgo a lo largo de una "
        "órbita muy alargada. La presión del gas intergaláctico comienza a "
        "modificar su contenido de hidrógeno y, por tanto, el futuro de su "
        "formación estelar."
    ),
    ("objects", "messier-M90", "curiosity_text"): (
        "M90 es una de las pocas galaxias de Messier con desplazamiento al azul, "
        "porque se mueve en nuestra dirección dentro del Cúmulo de Virgo. El "
        "gas de su disco es arrancado por la presión del medio intergaláctico."
    ),
    ("objects", "messier-M93", "curiosity_text"): (
        "Las estrellas más brillantes de M93 dibujan una figura triangular o "
        "similar a una mariposa. El cúmulo tiene varios cientos de millones de "
        "años, una edad suficiente para que algunas de sus estrellas más "
        "masivas hayan evolucionado hasta convertirse en gigantes rojas."
    ),
    ("objects", "messier-M95", "short_description"): (
        "M95 es una galaxia espiral barrada del Grupo de Leo, tenue y poco "
        "evidente a primera vista. Requiere cielos oscuros para destacar frente "
        "a las demás galaxias de la zona."
    ),
    ("objects", "messier-M100", "short_description"): (
        "M100 (Galaxia del Espejo) es una elegante galaxia espiral de gran "
        "diseño en Cabellera de Berenice. En el ocular es tenue y exige un cielo "
        "oscuro, pero su núcleo permite situarla en el rico entorno del Cúmulo "
        "de Virgo."
    ),
    ("objects", "messier-M105", "short_description"): (
        "M105 es una galaxia elíptica de Leo, la mayor de este tipo en el "
        "catálogo de Messier y miembro del Grupo de Leo. Visualmente es sencilla, "
        "pero revela un entorno galáctico rico y compacto."
    ),
    ("objects", "messier-M106", "short_description"): (
        "M106 es una galaxia espiral activa de Lebreles, conocida por sus "
        "emisiones energéticas y sus máseres de agua. En el ocular es una de las "
        "galaxias más brillantes y accesibles de la región."
    ),
    ("objects", "messier-M107", "short_description"): (
        "M107 (Cúmulo del Crucifijo) es un cúmulo globular de Ofiuco, "
        "relativamente disperso y menos denso que los ejemplos más famosos. "
        "Requiere cielos oscuros, pero ofrece una delicada textura estelar."
    ),
    ("objects", "caldwell-C19", "curiosity_text"): (
        "La Nebulosa del Capullo se encuentra en el extremo de la larga nebulosa "
        "oscura Barnard 168. El contraste entre el capullo brillante y la franja "
        "oscura muestra dos formas opuestas en las que el mismo polvo puede "
        "reflejar o bloquear la luz."
    ),
    ("objects", "caldwell-C23", "curiosity_text"): (
        "NGC 891 se utiliza a menudo como análogo de una galaxia semejante a la "
        "Vía Láctea vista de canto. Sus filamentos de polvo se elevan muy por "
        "encima del disco, impulsados por vientos y supernovas desde las regiones "
        "de formación estelar."
    ),
    ("objects", "caldwell-C25", "curiosity_text"): (
        "NGC 2419 recibe el sobrenombre de Vagabundo Intergaláctico porque "
        "orbita a una distancia enorme, más allá del borde brillante de la Vía "
        "Láctea. Es tan masivo y complejo que podría ser el núcleo residual de "
        "una galaxia enana capturada."
    ),
    ("objects", "caldwell-C34", "short_description"): (
        "C34, NGC 6960, es la parte occidental de la Nebulosa del Velo y cruza "
        "visualmente la estrella 52 Cygni. La estrella facilita la localización, "
        "pero puede perjudicar la adaptación a la oscuridad; con un filtro OIII, "
        "la nebulosa aparece como un arco fino e irregular que rebasa el campo. "
        "Es uno de los remanentes de supernova visualmente más espectaculares. "
        "El perfil observable puede ser menor que los 70′ x 6′ catalogados si el "
        "fondo del cielo reduce el contraste de los filamentos."
    ),
    ("objects", "caldwell-C39", "curiosity_text"): (
        "NGC 2392 presenta dos envolturas: una capa interior brillante y una "
        "región exterior filamentosa. Los rápidos vientos de la estrella central "
        "golpean el material expulsado con anterioridad y generan esta doble "
        "arquitectura."
    ),
    ("objects", "caldwell-C47", "curiosity_text"): (
        "NGC 6934 contiene estrellas rezagadas azules, más calientes y luminosas "
        "de lo esperable para la edad del cúmulo. Su distribución ayuda a "
        "reconstruir cómo las colisiones y los sistemas binarios han mezclado "
        "el núcleo."
    ),
    ("objects", "caldwell-C49", "short_description"): (
        "C49, NGC 2237, es la gran nebulosa de emisión asociada a la Nebulosa "
        "Roseta en Unicornio. Rodea un cúmulo abierto central y visualmente "
        "aparece como un anillo muy grande y tenue, dividido en segmentos más "
        "brillantes. Un campo amplio, un cielo oscuro y un filtro UHC u OIII "
        "son fundamentales. La Nebulosa Roseta abarca unos 80′ x 60′; al no "
        "disponer de una magnitud integrada fiable, la extensión y el contraste "
        "del fondo guían la elección del campo."
    ),
    ("objects", "caldwell-C51", "short_description"): (
        "C51 (IC 1613) es una galaxia irregular de la constelación de Ballena. "
        "Es extensa y posee un brillo superficial muy bajo: busque primero el "
        "tenue resplandor general y recorra después las regiones exteriores con "
        "visión periférica. En el campo abarca 12′ x 11′ y tiene una magnitud "
        "integrada de 9,0."
    ),
    ("objects", "caldwell-C53", "short_description"): (
        "C53 (NGC 3115) es una galaxia lenticular de la constelación de Sextante. "
        "Muestra una luz regular y concentrada, sin brazos visibles; el detalle "
        "principal es el gradiente desde el núcleo hacia el halo exterior. Su "
        "magnitud integrada es 9,1 y su extensión aparente, 8′ x 3′."
    ),
    ("objects", "caldwell-C57", "curiosity_text"): (
        "La Galaxia de Barnard fue una de las primeras galaxias enanas situadas "
        "fuera de la Vía Láctea que se estudiaron en detalle. Las variables "
        "cefeidas observadas en su interior ayudaron a Edwin Hubble a extender "
        "la escala de distancias más allá de nuestra galaxia."
    ),
    ("objects", "messier-M53", "observing_notes"): (
        "En M53, busque la transición entre el núcleo y el halo a lo largo de "
        "sus 13′ de diámetro, sin depender únicamente de la magnitud 7,6."
    ),
    ("objects", "caldwell-C59", "observing_notes"): (
        "En C59 (NGC 3242 - Fantasma de Júpiter), registre por separado los "
        "efectos del filtro y del aumento; su magnitud integrada es 8,6 y su "
        "extensión de referencia, 0,3′/21′."
    ),
    ("objects", "caldwell-C63", "curiosity_text"): (
        "La Nebulosa de la Hélice contiene miles de nudos cometarios, cada uno "
        "del tamaño del sistema solar. Sus densas cabezas resisten la radiación "
        "de la estrella central, mientras que las largas colas apuntan hacia el "
        "exterior."
    ),
    ("objects", "caldwell-C66", "curiosity_text"): (
        "NGC 5694 es un cúmulo globular remoto e inusualmente compacto situado "
        "en el halo exterior de la Vía Láctea. Sus propiedades químicas y "
        "dinámicas sugieren que pudo originarse en una galaxia enana absorbida "
        "posteriormente."
    ),
    ("objects", "caldwell-C69", "curiosity_text"): (
        "La estrella central de la Nebulosa de la Mariposa supera los 200.000 K "
        "y se encuentra entre las más calientes conocidas. Un denso toro de "
        "polvo oculta el centro y obliga al gas a expandirse hacia dos lóbulos "
        "opuestos."
    ),
    ("objects", "caldwell-C88", "curiosity_text"): (
        "El cúmulo NGC 5823 fue catalogado por el astrónomo escocés James Dunlop "
        "durante sus observaciones en Australia en 1826. Tiene unos 800 millones "
        "de años, tiempo suficiente para que sus estrellas originales más "
        "masivas ya hayan desaparecido."
    ),
    ("catalogue_objects", "messier-M84", "description"): (
        "M84 (NGC 4374) - Galaxia elíptica en Virgo."
    ),
    ("catalogue_objects", "messier-M86", "description"): (
        "M86 (NGC 4406) - Galaxia elíptica o lenticular en Virgo."
    ),
    ("catalogue_objects", "caldwell-C53", "description"): (
        "C53 (NGC 3115) - Galaxia lenticular en Sextante."
    ),
}

_SPANISH_CONSTELLATION_NAMES = {
    "Andromeda": "Andrómeda",
    "Apus": "Ave del Paraíso",
    "Aquarius": "Acuario",
    "Ara": "Altar",
    "Boötes": "Boyero",
    "Bootes": "Boyero",
    "Camelopardalis": "Jirafa",
    "Cancer": "Cáncer",
    "Canes Venatici": "Lebreles",
    "Canis Major": "Can Mayor",
    "Capricornus": "Capricornio",
    "Carina": "Quilla",
    "Cassiopeia": "Casiopea",
    "Centaurus": "Centauro",
    "Cepheus": "Cefeo",
    "Cetus": "Ballena",
    "Chamaeleon": "Camaleón",
    "Circinus": "Compás",
    "Columba": "Paloma",
    "Coma Berenices": "Cabellera de Berenice",
    "Corona Australis": "Corona Austral",
    "Corvus": "Cuervo",
    "Crux": "Cruz del Sur",
    "Cygnus": "Cisne",
    "Delphinus": "Delfín",
    "Draco": "Dragón",
    "Dragon": "Dragón",
    "Fornax": "Horno",
    "Gemini": "Géminis",
    "Hercules": "Hércules",
    "Horologium": "Reloj",
    "Hydra": "Hidra",
    "Lacerta": "Lagarto",
    "Leo": "Leo",
    "Lepus": "Liebre",
    "Lynx": "Lince",
    "Lyra": "Lira",
    "Monoceros": "Unicornio",
    "Musca": "Mosca",
    "Norma": "Escuadra",
    "Ophiuchus": "Ofiuco",
    "Orion": "Orión",
    "Pavo": "Pavo",
    "Pegasus": "Pegaso",
    "Perseus": "Perseo",
    "Pisces": "Piscis",
    "Puppis": "Popa",
    "Sagitta": "Flecha",
    "Sagittarius": "Sagitario",
    "Scorpius": "Escorpio",
    "Sculptor": "Escultor",
    "Scutum": "Escudo",
    "Serpens": "Serpiente",
    "Sextans": "Sextante",
    "Taurus": "Tauro",
    "Triangulum Australe": "Triángulo Austral",
    "Triangulum": "Triángulo",
    "Tucana": "Tucán",
    "Ursa Major": "Osa Mayor",
    "Vela": "Vela",
    "Virgo": "Virgo",
    "Vulpecula": "Vulpecula",
    "Altare": "Altar",
    "Carena": "Quilla",
    "Corona Australe": "Corona Austral",
    "Triangolo Australe": "Triángulo Austral",
    "Vele": "Vela",
}


def _apply_spanish_editorial_replacements(value: str) -> str:
    for source, replacement in sorted(
        _SPANISH_EDITORIAL_REPLACEMENTS,
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        value = value.replace(source, replacement)
    return value


def source_language(section: str, item_key: str, field: str) -> str:
    """Returns the language actually used by each seed field.

    The bundled CSV files predate structured localization and legitimately mix
    Italian and English. Treating an entire section as one language caused
    source text to leak into the opposite locale and, on refresh, translated
    already translated content.
    """

    if section == "objects":
        return "it"
    if section == "catalogue_objects":
        return "it" if item_key.startswith("caldwell-") else "en"
    if section == "equipment_telescopes":
        return "en" if field == "notes" else "it"
    if section in {"equipment_eyepieces", "equipment_barlows"}:
        return "en"
    if section in {"equipment_filters", "equipment_reducers"}:
        return "it"
    raise KeyError(f"Unknown content section: {section}")


def _read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@cache
def _caldwell_english_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for row in _read_csv("catalogue_objects_seed.csv"):
        object_id = row["object_id"].strip()
        if not object_id.startswith("caldwell-"):
            continue
        prefix = row["descrizione"].split(" - ", maxsplit=1)[0].strip()
        descriptions[object_id] = (
            f"{prefix} - {row['tipo'].strip()} in {row['costellazione'].strip()}."
        )
    return descriptions


def curate_content_translation(
    section: str,
    item_key: str,
    field: str,
    value: str,
    language_code: str,
) -> str:
    for character in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        value = value.replace(character, "")
    if language_code == "es":
        key = (section, item_key, field)
        override = _SPANISH_EDITORIAL_OVERRIDES.get(key)
        if override:
            return _apply_spanish_editorial_replacements(override)
        override = _SPANISH_CONTENT_OVERRIDES.get(key)
        if override:
            return _apply_spanish_editorial_replacements(override)
        if section == "catalogue_objects" and field == "name":
            reviewed_name = _SPANISH_CATALOGUE_NAMES.get(item_key)
            if reviewed_name:
                return _apply_spanish_editorial_replacements(reviewed_name)
        for source, replacement in sorted(
            _SPANISH_CONTENT_REPLACEMENTS,
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            value = value.replace(source, replacement)
        for source, replacement in sorted(
            _SPANISH_CONSTELLATION_NAMES.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            value = re.sub(rf"\b{re.escape(source)}\b", replacement, value)
        value = value.replace("Ballena A", "Cetus A")
        value = value.replace("bulto", "bulbo")
        if section == "equipment_telescopes":
            value = _SPANISH_TELESCOPE_LABELS.get(field, {}).get(value, value)
        if section == "objects" and field == "best_seen":
            value = _SPANISH_BEST_SEEN.get(value, value)
        value = re.sub(r"\bNG (?=\d)", "NGC ", value)
        value = re.sub(r"\bCI (?=\d)", "IC ", value)
        value = value.replace("en la constelación del Boyero", "en la constelación de Boyero")
        value = value.replace(
            "en la constelación Corona Austral",
            "en la constelación de la Corona Austral",
        )
        value = value.replace(
            "en la constelación Triángulo Austral",
            "en la constelación del Triángulo Austral",
        )
        value = value.replace(
            "en la constelación Dorado",
            "en la constelación de Dorado",
        )
        value = re.sub(
            r"en la constelación (?!de\b|del\b)(?=[A-ZÁÉÍÓÚÑ])",
            "en la constelación de ",
            value,
        )
        value = value.replace("), Cúmulo", "), cúmulo")
        value = value.replace("), Galaxia", "), galaxia")
        value = value.replace("), Nebulosa", "), nebulosa")
        value = value.replace("Nebulosa de la región H II", "Nebulosa de emisión")
        value = value.replace("Galaxia Starburst", "Galaxia con estallido estelar")
        value = value.replace(": Cúmulo", ": cúmulo")
        value = value.replace(" en Cruz del Sur.", " en la Cruz del Sur.")
        value = value.replace(" en Triángulo Austral.", " en el Triángulo Austral.")
        value = value.replace("; Primero ", "; primero ")
        value = value.replace("; Menos ", "; menos ")
        value = value.replace("; Busque ", "; busque ")
        value = value.replace("; Explore ", "; explore ")
        value = value.replace("′ / ", "′/")
        if section == "objects" and field == "observing_notes":
            for source, replacement in (
                ("Búscalo", "Búsquelo"),
                ("Necesitas", "Necesita"),
                ("apuntes", "apunte"),
                ("Obsérvalo", "Obsérvelo"),
                ("Espera", "Espere"),
                ("Prefiere", "Prefiera"),
                ("Léelo", "Léalo"),
                ("Alternar", "Alterne"),
                ("evalúa", "evalúe"),
                ("utiliza", "utilice"),
                ("Utiliza", "Utilice"),
                ("registra", "registre"),
                ("Registra", "Registre"),
                ("protege", "proteja"),
                ("Protege", "Proteja"),
                ("comprueba", "compruebe"),
                ("Comprueba", "Compruebe"),
                ("Explora", "Explore"),
                ("sólo", "solo"),
                ("amplíe", "suba el aumento"),
            ):
                value = re.sub(rf"\b{source}\b", replacement, value)
            value = re.sub(
                r"(Para evaluar [MC]\d+, con magnitud integrada [0-9]+,[0-9]+,) comparar\b",
                r"\1 compare",
                value,
            )
            value = re.sub(
                r"Para ([MC]\d+(?: \([^)]*\))?) se integra la magnitud ([0-9,]+):",
                r"Para \1, con magnitud integrada \2,",
                value,
            )
            value = re.sub(
                r"Para ([MC]\d+(?: \([^)]*\))?), la magnitud ([0-9,]+) está integrada:",
                r"Para \1, con magnitud integrada \2,",
                value,
            )
            value = re.sub(
                r"; en una magnitud integrada de ([0-9,]+),",
                r"; con magnitud integrada \1,",
                value,
            )
            value = value.replace("magnitud integrada 5.3", "magnitud integrada 5,3")
            value = value.replace(", verificar primero", ", compruebe primero")
        value = re.sub(
            r"La preparación del campo para (C\d+) comienza en "
            r"(.+?) de extensión y magnitud integrada de ([0-9,]+)\.",
            r"La preparación del campo para \1 parte de una extensión de \2 "
            r"y una magnitud integrada de \3.",
            value,
        )
        value = re.sub(r"(?<=\d)\s+′", "′", value)
        value = re.sub(
            r"Para (.+?), extendido ([0-9]+(?:,[0-9]+)?′),",
            r"Para \1, con una extensión de \2,",
            value,
        )
        value = re.sub(
            r"En (.+?), extendido ([0-9]+(?:,[0-9]+)?′) y "
            r"(?:de |con )?magnitud integrada ([0-9]+(?:,[0-9]+)?)",
            r"En \1, con una extensión de \2 y magnitud integrada \3",
            value,
        )
        value = re.sub(
            r"Para (.+?), extendida ([0-9]+(?:,[0-9]+)?′) y "
            r"magnitud integrada ([0-9]+(?:,[0-9]+)?)",
            r"Para \1, con una extensión de \2 y magnitud integrada \3",
            value,
        )
        for source, replacement in (
            ("; La ", "; la "),
            ("; El ", "; el "),
            ("; Los ", "; los "),
            ("; Las ", "; las "),
            ("; No ", "; no "),
            ("; A medida ", "; a medida "),
            ("; Utilice ", "; utilice "),
            ("; Pruebe ", "; pruebe "),
            ("; Mantenga ", "; mantenga "),
            ("; Se ", "; se "),
            ("; Bajo ", "; bajo "),
            ("; También ", "; también "),
            ("; En ", "; en "),
            ("; Al ", "; al "),
            ("; Explore ", "; explore "),
            ("; Localice ", "; localice "),
            ("; Sigue ", "; siga "),
            ("; Evite ", "; evite "),
            ("; busca ", "; busque "),
            ("; deja ", "; deje "),
        ):
            value = value.replace(source, replacement)
        return _apply_spanish_editorial_replacements(value)
    if language_code != "en":
        return value
    if section == "catalogue_objects" and field == "description":
        description = _caldwell_english_descriptions().get(item_key)
        if description:
            return description
    override = _ENGLISH_CONTENT_OVERRIDES.get((section, item_key, field))
    if override:
        return override
    if section == "equipment_telescopes":
        return _ENGLISH_TELESCOPE_LABELS.get(field, {}).get(value, value)
    if section == "objects":
        for source, replacement in _ENGLISH_OBJECT_TEXT_REPLACEMENTS:
            value = value.replace(source, replacement)
        value = re.sub(
            r"\b(On|In|For|With) ((?:M|C)\d+(?: \([^)]*\))?), of integrated magnitude",
            r"For \2, with integrated magnitude",
            value,
        )
        value = re.sub(
            r"\b(To evaluate (?:M|C)\d+), of integrated magnitude",
            r"\1, with integrated magnitude",
            value,
        )
        value = re.sub(
            r"The ([0-9.]+) magnitude figure concerns the entire object",
            r"The integrated magnitude of \1 describes the entire object",
            value,
        )
        value = re.sub(
            r"The ([0-9.]+) magnitude figure applies to the entire object",
            r"The integrated magnitude of \1 describes the entire object",
            value,
        )
        value = re.sub(
            r"the ([0-9.]+) integrated magnitude does not (?:alone|by itself) describe",
            r"an integrated magnitude of \1 does not by itself describe",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"total brightness corresponds to (?:the )?integrated magnitude ([0-9.]+)",
            r"total brightness corresponds to an integrated magnitude of \1",
            value,
            flags=re.IGNORECASE,
        )
        value = value.replace("Central at low magnification", "Center it at low magnification")
        value = value.replace("then move up", "then increase magnification")
        value = value.replace("and move up", "and increase magnification")
        value = value.replace(
            "searches for edge resolution first",
            "look for resolution at the edge first",
        )
        value = value.replace("for full extension", "to see its full extent")
        value = value.replace("in the frame", "in the field of view")
        value = value.replace("initially retains a wider field of", "start with a field wider than")
        value = value.replace("initially preserves a field wider than", "start with a field wider than")
        value = value.replace("identify him with certainty", "identify it with certainty")
        value = value.replace("make a bigger difference", "make a greater difference")
        value = value.replace("medium enlargements", "moderate magnification")
    if section in {"objects", "catalogue_objects"}:
        return re.sub(r"\b(NGC|IC)\s*(\d)", r"\1 \2", value)
    return value


def source_content() -> dict[str, dict[str, dict[str, str]]]:
    sections: dict[str, dict[str, dict[str, str]]] = OrderedDict()
    objects: dict[str, dict[str, str]] = OrderedDict()
    for row in _read_csv("object_descriptions_seed.csv"):
        object_id = row["object_id"].strip()
        if object_id in objects:
            raise ValueError(f"Duplicate object translation key: {object_id}")
        objects[object_id] = {
            field: row[field].strip()
            for field in OBJECT_FIELDS
            if row.get(field, "").strip()
        }
    for row in _read_csv("object_curiosities_seed.csv"):
        object_id = row["object_id"].strip()
        if "curiosity_text" in objects.get(object_id, {}):
            raise ValueError(f"Duplicate object curiosity key: {object_id}")
        objects.setdefault(object_id, {})["curiosity_text"] = row[
            "curiosity_text"
        ].strip()
    sections["objects"] = objects

    catalogue_objects: dict[str, dict[str, str]] = OrderedDict()
    for row in _read_csv("catalogue_objects_seed.csv"):
        object_id = row["object_id"].strip()
        if object_id.startswith("ngc-"):
            continue
        if object_id in catalogue_objects:
            raise ValueError(f"Duplicate catalogue translation key: {object_id}")
        name = row["nome"].strip()
        catalogue_objects[object_id] = {
            "name": name,
            "description": row["descrizione"].strip(),
        }
    sections["catalogue_objects"] = catalogue_objects

    equipment_specs = (
        (
            "equipment_telescopes",
            "telescope_catalog_seed.csv",
            ("brand", "model"),
            ("optical_type", "mount_type", "notes"),
        ),
        (
            "equipment_eyepieces",
            "eyepiece_catalog_seed.csv",
            (
                "brand",
                "model",
                "eyepiece_type",
                "focal_length_mm",
                "min_focal_length_mm",
                "max_focal_length_mm",
            ),
            ("notes",),
        ),
        (
            "equipment_barlows",
            "barlow_catalog_seed.csv",
            ("brand", "model", "multiplier"),
            ("notes",),
        ),
        (
            "equipment_filters",
            "filter_catalog_seed.csv",
            ("brand", "model"),
            ("notes",),
        ),
        (
            "equipment_reducers",
            "reducer_catalog_seed.csv",
            ("brand", "model", "reduction_factor"),
            ("connection", "notes"),
        ),
    )
    for section, filename, identity_fields, fields in equipment_specs:
        items: dict[str, dict[str, str]] = OrderedDict()
        for row in _read_csv(filename):
            key = content_key(*(row.get(field, "") for field in identity_fields))
            if key in items:
                raise ValueError(
                    f"Duplicate equipment translation key in {filename}: {key}"
                )
            items[key] = {
                field: row[field].strip()
                for field in fields
                if row.get(field, "").strip()
            }
        sections[section] = items
    return sections


def _chunks(values: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_size = 0
    for value in values:
        added_size = len(value) + (len(SEPARATOR) if current else 0)
        if current and current_size + added_size > TRANSLATION_CHUNK_LIMIT:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(value)
        current_size += len(value) + (len(SEPARATOR) if len(current) > 1 else 0)
    if current:
        chunks.append(current)
    return chunks


def _translate_chunk(translator: GoogleTranslator, values: list[str]) -> list[str]:
    source = SEPARATOR.join(values)
    for attempt in range(4):
        try:
            translated = translator.translate(source)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
            continue
        parts = [part.strip() for part in translated.split("[NIGHTSCOPE_SPLIT_0001]")]
        if len(parts) == len(values) and all(parts):
            return parts
        if len(values) == 1 and translated.strip():
            return [translated.strip()]
        if attempt == 3:
            raise RuntimeError("Translation provider changed a NightScope batch separator.")
        time.sleep(1.5 * (attempt + 1))
    raise AssertionError("unreachable")


def translate_values(
    values: list[str],
    language_code: str,
    *,
    source_language: str,
) -> dict[str, str]:
    unique_values = list(dict.fromkeys(value for value in values if value))
    translator = GoogleTranslator(source=source_language, target=language_code)
    translations: dict[str, str] = {}
    chunks = _chunks(unique_values)
    for index, chunk in enumerate(chunks, start=1):
        translated = _translate_chunk(translator, chunk)
        translations.update(zip(chunk, translated, strict=True))
        print(
            f"{source_language}->{language_code}: "
            f"translated batch {index}/{len(chunks)}"
        )
        time.sleep(0.15)
    return translations


def should_generate_translation(
    section: str,
    previous: str,
    *,
    refresh: bool,
    draft_editorial: bool,
) -> bool:
    """Keep object prose human-owned unless draft generation is explicit."""

    if section == "objects" and not draft_editorial:
        return False
    return refresh or not previous


def update_pack(
    language_code: str,
    *,
    refresh: bool,
    draft_editorial: bool = False,
) -> None:
    metadata_path = TRANSLATIONS_DIR / f"{language_code}.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if payload.get("language", {}).get("code") != language_code:
        raise ValueError(f"Language metadata mismatch: {metadata_path}")
    translation_code = str(
        payload.get("language", {}).get("translation_code") or language_code
    )

    sources = source_content()
    current_content = payload.get("content")
    if not isinstance(current_content, dict):
        current_content = {}

    required_by_source: dict[str, list[str]] = OrderedDict()
    for section, items in sources.items():
        for item_key, fields in items.items():
            existing = current_content.get(section, {}).get(item_key, {})
            for field, source in fields.items():
                field_source_language = source_language(section, item_key, field)
                if translation_code == field_source_language:
                    continue
                previous = str(existing.get(field, "")).strip()
                if should_generate_translation(
                    section,
                    previous,
                    refresh=refresh,
                    draft_editorial=draft_editorial,
                ):
                    required_by_source.setdefault(field_source_language, []).append(source)
    translated: dict[str, str] = {}
    for source_code, required in required_by_source.items():
        translated.update(
            translate_values(
                required,
                translation_code,
                source_language=source_code,
            )
        )

    content: dict[str, dict[str, dict[str, str]]] = OrderedDict()
    for section, items in sources.items():
        if section == "objects" and not draft_editorial:
            # Reviewed prose is opaque here: historical overrides and language
            # cleanup rules belong only to explicitly requested working drafts.
            if section in current_content:
                content[section] = current_content[section]
            continue
        translated_items: dict[str, dict[str, str]] = OrderedDict()
        for item_key, fields in items.items():
            existing = current_content.get(section, {}).get(item_key, {})
            translated_fields: dict[str, str] = OrderedDict()
            for field, source in fields.items():
                if translation_code == source_language(section, item_key, field):
                    continue
                previous = str(existing.get(field, "")).strip()
                value = translated.get(source) if refresh or not previous else previous
                translated_fields[field] = curate_content_translation(
                    section,
                    item_key,
                    field,
                    str(value or source).strip(),
                    translation_code,
                )
            if translated_fields:
                translated_items[item_key] = translated_fields
        if translated_items:
            content[section] = translated_items
    payload["content"] = content
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate NightScope structured language-pack content from seed CSV files."
    )
    parser.add_argument(
        "languages",
        nargs="*",
        help="Language-pack codes to update; defaults to every discovered JSON pack.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Replace existing non-editorial generated content instead of filling only "
            "missing fields."
        ),
    )
    parser.add_argument(
        "--draft-editorial",
        action="store_true",
        help=(
            "Allow machine-generated object prose as an explicitly unreviewed draft; "
            "batch acceptance still requires manual IT/EN/ES review."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    languages = args.languages or sorted(path.stem for path in TRANSLATIONS_DIR.glob("*.json"))
    for language_code in languages:
        update_pack(
            language_code,
            refresh=args.refresh,
            draft_editorial=args.draft_editorial,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
