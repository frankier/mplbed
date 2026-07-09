from mplbed.html import _impl


def _wrap_markupsafe(func):
    def wrapper(*args, **kwargs):
        from markupsafe import Markup

        return Markup(func(*args, **kwargs))

    return wrapper


figure_html_from_id = _wrap_markupsafe(_impl.figure_html_from_id)
head_content = _wrap_markupsafe(_impl.head_content)
figure_html = _wrap_markupsafe(_impl.figure_html)


__all__ = [
    "figure_html_from_id",
    "figure_html",
    "head_content",
]
