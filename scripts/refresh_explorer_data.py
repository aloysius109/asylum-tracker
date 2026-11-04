"""Validate UNHCR inputs and build a browser-ready country/year/unit dataset."""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview/data"
BASE = "https://api.unhcr.org/population/v1/"
KEYS = ["Year", "Country of asylum (ISO)", "Cases / Persons"]
VOLUMES = {
    "asylum-applications": {"applied": "applications"},
    "asylum-decisions": {
        "Recognized decisions": "recognised",
        "Complementary protection": "other_protection",
        "Rejected decisions": "rejected",
        "Otherwise closed": "closed",
        "Total decisions": "decisions",
    },
}


def validate(frame, dataset, year_to):
    required = {*KEYS, "Country of asylum", *VOLUMES[dataset]}
    missing = required.difference(frame.columns)
    if missing or frame.empty:
        raise ValueError(f"{dataset}: empty data or missing columns {sorted(missing)}")
    if frame[KEYS].isna().any().any():
        raise ValueError(f"{dataset}: missing grouping keys")
    if not set(frame["Cases / Persons"]).issubset({"P", "C"}):
        raise ValueError(f"{dataset}: unexpected reporting units")
    if not frame["Country of asylum (ISO)"].map(lambda value: bool(re.fullmatch(r"[A-Z]{3}", str(value)))).all():
        raise ValueError(f"{dataset}: unexpected country codes")
    years = pd.to_numeric(frame.Year, errors="raise")
    if not years.between(2000, year_to).all() or not years.eq(years.round()).all():
        raise ValueError(f"{dataset}: years outside the requested complete-calendar-year range")
    frame["Year"] = years.astype(int)
    for column in VOLUMES[dataset]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        observed = frame[column].dropna()
        if observed.empty or not observed.ge(0).all() or not observed.eq(observed.round()).all():
            raise ValueError(f"{dataset}: invalid counts in {column}")
    return frame


def build(frames, metadata):
    groups = []
    for dataset, mapping in VOLUMES.items():
        frame = frames[dataset]
        grouped = frame.groupby(KEYS, as_index=False)[list(mapping)].sum(min_count=1)
        for column in mapping:
            if frame[column].sum() != grouped[column].sum():
                raise ValueError(f"{dataset}: aggregation changed {column} totals")
        groups.append(grouped.rename(columns=mapping))
    joined = groups[0].merge(groups[1], how="outer", on=KEYS, validate="one_to_one")
    joined = joined.rename(columns={"Year": "year", "Country of asylum (ISO)": "country", "Cases / Persons": "unit"})
    joined = joined.sort_values(["country", "unit", "year"])
    rows = []
    for record in joined.to_dict("records"):
        rows.append({key: None if pd.isna(value) else int(value) if isinstance(value, (int, float)) else value
                     for key, value in record.items()})
    names = pd.concat([frame[["Year", "Country of asylum (ISO)", "Country of asylum"]] for frame in frames.values()])
    names = names.sort_values("Year").drop_duplicates("Country of asylum (ISO)", keep="last")
    countries = sorted(
        [{"iso": row["Country of asylum (ISO)"], "name": row["Country of asylum"]}
         for row in names.to_dict("records")], key=lambda country: country["name"])
    mismatch = joined[["recognised", "other_protection", "rejected", "closed"]].sum(axis=1, min_count=4)
    warnings = int((joined["decisions"].notna() & mismatch.notna() & mismatch.ne(joined["decisions"])).sum())
    metadata["outcome_total_mismatch_rows"] = warnings
    metadata["countries"] = len(countries)
    metadata["year_from"] = 2000
    metadata["year_to_available"] = max(row["year"] for row in rows)
    metadata["year_to_common"] = min(int(frame.Year.max()) for frame in frames.values())
    return {"metadata": metadata, "countries": countries, "rows": rows}


def refresh(bundled=False):
    downloaded_at = datetime.now(timezone.utc)
    year_to = downloaded_at.year - 1
    frames, sources, raw = {}, {}, {}
    for dataset in VOLUMES:
        params = {"yearFrom": 2000, "yearTo": year_to, "coo_all": "true",
                  "coa_all": "true", "cf_type": "ISO", "download": "true"}
        url = requests.Request("GET", BASE + dataset + "/", params=params).prepare().url
        if bundled:
            content = (ROOT / (dataset + ".csv")).read_bytes()
        else:
            response = requests.get(url, timeout=(20, 180))
            response.raise_for_status()
            with ZipFile(BytesIO(response.content)) as archive:
                name = next((name for name in archive.namelist() if Path(name).name == dataset + ".csv"), None)
                if name is None:
                    raise ValueError(f"{dataset}: expected CSV is missing from API archive")
                content = archive.read(name)
        frame = validate(pd.read_csv(BytesIO(content)), dataset, year_to)
        frames[dataset] = frame
        raw[dataset + ".csv"] = content
        sources[dataset] = {"url": url, "sha256": hashlib.sha256(content).hexdigest(),
                            "rows": len(frame), "year_from": int(frame.Year.min()), "year_to": int(frame.Year.max())}
    metadata = {
        "downloaded_at_utc": None if bundled else downloaded_at.isoformat(),
        "prepared_at_utc": downloaded_at.isoformat(),
        "source_mode": "bundled snapshot" if bundled else "UNHCR API",
        "requested_year_to": year_to,
        "sources": sources,
        "refresh_policy": "Weekly on Monday, with additional refreshes on publication updates.",
    }
    payload = build(frames, metadata)
    # A large unexpected coverage loss fails the refresh and leaves the deployed site intact.
    previous_path = DEST / "explorer.json"
    if not bundled and previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        for dataset, source in sources.items():
            old = previous["metadata"]["sources"][dataset]
            if source["rows"] < .8 * old["rows"] or source["year_from"] > old["year_from"] or source["year_to"] < old["year_to"]:
                raise ValueError(f"{dataset}: source coverage regressed; review before publication.")
        if len(payload["rows"]) < .8 * len(previous["rows"]) or len(payload["countries"]) < .8 * len(previous["countries"]):
            raise ValueError("Refresh lost over 20% of country/year coverage; inspect the source before publication.")
    DEST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DEST) as work:
        work = Path(work)
        (work / "explorer.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")
        with ZipFile(work / "source-snapshot.zip", "w", ZIP_DEFLATED) as archive:
            for filename, content in raw.items():
                archive.writestr(filename, content)
            archive.writestr("provenance.json", json.dumps(metadata, indent=2))
        # Stage in the public data directory so Windows files inherit its access permissions.
        for filename in ["source-snapshot.zip", "explorer.json"]:
            staging = DEST / ("." + filename + ".tmp")
            staging.write_bytes((work / filename).read_bytes())
            staging.replace(DEST / filename)
    print(f"Prepared {len(payload['rows']):,} country/year/unit observations for {len(payload['countries'])} receiving-country codes.")
    print(f"Source: {metadata['source_mode']}; downloaded: {metadata['downloaded_at_utc']}; shared endpoint: {metadata['year_to_common']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Fetch and validate current UNHCR snapshots; fail on errors.")
    mode.add_argument("--bundled", action="store_true", help="Prepare a local demonstration; never label it as newly downloaded.")
    args = parser.parse_args()
    refresh(bundled=args.bundled)
