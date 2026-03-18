#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: Functions and objects used for unit tests on the postfix logsums python modules.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 - 2026 Frank Brehm, Berlin
@license: AGPL
"""

import argparse
import logging
import os
import pprint
import shutil
import sys
import textwrap
from pathlib import Path

try:
    from fb_logging.colored import ColoredFormatter as Formatter
except ImportError:
    from logging import Formatter

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = str(Path(__file__).parent.parent)
sys.path.insert(0, libdir)

# =============================================================================
DEFAULT_TERMINAL_WIDTH = 99
DEFAULT_TERMINAL_HEIGHT = 40

LOG = logging.getLogger(__name__)


# =============================================================================
def pp(value, indent=4, width=None, depth=None):
    """Return a pretty print string of the given value."""
    if not width:
        term_size = shutil.get_terminal_size((DEFAULT_TERMINAL_WIDTH, DEFAULT_TERMINAL_HEIGHT))
        width = term_size.columns

    pretty_printer = pprint.PrettyPrinter(indent=indent, width=width, depth=depth)
    return pretty_printer.pformat(value)


# =============================================================================
def get_arg_verbose():
    """Get and return command line arguments."""
    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-v", "--verbose", action="count", dest="verbose", help="Increase the verbosity level"
    )
    args = arg_parser.parse_args()

    return args.verbose


# =============================================================================
def init_root_logger(verbose=0):
    """Initialize the root logger."""
    root_log = logging.getLogger()
    root_log.setLevel(logging.WARNING)
    if verbose:
        root_log.setLevel(logging.INFO)
        if verbose > 1:
            root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    if appname.endswith('.py'):
        ext_index = appname.rindex('.py')
        if ext_index >= 0:
            appname = appname[0:ext_index]

    format_str = appname + ": "
    if verbose:
        if verbose > 1:
            format_str += "%(name)s(%(lineno)d) %(funcName)s() "
        else:
            format_str += "%(name)s "
    format_str += "%(levelname)s - %(message)s"
    formatter = None
    formatter = Formatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)


# =============================================================================
class MonitoringScriptsTestcase(unittest.TestCase):
    """Base test case for all testcase classes of this package."""

    # -------------------------------------------------------------------------
    @classmethod
    def current_function_name(cls, level=0):
        """Return the name of the function, from where this method was called."""
        return sys._getframe(level + 1).f_code.co_name

    # -------------------------------------------------------------------------
    @classmethod
    def get_method_doc(cls):
        """Return the docstring of the method, from where this method was called."""
        func_name = cls.current_function_name(1)
        doc_str = getattr(cls, func_name).__doc__
        cname = cls.__name__
        mname = "{cls}.{meth}()".format(cls=cname, meth=func_name)
        msg = "This is {}.".format(mname)
        if doc_str is None:
            return msg
        doc_str = textwrap.dedent(doc_str).strip()
        if doc_str:
            msg = "{m} - {d}".format(m=mname, d=doc_str)
        return msg

    # -------------------------------------------------------------------------
    def __init__(self, methodName="runTest", verbose=0):
        """Initialize the base testcase class."""
        self._verbose = int(verbose)

        appname = os.path.basename(sys.argv[0]).replace(".py", "")
        self._appname = appname

        super(MonitoringScriptsTestcase, self).__init__(methodName)

        self.assertGreaterEqual(
            sys.version_info[0], 3, "Unsupported Python version {}.".format(sys.version)
        )

        if sys.version_info[0] == 3:
            self.assertGreaterEqual(
                sys.version_info[1], 8, "Unsupported Python version {}.".format(sys.version)
            )

        if self.verbose > 2:
            LOG.debug("Used Phyton version: {!r}.".format(sys.version))
            LOG.debug("Used Phyton include path:\n" + pp(sys.path))

    # -------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, "_verbose", 0)

    # -------------------------------------------------------------------------
    @property
    def appname(self):
        """The name of the current running application."""
        return self._appname

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        """Tear down routine for calling each particular test method."""
        pass


# =============================================================================
if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
