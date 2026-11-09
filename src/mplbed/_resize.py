def resolve_resize_options(fit: str, resize_handle: bool | None) -> bool:
    """Validate figure sizing options and resolve the resize-handle default."""
    if fit not in {"none", "width", "container"}:
        raise ValueError("fit must be 'none', 'width', or 'container'")
    if resize_handle is None:
        return fit == "none"
    if not isinstance(resize_handle, bool):
        raise TypeError("resize_handle must be True, False, or None")
    return resize_handle
