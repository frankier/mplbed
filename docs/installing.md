# Installing

Currently you can install this package from Github:

    $ uv add git+https://github.com/frankier/mplbed

Install the optional NiceGUI integration with:

    $ uv add "mplbed[nicegui]"

Then configure the NiceGUI app before `ui.run()` and create an interactive
element with `mplbed.integration.nicegui.matplotlib`.

