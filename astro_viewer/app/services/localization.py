from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from PySide6.QtCore import QCoreApplication, QDateTime, QLocale


DEFAULT_LANGUAGE_CODE = "it"

_active_language_code = DEFAULT_LANGUAGE_CODE
_active_locale_name = "it_IT"
_active_formats: dict[str, str] = {
    "date": "dd/MM/yyyy",
    "date_time": "dd/MM/yyyy HH:mm",
}
_active_content: Mapping[str, Any] = {}


class LocalizedText(str):
    """Canonical source text plus interpolation values, rendered at the UI boundary."""

    __slots__ = ("source", "values")

    def __new__(cls, source: str, values: Mapping[str, Any] | None = None):
        clean_values = dict(values or {})
        canonical = source.format_map(_CanonicalFormatValues(clean_values))
        instance = super().__new__(cls, canonical)
        instance.source = source
        instance.values = clean_values
        return instance

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return LocalizedText, (self.source, self.values)


class LocalizedContentText(str):
    """Reference to a language-pack override for a canonical seeded value."""

    __slots__ = ("section", "item_key", "field", "source")

    def __new__(
        cls,
        section: str,
        item_key: str,
        field: str,
        source: str,
    ):
        instance = super().__new__(cls, source)
        instance.section = section
        instance.item_key = item_key
        instance.field = field
        instance.source = source
        return instance

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return LocalizedContentText, (
            self.section,
            self.item_key,
            self.field,
            self.source,
        )


class LocalizedDateTimeText(str):
    __slots__ = ("value", "include_time")

    def __new__(cls, value: datetime, include_time: bool):
        format_string = "dd/MM/yyyy HH:mm" if include_time else "dd/MM/yyyy"
        canonical = QLocale("it_IT").toString(QDateTime(value), format_string)
        instance = super().__new__(cls, canonical)
        instance.value = value
        instance.include_time = include_time
        return instance

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return LocalizedDateTimeText, (self.value, self.include_time)


class LocalizedJoinedText(str):
    """A lazy join that preserves localization metadata for every item."""

    __slots__ = ("values", "separator")

    def __new__(cls, values: tuple[object, ...], separator: str):
        instance = super().__new__(cls, separator.join(str(value) for value in values))
        instance.values = values
        instance.separator = separator
        return instance

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return LocalizedJoinedText, (self.values, self.separator)


class LocalizedNumberText(str):
    __slots__ = ("value", "decimals")

    def __new__(cls, value: float, decimals: int):
        rounded_value = round(float(value), int(decimals))
        instance = super().__new__(
            cls,
            QLocale("it_IT").toString(rounded_value, "f", decimals),
        )
        instance.value = rounded_value
        instance.decimals = int(decimals)
        return instance

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return LocalizedNumberText, (self.value, self.decimals)


class _CanonicalFormatValues(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def activate_language_pack(payload: Mapping[str, Any]) -> None:
    global _active_language_code, _active_locale_name, _active_formats, _active_content

    language = payload.get("language") if isinstance(payload, Mapping) else None
    language = language if isinstance(language, Mapping) else {}
    _active_language_code = str(language.get("code") or DEFAULT_LANGUAGE_CODE)
    _active_locale_name = str(language.get("locale") or "it_IT")

    formats = payload.get("formats") if isinstance(payload, Mapping) else None
    formats = formats if isinstance(formats, Mapping) else {}
    _active_formats = {
        "date": str(formats.get("date") or "dd/MM/yyyy"),
        "date_time": str(formats.get("date_time") or "dd/MM/yyyy HH:mm"),
    }

    content = payload.get("content") if isinstance(payload, Mapping) else None
    _active_content = content if isinstance(content, Mapping) else {}


def active_language_code() -> str:
    return _active_language_code


def tr(source: str, /, **values: Any) -> LocalizedText:
    """Marks a Python presentation message for Qt Linguist extraction."""

    return LocalizedText(source, values)


def content_text(
    section: str,
    item_key: str,
    field: str,
    source: object,
) -> str:
    text = str(source or "")
    if not text:
        return ""
    return LocalizedContentText(section, item_key, field, text)


def content_key(*parts: object) -> str:
    """Builds a stable language-pack key from seed identity fields."""

    return "::".join(_content_key_part(part) for part in parts)


def _content_key_part(value: object) -> str:
    text = " ".join(str(value or "").split()).casefold()
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    if not number.is_finite():
        return text
    if number == number.to_integral():
        return format(number.quantize(Decimal(1)), "f")
    return format(number.normalize(), "f").rstrip("0").rstrip(".")


def join_text(values: list[object] | tuple[object, ...], separator: str = " · ") -> str:
    return LocalizedJoinedText(tuple(value for value in values if value not in (None, "")), separator)


def presentation_text(value: object, *, strip: bool = False) -> str:
    """Converts arbitrary values without discarding lazy localization metadata."""

    if value is None:
        return ""
    if isinstance(
        value,
        (
            LocalizedText,
            LocalizedContentText,
            LocalizedDateTimeText,
            LocalizedJoinedText,
            LocalizedNumberText,
        ),
    ):
        canonical = str.__str__(value)
        return value if not strip or canonical == canonical.strip() else canonical.strip()
    text = str(value)
    return text.strip() if strip else text


def render_text(value: object) -> str:
    if isinstance(value, LocalizedNumberText):
        return QLocale(_active_locale_name).toString(value.value, "f", value.decimals)

    if isinstance(value, LocalizedJoinedText):
        return value.separator.join(render_text(item) for item in value.values)

    if isinstance(value, LocalizedDateTimeText):
        format_key = "date_time" if value.include_time else "date"
        return QLocale(_active_locale_name).toString(
            QDateTime(value.value),
            _active_formats[format_key],
        )

    if isinstance(value, LocalizedContentText):
        section = _active_content.get(value.section, {})
        item = section.get(value.item_key, {}) if isinstance(section, Mapping) else {}
        translated = item.get(value.field) if isinstance(item, Mapping) else None
        return str(translated) if translated not in (None, "") else value.source

    if isinstance(value, LocalizedText):
        template = QCoreApplication.translate("", value.source)
        rendered_values = {
            key: render_text(item)
            if isinstance(
                item,
                (
                    LocalizedText,
                    LocalizedContentText,
                    LocalizedDateTimeText,
                    LocalizedJoinedText,
                    LocalizedNumberText,
                ),
            )
            else item
            for key, item in value.values.items()
        }
        return template.format_map(_CanonicalFormatValues(rendered_values))

    return str(value)


def render_payload(value: Any) -> Any:
    if isinstance(
        value,
        (
            LocalizedText,
            LocalizedContentText,
            LocalizedDateTimeText,
            LocalizedJoinedText,
            LocalizedNumberText,
        ),
    ):
        return render_text(value)
    if isinstance(value, dict):
        return {key: render_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [render_payload(item) for item in value]
    if isinstance(value, tuple):
        return [render_payload(item) for item in value]
    return value


def format_datetime(value: datetime, *, include_time: bool = True) -> str:
    return LocalizedDateTimeText(value, include_time)


def format_number(value: float, *, decimals: int = 0) -> str:
    return LocalizedNumberText(value, decimals)


def format_compact_number(value: float, *, max_decimals: int = 2) -> str:
    normalized = f"{float(value):.{max_decimals}f}".rstrip("0").rstrip(".")
    decimals = len(normalized.partition(".")[2])
    return LocalizedNumberText(value, decimals)


def format_month_year(month: int, year: int) -> str:
    locale = QLocale(_active_locale_name)
    month_name = locale.monthName(month, QLocale.LongFormat)
    return f"{month_name} {year}"
