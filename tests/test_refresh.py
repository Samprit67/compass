"""Offline test of the ETL: build a tiny O*NET slice + crosswalk in a tmpdir and
run the pipeline against it. No network, no committed binary fixtures."""

from __future__ import annotations

import pytest

openpyxl = pytest.importorskip("openpyxl")

from compass.data.refresh import build_profiles, load_crosswalk, load_onet  # noqa: E402

# element ids for R I A S E C
_EL = ["1.B.1.a", "1.B.1.b", "1.B.1.c", "1.B.1.d", "1.B.1.e", "1.B.1.f"]


def _write_onet(root, occ_interest, titles, zones):
    root.mkdir(parents=True, exist_ok=True)
    lines = ["O*NET-SOC Code\tElement ID\tElement Name\tScale ID\tData Value\tDate\tDomain Source"]
    for code, vec in occ_interest.items():
        for eid, val in zip(_EL, vec, strict=True):
            lines.append(f"{code}\t{eid}\tx\tOI\t{val}\t02/2026\tExpert")
    (root / "Career Interest Types.txt").write_text("\n".join(lines) + "\n")

    occ = ["O*NET-SOC Code\tTitle\tDescription"]
    for code, title in titles.items():
        occ.append(f"{code}\t{title}\ta description")
    (root / "Occupation Data.txt").write_text("\n".join(occ) + "\n")

    jz = ["O*NET-SOC Code\tJob Zone\tDate\tDomain Source"]
    for code, z in zones.items():
        jz.append(f"{code}\t{z}\t2023\tAnalyst")
    (root / "Job Zones.txt").write_text("\n".join(jz) + "\n")

    for name in ("Knowledge.txt", "Essential Skills.txt"):
        rows = [
            "O*NET-SOC Code\tElement ID\tElement Name\tScale ID\tData Value\tN\tSE\tL\tU\tRS\tNR\tDate\tSrc"
        ]
        for code in titles:
            rows.append(f"{code}\t2.C.1.a\tSomething\tIM\t4.2\t10\t0\t0\t0\tN\tn/a\t2023\tX")
        (root / name).write_text("\n".join(rows) + "\n")


def _write_crosswalk(path, rows):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("CIP-SOC")
    ws.append(["CIP2020Code", "CIP2020Title", "SOC2018Code", "SOC2018Title"])
    for r in rows:
        ws.append(r)
    wb.save(path)


@pytest.fixture
def tiny_sources(tmp_path):
    onet_dir = tmp_path / "onet"
    _write_onet(
        onet_dir,
        occ_interest={
            "15-1252.00": [3.6, 6.0, 2.4, 1.8, 1.9, 5.6],  # software dev: I C R
            "25-1021.00": [4.5, 6.0, 2.0, 2.5, 2.0, 4.0],  # cs teacher
            "27-1024.00": [2.5, 2.0, 6.5, 3.0, 3.5, 3.0],  # graphic designer: A
            "27-1013.00": [3.0, 2.5, 6.2, 4.0, 3.0, 2.5],  # fine artist: A
            "11-9199.00": [2.5, 2.5, 2.0, 3.0, 6.0, 5.0],  # junk catch-all
        },
        titles={
            "15-1252.00": "Software Developers",
            "25-1021.00": "Computer Science Teachers, Postsecondary",
            "27-1024.00": "Graphic Designers",
            "27-1013.00": "Fine Artists",
            "11-9199.00": "Managers, All Other",
        },
        zones={"15-1252.00": 4, "25-1021.00": 5, "27-1024.00": 4, "27-1013.00": 4, "11-9199.00": 4},
    )
    xlsx = tmp_path / "cw.xlsx"
    _write_crosswalk(
        xlsx,
        [
            ["11.0701", "Computer Science.", "15-1252", "Software Developers"],
            ["11.0701", "Computer Science.", "25-1021", "CS Teachers"],
            ["11.0701", "Computer Science.", "11-9199", "Managers, All Other"],
            ["50.0409", "Graphic Design.", "27-1024", "Graphic Designers"],
            ["50.0409", "Graphic Design.", "27-1013", "Fine Artists"],
        ],
    )
    return onet_dir, xlsx


def test_junk_soc_dropped_from_crosswalk(tiny_sources):
    _, xlsx = tiny_sources
    cw = load_crosswalk(xlsx)
    assert "11-9199" not in cw["11.0701"]
    assert cw["50.0409"] == ["27-1024", "27-1013"]


def test_build_profiles_produces_sensible_codes(tiny_sources):
    onet_dir, xlsx = tiny_sources
    onet = load_onet(onet_dir)
    cw = load_crosswalk(xlsx)
    majors = [
        {"slug": "cs", "name": "CS", "category": "c", "blurb": "b", "cip": ["11.0701"]},
        {"slug": "gd", "name": "GD", "category": "c", "blurb": "b", "cip": ["50.0409"]},
    ]
    profiles = build_profiles(majors, onet, cw)
    by_slug = {p["slug"]: p for p in profiles}
    assert by_slug["cs"]["riasec"][1] > by_slug["cs"]["riasec"][3]  # I beats S
    # graphic design should lead with Artistic (index 2)
    assert by_slug["gd"]["riasec"].index(max(by_slug["gd"]["riasec"])) == 2


def test_extra_soc_augments_a_thin_major(tiny_sources):
    onet_dir, xlsx = tiny_sources
    onet = load_onet(onet_dir)
    cw = load_crosswalk(xlsx)
    thin = [
        {
            "slug": "t",
            "name": "T",
            "category": "c",
            "blurb": "b",
            "cip": ["99.9999"],
            "extra_soc": ["27-1013"],
        }
    ]
    profiles = build_profiles(thin, onet, cw)
    assert profiles and profiles[0]["n_occupations"] == 1
    assert profiles[0]["thin"] is True
