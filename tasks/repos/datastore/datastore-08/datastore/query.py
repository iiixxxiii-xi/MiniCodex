"""Filter, group-by, dedupe, and aggregation helpers over record lists."""

from datastore.csvio import parse_csv_dicts


def filter_records(records, predicate):
    """Return the records for which ``predicate(record)`` is truthy."""
    return [record for record in records if predicate(record)]


def group_by(records, key):
    """Group ``records`` into a dict mapping ``key(record)`` -> list of records."""
    groups = {}
    for record in records:
        k = key(record)
        groups.setdefault(k, []).append(record)
    return groups


def dedupe(records, key=None):
    """Return ``records`` with duplicates removed, keeping first occurrence.

    ``key`` may be a callable or a string field name; by default the whole
    record is compared.
    """
    seen = set()
    out = []
    for record in records:
        if key is None:
            k = record
        elif callable(key):
            k = key(record)
        else:
            k = key
        if k in seen:
            continue
        seen.add(k)
        out.append(record)
    return out


def aggregate(records, key, func, default=None):
    """Apply ``func`` to the list of values at ``key`` across ``records``.

    Returns ``default`` when there are no records.
    """
    values = [record[key] for record in records]
    if not values:
        return default
    return func(values)


def select_fields(records, *fields):
    """Project each record down to just the given ``fields``."""
    return [{field: record[field] for field in fields} for record in records]


def group_csv(text, key):
    """Parse CSV ``text`` into record dicts and group them by ``key``."""
    records = parse_csv_dicts(text)
    return group_by(records, lambda record: record[key])
