#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@summary: This module provides a basic monitoring check class.

@author:    Frank Brehm
@contact:   frank@brehm-online.com

@copyright: © 2023 - 2026 Frank Brehm, Berlin, Germany
@license: GPL3+
@date:      2026-03-13

"""

from __future__ import print_function

import logging
from numbers import Number

# Own modules
from .obj import MonitoringObject
from .range import MonitoringRange

LOG = logging.getLogger(__name__)

__version__ = "0.9.0"

# =============================================================================
class MonitoringThreshold(MonitoringObject):
    """Encapsulation of a Nagios threshold, how used by some Nagios plugins."""

    # -------------------------------------------------------------------------
    def __init__(self, warning=None, critical=None):
        """
        Initialise the MonitoringThreshold object.

        @param warning: the warning threshold
        @type warning: str, int, long, float or MonitoringRange
        @param critical: the critical threshold
        @type critical: str, int, long, float or MonitoringRange
        """
        self._warning = MonitoringRange()
        """
        @ivar: the warning threshold
        @type: MonitoringRange
        """

        self._critical = MonitoringRange()
        """
        @ivar: the critical threshold
        @type: MonitoringRange
        """

        self.set_thresholds(warning=warning, critical=critical)

    # -----------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold."""
        return self._warning

    @warning.setter
    def warning(self, value):
        if value is None or (isinstance(value, str) and value == ""):
            self._warning = MonitoringRange()
            return

        if isinstance(value, MonitoringRange):
            self._warning = value
            return

        if isinstance(value, int) or isinstance(value, int):
            value = "%d" % (value)
        elif isinstance(value, float):
            value = "%f" % (value)

        self._warning = MonitoringRange(value)

    # -----------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold."""
        return self._critical

    @critical.setter
    def critical(self, value):
        if value is None or (isinstance(value, str) and value == ""):
            self._critical = MonitoringRange()
            return

        if isinstance(value, MonitoringRange):
            self._critical = value
            return

        if isinstance(value, int) or isinstance(value, int):
            value = "%d" % (value)
        elif isinstance(value, float):
            value = "%f" % (value)

        self._critical = MonitoringRange(value)

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """
        ret = super(MonitoringThreshold, self).as_dict()

        ret["warning"] = self.warning.as_dict()
        ret["critical"] = self.critical.as_dict()

        return ret

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<MonitoringThreshold(warning=%r, critical=%r)>" % (self.warning, self.critical)

        return out

    # -------------------------------------------------------------------------
    def set_thresholds(self, warning=None, critical=None):
        """
        Re-initialise the MonitoringThreshold object.

        @param warning: the warning threshold
        @type warning: str, int, long, float or MonitoringRange
        @param critical: the critical threshold
        @type critical: str, int, long, float or MonitoringRange
        """
        self.warning = warning
        self.critical = critical

    # -------------------------------------------------------------------------
    def get_status(self, values):
        """
        Check the given values against the critical and the warning range.

        @param values: a list with values to check against the critical
                       and warning range property
        @type values: int or long or float or list of them

        @return: a nagios state
        @rtype: int
        """
        if isinstance(values, Number):
            values = [values]

        if self.critical.initialized:
            for value in values:
                if value not in self.critical:
                    return self.status_critical

        if self.warning.initialized:
            for value in values:
                if value not in self.warning:
                    return self.status_warning

        return self.status_ok


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
