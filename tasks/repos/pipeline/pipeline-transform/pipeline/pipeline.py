"""Pipeline: read -> transform -> write."""

from pipeline.io import read_lines
from pipeline.transform import transform


def run(in_path: str, out_path: str) -> int:
    lines = read_lines(in_path)
    out = [transform(l) for l in lines]
    with open(out_path, "w") as f:
        for l in out:
            f.write(l + "\n")
    return len(out)
