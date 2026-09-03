from textutils.case import camel_to_snake, slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_punctuation():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_multiple_spaces():
    assert slugify("a  b") == "a-b"


def test_slugify_already_slug():
    assert slugify("hello-world") == "hello-world"


def test_slugify_leading_trailing():
    assert slugify("  Hello World  ") == "hello-world"


def test_slugify_accents():
    assert slugify("café au lait") == "caf-au-lait"


def test_slugify_empty():
    assert slugify("") == ""


def test_camel_to_snake_basic():
    assert camel_to_snake("camelCase") == "camel_case"


def test_camel_to_snake_pascal():
    assert camel_to_snake("PascalCase") == "pascal_case"


def test_camel_to_snake_single_upper():
    assert camel_to_snake("camelC") == "camel_c"


def test_camel_to_snake_acronym():
    assert camel_to_snake("HTTPResponse") == "http_response"


def test_camel_to_snake_acronym_prefix():
    assert camel_to_snake("parseHTMLDocument") == "parse_html_document"


def test_camel_to_snake_already_snake():
    assert camel_to_snake("snake_case") == "snake_case"


def test_camel_to_snake_all_lower():
    assert camel_to_snake("lowercase") == "lowercase"
