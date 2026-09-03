"""Case conversion and URL-slug helpers."""

import re


def slugify(text: str) -> str:
    """Convert ``text`` to a lowercase URL slug.

    Non-alphanumeric runs become a single hyphen; leading/trailing hyphens are
    stripped. ``"Hello, World!"`` -> ``"hello-world"``.
    """
    lowered = text.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    return hyphenated.strip("-")


def camel_to_snake(text: str) -> str:
    """Convert CamelCase or PascalCase ``text`` to snake_case.

    ``"CamelCase"`` -> ``"camel_case"``, ``"HTTPResponse"`` -> ``"http_response"``,
    ``"camelC"`` -> ``"camel_c"``.
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", text)
    return s1.lower()
