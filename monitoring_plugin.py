#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author: Frank Brehm <frank@brehm-online.com
#         Berlin, Germany, 2023
# Date:   2023-02-16
#
# This module provides a basic monitoring check class
#
from __future__ import print_function

import sys
import os
import logging
import argparse
import shutil
import traceback
import datetime
import re

from pathlib import Path

from numbers import Number

if sys.version_info[0] != 3:
    print("This script is intended to use with Python3.", file=sys.stderr)
    print("You are using Python: {0}.{1}.{2}-{3}-{4}.\n".format(
        *sys.version_info), file=sys.stderr)
    sys.exit(1)

if sys.version_info[1] < 6:
    print("A minimal Python version of 3.6 is necessary to execute this script.", file=sys.stderr)
    print("You are using Python: {0}.{1}.{2}-{3}-{4}.\n".format(
        *sys.version_info), file=sys.stderr)
    sys.exit(1)

# Third party modules
import fb_tools

from fb_tools.common import to_bytes

LOG = logging.getLogger(__name__)

DEFAULT_TERMINAL_WIDTH = 99
DEFAULT_TERMINAL_HEIGHT = 40

__author__ = 'Frank Brehm <frank@brehm-online.com>'
__copyright__ = '(C) 2023 by Frank Brehm, Berlin'
__version__ = '0.3.0'


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

    return fb_tools.common.pp(value, indent=indent, width=width, depth=depth)


# =============================================================================
class MonitoringException(Exception):

    pass


# =============================================================================
class MonitoringPerformanceError(MonitoringException):
    """
    Base class for all exception classes and object, raised in this module.
    """

    pass


# =============================================================================
class MonitoringRangeError(MonitoringException):
    """Base exception class for all exceptions in this module."""
    pass


# =============================================================================
class InvalidRangeError(MonitoringRangeError):
    """
    A special exception, which is raised, if an invalid range string was found.
    """

    # -------------------------------------------------------------------------
    def __init__(self, wrong_range):
        """
        Constructor.

        @param wrong_range: the wrong range, whiche lead to this exception.
        @type wrong_range: str

        """

        self.wrong_range = wrong_range

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        return "Wrong range %r." % (self.wrong_range)


# =============================================================================
class InvalidRangeValueError(MonitoringRangeError):
    """
    A special exception, which is raised, if an invalid value should be checked
    against the current range object.
    """

    # -------------------------------------------------------------------------
    def __init__(self, value):
        """
        Constructor.

        @param value: the wrong value, whiche lead to this exception.
        @type value: object

        """

        self.value = value

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        return "Wrong value %r to check against a range." % (self.value)


# =============================================================================
class MonitoringPluginError(MonitoringException):
    """Base exception for an exception inside a monitoring plugin."""

    pass


# =============================================================================
class FunctionNotImplementedError(MonitoringPluginError, NotImplementedError):
    """
    Error class for not implemented functions.
    """

    # -------------------------------------------------------------------------
    def __init__(self, function_name, class_name):
        """
        Constructor.

        @param function_name: the name of the not implemented function
        @type function_name: str
        @param class_name: the name of the class of the function
        @type class_name: str

        """

        self.function_name = function_name
        if not function_name:
            self.function_name = '__unkown_function__'

        self.class_name = class_name
        if not class_name:
            self.class_name = '__unkown_class__'

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting into a string for error output.
        """

        msg = "Function %(func)s() has to be overridden in class '%(cls)s'."
        return msg % {'func': self.function_name, 'cls': self.class_name}


# =============================================================================
class MonitoringObject(object):
    """
    Base object of all classes in this module (except Exceptions).

    It defines some usefull class properties.
    """
    # nested metaclass definition
    class __metaclass__(type):
        def __new__(mcl, classname, bases, classdict):
            cls = type.__new__(mcl, classname, bases, classdict)  # creates class
            cls.static_init()  # call the classmethod
            return cls

    re_digit = re.compile(r'[\d~]')
    re_dot = re.compile(r'\.')
    re_ws = re.compile(r'\s')

    errors = {
        'OK': 0,
        'WARNING': 1,
        'CRITICAL': 2,
        'UNKNOWN': 3,
        'DEPENDENT': 4,
    }
    error_codes = {}

    # -------------------------------------------------------------------------
    @classmethod
    def static_init(cls):

        cls.error_codes = {}
        for name in cls.errors.keys():
            code = cls.errors[name]
            cls.error_codes[code] = name

    # -------------------------------------------------------------------------
    @property
    def status_ok(self):
        """The numerical value of OK."""
        return self.errors['OK']

    # -------------------------------------------------------------------------
    @property
    def status_warning(self):
        """The numerical value of WARNING."""
        return self.errors['WARNING']

    # -------------------------------------------------------------------------
    @property
    def status_critical(self):
        """The numerical value of CRITICAL."""
        return self.errors['CRITICAL']

    # -------------------------------------------------------------------------
    @property
    def status_unknown(self):
        """The numerical value of UNKNOWN."""
        return self.errors['UNKNOWN']

    # -------------------------------------------------------------------------
    @property
    def status_dependent(self):
        """The numerical value of DEPENDENT."""
        return self.errors['DEPENDENT']


# =============================================================================
class MonitoringRange(MonitoringObject):
    """
    Encapsulation of a Nagios range, how used by some Nagios plugins.
    """

    match_num_val = r'[+-]?\d+(?:\.\d*)?'
    match_range = r'^(\@)?(?:(' + match_num_val + r'|~)?:)?(' + match_num_val + r')?$'

    re_range = re.compile(match_range)

    # -------------------------------------------------------------------------
    def __init__(
        self, range_str=None, start=None, end=None,
            invert_match=False, initialized=None):
        """
        Initialisation of the MonitoringRange object.

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
            raise ValueError(
                "Start value %r for MonitoringRange is unusable." % (start))

        if isinstance(end, int):
            self._end = int(end)
        elif isinstance(end, float):
            self._end = end
        elif end is not None:
            raise ValueError(
                "End value %r for MonitoringRange is unusable." % (end))

        self._invert_match = bool(invert_match)

        if initialized is not None:
            self._initialized = bool(initialized)
        elif self.start is not None or self.end is not None:
            self._initialized = True

    # -----------------------------------------------------------
    @property
    def start(self):
        """The start value of the range, infinite, if None."""
        return self._start

    # -----------------------------------------------------------
    @property
    def end(self):
        """The end value of the range, infinite, if None."""
        return self._end

    # -----------------------------------------------------------
    @property
    def invert_match(self):
        """
        Invert check logic - if true, then the check results in true,
        if the value to check is outside the range, not inside
        """
        return self._invert_match

    # -----------------------------------------------------------
    @property
    def is_set(self):
        """The initialisation of this object is complete."""
        return self._initialized

    # -----------------------------------------------------------
    @property
    def initialized(self):
        """The initialisation of this object is complete."""
        return self._initialized

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string."""

        if not self.initialized:
            return ''

        res = ''
        if self.invert_match:
            res = '@'

        if self.start is None:
            res += '~:'
        elif self.start != 0:
            res += str(self.start) + ':'

        if self.end is not None:
            res += str(self.end)

        return res

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
            '__class__': self.__class__.__name__,
            'start': self.start,
            'end': self.end,
            'invert_match': self.invert_match,
            'initialized': self.initialized,
        }

        return d

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = '<MonitoringRange(start=%r, end=%r, invert_match=%r, initialized=%r)>' % (
            self.start, self.end, self.invert_match, self.initialized)

        return out

    # -------------------------------------------------------------------------
    def single_val(self):
        """
        Returns a single Number value.

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
        Parsing the given range_str and set self.start, self.end and
        self.invert_match with the appropriate values.

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
        rstr = self.re_ws.sub('', range_str)
        LOG.debug("Parsing given range %r ...", rstr)

        self._start = None
        self._end = None
        self._initialized = False

        # check for valid range definition
        match = self.re_digit.search(rstr)
        if not match:
            raise InvalidRangeError(range_str)

        LOG.debug("Parsing range with regex %r ...", self.match_range)
        match = self.re_range.search(rstr)
        if not match:
            raise InvalidRangeError(range_str)

        LOG.debug("Found range parts: %r.", match.groups())
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
            if start == '~':
                start_should_infinity = True
                start = None
            else:
                if self.re_dot.search(start):
                    start = float(start)
                else:
                    start = int(start)
                valid = True

        if start is None:
            if start_should_infinity:
                LOG.debug("The start is None, but should be infinity.")
            else:
                LOG.debug("The start is None, but should be NOT infinity.")

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
        """Recverse method of self.check(), it inverts the result of check()
        to provide the exact same behaviour like the check_range() method
        of the Perl Nagios::Plugin::Range object."""

        if self.check(value):
            return False
        return True

    # -------------------------------------------------------------------------
    def __contains__(self, value):
        """
        Special method to implement the 'in' operator. With the help of this
        method it's possible to write such things like::

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
        Checks the given value against the current range.

        @raise MonitoringRangeError: if the current range is not initialized
        @raise InvalidRangeValueError: if the given value is not a number

        @param value: the value to check against the current range
        @type value: int or long or float

        @return: the value is inside the range or not.
                 if self.invert_match is True, then this retur value is reverted
        @rtype: bool

        """

        if not self.initialized:
            raise MonitoringRangeError(
                "The current MonitoringRange object is not initialized.")

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
            "This point should never been reached in "
            "checking a value against a range.")

        return my_false


# =============================================================================
class MonitoringPerformance(MonitoringObject):
    """
    A class for handling monitoring performance data.

    """

    # Some regular expressions ...
    re_not_word = re.compile(r'\W')
    re_trailing_semicolons = re.compile(r';;$')
    re_slash = re.compile(r'/')
    re_leading_slash = re.compile(r'^/')
    re_comma = re.compile(r',')

    pat_value = r'[-+]?[\d\.,]+'
    pat_value_neg_inf = pat_value + r'|~'
    """pattern for a range with a negative infinity"""

    pat_perfstring = r"^'?([^'=]+)'?=(" + pat_value + r')([\w%]*);?'
    pat_perfstring += r'(' + pat_value_neg_inf + r'\:?' + pat_value + r'?)?;?'
    pat_perfstring += r'(' + pat_value_neg_inf + r'\:?' + pat_value + r'?)?;?'
    pat_perfstring += r'(' + pat_value + r'?)?;?'
    pat_perfstring += r'(' + pat_value + r'?)?'

    re_perfstring = re.compile(pat_perfstring)

    re_perfoutput = re.compile(r'^(.*?=.*?)\s+')

    # -------------------------------------------------------------------------
    def __init__(
        self, label, value, uom=None, threshold=None, warning=None, critical=None,
            min_data=None, max_data=None):
        """
        Initialisation of the MonitoringPerformance object.

        @param label: the label of the performance data, mandantory
        @type label: str
        @param value: the value of the performance data, mandantory
        @type value: Number
        @param uom: the unit of measure
        @type uom: str or None
        @param threshold: an object for the warning and critical thresholds
                          if set, it overrides the warning and critical parameters
        @type threshold: MonitoringThreshold or None
        @param warning: a range for the warning threshold,
                        ignored, if threshold is given
        @type warning: MonitoringRange, str, Number or None
        @param critical: a range for the critical threshold,
                        ignored, if threshold is given
        @type critical: MonitoringRange, str, Number or None
        @param min_data: the minimum data for performance output
        @type min_data: Number or None
        @param max_data: the maximum data for performance output
        @type max_data: Number or None

        """

        self._label = str(label).strip()
        """
        @ivar: the label of the performance data
        @type: str
        """
        if label is None or self._label == '':
            raise MonitoringPerformanceError(
                "Empty label %r for MonitoringPerformance given." % (label))

        self._value = value
        """
        @ivar: the value of the performance data
        @type: Number
        """
        if not isinstance(value, Number):
            raise MonitoringPerformanceError(
                "Wrong value %r for MonitoringPerformance given." % (value))

        self._uom = ''
        """
        @ivar: the unit of measure
        @type: str
        """
        if uom is not None:
            # remove all whitespaces
            self._uom = self.re_ws.sub('', str(uom))

        warn_range = MonitoringRange()
        if warning:
            warn_range = MonitoringRange(warning)

        crit_range = MonitoringRange()
        if critical:
            crit_range = MonitoringRange(critical)

        self._threshold = None
        """
        @ivar: the threshold object containing the warning and the
               critical threshold
        @type: MonitoringThreshold
        """
        if isinstance(threshold, MonitoringThreshold):
            self._threshold = threshold
        elif threshold is not None:
            raise MonitoringPerformanceError(
                "The given threshold %r is neither None nor a MonitoringThreshold object." % (
                    threshold))
        else:
            self._threshold = MonitoringThreshold(
                warning=warn_range,
                critical=crit_range
            )

        self._min_data = None
        """
        @ivar: the minimum data for performance output
        @type: Number or None
        """
        if min_data is not None:
            if not isinstance(min_data, Number):
                raise MonitoringPerformanceError(
                    "The given min_data %r is not None and not a Number." % (min_data))
            else:
                self._min_data = min_data

        self._max_data = None
        """
        @ivar: the maximum data for performance output
        @type: Number or None
        """
        if max_data is not None:
            if not isinstance(max_data, Number):
                raise MonitoringPerformanceError(
                    "The given max_data %r is not None and not a Number." % (max_data))
            else:
                self._max_data = max_data

    # -----------------------------------------------------------
    @property
    def label(self):
        """The label of the performance data."""
        return self._label

    # -----------------------------------------------------------
    @property
    def clean_label(self):
        """Returns a "clean" label for use as a dataset name in RRD, ie, it
        converts characters that are not [a-zA-Z0-9_] to _."""

        name = self.label
        if name == '/':
            name = "root"
        elif self.re_slash.search(name):
            name = self.re_leading_slash.sub('', name)
            name = self.re_slash.sub('_', name)

        name = self.re_not_word.sub('_', name)
        return name

    # -----------------------------------------------------------
    @property
    def rrdlabel(self):
        """Returns a string based on 'label' that is suitable for use as
        dataset name of an RRD i.e. munges label to be 1-19 characters long
        with only characters [a-zA-Z0-9_]."""

        return self.clean_label[0:19]

    # -----------------------------------------------------------
    @property
    def value(self):
        """The value of the performance data."""
        return self._value

    # -----------------------------------------------------------
    @property
    def uom(self):
        """The unit of measure."""
        return self._uom

    # -----------------------------------------------------------
    @property
    def threshold(self):
        """The threshold object containing the warning and the critical threshold."""
        return self._threshold

    # -----------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold for performance data."""
        return self._threshold.warning

    # -----------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold for performance data."""
        return self._threshold.critical

    # -----------------------------------------------------------
    @property
    def min_data(self):
        """The minimum data for performance output."""
        return self._min_data

    # -----------------------------------------------------------
    @property
    def max_data(self):
        """The maximum data for performance output."""
        return self._max_data

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = (
            '<MonitoringPerformance(label=%r, value=%r, uom=%r, threshold=%r, '
            'min_data=%r, max_data=%r)>' % (
                self.label, self.value, self.uom, self.threshold, self.min_data, self.max_data))

        return out

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
            '__class__': self.__class__.__name__,
            'label': self.label,
            'value': self.value,
            'uom': self.uom,
            'threshold': self.threshold.as_dict(),
            'min_data': self.min_data,
            'max_data': self.max_data,
            'status': self.status(),
        }

        return d

    # -------------------------------------------------------------------------
    def status(self):
        """
        Returns the Monitoring state of the current value against the thresholds

        @return: Monitoring.state
        @rtype: int

        """

        return self.threshold.get_status([self.value])

    # -------------------------------------------------------------------------
    @staticmethod
    def _nvl(value):
        """Map None to ''."""

        if value is None:
            return ''
        return str(value)

    # -------------------------------------------------------------------------
    def perfoutput(self):
        """
        Outputs the data in MonitoringPlugin perfdata format i.e.
        label=value[uom];[warn];[crit];[min];[max].

        """

        # Add quotes if label contains a space character
        label = self.label
        if self.re_ws.search(label):
            label = "'" + self.label + "'"

        out = "%s=%s%s;%s;%s;%s;%s" % (
            label,
            self.value,
            self._nvl(self.uom),
            self._nvl(self.warning),
            self._nvl(self.critical),
            self._nvl(self.min_data),
            self._nvl(self.max_data),
        )

        # omit trailing ;;
        out = self.re_trailing_semicolons.sub('', out)

        return out

    # -------------------------------------------------------------------------
    @classmethod
    def _parse(cls, string):

        LOG.debug("Parsing string %r for performance data", string)
        match = cls.re_perfstring.search(string)
        if not match:
            LOG.warn("String %r was not a valid performance output.", string)
            return None

        LOG.debug("Found parsed performance output: %r", match.groups())

        if match.group(1) is None or match.group(1) == '':
            LOG.warn(
                "String %r was not a valid performance output, no label found.", string)
            return None

        if match.group(2) is None or match.group(2) == '':
            LOG.warn(
                "String %r was not a valid performance output, no value found.", string)
            return None

        info = []
        i = 0
        for field in match.groups():
            val = None
            if i in (0, 2):
                val = field.strip()
            elif field is not None:
                val = cls.re_comma.sub('.', field)
                try:
                    if cls.re_dot.search(field):
                        val = float(field)
                    else:
                        val = int(field)
                except ValueError as e:
                    LOG.warn(
                        "Invalid performance value %r found: %s", field, str(e))
                    return None
            info.append(val)
            i += 1

        LOG.debug("Found parfdata fields: %r", info)

        obj = cls(
            label=info[0], value=info[1], uom=info[2], warning=info[3],
            critical=info[4], min_data=info[5], max_data=info[6])

        return obj

    # -------------------------------------------------------------------------
    @classmethod
    def parse_perfstring(cls, perfstring):
        """
        Parses the given string with performance output strings and gives
        back a list of MonitoringPerformance objects from all successful parsed
        performance output strings.

        If there is an error parsing the string - which may consists of
        several sets of data -  will return a list with all the
        successfully parsed sets.

        If values are input with commas instead of periods, due to different
        locale settings, then it will still be parsed, but the commas will
        be converted to periods.

        @param perfstring: the string with performance output strings to parse
        @type perfstring: str

        @return: list of MonitoringPerformance objects
        @rtype: list

        """

        ps = perfstring.strip()
        perfs = []

        while ps:

            obj = None
            ps = ps.strip()
            if ps == '':
                break

            if ps.count('=') > 1:

                # If there is more than 1 equals sign, split it out and
                # parse individually
                match = cls.re_perfoutput.search(ps)
                if match:
                    obj = match.group(1)
                    ps = cls.re_perfoutput.sub('', ps, 1)
                    obj = cls._parse(ps)
                else:
                    # This could occur if perfdata was soemthing=value=
                    LOG.warn("Didn't found performance data in %r.", ps)
                    break

            else:
                obj = cls._parse(ps)
                ps = ''

            if obj:
                perfs.append(obj)

        LOG.debug("Found performance data: %r", perfs)
        return perfs


# =============================================================================
class MonitoringThreshold(MonitoringObject):
    """
    Encapsulation of a Nagios threshold, how used by some Nagios plugins.
    """

    # -------------------------------------------------------------------------
    def __init__(self, warning=None, critical=None):
        """
        Initialisation of the MonitoringThreshold object.

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
        if value is None or (
                isinstance(value, str) and value == ''):
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
        if value is None or (
                isinstance(value, str) and value == ''):
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

        d = {
            '__class__': self.__class__.__name__,
            'warning': None,
            'critical': None,
        }

        if self.warning:
            d['warning'] = self.warning.as_dict()

        if self.critical:
            d['critical'] = self.critical.as_dict()

        return d

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = '<MonitoringThreshold(warning=%r, critical=%r)>' % (
            self.warning, self.critical)

        return out

    # -------------------------------------------------------------------------
    def set_thresholds(self, warning=None, critical=None):
        """
        Re-Initialisation of the MonitoringThreshold object.

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
        Checks the given values against the critical and the warning range.

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
class MonitoringPlugin(MonitoringObject):

    # -------------------------------------------------------------------------
    @classmethod
    def get_generic_appname(cls, appname=None):

        if appname:
            v = str(appname).strip()
            if v:
                return v
        aname = sys.argv[0]
        aname = re.sub(r'\.py$', '', aname, flags=re.IGNORECASE)
        return os.path.basename(aname)

    # -------------------------------------------------------------------------
    def __init__(
            self, appname=None, verbose=0, version=__version__, base_dir=None,
            description=None, initialized=False):

        self._appname = self.get_generic_appname(appname)
        self._version = version
        self._verbose = int(verbose)
        self._initialized = False
        self._base_dir = None
        self._status = 3
        self._status_msg = None
        self.perf_data = []

        self.messages = {
            'warning': [],
            'critical': [],
            'ok': [],
        }

        if base_dir:
            self.base_dir = Path(base_dir)
        if not self._base_dir:
            self._base_dir = Path(os.getcwd()).resolve()

        self._description = description
        """
        @ivar: a short text describing the application
        @type: str
        """

        if not self.description:
            self._description = "Unknown and undescriped monitoring plugin."

        self._init_arg_parser()

    # -------------------------------------------------------------------------
    def post_init(self):

        self._perform_arg_parser()
        self.init_logging()

    # -------------------------------------------------------------------------
    def handle_error(
            self, error_message=None, exception_name=None, do_traceback=False):

        msg = str(error_message).strip()
        if not msg:
            msg = 'undefined error.'
        title = None

        if isinstance(error_message, Exception):
            title = error_message.__class__.__name__
        else:
            if exception_name is not None:
                title = exception_name.strip()
            else:
                title = 'Exception happened'
        msg = title + ': ' + msg

        root_log = logging.getLogger()
        has_handlers = False
        if root_log.handlers:
            has_handlers = True

        if has_handlers:
            LOG.error(msg)
            if do_traceback:
                LOG.error(traceback.format_exc())
        else:
            curdate = datetime.datetime.now()
            curdate_str = "[" + curdate.isoformat(' ') + "]: "
            msg = curdate_str + msg + "\n"
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr.buffer.write(to_bytes(msg))
            else:
                sys.stderr.write(msg)
            if do_traceback:
                traceback.print_exc()

        return

    # -----------------------------------------------------------
    @property
    def appname(self):
        """The name of the current running application."""
        if hasattr(self, '_appname'):
            return self._appname
        return os.path.basename(sys.argv[0])

    @appname.setter
    def appname(self, value):
        if value:
            v = str(value).strip()
            if v:
                self._appname = v

    # -----------------------------------------------------------
    @property
    def version(self):
        """The version string of the current object or application."""
        return getattr(self, '_version', __version__)

    # -----------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    @verbose.setter
    def verbose(self, value):
        v = int(value)
        if v >= 0:
            self._verbose = v
        else:
            LOG.warning("Wrong verbose level {!r}, must be >= 0".format(value))

    # -----------------------------------------------------------
    @property
    def initialized(self):
        """The initialisation of this object is complete."""
        return getattr(self, '_initialized', False)

    @initialized.setter
    def initialized(self, value):
        self._initialized = bool(value)

    # -----------------------------------------------------------
    @property
    def base_dir(self):
        """The base directory used for different purposes."""
        return self._base_dir

    @base_dir.setter
    def base_dir(self, value):
        base_dir_path = Path(value)
        if str(base_dir_path).startswith('~'):
            base_dir_path = base_dir_path.expanduser()
        if not base_dir_path.exists():
            msg = "Base directory {!r} does not exists.".format(str(value))
            self.handle_error(msg, self.appname)
        elif not base_dir_path.is_dir():
            msg = "Path for base directory {!r} is not a directory.".format(str(value))
            self.handle_error(msg, self.appname)
        else:
            self._base_dir = base_dir_path

    # -----------------------------------------------------------
    @property
    def description(self):
        """Get a short text describing the application."""
        return self._description

    # -----------------------------------------------------------
    @property
    def status(self):
        """The current numeric status of the plugin."""
        return self._status

    @status.setter
    def status(self, value):
        val = int(value)
        if val < 0 or val > 3:
            raise MonitoringException(
                "Invalid state {!r} given - mus be >= 0 an <= 4.".format(value))
        self._status = val

    # -----------------------------------------------------------
    @property
    def status_msg(self):
        """The status message to show on output."""
        return self._status_msg

    @status_msg.setter
    def status_msg(self, value):
        if value is None:
            self._status_msg = None
            return
        val = str(value).strip()
        if val:
            self._status_msg = val
        else:
            self._status_msg = None

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        """

        return pp(self.as_dict(short=True))

    # -------------------------------------------------------------------------
    def as_dict(self, short=True):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = {}
        for key in self.__dict__:
            if short and key.startswith('_') and not key.startswith('__'):
                continue
            res[key] = self.__dict__[key]

        res['__class_name__'] = self.__class__.__name__
        res['appname'] = self.appname
        res['version'] = self.version
        res['verbose'] = self.verbose
        res['description'] = self.verbose
        res['initialized'] = self.initialized
        res['base_dir'] = self.base_dir
        res['state'] = self.state
        res['status_msg'] = self.status_msg
        res['perf_data'] = []
        for pdata in self.perf_data:
            res['perf_data'].append(pdata.as_dict())

        return res

    # -------------------------------------------------------------------------
    def _init_arg_parser(self):
        """
        Local called method to initiate the argument parser.

        @raise PBApplicationError: on some errors

        """

        self.arg_parser = argparse.ArgumentParser(
            prog=self.appname,
            description=self.description,
            add_help=False,
        )

        self.init_arg_parser()

        general_group = self.arg_parser.add_argument_group('General_options')

        general_group.add_argument(
            "-v", "--verbose", action="count", dest='verbose',
            help='Increase the verbosity level',
        )

        general_group.add_argument(
            "-h", "--help", action='help', dest='help',
            help='Show this help message and exit.'
        )

        general_group.add_argument(
            "--usage", action='store_true', dest='usage',
            help="Display brief usage message and exit."
        )

        v_msg = "Version of %(prog)s: {}".format(self.version)
        general_group.add_argument(
            "-V", '--version', action='version', version=v_msg,
            help="Show program's version number and exit."
        )

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        '''Can be overridden ...'''
        pass

    # -------------------------------------------------------------------------
    def _perform_arg_parser(self):

        self.args = self.arg_parser.parse_args()

        if self.args.usage:
            self.arg_parser.print_usage(sys.stdout)
            self.exit(0)

        if self.args.verbose is not None and self.args.verbose > self.verbose:
            self.verbose = self.args.verbose

        self.perform_arg_parser()

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):
        '''Can be overridden ...'''
        pass

    # -------------------------------------------------------------------------
    def add_perfdata(
        self, label, value, uom=None, threshold=None, warning=None, critical=None,
            min_data=None, max_data=None):
        """
        Adding a MonitoringPerformance object to self.perf_data.

        @param label: the label of the performance data, mandantory
        @type label: str
        @param value: the value of the performance data, mandantory
        @type value: Number
        @param uom: the unit of measure
        @type uom: str or None
        @param threshold: an object for the warning and critical thresholds
                          if set, it overrides the warning and critical parameters
        @type threshold: MonitoringThreshold or None
        @param warning: a range for the warning threshold,
                        ignored, if threshold is given
        @type warning: MonitoringRange, str, Number or None
        @param critical: a range for the critical threshold,
                        ignored, if threshold is given
        @type critical: MonitoringRange, str, Number or None
        @param min_data: the minimum data for performance output
        @type min_data: Number or None
        @param max_data: the maximum data for performance output
        @type max_data: Number or None

        """

        pdata = MonitoringPerformance(
            label=label, value=value, uom=uom, threshold=threshold,
            warning=warning, critical=critical, min_data=min_data, max_data=max_data,
        )

        self.perf_data.append(pdata)

    # -------------------------------------------------------------------------
    def nagios_exit(self, status_code, status_msg):

        if status_code not in self.error_codes:
            ocode = status_code
            status_code = 3
            status_msg += ' (Unknown status code {})'.format(ocode)

        status_name = self.error_codes[status_code]

        msg = "{sn} - {app}: {msg}".format(
            sn=status_name, app=self.appname, msg=status_msg)
        print(msg)
        sys.exit(status_code)

    # -------------------------------------------------------------------------
    def init_logging(self):
        """
        Initialize the logger object.
        It creates a colored loghandler with all output to STDERR.
        Maybe overridden in descendant classes.

        @return: None
        """

        log_level = logging.INFO
        if self.verbose:
            log_level = logging.DEBUG

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # create formatter
        format_str = ''
        if self.verbose:
            format_str = '[%(asctime)s]: '
        format_str += self.appname + ': '
        if self.verbose:
            if self.verbose > 1:
                format_str += '%(name)s(%(lineno)d) %(funcName)s() '
            else:
                format_str += '%(name)s '
        format_str += '%(levelname)s - %(message)s'
        formatter = logging.Formatter(format_str)

        # create log handler for console output
        lh_console = logging.StreamHandler(sys.stderr)
        lh_console.setLevel(log_level)
        lh_console.setFormatter(formatter)

        root_logger.addHandler(lh_console)

        return

    # -------------------------------------------------------------------------
    def all_perfoutput(self):
        """Generates a string with all formatted performance data."""

        if not self.perf_data:
            return ''

        return ' '.join([x.perfoutput() for x in self.perf_data])

    # -------------------------------------------------------------------------
    def die(self, message, no_status_line=False):
        """Exiting with status 'unknown' and without outputting performance data."""

        self.exit(self.status_unknown, message=message, no_status_line=no_status_line)

    # -------------------------------------------------------------------------
    def exit(self, status=None, message=None, no_status_line=False):
        """Exit the current application."""

        if status is None:
            status = self.status
        else:
            status = int(status)
        code = self.error_codes[status]

        if message is None:
            message = self.status_msg
        else:
            if isinstance(message, list) or isinstance(message, tuple):
                message = ' '.join(lambda x: str(x).strip(), message)
            else:
                message = str(message).strip()

        # Setup output
        output = ''
        if no_status_line:
            if message:
                output = message
            else:
                output = "[no message]"
        else:
            output = self.appname + " " + code
            if message:
                output += " - " + message
            pdata = self.all_perfoutput()
            if pdata:
                output += " | " + pdata

        print(output)
        sys.exit(status)

    # -------------------------------------------------------------------------
    def pre_run(self):
        """
        Execute some actions before the main routine.

        This is a dummy method an could be overwritten by descendant classes.
        """
        pass

    # -------------------------------------------------------------------------
    def run(self):
        """
        Execute the main actions of the application.

        Dummy function as main routine.

        MUST be overwritten by descendant classes.
        """
        raise FunctionNotImplementedError('run()', self.__class__.__name__)

    # -------------------------------------------------------------------------
    def _run(self):
        """
        Execute the main actions of the application.

        The visible start point of this object.

        @return: None
        """
        if not self.initialized:
            self.handle_error("The application is not completely initialized.", '', True)
            self.exit(9)

        try:
            self.pre_run()
        except Exception as e:
            self.handle_error(str(e), e.__class__.__name__, True)
            self.exit(98)

        if not self.initialized:
            raise MonitoringException(
                "Object {!r} seems not to be completely initialized.".format(
                    self.__class__.__name__))

        try:
            self.run()
        except MonitoringException as e:
            self.die(str(e), no_status_line=True)
        except Exception as e:
            self.handle_error(str(e), e.__class__.__name__, True)
            self.status = self.status_unknown
            self.die(str(e), no_status_line=True)

        try:
            self.post_run()
        except MonitoringException as e:
            self.die(str(e), no_status_line=True)
        except Exception as e:
            self.handle_error(str(e), e.__class__.__name__, True)
            self.status = self.status_unknown
            self.die(str(e), no_status_line=True)

        self.exit()

    # -------------------------------------------------------------------------
    def post_run(self):
        """
        Execute some actions after the main routine.

        This is a dummy method an could be overwritten by descendant classes.
        """

        pass

    # -------------------------------------------------------------------------
    def __call__(self):
        return self._run()


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
