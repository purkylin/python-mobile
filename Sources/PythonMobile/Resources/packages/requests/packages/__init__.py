"""Compatibility namespace exposed by the standard Requests package."""

import sys

import urllib3


# Requests exposes urllib3 through requests.packages for older integrations.
# Keep the bundled urllib3 module as the implementation so imports such as
# requests.packages.urllib3.util.retry continue to work without duplicating it.
sys.modules.setdefault(__name__ + ".urllib3", urllib3)

