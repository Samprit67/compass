# Changelog

All notable changes to Compass. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-09-01

First public version.

### Added

- The 60-item O*NET Interest Profiler Short Form, in the browser and in the
  terminal (`compass quiz`).
- Interest profiles for 112 US undergraduate majors, built from O*NET 31.0 and
  the NCES CIP-to-SOC crosswalk (`compass/data/refresh.py`).
- A 0-100 fit score: a blend of profile-shape correlation and Holland high-point
  agreement, with a dealbreaker penalty.
- Per-recommendation explanation: matched and clashing interests, and the
  individual answers that moved the score, each with a sensitivity delta.
- Web dashboard: quiz flow, ranked results with a hand-drawn interest hexagon,
  per-major detail pages with related majors and labor-market context, light and
  dark themes, answers saved locally.
- REST API (`/api/score`, `/api/majors`, `/api/compare`, ...) and a `rich` CLI
  sharing one serialiser.
- Confidence handling: a flat or half-finished profile is reported as
  low-confidence with an explanatory note.
- `compass data refresh` to rebuild the profiles from the official sources, with
  a `--check` mode for CI.
