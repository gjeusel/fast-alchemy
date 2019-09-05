"""
isort:skip_file
"""
from .class_builder import BaseClassBuilder  # noqa: F401
from .field_builder import BaseFieldBuilder  # noqa: F401
from .loader_orchestrator import BaseInstanceLoader  # noqa: F401

from .fast import FastAlchemy, FlaskFastAlchemy  # noqa: F401

import os
from pkg_resources import DistributionNotFound, get_distribution

try:
    _dist = get_distribution("fast_alchemy")

    # Normalize case for Windows systems
    dist_loc = os.path.normcase(_dist.location)
    here = os.path.normcase(__file__)

    if not here.startswith(os.path.join(dist_loc, "fast_alchemy")):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = "Version not found."
else:
    __version__ = _dist.version
