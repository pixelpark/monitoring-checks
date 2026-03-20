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

import copy
import logging
import re

# Own modules

LOG = logging.getLogger(__name__)

__version__ = "0.9.0"

# =============================================================================
def reverse_error_codes(errors):
    """Generate the reversed errors hash for a MonitoringObject."""
    error_codes = {}

    for name in errors.keys():
        code = errors[name]
        error_codes[code] = name

    return error_codes


# =============================================================================
class MonitoringObject(object):
    """
    Base object of all classes in this module (except Exceptions).

    It defines some usefull class properties.
    """

    re_digit = re.compile(r"[\d~]")
    re_dot = re.compile(r"\.")
    re_ws = re.compile(r"\s")

    errors = {
        "OK": 0,
        "WARNING": 1,
        "CRITICAL": 2,
        "UNKNOWN": 3,
        "DEPENDENT": 4,
    }
    error_codes = reverse_error_codes(errors)

    # -------------------------------------------------------------------------
    @property
    def status_ok(self):
        """Give the numerical value of OK."""
        return self.errors["OK"]

    # -------------------------------------------------------------------------
    @property
    def status_warning(self):
        """Give the numerical value of WARNING."""
        return self.errors["WARNING"]

    # -------------------------------------------------------------------------
    @property
    def status_critical(self):
        """Give the numerical value of CRITICAL."""
        return self.errors["CRITICAL"]

    # -------------------------------------------------------------------------
    @property
    def status_unknown(self):
        """Give the numerical value of UNKNOWN."""
        return self.errors["UNKNOWN"]

    # -------------------------------------------------------------------------
    @property
    def status_dependent(self):
        """Give the numerical value of DEPENDENT."""
        return self.errors["DEPENDENT"]

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecast into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """
        ret = {
            "__class__": self.__class__.__name__,
            "errors": copy.copy(self.errors),
            "error_codes": copy.copy(self.error_codes),
            "status_ok": self.status_ok,
            "status_warning": self.status_warning,
            "status_critical": self.status_critical,
            "status_unknown": self.status_unknown,
            "status_dependent": self.status_dependent,
        }

        return ret


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
