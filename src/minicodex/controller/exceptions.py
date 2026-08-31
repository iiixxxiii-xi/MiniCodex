class MinicodexError(Exception):
    """Base class for minicodex control-flow exceptions."""


class FormatError(MinicodexError):
    """The model produced output that cannot be resolved into a valid action."""


class LimitsExceeded(MinicodexError):
    """A step/token/cost budget was exceeded."""

    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(reason)
