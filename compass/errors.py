"""The exception types meant to reach a human.

Anything that is not a subclass of :class:`CompassError` is a bug and should
crash loudly rather than be turned into a friendly message.
"""

from __future__ import annotations


class CompassError(Exception):
    """Base class for expected, user-facing failures."""

    status_code = 400


class NotFoundError(CompassError):
    """A major (or other resource) was asked for by name and does not exist."""

    status_code = 404


class DataError(CompassError):
    """The bundled data files are missing or malformed."""

    status_code = 500
