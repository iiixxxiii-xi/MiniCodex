"""IO: read lines from a file."""


def read_lines(path: str) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]
