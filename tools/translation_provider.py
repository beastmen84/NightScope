"""Provide the timeout-bounded HTTP translation adapter used only by maintenance tools."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Callable

import requests


GOOGLE_TRANSLATE_URL = "https://translate.google.com/m"
MAX_TRANSLATION_CHARACTERS = 5_000
REQUEST_TIMEOUT = (5, 20)


class TranslationProviderError(RuntimeError):
    """Raised when the best-effort machine-translation endpoint fails."""


class _TranslationResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture_depth = 0
        self._parts: list[str] = []

    @property
    def result(self) -> str:
        return "".join(self._parts).strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._capture_depth:
            self._capture_depth += 1
            return
        if tag != "div":
            return
        classes = set((dict(attrs).get("class") or "").split())
        if classes.intersection({"result-container", "t0"}):
            self._capture_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self._capture_depth:
            self._capture_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_depth:
            self._parts.append(data)


class GoogleTranslator:
    """Small, timeout-bounded adapter for NightScope translation maintenance."""

    def __init__(
        self,
        source: str,
        target: str,
        *,
        http_get: Callable[..., requests.Response] = requests.get,
    ) -> None:
        self._source = source.strip()
        self._target = target.strip()
        self._http_get = http_get

    def translate(self, text: str) -> str:
        value = str(text).strip()
        if not value or self._source == self._target:
            return value
        if len(value) > MAX_TRANSLATION_CHARACTERS:
            raise ValueError(
                f"Translation input exceeds {MAX_TRANSLATION_CHARACTERS} characters."
            )

        try:
            response = self._http_get(
                GOOGLE_TRANSLATE_URL,
                params={"sl": self._source, "tl": self._target, "q": value},
                headers={
                    "Accept": "text/html",
                    "User-Agent": "NightScope translation maintenance tool",
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TranslationProviderError(
                f"Translation provider request failed: {exc.__class__.__name__}."
            ) from exc

        parser = _TranslationResultParser()
        parser.feed(response.text)
        translated = parser.result
        if not translated:
            raise TranslationProviderError(
                "Translation provider returned an unrecognized response."
            )
        return translated
