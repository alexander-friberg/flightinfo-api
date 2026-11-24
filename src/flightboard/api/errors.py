"""What can go wrong when talking to Swedavia, as types the menu can catch and explain."""


class ApiError(Exception):
    """Base class: the API could not give us what we asked for. The message is user-facing."""


class AuthError(ApiError):
    """401/403: the subscription key is missing, wrong or not subscribed to FlightInfo."""


class QuotaExceededError(ApiError):
    """429: either the query endpoint's one-call-per-2-s limit or the monthly quota."""


class ApiUnavailableError(ApiError):
    """5xx, timeout or no connection: Swedavia can't be reached right now."""


class BadQueryError(ApiError):
    """400 on the query endpoint: the OData filter was rejected."""
