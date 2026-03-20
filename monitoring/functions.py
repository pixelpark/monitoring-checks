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
import pprint
import shutil

try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence

# Own modules
from . import DEFAULT_TERMINAL_HEIGHT
from . import DEFAULT_TERMINAL_WIDTH


LOG = logging.getLogger(__name__)

__version__ = "0.9.0"


# =============================================================================
def pp(value, indent=4, width=None, depth=None):
    """
    Return a pretty print string of the given value.

    @return: pretty print string
    @rtype: str
    """
    if not width:
        term_size = shutil.get_terminal_size((DEFAULT_TERMINAL_WIDTH, DEFAULT_TERMINAL_HEIGHT))
        width = term_size.columns

    pretty_printer = pprint.PrettyPrinter(indent=indent, width=width, depth=depth)
    return pretty_printer.pformat(value)


# =============================================================================
def to_unicode(obj, encoding="utf-8"):
    """Convert given value to unicode."""
    do_decode = False
    if isinstance(obj, (bytes, bytearray)):
        do_decode = True

    if do_decode:
        obj = obj.decode(encoding)

    return obj


# =============================================================================
def encode_or_bust(obj, encoding="utf-8"):
    """Convert given value to a byte string withe the given encoding."""
    do_encode = False
    if isinstance(obj, str):
        do_encode = True

    if do_encode:
        obj = obj.encode(encoding)

    return obj


# =============================================================================
def to_utf8(obj):
    """Convert given value to a utf-8 encoded byte string."""
    return encode_or_bust(obj, "utf-8")


# =============================================================================
def to_bytes(obj, encoding="utf-8"):
    """Do the same as encode_or_bust()."""
    return encode_or_bust(obj, encoding)


# =============================================================================
def to_str(obj, encoding="utf-8"):
    """Transform he given string-like object into the str-type.

    This will be done according to the current Python version.
    """
    return to_unicode(obj, encoding)


# =============================================================================
def is_sequence(arg):
    """Return, whether the given value is a sequential object, but nat a str."""
    if not isinstance(arg, Sequence):
        return False

    if hasattr(arg, "strip"):
        return False

    return True


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
