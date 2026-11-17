# -*- coding: utf-8 -*-
"""Build compact, deterministic samples for final submission."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
METADATA = DATA / "metadata"
CITIES = {"BALTIMORE", "CLEVELAND", "LOS ANGELES", "MILWAUKEE", "NEW YORK", "WASHINGTON"}
DISEASES = {"DIPHTHERIA", "INFLUENZA", "POLIOMYELITIS"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_csv(source, layer, path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = sum(1 for _ in reader)
    return {
        "source": source,
        "layer": layer,
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "rows": rows,
        "columns": len(header),
        "sha256": digest.hexdigest(),
    }


def build_newspaper():
    selected = {}
    fallback = {}
    sources = [
        DATA / "cleaned" / "newspaper" / "newspaper_hits_weekly.csv",
        DATA / "cleaned" / "newspaper" / "newspaper_hits_weekly_zip.csv",
    ]
    fields = ["city", "paper", "disease", "sunday_date", "n_hits", "n_hits_strong", "n_hits_weak", "n_pages"]
    for source in sources:
        for row in read_csv(source):
            key = (row["city"].upper(), row["disease"])
            if key[0] not in CITIES or key[1] not in DISEASES:
                continue
            fallback.setdefault(key, row)
            if int(row["n_hits"] or 0) > 0:
                selected.setdefault(key, row)
    rows = [selected.get(key, fallback[key]) for key in sorted(fallback)]
    return rows, fields, {"cities": len({r["city"] for r in rows}), "diseases": len({r["disease"] for r in rows})}


def build_noaa():
    selected = {}
    source = DATA / "cleaned" / "noaa" / "noaa_weekly_sixcities.csv"
    fields = ["city", "sunday_date", "week_end", "tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum", "n_days", "n_stations"]
    for row in read_csv(source):
        city = row["city"]
        if city in CITIES and city not in selected and row["sunday_date"] >= "1915-01-01" and row["tavg_avg"]:
            selected[city] = row
    rows = [selected[key] for key in sorted(selected)]
    return rows, fields, {"cities": len(rows)}


def build_nhgis():
    points = {row["city_id"]: row for row in read_csv(DATA / "cleaned" / "nhgis" / "nhgis_points_geo.csv")}
    fields = ["city_id", "city_name", "state_abbr", "census_year", "population", "tycho_city", "lon", "lat", "source_title", "boundary_comparability"]
    rows = []
    for row in read_csv(DATA / "cleaned" / "nhgis" / "population_clean.csv"):
        if row["census_year"] != "1930" or row["tycho_city"] not in CITIES:
            continue
        point = points[row["city_id"]]
        rows.append({**row, "lon": point["lon"], "lat": point["lat"]})
    rows.sort(key=lambda item: item["tycho_city"])
    return rows, fields, {"cities": len(rows), "census_year": 1930}


def build_integrated():
    selected = {}
    source = DATA / "integrated" / "weekly_sixcities_1915_1922_1930_1932.csv"
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        for row in reader:
            city = row["city"]
            if city in CITIES and city not in selected and row["year"] == "1920" and row["population"] and row["tavg_avg"] and row["np_pages"]:
                selected[city] = row
    rows = [selected[key] for key in sorted(selected)]
    return rows, fields, {"cities": len(rows), "year": 1920}


def main():
    builders = {
        "newspaper": build_newspaper,
        "noaa": build_noaa,
        "nhgis": build_nhgis,
        "integrated": build_integrated,
    }
    validation = {"generated_by": "scripts/build_submission_samples.py", "samples": {}}
    for source, builder in builders.items():
        rows, fields, coverage = builder()
        output = METADATA / source / f"sample_{source}.csv"
        write_csv(output, rows, fields)
        validation["samples"][source] = {
            "file": str(output.relative_to(ROOT)).replace("\\", "/"),
            "rows": len(rows),
            **coverage,
        }
        print(f"{source}: {len(rows)} rows -> {output}")

    tycho = METADATA / "tycho" / "sample_tycho.csv"
    tycho_rows = list(read_csv(tycho))
    validation["samples"]["tycho"] = {
        "file": str(tycho.relative_to(ROOT)).replace("\\", "/"),
        "rows": len(tycho_rows),
        "cities": len({row["city"] for row in tycho_rows}),
        "diseases": len({row["disease"] for row in tycho_rows}),
    }
    raw_newspaper_manifest = METADATA / "newspaper" / "sample_newspaper_raw.csv"
    if raw_newspaper_manifest.exists():
        raw_newspaper_rows = list(read_csv(raw_newspaper_manifest))
        validation["samples"]["newspaper_raw"] = {
            "file": str(raw_newspaper_manifest.relative_to(ROOT)).replace("\\", "/"),
            "files": len(raw_newspaper_rows),
            "cities": len({row["city"] for row in raw_newspaper_rows}),
            "bounded_scan_seconds": 45,
            "large_zip_scanned": False,
        }
    (METADATA / "samples_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest_files = [
        ("newspaper", "cleaned", DATA / "cleaned" / "newspaper" / "newspaper_hits_weekly.csv"),
        ("newspaper", "cleaned", DATA / "cleaned" / "newspaper" / "newspaper_hits_weekly_zip.csv"),
        ("newspaper", "cleaned", DATA / "cleaned" / "newspaper" / "newspaper_coverage_matrix.csv"),
        ("newspaper", "cleaned", DATA / "cleaned" / "newspaper" / "newspaper_coverage_matrix_zip.csv"),
        ("tycho", "cleaned", DATA / "cleaned" / "tycho" / "cleaned_tycho_weekly_sixcities.csv"),
        ("noaa", "cleaned", DATA / "cleaned" / "noaa" / "noaa_weekly_sixcities.csv"),
        ("nhgis", "cleaned", DATA / "cleaned" / "nhgis" / "population_clean.csv"),
        ("nhgis", "cleaned", DATA / "cleaned" / "nhgis" / "nhgis_points_geo.csv"),
        ("integrated", "integrated", DATA / "integrated" / "weekly_sixcities_1915_1922_1930_1932.csv"),
    ]
    if raw_newspaper_manifest.exists():
        manifest_files.append(("newspaper", "raw_sample_manifest", raw_newspaper_manifest))
    for source in ("newspaper", "tycho", "noaa", "nhgis", "integrated"):
        manifest_files.append((source, "sample", METADATA / source / f"sample_{source}.csv"))
    manifest_rows = [summarize_csv(*item) for item in manifest_files]
    write_csv(
        METADATA / "dataset_manifest.csv",
        manifest_rows,
        ["source", "layer", "file", "bytes", "rows", "columns", "sha256"],
    )


if __name__ == "__main__":
    main()
