"""Scanning directories for files by extension."""

import os


def list_by_extension(directory, extension):
    """Return a sorted list of file names in ``directory`` matching ``extension``.

    Matching is case-insensitive and ignores a leading dot, so ``".txt"``,
    ``"txt"`` and ``".TXT"`` all match ``report.TXT``.
    """
    ext = extension.lower().lstrip(".")
    names = []
    for name in os.listdir(directory):
        full = os.path.join(directory, name)
        if os.path.isfile(full) and name.endswith("." + ext):
            names.append(name)
    return sorted(names)
