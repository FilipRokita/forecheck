"""Failures the use cases report to their callers."""


class SourceError(Exception):
    """A data provider could not give what was asked."""


class SourceUnavailableError(SourceError):
    """The provider is down, slow or answered with something unusable."""


class RateLimitedError(SourceError):
    """The provider refuses more requests for now. Retrying today will not help."""
