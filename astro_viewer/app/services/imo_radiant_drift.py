"""Read optional IMO radiant-drift columns conservatively near annual maxima.

The position-preserving Table 6 text contains blank cells and labels both above
and below their columns. Header alignment, date bounds and agreement with the
independent Working List are required; an unfamiliar layout has no drift data.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from math import acos, cos, radians, sin


MONTHS = {name: index for index, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
COORDINATES = re.compile(r"(?<!\d)(\d{1,3})[°◦]?\s+([+−-]\s*\d{1,2}|0)[°◦]?(?!\d)")


def extract_drift_layout(page):
    """Preserve PDF x positions; omit raised degree glyphs, not blank cells.

    Generic layout extraction stretches some sparse rows differently in the
    source publication. A small, fixed-pitch coordinate projection avoids that.
    Only unrotated, normal-size table text is accepted.
    """
    rows = {}

    def visit(text, matrix, text_matrix, font, size):
        if size < 8 or not text.strip() or matrix[:4] != [1.0, 0.0, 0.0, 1.0]:
            return
        x, y = text_matrix[4] + matrix[4], text_matrix[5] + matrix[5]
        if not 0 <= x < 1000 or not 0 <= y < 2000:
            return
        key = next((value for value in rows if abs(value - y) < 1), y)
        rows.setdefault(key, []).append((x, text.replace("\n", " ")))

    page.extract_text(visitor_text=visit)
    lines = []
    for _, pieces in sorted(rows.items(), reverse=True):
        line = ""
        for x, text in sorted(pieces):
            line += " " * max(1, round(x / 3) - len(line)) + text.strip()
        lines.append(line)
    return "\n".join(lines)


def radiant_drift_rows(layout, shower) -> tuple[tuple[date, float, float], ...]:
    """Import only a bounded, unambiguous column around this shower's maximum."""
    code = r"\s*".join(re.escape(letter) for letter in shower.code)
    centers = [(match.start() + match.end()) / 2 for line in layout.splitlines()
               for match in re.finditer(rf"\b{code}\b", line)]
    # The PDF reader can merge the first three header cells into one string.
    # Their explicit left-to-right labels match the complete first date row.
    if shower.code == "QUA" and re.search(r"\bDate\s+ANT\s+QUA\s+COM\b", layout):
        first_row = next((line for line in layout.splitlines() if re.match(r"\s*Jan\s+0\s", line)), "")
        pairs = list(COORDINATES.finditer(first_row))
        if len(pairs) == 3:
            centers = [(pairs[1].start() + pairs[1].end()) / 2]
    if not centers or max(centers) - min(centers) > 8:
        return ()
    center = sum(centers) / len(centers)
    rows = {}
    for line in layout.splitlines():
        stamp = re.match(r"\s*([A-Z][a-z]{2})\s+(\d{1,2})\s", line)
        if not stamp or stamp[1] not in MONTHS:
            continue
        try:
            # IMO Jan 0 denotes the previous December 31.
            month, number = MONTHS[stamp[1]], int(stamp[2])
            day = (date(shower.peak.year, 1, 1) - timedelta(days=1)
                   if month == 1 and number == 0 else date(shower.peak.year, month, number))
        except ValueError:
            return ()
        if abs((day - shower.peak).days) > 10:
            continue
        candidates = [match for match in COORDINATES.finditer(line)
                      if abs((match.start() + match.end()) / 2 - center) <= 8]
        if len(candidates) > 1:
            return ()
        if not candidates:
            continue
        match = candidates[0]
        ra, dec = float(match[1]), float(match[2].replace("−", "-").replace(" ", ""))
        if not 0 <= ra < 360 or not -90 <= dec <= 90:
            return ()
        separation = _separation(ra, dec, shower.radiant_ra_deg, shower.radiant_dec_deg)
        # Adjacent showers can reuse this column. Never import another radiant.
        if separation > 15:
            continue
        if day in rows and rows[day] != (ra, dec):
            return ()
        rows[day] = (ra, dec)
    result = tuple((day, *values) for day, values in sorted(rows.items()))
    if len(result) < 2:
        return ()
    for first, second in zip(result, result[1:]):
        days = (second[0] - first[0]).days
        if not 0 < days <= 10 or _separation(*first[1:], *second[1:]) / days > 3:
            return ()
    if not result[0][0] <= shower.peak <= result[-1][0]:
        return ()
    return result


def _separation(ra, dec, other_ra, other_dec):
    value = sin(radians(dec)) * sin(radians(other_dec)) + cos(radians(dec)) * cos(radians(other_dec)) * cos(radians(ra - other_ra))
    return acos(max(-1, min(1, value))) * 180 / 3.141592653589793
