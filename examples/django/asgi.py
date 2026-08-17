"""
Runs the mplbed/Django example under Daphne, following the Django
documentation on deploying with ASGI/Daphne:

https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/daphne/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

from mplbed import mplbed_django

application = mplbed_django.setup(get_asgi_application())
