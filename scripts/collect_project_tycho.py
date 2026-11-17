#!/usr/bin/env python3
"""Download and prepare Project Tycho historical data without preselecting diseases.

The script downloads the official Zenodo archives for Project Tycho Level 1
version 1.0.0 and Level 2 version 1.1.0, verifies their MD5 checksums,
extracts them, filters all diseases to a requested year interval, and writes
coverage tables that can be used later to choose diseases and cities.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


ARCHIVES = {
    "level1": {
        "version": "1.0.0",
        "url": "https://zenodo.org/records/12608992/files/ProjectTycho_Level1_v1.0.0.zip?download=1",
        "md5": "4c3991594d8dbad117e69ef49808eb5b",
        "zip_name": "ProjectTycho_Level1_v1.0.0.zip",
        "csv_name": "ProjectTycho_Level1_v1.0.0.csv",
        "doi": "10.5281/zenodo.12608992",
    },
    "level2": {
        "version": "1.1.0",
        "url": "https://zenodo.org/records/12608994/files/ProjectTycho_Level2_v1.1.0.zip?download=1",
        "md5": "c3f3b1cfa4e8aa54cb730f26283cc194",
        "zip_name": "ProjectTycho_Level2_v1.1.0.zip",
        "csv_name": "ProjectTycho_Level2_v1.1.0.csv",
        "doi": "10.5281/zenodo.12608994",
    },
}


@dataclass
class DiseaseStats:
    records: int = 0
    first_year: int = 9999
    last_year: int = 0
    nonzero_records: int = 0
    missing_number_records: int = 0
    states: set[str] = field(default_factory=set)
    locations: set[str] = field(default_factory=set)
    cities: set[str] = field(default_factory=set)
    state_locations: set[str] = field(default_factory=set)
    epi_weeks: set[str] = field(default_factory=set)
    events: set[str] = field(default_factory=set)


@dataclass
class LocationStats:
    records: int = 0
    first_year: int = 9999
    last_year: int = 0
    epi_weeks: set[str] = field(default_factory=set)
    events: set[str] = field(default_factory=set)
    nonzero_records: int = 0


def md5sum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Project-Tycho-course-collector/1.0"})
    with urllib.request.urlopen(request) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    partial.replace(target)


def ensure_archive(name: str, raw_dir: Path, skip_download: bool) -> tuple[Path, Path]:
    spec = ARCHIVES[name]
    archive = raw_dir / spec["zip_name"]
    extract_dir = raw_dir / f"{name}_v{spec['version']}"
    csv_path = extract_dir / spec["csv_name"]

    if not archive.exists():
        if skip_download:
            raise FileNotFoundError(f"Missing archive while --skip-download is set: {archive}")
        download(spec["url"], archive)

    actual_md5 = md5sum(archive)
    if actual_md5.lower() != spec["md5"].lower():
        raise RuntimeError(f"MD5 mismatch for {archive.name}: {actual_md5}")

    if not csv_path.exists():
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if member.filename.startswith("__MACOSX/"):
                    continue
                bundle.extract(member, extract_dir)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found after extracting {archive}")
    return archive, csv_path


def clean_chunk(chunk: pd.DataFrame, level: str, start_year: int, end_year: int) -> pd.DataFrame:
    chunk.columns = [str(column).strip() for column in chunk.columns]
    chunk["epi_week"] = chunk["epi_week"].astype(str).str.strip()
    year = pd.to_numeric(chunk["epi_week"].str.slice(0, 4), errors="coerce")
    keep = year.between(start_year, end_year, inclusive="both")
    result = chunk.loc[keep].copy()
    result["year"] = year.loc[keep].astype("Int64")
    result["week"] = pd.to_numeric(result["epi_week"].str.slice(4, 6), errors="coerce").astype("Int64")
    result["source_level"] = level.upper()
    for column in ("state", "loc", "loc_type", "disease", "event"):
        if column in result.columns:
            result[column] = result[column].astype(str).str.strip()
    if level == "level1":
        result["event"] = "CASES"
        result["number"] = result["cases"]
    return result


def update_stats(
    frame: pd.DataFrame,
    level: str,
    disease_stats: dict[tuple[str, str], DiseaseStats],
    location_stats: dict[tuple[str, str, str, str, str], LocationStats],
    samples: dict[tuple[str, str], list[dict]],
) -> None:
    if frame.empty:
        return
    numeric = pd.to_numeric(frame["number"], errors="coerce")
    frame = frame.assign(_number_numeric=numeric)

    for disease, group in frame.groupby("disease", dropna=False, sort=False):
        disease_name = str(disease)
        key = (level.upper(), disease_name)
        stats = disease_stats[key]
        years = group["year"].dropna().astype(int)
        stats.records += len(group)
        if not years.empty:
            stats.first_year = min(stats.first_year, int(years.min()))
            stats.last_year = max(stats.last_year, int(years.max()))
        stats.nonzero_records += int((group["_number_numeric"] > 0).sum())
        stats.missing_number_records += int(group["_number_numeric"].isna().sum())
        stats.states.update(value for value in group["state"].dropna().astype(str) if value)
        stats.locations.update(value for value in group["loc"].dropna().astype(str) if value)
        stats.epi_weeks.update(value for value in group["epi_week"].dropna().astype(str) if value)
        stats.events.update(value for value in group["event"].dropna().astype(str) if value)
        city_mask = group["loc_type"].astype(str).str.upper().eq("CITY")
        state_mask = group["loc_type"].astype(str).str.upper().eq("STATE")
        stats.cities.update(value for value in group.loc[city_mask, "loc"].dropna().astype(str) if value)
        stats.state_locations.update(value for value in group.loc[state_mask, "loc"].dropna().astype(str) if value)

        remaining = 5 - len(samples[key])
        if remaining > 0:
            samples[key].extend(group.drop(columns=["_number_numeric"]).head(remaining).to_dict("records"))

    group_columns = ["disease", "state", "loc", "loc_type"]
    for values, group in frame.groupby(group_columns, dropna=False, sort=False):
        disease, state, loc, loc_type = (str(value) for value in values)
        key = (level.upper(), disease, state, loc, loc_type)
        stats = location_stats[key]
        years = group["year"].dropna().astype(int)
        stats.records += len(group)
        if not years.empty:
            stats.first_year = min(stats.first_year, int(years.min()))
            stats.last_year = max(stats.last_year, int(years.max()))
        stats.epi_weeks.update(value for value in group["epi_week"].dropna().astype(str) if value)
        stats.events.update(value for value in group["event"].dropna().astype(str) if value)
        stats.nonzero_records += int((group["_number_numeric"] > 0).sum())


def filter_dataset(
    level: str,
    source_csv: Path,
    output_csv: Path,
    start_year: int,
    end_year: int,
    disease_stats: dict[tuple[str, str], DiseaseStats],
    location_stats: dict[tuple[str, str, str, str, str], LocationStats],
    samples: dict[tuple[str, str], list[dict]],
    chunksize: int,
) -> int:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    wrote_header = False
    total_rows = 0
    for chunk in pd.read_csv(
        source_csv,
        dtype=str,
        keep_default_na=False,
        na_values=["\\N"],
        chunksize=chunksize,
        low_memory=False,
    ):
        filtered = clean_chunk(chunk, level, start_year, end_year)
        if filtered.empty:
            continue
        filtered.to_csv(output_csv, mode="a" if wrote_header else "w", header=not wrote_header, index=False)
        wrote_header = True
        total_rows += len(filtered)
        update_stats(filtered, level, disease_stats, location_stats, samples)
    if not wrote_header:
        output_csv.write_text("", encoding="utf-8")
    return total_rows


def write_disease_coverage(path: Path, stats: dict[tuple[str, str], DiseaseStats]) -> None:
    rows = []
    for (level, disease), item in sorted(stats.items()):
        rows.append(
            {
                "source_level": level,
                "disease": disease,
                "records": item.records,
                "first_year": item.first_year if item.first_year != 9999 else "",
                "last_year": item.last_year or "",
                "unique_epi_weeks": len(item.epi_weeks),
                "unique_states": len(item.states),
                "unique_locations": len(item.locations),
                "unique_cities": len(item.cities),
                "unique_state_locations": len(item.state_locations),
                "events": "|".join(sorted(value for value in item.events if value)),
                "nonzero_records": item.nonzero_records,
                "missing_number_records": item.missing_number_records,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def write_location_coverage(path: Path, stats: dict[tuple[str, str, str, str, str], LocationStats]) -> None:
    rows = []
    for (level, disease, state, loc, loc_type), item in sorted(stats.items()):
        rows.append(
            {
                "source_level": level,
                "disease": disease,
                "state": state,
                "loc": loc,
                "loc_type": loc_type,
                "records": item.records,
                "first_year": item.first_year if item.first_year != 9999 else "",
                "last_year": item.last_year or "",
                "unique_epi_weeks": len(item.epi_weeks),
                "events": "|".join(sorted(value for value in item.events if value)),
                "nonzero_records": item.nonzero_records,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def write_samples(path: Path, samples: dict[tuple[str, str], list[dict]]) -> None:
    target_diseases = {"DIPHTHERIA", "INFLUENZA", "POLIOMYELITIS"}
    records = []
    for key in sorted(samples):
        if key[1] in target_diseases:
            records.extend(samples[key][:1])
    pd.DataFrame(records).to_csv(path, index=False, encoding="utf-8-sig")


def write_field_dictionary(path: Path) -> None:
    rows = [
        ("epi_week", "两版", "流行病学年周，YYYYWW", "时间关联主字段"),
        ("year", "派生", "由 epi_week 前四位提取的年份", "筛选与年度统计"),
        ("week", "派生", "由 epi_week 后两位提取的周序号", "周级面板"),
        ("country", "Level 2", "国家代码，本版本为 US", "国家筛选"),
        ("state", "两版", "美国州邮政缩写", "空间关联"),
        ("loc", "两版", "州或城市名称", "空间关联"),
        ("loc_type", "两版", "地点类型 STATE 或 CITY", "区分空间粒度"),
        ("disease", "两版", "报告的疾病名称", "疾病语义关联"),
        ("event", "Level 2/派生", "CASES 或 DEATHS；Level 1 固定为 CASES", "区分病例与死亡"),
        ("number", "Level 2/派生", "报告数量；Level 1 由 cases 复制", "统一计数字段"),
        ("cases", "Level 1", "报告病例数", "Level 1 疫情强度"),
        ("incidence_per_100000", "Level 1", "每十万人发病率", "跨地点比较"),
        ("from_date", "Level 2", "报告周期起始日 YYYY-MM-DD", "精确时间连接"),
        ("to_date", "Level 2", "报告周期结束日 YYYY-MM-DD", "精确时间连接"),
        ("url", "Level 2", "原始报告来源链接", "溯源"),
        ("source_level", "派生", "LEVEL1 或 LEVEL2", "区分数据版本"),
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "source", "meaning", "project_use"])
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--start-year", type=int, default=1916)
    parser.add_argument("--end-year", type=int, default=1953)
    parser.add_argument("--chunksize", type=int, default=250_000)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    raw_dir = args.root / "data" / "raw" / "tycho" / "source_archives"
    output_dir = args.root / "data" / "raw" / "tycho"
    metadata_dir = args.root / "data" / "metadata" / "tycho" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    disease_stats: dict[tuple[str, str], DiseaseStats] = defaultdict(DiseaseStats)
    location_stats: dict[tuple[str, str, str, str, str], LocationStats] = defaultdict(LocationStats)
    samples: dict[tuple[str, str], list[dict]] = defaultdict(list)
    manifest = []

    for level in ("level1", "level2"):
        archive, source_csv = ensure_archive(level, raw_dir, args.skip_download)
        output_csv = output_dir / f"ProjectTycho_{level.upper()}_{args.start_year}_{args.end_year}_all_diseases.csv"
        if output_csv.exists():
            output_csv.unlink()
        rows = filter_dataset(
            level,
            source_csv,
            output_csv,
            args.start_year,
            args.end_year,
            disease_stats,
            location_stats,
            samples,
            args.chunksize,
        )
        manifest.append(
            {
                "source_level": level.upper(),
                "version": ARCHIVES[level]["version"],
                "doi": ARCHIVES[level]["doi"],
                "download_url": ARCHIVES[level]["url"],
                "archive_file": str(archive.relative_to(args.root)),
                "archive_bytes": archive.stat().st_size,
                "archive_md5": md5sum(archive),
                "source_csv_file": str(source_csv.relative_to(args.root)),
                "source_csv_bytes": source_csv.stat().st_size,
                "filtered_file": str(output_csv.relative_to(args.root)),
                "filtered_bytes": output_csv.stat().st_size,
                "filtered_rows": rows,
                "filter_start_year": args.start_year,
                "filter_end_year": args.end_year,
            }
        )

    write_disease_coverage(metadata_dir / f"disease_coverage_{args.start_year}_{args.end_year}.csv", disease_stats)
    write_location_coverage(metadata_dir / f"location_coverage_{args.start_year}_{args.end_year}.csv", location_stats)
    write_samples(metadata_dir / "sample_tycho.csv", samples)
    write_field_dictionary(metadata_dir / "field_dictionary.csv")
    pd.DataFrame(manifest).to_csv(metadata_dir / "data_manifest.csv", index=False, encoding="utf-8-sig")
    (metadata_dir / "run_summary.json").write_text(
        json.dumps(
            {
                "start_year": args.start_year,
                "end_year": args.end_year,
                "disease_count_by_level": {
                    level: sum(1 for key in disease_stats if key[0] == level)
                    for level in ("LEVEL1", "LEVEL2")
                },
                "manifest": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
