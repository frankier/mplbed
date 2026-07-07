import matplotlib


def use(ext=True):
    if ext:
        matplotlib.use("module://mplbed.webaggext.impl")
    else:
        matplotlib.use("webagg")
