"""Rebuild ``major_profiles.json`` from the official government sources.

This is a developer tool, not part of the running app. The app and the test
suite read the committed ``major_profiles.json``; this script is how that file
gets regenerated when O*NET publishes a new database version.

Sources (all public, no scraping):

* **O*NET Database** (text bundle) - onetcenter.org, CC BY 4.0. Gives the RIASEC
  interest profile, Job Zone, top knowledge areas and top skills for each
  occupation.
* **CIP to SOC Crosswalk** - nces.ed.gov, public domain. Maps each college major
  (CIP code) to the occupations it leads to (SOC codes).

Run it with the ``data`` extra installed::

    pip install -e ".[data]"
    python -m compass.data.refresh            # download, build, write
    python -m compass.data.refresh --check    # rebuild in memory, diff, do not write

Downloads are cached under ``~/.cache/compass`` (override with
``COMPASS_DATA_CACHE``) so repeated runs do not re-fetch ~13 MB.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

ONET_VERSION = "31.0"
_V = ONET_VERSION.replace(".", "_")
ONET_ZIP_URL = f"https://www.onetcenter.org/dl_files/database/db_{_V}_0_text.zip"
CROSSWALK_URL = "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx"

_HERE = Path(__file__).parent
MAJORS_YAML = _HERE / "majors.yaml"
OUTPUT_JSON = _HERE / "major_profiles.json"

# How many occupations, at most, feed one major's profile. Some CIP codes map to
# 15+ SOC codes; past the first handful they are mostly "Postsecondary Teachers
# of <field>" and dilute the signal.
MAX_OCCUPATIONS = 12
# How many knowledge areas / skills to keep for the major detail view.
TOP_N_TRAITS = 6
# How many representative job titles to keep.
MAX_CAREERS = 8

_RIASEC_ELEMENTS = {
    "1.B.1.a": 0,  # Realistic
    "1.B.1.b": 1,  # Investigative
    "1.B.1.c": 2,  # Artistic
    "1.B.1.d": 3,  # Social
    "1.B.1.e": 4,  # Enterprising
    "1.B.1.f": 5,  # Conventional
}

_USER_AGENT = "compass-data-refresh/0.1 (+https://github.com/Samprit67/compass)"

# Cross-field catch-all SOC codes. The crosswalk attaches these to almost every
# social-science and business major; O*NET has no interest profile for the
# summary code, so expanding them pulls in an unrelated grab-bag of detailed
# occupations (a "Managers, All Other" turns into Wind Energy Operations
# Managers, Loss Prevention Managers, ...). Field-specific "All Other" codes such
# as 19-1029 "Biological Scientists, All Other" are kept: their detail
# occupations (Biologists, Geneticists, ...) are on point.
_JUNK_SOC = frozenset(
    {
        "11-9199",  # Managers, All Other
        "13-1199",  # Business Operations Specialists, All Other
        "13-1198",  # Project Management Specialists (over-attached)
        "15-1299",  # Computer Occupations, All Other
        "17-2199",  # Engineers, All Other
        "11-9179",  # Personal Service Managers, All Other
        "19-2099",  # Physical Scientists, All Other
        "19-3039",  # Psychologists, All Other (over-attached; Psychology itself maps to 19-3032/33)
        "19-3099",  # Social Scientists and Related Workers, All Other
        "19-4099",  # Life, Physical, and Social Science Technicians, All Other
        "25-1199",  # Postsecondary Teachers, All Other
        "25-3099",  # Teachers and Instructors, All Other
        "25-9099",  # Educational Instruction and Library Workers, All Other
        "27-3099",  # Media and Communication Workers, All Other
        "29-1299",  # Healthcare Diagnosing or Treating Practitioners, All Other
        "29-9099",  # Healthcare Practitioners and Technical Workers, All Other
        "43-9199",  # Office and Administrative Support Workers, All Other
    }
)


# --------------------------------------------------------------------------- IO


def _cache_dir() -> Path:
    override = os.environ.get("COMPASS_DATA_CACHE")
    base = Path(override) if override else Path.home() / ".cache" / "compass"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _download(url: str, dest: Path) -> None:
    import httpx

    if dest.exists() and dest.stat().st_size > 0:
        return
    print(f"  downloading {url}")
    with httpx.Client(follow_redirects=True, timeout=120.0, headers={"User-Agent": _USER_AGENT}) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    print(f"  saved {dest} ({dest.stat().st_size // 1024} KB)")


def _ensure_sources() -> tuple[Path, Path]:
    """Return (onet_text_dir, crosswalk_xlsx_path), downloading + extracting if needed."""
    cache = _cache_dir()
    zip_path = cache / f"onet_db_{ONET_VERSION}_text.zip"
    xlsx_path = cache / "cip_soc_crosswalk.xlsx"
    _download(ONET_ZIP_URL, zip_path)
    _download(CROSSWALK_URL, xlsx_path)

    onet_dir = cache / f"onet_db_{ONET_VERSION}_text"
    if not onet_dir.exists():
        print(f"  extracting {zip_path.name}")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(cache)
        # the archive holds a single top-level folder like "db_31_0_text/"
        extracted = next(p for p in cache.iterdir() if p.is_dir() and p.name.startswith("db_"))
        extracted.rename(onet_dir)
    return onet_dir, xlsx_path


def _read_tsv(path: Path) -> Iterable[list[str]]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        header = next(fh)
        del header
        for line in fh:
            yield line.rstrip("\n").split("\t")


# ------------------------------------------------------------------- O*NET load


@dataclass
class OnetTables:
    """Everything Compass needs from the O*NET text bundle, keyed by O*NET-SOC code."""

    riasec: dict[str, list[float]] = field(default_factory=dict)  # code -> 6 values (1-7)
    title: dict[str, str] = field(default_factory=dict)
    job_zone: dict[str, int] = field(default_factory=dict)
    knowledge: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))
    skills: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))


def load_onet(onet_dir: Path) -> OnetTables:
    t = OnetTables()

    partial: dict[str, list[float | None]] = defaultdict(lambda: [None] * 6)
    for row in _read_tsv(onet_dir / "Career Interest Types.txt"):
        code, element_id, _name, scale_id, value, *_ = row
        if scale_id != "OI":
            continue
        idx = _RIASEC_ELEMENTS.get(element_id)
        if idx is not None:
            partial[code][idx] = float(value)
    for code, vals in partial.items():
        if all(v is not None for v in vals):
            t.riasec[code] = [float(v) for v in vals if v is not None]

    for row in _read_tsv(onet_dir / "Occupation Data.txt"):
        code, title, *_ = row
        t.title[code] = title

    for row in _read_tsv(onet_dir / "Job Zones.txt"):
        code, zone, *_ = row
        t.job_zone[code] = int(zone)

    for fname, target in (("Knowledge.txt", t.knowledge), ("Essential Skills.txt", t.skills)):
        for row in _read_tsv(onet_dir / fname):
            code, _eid, name, scale_id, value, *_ = row
            if scale_id == "IM":
                target[code][name] = float(value)

    return t


# --------------------------------------------------------------- crosswalk load


def load_crosswalk(xlsx_path: Path) -> dict[str, list[str]]:
    """CIP 2020 code -> list of 6-digit SOC 2018 codes.

    Cross-field catch-all occupations (see ``_JUNK_SOC``) are dropped.
    """
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb["CIP-SOC"]
    out: dict[str, list[str]] = defaultdict(list)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        cip, _ctitle, soc, _stitle = row[:4]
        if cip is None or soc is None:
            continue
        soc = str(soc).strip()
        cip = str(cip).strip()
        if soc in _JUNK_SOC:
            continue
        if soc not in out[cip]:
            out[cip].append(soc)
    wb.close()
    return dict(out)


# --------------------------------------------------------------------- building


def _onet_codes_for_soc(soc6: str, onet: OnetTables) -> list[str]:
    """The O*NET-SOC codes (e.g. 15-1252.00, .01) that belong to a 6-digit SOC."""
    base = f"{soc6}.00"
    if base in onet.riasec:
        return [base]
    return sorted(c for c in onet.riasec if c.startswith(f"{soc6}."))


def _mean_vectors(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    return [round(sum(v[i] for v in vectors) / n, 3) for i in range(len(vectors[0]))]


def _top_traits(maps: list[dict[str, float]], n: int) -> list[str]:
    agg: dict[str, list[float]] = defaultdict(list)
    for m in maps:
        for name, val in m.items():
            agg[name].append(val)
    ranked = sorted(agg.items(), key=lambda kv: (-sum(kv[1]) / len(kv[1]), kv[0]))
    return [name for name, _ in ranked[:n]]


def build_profiles(
    majors: list[dict],
    onet: OnetTables,
    crosswalk: dict[str, list[str]],
) -> list[dict]:
    profiles: list[dict] = []
    problems: list[str] = []

    for major in majors:
        slug = major["slug"]
        soc6_codes: list[str] = []
        for cip in major["cip"]:
            mapped = crosswalk.get(cip)
            if not mapped:
                problems.append(f"{slug}: CIP {cip} not in crosswalk")
                continue
            for soc in mapped:
                if soc not in soc6_codes:
                    soc6_codes.append(soc)
        # The NCES crosswalk maps some interdisciplinary majors (Philosophy,
        # Cognitive Science, ...) to a single "Postsecondary Teachers of X"
        # occupation. `extra_soc` in majors.yaml adds a few closely related
        # occupations by hand so those profiles are not built from one point.
        for soc in major.get("extra_soc", []):
            if soc not in soc6_codes:
                soc6_codes.append(soc)

        onet_codes: list[str] = []
        for soc6 in soc6_codes:
            for code in _onet_codes_for_soc(soc6, onet):
                if code not in onet_codes:
                    onet_codes.append(code)

        # A four-year major mostly prepares you for Job Zone 4-5 work. Drop the
        # Zone 1-2 occupations (technicians, aides, guides) the crosswalk also
        # lists, unless that would leave too little to average over.
        degree_level = [c for c in onet_codes if onet.job_zone.get(c, 3) >= 3]
        if len(degree_level) >= 2:
            onet_codes = degree_level
        onet_codes = onet_codes[:MAX_OCCUPATIONS]

        if len(onet_codes) < 1:
            problems.append(f"{slug}: no occupation with interest data, skipping")
            continue
        if len(onet_codes) < 2:
            problems.append(f"{slug}: profile built from a single occupation ({onet_codes[0]})")

        riasec_vectors = [onet.riasec[c] for c in onet_codes]
        zones = [onet.job_zone[c] for c in onet_codes if c in onet.job_zone]
        knowledge_maps = [onet.knowledge[c] for c in onet_codes if c in onet.knowledge]
        skill_maps = [onet.skills[c] for c in onet_codes if c in onet.skills]

        # For the "example careers" list, surface the field's own practitioner
        # roles ahead of the generic "... Managers" and "... Teachers,
        # Postsecondary" that the crosswalk attaches to almost every major.
        def _career_rank(code: str) -> tuple[int, str]:
            title = onet.title.get(code, "")
            generic = title.endswith(("Postsecondary", "Managers")) or "Teachers, Except" in title
            return (1 if generic else 0, code)

        titles: list[str] = []
        for c in sorted(onet_codes, key=_career_rank):
            title = onet.title.get(c)
            if title and title not in titles:
                titles.append(title)

        profiles.append(
            {
                "slug": slug,
                "name": major["name"],
                "category": major["category"],
                "blurb": major["blurb"],
                "description": major.get("description", major["blurb"]),
                "cip_codes": list(major["cip"]),
                "riasec": _mean_vectors(riasec_vectors),
                "example_careers": titles[:MAX_CAREERS],
                "job_zone": round(sum(zones) / len(zones), 2) if zones else 0.0,
                "top_knowledge": _top_traits(knowledge_maps, TOP_N_TRAITS) if knowledge_maps else [],
                "top_skills": _top_traits(skill_maps, TOP_N_TRAITS) if skill_maps else [],
                "n_occupations": len(onet_codes),
                "thin": len(onet_codes) < 3,
            }
        )

    if problems:
        print(f"\n  {len(problems)} note(s):", file=sys.stderr)
        for p in problems:
            print(f"    - {p}", file=sys.stderr)

    profiles.sort(key=lambda p: (p["category"], p["name"]))
    return profiles


def _document(profiles: list[dict]) -> dict:
    return {
        "meta": {
            "onet_version": ONET_VERSION,
            "generated": date.today().isoformat(),
            "n_majors": len(profiles),
            "riasec_order": [
                "realistic",
                "investigative",
                "artistic",
                "social",
                "enterprising",
                "conventional",
            ],
            "riasec_scale": "O*NET Occupational Interests, 1 to 7",
            "sources": [
                "O*NET Database 31.0, U.S. Department of Labor (CC BY 4.0)",
                "CIP 2020 to SOC 2018 Crosswalk, NCES (public domain)",
            ],
        },
        "majors": profiles,
    }


def refresh(*, write: bool = True) -> dict:
    majors = yaml.safe_load(MAJORS_YAML.read_text())["majors"]
    print(f"building profiles for {len(majors)} majors")
    onet_dir, xlsx_path = _ensure_sources()
    onet = load_onet(onet_dir)
    print(f"  O*NET: {len(onet.riasec)} occupations with interest data")
    crosswalk = load_crosswalk(xlsx_path)
    print(f"  crosswalk: {len(crosswalk)} CIP codes")
    profiles = build_profiles(majors, onet, crosswalk)
    doc = _document(profiles)
    print(f"  built {len(profiles)} major profiles")

    if write:
        OUTPUT_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print(f"  wrote {OUTPUT_JSON}")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="rebuild and diff, do not write")
    args = parser.parse_args(argv)

    if args.check:
        fresh = refresh(write=False)
        current = json.loads(OUTPUT_JSON.read_text()) if OUTPUT_JSON.exists() else {}
        fmeta = {k: v for k, v in fresh["meta"].items() if k != "generated"}
        fresh_no_date = {**fresh, "meta": fmeta}
        cmeta = {k: v for k, v in current.get("meta", {}).items() if k != "generated"}
        cur_no_date = {**current, "meta": cmeta}
        if fresh_no_date == cur_no_date:
            print("up to date")
            return 0
        print("major_profiles.json is stale (rerun without --check)")
        return 1

    refresh(write=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
