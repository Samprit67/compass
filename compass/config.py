"""Runtime settings, overridable from the environment (all ``COMPASS_*``)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8791
    top_n: int = 12
    """How many ranked majors to attach explanations to and show by default."""


def settings_from_env() -> Settings:
    s = Settings()
    if v := os.environ.get("COMPASS_HOST"):
        s.host = v
    if v := os.environ.get("COMPASS_PORT"):
        s.port = int(v)
    if v := os.environ.get("COMPASS_TOP_N"):
        s.top_n = int(v)
    return s
