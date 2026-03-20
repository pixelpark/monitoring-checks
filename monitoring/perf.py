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
from numbers import Number

# Own modules
from .errors import MonitoringPerformanceError
from .obj import MonitoringObject
from .range import MonitoringRange
from .threshold import MonitoringThreshold

LOG = logging.getLogger(__name__)

__version__ = "0.9.0"


# =============================================================================
class MonitoringPerformance(MonitoringObject):
    """A class for handling monitoring performance data."""

    # Some regular expressions ...
    re_not_word = re.compile(r"\W")
    re_trailing_semicolons = re.compile(r";;$")
    re_slash = re.compile(r"/")
    re_leading_slash = re.compile(r"^/")
    re_comma = re.compile(r",")

    pat_value = r"[-+]?[\d\.,]+"
    pat_value_neg_inf = pat_value + r"|~"
    """pattern for a range with a negative infinity"""

    pat_perfstring = r"^'?([^'=]+)'?=(" + pat_value + r")([\w%]*);?"
    pat_perfstring += r"(" + pat_value_neg_inf + r"\:?" + pat_value + r"?)?;?"
    pat_perfstring += r"(" + pat_value_neg_inf + r"\:?" + pat_value + r"?)?;?"
    pat_perfstring += r"(" + pat_value + r"?)?;?"
    pat_perfstring += r"(" + pat_value + r"?)?"

    re_perfstring = re.compile(pat_perfstring)

    re_perfoutput = re.compile(r"^(.*?=.*?)\s+")

    # -------------------------------------------------------------------------
    def __init__(
        self,
        label,
        value,
        uom=None,
        threshold=None,
        warning=None,
        critical=None,
        min_data=None,
        max_data=None,
    ):
        """
        Initialise a MonitoringPerformance object.

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
        if label is None or self._label == "":
            raise MonitoringPerformanceError(
                "Empty label %r for MonitoringPerformance given." % (label)
            )

        self._value = value
        """
        @ivar: the value of the performance data
        @type: Number
        """
        if not isinstance(value, Number):
            raise MonitoringPerformanceError(
                "Wrong value %r for MonitoringPerformance given." % (value)
            )

        self._uom = ""
        """
        @ivar: the unit of measure
        @type: str
        """
        if uom is not None:
            # remove all whitespaces
            self._uom = self.re_ws.sub("", str(uom))

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
                "The given threshold %r is neither None nor a MonitoringThreshold object."
                % (threshold)
            )
        else:
            self._threshold = MonitoringThreshold(warning=warn_range, critical=crit_range)

        self._min_data = None
        """
        @ivar: the minimum data for performance output
        @type: Number or None
        """
        if min_data is not None:
            if not isinstance(min_data, Number):
                raise MonitoringPerformanceError(
                    "The given min_data %r is not None and not a Number." % (min_data)
                )
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
                    "The given max_data %r is not None and not a Number." % (max_data)
                )
            else:
                self._max_data = max_data

    # -----------------------------------------------------------
    @property
    def label(self):
        """Give the label of the performance data."""
        return self._label

    # -----------------------------------------------------------
    @property
    def clean_label(self):
        """
        Return a "clean" label for use as a dataset name in RRD.

        ie, it converts characters that are not [a-zA-Z0-9_] to _.
        """
        name = self.label
        if name == "/":
            name = "root"
        elif self.re_slash.search(name):
            name = self.re_leading_slash.sub("", name)
            name = self.re_slash.sub("_", name)

        name = self.re_not_word.sub("_", name)
        return name

    # -----------------------------------------------------------
    @property
    def rrdlabel(self):
        """
        Return a string based on 'label' that is suitable for use as dataset name of an RRD.

        I.e. munges label to be 1-19 characters long with only characters [a-zA-Z0-9_].
        """
        return self.clean_label[0:19]

    # -----------------------------------------------------------
    @property
    def value(self):
        """Give the value of the performance data."""
        return self._value

    # -----------------------------------------------------------
    @property
    def uom(self):
        """Give the unit of measure."""
        return self._uom

    # -----------------------------------------------------------
    @property
    def threshold(self):
        """Give the threshold object containing the warning and the critical threshold."""
        return self._threshold

    # -----------------------------------------------------------
    @property
    def warning(self):
        """Give the warning threshold for performance data."""
        return self._threshold.warning

    # -----------------------------------------------------------
    @property
    def critical(self):
        """Give the critical threshold for performance data."""
        return self._threshold.critical

    # -----------------------------------------------------------
    @property
    def min_data(self):
        """Give the minimum data for performance output."""
        return self._min_data

    # -----------------------------------------------------------
    @property
    def max_data(self):
        """Give the maximum data for performance output."""
        return self._max_data

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecast into a string for reproduction."""
        fields = []
        for fname in ("label", "value", "uom", "threshold", "min_data", "max_data"):
            fval = getattr(self, fname)
            fields.append(f"{fname}={fval!r}")

        return f"<{self.__class__.__name__}>(" + ", ".join(fields) + ")>"

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecast into a dictionary.

        @return: structure as dict
        @rtype:  dict
        """
        ret = super(MonitoringPerformance, self).as_dict()

        ret["label"] = self.label
        ret["value"] = self.value
        ret["uom"] = self.uom
        ret["threshold"] = self.threshold
        ret["min_data"] = self.min_data
        ret["max_data"] = self.max_data
        ret["status"] = self.status()

        return ret

    # -------------------------------------------------------------------------
    def status(self):
        """
        Return the Monitoring state of the current value against the thresholds.

        @return: Monitoring.state
        @rtype: int
        """
        return self.threshold.get_status([self.value])

    # -------------------------------------------------------------------------
    @staticmethod
    def _nvl(value):
        """Map None to ''."""
        if value is None:
            return ""
        return str(value)

    # -------------------------------------------------------------------------
    def perfoutput(self):
        """
        Output the data in MonitoringPlugin perfdata format.

        I.e.  label=value[uom];[warn];[crit];[min];[max].
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
        out = self.re_trailing_semicolons.sub("", out)

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

        if match.group(1) is None or match.group(1) == "":
            LOG.warn("String %r was not a valid performance output, no label found.", string)
            return None

        if match.group(2) is None or match.group(2) == "":
            LOG.warn("String %r was not a valid performance output, no value found.", string)
            return None

        info = []
        i = 0
        for field in match.groups():
            val = None
            if i in (0, 2):
                val = field.strip()
            elif field is not None:
                val = cls.re_comma.sub(".", field)
                try:
                    if cls.re_dot.search(field):
                        val = float(field)
                    else:
                        val = int(field)
                except ValueError as e:
                    LOG.warn("Invalid performance value %r found: %s", field, str(e))
                    return None
            info.append(val)
            i += 1

        LOG.debug("Found parfdata fields: %r", info)

        obj = cls(
            label=info[0],
            value=info[1],
            uom=info[2],
            warning=info[3],
            critical=info[4],
            min_data=info[5],
            max_data=info[6],
        )

        return obj

    # -------------------------------------------------------------------------
    @classmethod
    def parse_perfstring(cls, perfstring):
        """
        Parse the given string with performance output strings.

        It gives back a list of MonitoringPerformance objects from all successful parsed
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
            if ps == "":
                break

            if ps.count("=") > 1:

                # If there is more than 1 equals sign, split it out and
                # parse individually
                match = cls.re_perfoutput.search(ps)
                if match:
                    obj = match.group(1)
                    ps = cls.re_perfoutput.sub("", ps, 1)
                    obj = cls._parse(ps)
                else:
                    # This could occur if perfdata was soemthing=value=
                    LOG.warn("Didn't found performance data in %r.", ps)
                    break

            else:
                obj = cls._parse(ps)
                ps = ""

            if obj:
                perfs.append(obj)

        LOG.debug("Found performance data: %r", perfs)
        return perfs


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
