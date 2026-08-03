from __future__ import annotations


class RadioNewsError(RuntimeError):
    """Base class for expected first-slice failures."""


class ConfigError(RadioNewsError):
    """The fixture-only configuration is invalid."""


class FixtureParseError(RadioNewsError):
    """The packaged RSS fixture cannot be parsed safely."""


class IdentityConflict(RadioNewsError):
    """An existing identity key points to different significant data."""


class SourceConfigurationConflict(IdentityConflict):
    """A source_id was reused with a different logical configuration."""


class MigrationError(RadioNewsError):
    """A database migration could not be applied or verified."""


class MigrationChecksumMismatch(MigrationError):
    """An already-applied migration no longer has the recorded checksum."""
