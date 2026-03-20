#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@summary: This module provides a basic monitoring check class.

@author:    Frank Brehm
@contact:   frank@brehm-online.com

@copyright: © 2023 - 2026 Frank Brehm, Berlin, Germany
@license: GPL3+
@date:      2026-03-20

"""

from __future__ import print_function

import logging

DEFAULT_TERMINAL_WIDTH = 99
DEFAULT_TERMINAL_HEIGHT = 40

# Own modules
from .argparse_actions import DirectoryOptionAction
from .argparse_actions import LogFileOptionAction
from .errors import ApiError
from .errors import FunctionNotImplementedError
from .errors import InvalidRangeError
from .errors import InvalidRangeValueError
from .errors import MonitoringException
from .errors import MonitoringPerformanceError
from .errors import MonitoringPluginError
from .errors import MonitoringRangeError
from .functions import encode_or_bust
from .functions import is_sequence
from .functions import pp
from .functions import to_bytes
from .functions import to_str
from .functions import to_unicode
from .functions import to_utf8
from .obj import MonitoringObject
from .perf import MonitoringPerformance
from .plugin import MonitoringPlugin
from .range import MonitoringRange
from .range import RangeAlertOn
from .threshold import MonitoringThreshold

LOG = logging.getLogger(__name__)

__author__ = "Frank Brehm <frank@brehm-online.com>"
__copyright__ = "(C) 2026 by Frank Brehm, Berlin"
__version__ = "0.9.0"

__all__ = [
    "ApiError",
    "DirectoryOptionAction",
    "FunctionNotImplementedError",
    "InvalidRangeError",
    "InvalidRangeValueError",
    "LogFileOptionAction",
    "MonitoringException",
    "MonitoringObject",
    "MonitoringPlugin",
    "MonitoringPluginError",
    "MonitoringPerformance",
    "MonitoringPerformanceError",
    "MonitoringRange",
    "MonitoringRangeError",
    "MonitoringThreshold",
    "encode_or_bust",
    "is_sequence",
    "pp",
    "to_bytes",
    "to_str",
    "to_unicode",
    "to_utf8",
]


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
