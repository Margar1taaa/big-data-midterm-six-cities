# -*- coding: utf-8 -*-
"""Bounded raw-newspaper sampler: no recursive traversal and no ZIP scan."""

import csv
import hashlib
import os
import shutil
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "newspaper"
OUT_DIR = ROOT / "data" / "metadata" / "newspaper" / "sample_newspaper_raw"
MANIFEST = ROOT / "data" / "metadata" / "newspaper" / "sample_newspaper_raw.csv"

MAX_SECONDS = 45
MAX_FILES = 3
MAX_ENTRIES_PER_LEVEL = 500
MAX_OCR_BYTES = 2 * 1024 * 1024
TARGETS = {
    "Baltimore": ("1915", "01"),
    "Cleveland": ("1915", "01"),
    "Los Angeles": ("1922", "01"),
}


def check_deadline(deadline):
    if time.monotonic() > deadline:
        raise TimeoutError(f"raw newspaper sampling exceeded {MAX_SECONDS} seconds")


def direct_dirs(path, deadline):
    """Inspect only one directory level and cap the number of entries."""
    check_deadline(deadline)
    result = []
    with os.scandir(path) as entries:
        for index, entry in enumerate(entries):
            if index >= MAX_ENTRIES_PER_LEVEL:
                break
            if entry.is_dir(follow_symlinks=False):
                result.append(Path(entry.path))
    check_deadline(deadline)
    return sorted(result, key=lambda item: item.name.casefold())


def choose_paper(city_dir, year, deadline):
    papers = direct_dirs(city_dir, deadline)
    for paper in papers:
        if (paper / year).is_dir():
            return paper
    return papers[0] if papers else None


def choose_named_or_first(parent, preferred, deadline):
    exact = parent / preferred
    if exact.is_dir():
        return exact
    choices = direct_dirs(parent, deadline)
    return choices[0] if choices else None


def choose_ocr(city, year, month, deadline):
    city_dir = RAW_ROOT / city
    paper = choose_paper(city_dir, year, deadline)
    if paper is None:
        return None
    year_dir = choose_named_or_first(paper, year, deadline)
    if year_dir is None:
        return None
    month_dir = choose_named_or_first(year_dir, month, deadline)
    if month_dir is None:
        return None
    current = month_dir
    for _level in ("day", "edition", "sequence"):
        choices = direct_dirs(current, deadline)
        if not choices:
            return None
        current = choices[0]
    ocr = current / "ocr.txt"
    return ocr if ocr.is_file() else None


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    started = time.monotonic()
    deadline = started + MAX_SECONDS
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for city, (year, month) in TARGETS.items():
        check_deadline(deadline)
        if len(rows) >= MAX_FILES:
            break
        source = choose_ocr(city, year, month, deadline)
        if source is None:
            continue
        size = source.stat().st_size
        if size > MAX_OCR_BYTES:
            continue
        relative = source.relative_to(RAW_ROOT)
        parts = relative.parts
        sample_name = "__".join([parts[0].replace(" ", "_"), parts[2], parts[3], parts[4], parts[6]]) + ".txt"
        destination = OUT_DIR / sample_name
        shutil.copyfile(source, destination)
        rows.append({
            "city": parts[0],
            "paper": parts[1],
            "date": "-".join(parts[2:5]),
            "edition": parts[5],
            "sequence": parts[6],
            "source_path": str(source.relative_to(ROOT)).replace("\\", "/"),
            "sample_file": str(destination.relative_to(ROOT)).replace("\\", "/"),
            "bytes": size,
            "sha256": sha256(source),
        })
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["city", "paper", "date", "edition", "sequence", "source_path", "sample_file", "bytes", "sha256"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    elapsed = time.monotonic() - started
    print(f"FILES={len(rows)} ELAPSED_SECONDS={elapsed:.3f} LIMIT_SECONDS={MAX_SECONDS}")


if __name__ == "__main__":
    main()
