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
import re
from enum import Enum
from numbers import Number

# Own modules
from .errors import InvalidRangeError
from .errors import InvalidRangeValueError
from .errors import MonitoringRangeError
from .obj import MonitoringObject

LOG = logging.getLogger(__name__)

__version__ = "0.9.0"


# =============================================================================
class RangeAlertOn(Enum):
    """Indicate, whether the check value raises an alert, if it is inside or outside the range."""

    OUTSIDE = 0
    INSIDE = 1


# =============================================================================
class MonitoringRange(MonitoringObject):
    """Encapsulation of a Nagios range, how used by some Nagios plugins."""

    match_num_val = r"[+-]?\d+(?:\.\d*)?"
    match_range = r"^(\@)?(?:(" + match_num_val + r"|~)?:)?(" + match_num_val + r")?$"

    re_range = re.compile(match_range)

    # -------------------------------------------------------------------------
    def __init__(self, range_str=None, start=None, end=None, invert_match=False, initialized=None):
        """
        Initialize the MonitoringRange object.

        @raise InvalidRangeError: if the given range_str was invalid
        @raise ValueError: on invalid start or end parameters, if
                           range_str was not given

        @param range_str: the range string of the type 'x:y' to use for
                          initialisation of the object, if given,
                          the parameters start, end and invert_match
                          are not considered
        @type range_str: str
        @param start: the start value of the range, infinite, if None
        @type start: long or int or float or None
        @param end: the end value of the range, infinite, if None
        @type end: long or int or float or None
        @param invert_match: invert check logic - if true, then the check
                             results in true, if the value to check is outside
                             the range, not inside
        @type invert_match: bool
        @param initialized: initialisation of this MonitoringRange object is complete
        @type initialized: bool

        """
        self._start = None
        """
        @ivar: the start value of the range, infinite, if None
        @type: long or float or None
        """

        self._end = None
        """
        @ivar: the end value of the range, infinite, if None
        @type: long or float or None
        """

        self._invert_match = False
        """
        @ivar: invert check logic - if true, then the check results in true,
               if the value to check is outside the range, not inside
        @type: bool
        """

        self._initialized = False
        """
        @ivar: initialisation of this MonitoringRange object is complete
        @type: bool
        """

        if range_str is not None:
            self.parse_range_string(range_str)
            return

        if isinstance(start, int):
            self._start = int(start)
        elif isinstance(start, float):
            self._start = start
        elif start is not None:
            raise ValueError("Start value %r for MonitoringRange is unusable." % (start))

        if isinstance(end, int):
            self._end = int(end)
        elif isinstance(end, float):
            self._end = end
        elif end is not None:
            raise ValueError("End value %r for MonitoringRange is unusable." % (end))

        self._invert_match = bool(invert_match)

        if initialized is not None:
            self._initialized = bool(initialized)
        elif self.start is not None or self.end is not None:
            self._initialized = True

    # -----------------------------------------------------------
    @property
    def start(self):
        """Give the start value of the range, infinite, if None."""
        return self._start

    # -----------------------------------------------------------
    @property
    def start_infinity(self):
        """Give True, if self.start is None, else False."""
        if self.start is None:
            return True
        return False

    # -----------------------------------------------------------
    @property
    def end(self):
        """Give the end value of the range, infinite, if None."""
        return self._end

    # -----------------------------------------------------------
    @property
    def end_infinity(self):
        """Give True, if self.end is None, else False."""
        if self.end is None:
            return True
        return False

    # -----------------------------------------------------------
    @property
    def invert_match(self):
        """
        Invert check logic.

        If true, then the check results in true,
        if the value to check is outside the range, not inside
        """
        return self._invert_match

    # -----------------------------------------------------------
    @property
    def alert_on(self):
        """
        Give RangeAlertOn.OUTSIDE, if self.invert_match is False.

        Otherwise it gives RangeAlertOn.INSIDE.
        """
        if self.invert_match:
            return RangeAlertOn.INSIDE
        else:
            return RangeAlertOn.OUTSIDE

    # -----------------------------------------------------------
    @property
    def is_set(self):
        """Give the initialisation of this object is complete."""
        return self._initialized

    # -----------------------------------------------------------
    @property
    def initialized(self):
        """Give the initialisation of this object is complete."""
        return self._initialized

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string."""
        if not self.initialized:
            return ""

        res = ""
        if self.invert_match:
            res = "@"

        if self.start is None:
            res += "~:"
        elif self.start != 0:
            res += str(self.start) + ":"

        if self.end is not None:
            res += str(self.end)

        return res

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecast into a dictionary.

        @return: structure as dict
        @rtype:  dict
        """
        ret = super(MonitoringRange, self).as_dict()

        ret["alert_on"] = self.alert_on
        ret["end"] = self.end
        ret["end_infinity"] = self.end_infinity
        ret["invert_match"] = self.invert_match
        ret["initialized"] = self.initialized
        ret["range_str"] = str(self)
        ret["start"] = self.start
        ret["start_infinity"] = self.start_infinity

        return ret

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("start={!r}".format(self.start))
        fields.append("end={!r}".format(self.end))
        fields.append("invert_match={!r}".format(self.invert_match))
        fields.append("initialized={!r}".format(self.initialized))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def single_val(self):
        """
        Return a single Number value.

        @return: self.end, if set, else self.start, if set, else None
        @rtype: Number or None

        """
        if not self.initialized:
            return None
        if self.end is not None:
            return self.end
        return self.start

    # -------------------------------------------------------------------------
    def parse_range_string(self, range_str):
        """
        Parse the given range_str.

        Set self.start, self.end and self.invert_match with the appropriate values.

        @raise InvalidRangeError: if the given range_str was invalid

        @param range_str: the range string of the type 'x:y' to use for
                          initialisation of the object
        @type range_str: str or Number
        """
        # range is a Number - all clear
        if isinstance(range_str, Number):
            self._start = 0
            self._end = range_str
            self._initialized = True
            return

        range_str = str(range_str)

        # strip out any whitespace
        rstr = self.re_ws.sub("", range_str)
        # LOG.debug("Parsing given range %r ...", rstr)

        self._start = None
        self._end = None
        self._initialized = False

        # check for valid range definition
        match = self.re_digit.search(rstr)
        if not match:
            raise InvalidRangeError(range_str)

        # LOG.debug("Parsing range with regex %r ...", self.match_range)
        match = self.re_range.search(rstr)
        if not match:
            raise InvalidRangeError(range_str)

        # LOG.debug("Found range parts: %r.", match.groups())
        invert = match.group(1)
        start = match.group(2)
        end = match.group(3)

        if invert is None:
            self._invert_match = False
        else:
            self._invert_match = True

        valid = False

        start_should_infinity = False

        if start is not None:
            if start == "~":
                start_should_infinity = True
                start = None
            else:
                if self.re_dot.search(start):
                    start = float(start)
                else:
                    start = int(start)
                valid = True

        # if start is None:
        #     if start_should_infinity:
        #         LOG.debug("The start is None, but should be infinity.")
        #     else:
        #         LOG.debug("The start is None, but should be NOT infinity.")

        if end is not None:
            if self.re_dot.search(end):
                end = float(end)
            else:
                end = int(end)
            if start is None and not start_should_infinity:
                start = 0
            valid = True

        if not valid:
            raise InvalidRangeError(range_str)

        if start is not None and end is not None and start > end:
            raise InvalidRangeError(range_str)

        self._start = start
        self._end = end
        self._initialized = True

    # -------------------------------------------------------------------------
    def check_range(self, value):
        """
        Invert the result of check().

        Reverse method of self.check(), it provides the exact same behaviour like the
        check_range() method of the Perl Nagios::Plugin::Range object.
        """
        if self.check(value):
            return False
        return True

    # -------------------------------------------------------------------------
    def __contains__(self, value):
        """
        Implement the 'in' operator.

        With the help of this method it's possible to write such things like:

            my_range = MonitoringRange(80)
            ....

            val = 5
            if val in my_range:
                print "Value %r is in range '%s'." % (val, my_range)
            else:
                print "Value %r is NOT in range '%s'." % (val, my_range)

        @param value: the value to check against the current range
        @type value: int or long or float
        """
        return self.check(value)

    # -------------------------------------------------------------------------
    def check(self, value):
        """
        Check the given value against the current range.

        @raise MonitoringRangeError: if the current range is not initialized
        @raise InvalidRangeValueError: if the given value is not a number

        @param value: the value to check against the current range
        @type value: int or long or float

        @return: the value is inside the range or not.
                 if self.invert_match is True, then this retur value is reverted
        @rtype: bool
        """
        if not self.initialized:
            raise MonitoringRangeError("The current MonitoringRange object is not initialized.")

        if not isinstance(value, Number):
            raise InvalidRangeValueError(value)

        my_true = True
        my_false = False
        if self.invert_match:
            my_true = False
            my_false = True

        if self.start is not None and self.end is not None:
            if self.start <= value and value <= self.end:
                return my_true
            else:
                return my_false

        if self.start is not None and self.end is None:
            if value >= self.start:
                return my_true
            else:
                return my_false

        if self.start is None and self.end is not None:
            if value <= self.end:
                return my_true
            else:
                return my_false

        raise MonitoringRangeError(
            "This point should never been reached in checking a value against a range."
        )

        return my_false


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
