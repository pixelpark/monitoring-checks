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

LOG = logging.getLogger(__name__)

__version__ = "0.9.0"


# =============================================================================
class MonitoringException(Exception):
    """Base class for all exception classes and object, raised in this module."""

    pass


# =============================================================================
class MonitoringPerformanceError(MonitoringException):
    """Exception class for things happend in class MonitoringPerformance."""

    pass


# =============================================================================
class MonitoringRangeError(MonitoringException):
    """Base exception class for all exceptions in this module."""

    pass


# =============================================================================
class InvalidRangeError(MonitoringRangeError):
    """A special exception, which is raised, if an invalid range string was found."""

    # -------------------------------------------------------------------------
    def __init__(self, wrong_range):
        """
        Initialize the InvalidRangeError.

        @param wrong_range: the wrong range, whiche lead to this exception.
        @type wrong_range: str
        """
        self.wrong_range = wrong_range

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string for error output."""
        return f"Wrong range {self.wrong_range!r}"

# =============================================================================
class InvalidRangeValueError(MonitoringRangeError):
    """An exception, if an invalid value should be checked against the current range object."""

    # -------------------------------------------------------------------------
    def __init__(self, value):
        """
        Initialize the InvalidRangeValueError.

        @param value: the wrong value, whiche lead to this exception.
        @type value: object
        """
        self.value = value

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string for error output."""
        return f"Wrong value {self.value!r} to check against a range."


# =============================================================================
class MonitoringPluginError(MonitoringException):
    """Base exception for an exception inside a monitoring plugin."""

    pass


# =============================================================================
class ApiError(MonitoringPluginError):
    """Base class for more complex exceptions."""

    # -------------------------------------------------------------------------
    def __init__(self, code, msg, uri=None):
        """Initialize the ApiError object."""
        self.code = code
        self.msg = msg
        self.uri = uri

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string."""
        if self.uri:
            msg = f"Got a {self.code} error code from {self.uri!r}: {self.msg}"
        else:
            msg = f"Got a {self.code} error code: {self.msg}"

        return msg


# =============================================================================
class FunctionNotImplementedError(MonitoringPluginError, NotImplementedError):
    """Error class for not implemented functions."""

    # -------------------------------------------------------------------------
    def __init__(self, function_name, class_name):
        """
        Initialize the FunctionNotImplementedError.

        @param function_name: the name of the not implemented function
        @type function_name: str
        @param class_name: the name of the class of the function
        @type class_name: str
        """
        self.function_name = function_name
        if not function_name:
            self.function_name = "__unkown_function__"

        self.class_name = class_name
        if not class_name:
            self.class_name = "__unkown_class__"

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecast into a string for error output."""
        return f"Function {self.function_name}() has to be overridden in class {self.class_name}."


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
