"""
Shows how an existing application can be integrated with mplbed. This example
uses MNE, an EEG/MNE library, to create a figure and then embeds it in a
Starlette application.
"""
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from mplbed import mplbed_starlette, raw_html

import mne


def homepage_template(*, head, fig):
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {head}
    <title>matplotlib</title>
  </head>

  <body>
    <div style="display: flex">
      <div>
        <h2>Figure</h2>
        {fig}
      </div>
    </div>
  </body>
</html>
"""


def homepage(request):
    sample_data_folder = mne.datasets.sample.data_path()
    sample_data_raw_file = (
        sample_data_folder / "MEG" / "sample" / "sample_audvis_filt-0-40_raw.fif"
    )
    raw = mne.io.read_raw_fif(sample_data_raw_file)
    fig = raw.plot(show=False)

    return Response(
        homepage_template(
            head=raw_html.head_content(),
            fig=raw_html.figure_html(fig, on_close="msg_disable")
        ),
        media_type='text/html'
    )


app = Starlette(
    debug=True,
    routes=[Route('/', homepage)],
)
mplbed_starlette.setup(app)