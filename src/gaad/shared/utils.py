"""Shared utility helpers."""


def extract_id(resource_name: str) -> str:
    """Extract the last path segment from a resource name.

    Args:
        resource_name: A GA4 resource name string (e.g. "properties/123/dataStreams/456").

    Returns:
        The last path segment (e.g. "456").
    """
    return resource_name.split("/")[-1]


def enum_name(value) -> str:
    """Return the ``.name`` attribute of an enum value, or ``str(value)`` as a fallback.

    Args:
        value: An enum value or any object.

    Returns:
        The string name of the enum, or ``str(value)`` if it has no ``.name``.
    """
    return value.name if hasattr(value, "name") else str(value)
