import matplotlib

from ._impl import FigureCollector

__all__ = ["FigureCollector", "use"]


def use(ext=True):
    """
    Set the matplib backend to webaggext.

    Parameters
    ----------
    ext : bool, optional
        Use the webaggext backend. `True` by default. Set to `False` to use the webagg backend.
    """
    if ext:
        matplotlib.use("module://mplbed.webaggext._impl")
    else:
        matplotlib.use("webagg")
