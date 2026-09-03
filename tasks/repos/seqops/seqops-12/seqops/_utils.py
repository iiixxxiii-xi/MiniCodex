"""Private shared helpers for the seqops package."""


def default_compare(a, b):
    """Three-way comparison of ``a`` and ``b``.

    Returns a negative int when ``a < b``, zero when equal, and a positive int
    when ``a > b`` (mirroring the legacy ``cmp`` builtin).
    """
    return (a < b) - (a > b)
