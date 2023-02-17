#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author: Frank Brehm <frank@brehm-online.com
#         Berlin, Germany, 2022
# Date:   2022-02-17
#
# Refactored from Perl script 'pflogsumm' from James S. Seymour, Release 1.1.5
#

from __future__ import absolute_import, print_function

import sys
import os
import logging
import argparse
import traceback
import datetime
import copy
import re
import pprint
import shutil
import textwrap

from argparse import RawDescriptionHelpFormatter

if sys.version_info[0] != 3:
    print("This script is intended to use with Python3.", file=sys.stderr)
    print("You are using Python: {0}.{1}.{2}-{3}-{4}.\n".format(
        *sys.version_info), file=sys.stderr)
    sys.exit(1)

if sys.version_info[1] < 4:
    print("A minimal Python version of 3.4 is necessary to execute this script.", file=sys.stderr)
    print("You are using Python: {0}.{1}.{2}-{3}-{4}.\n".format(
        *sys.version_info), file=sys.stderr)
    sys.exit(1)

LOG = logging.getLogger(__name__)

DEFAULT_TERMINAL_WIDTH = 99
DEFAULT_TERMINAL_HEIGHT = 40

__author__ = 'Frank Brehm <frank@brehm-online.com>'
__copyright__ = '(C) 2022 by Frank Brehm, Berlin'
__version__ = '0.1.0'


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
class NonNegativeItegerOptionAction(argparse.Action):

    # -------------------------------------------------------------------------
    def __call__(self, parser, namespace, value, option_string=None):

        try:
            val = int(value)
        except Exception as e:
            msg = "Got a {c} for converting {v!r} into an integer value: {e}".format(
                c=e.__class__.__name__, v=value, e=e)
            raise argparse.ArgumentError(self, msg)

        if val < 0:
            msg = "The option must not be negative (given: {}).".format(value)
            raise argparse.ArgumentError(self, msg)

        setattr(namespace, self.dest, val)


# =============================================================================
class PostfixLogsumsApp(object):

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
    def __init__(self):

        self._appname = self.get_generic_appname()
        self._version = __version__
        self._verbose = 0
        self._initialized = False

        self.init_arg_parser()
        self.perform_arg_parser()
        self.init_logging()

        self._initialized = True

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
            LOG.warning(_("Wrong verbose level {!r}, must be >= 0").format(value))

    # -----------------------------------------------------------
    @property
    def initialized(self):
        """The initialisation of this object is complete."""
        return getattr(self, '_initialized', False)

    @initialized.setter
    def initialized(self, value):
        self._initialized = bool(value)

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
        res['args'] = copy.copy(self.args.__dict__)
        res['version'] = self.version
        res['verbose'] = self.verbose
        res['initialized'] = self.initialized

        return res

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """
        Local called method to initiate the argument parser.

        @raise PBApplicationError: on some errors

        """

        description = """\
            {w} is a log analyzer/summarizer for the Postfix MTA.

            It is designed to provide an over-view of Postfix activity, with just enough
            detail to give the administrator a "heads up" for potential trouble spots.

            {w} generates summaries and, in some cases, detailed reports of mail server traffic
            volumes, rejected and bounced email, and server warnings, errors and panics."""
        description = textwrap.dedent(description.format(w='Postfix-logsums'))

        day_values = ('today', 'yesterday')

        self.arg_parser = argparse.ArgumentParser(
            prog=self.appname,
            description=description,
            formatter_class=RawDescriptionHelpFormatter,
            add_help=False,
        )

        logfile_group = self.arg_parser.add_argument_group('Options for scanning Postfix logfiles')

        logfile_group.add_argument(
            '--bounce-detail', type=int, metavar='COUNT', dest='bounce_detail',
            action=NonNegativeItegerOptionAction,
            help="Limit detailed bounce reports to the top <COUNT>. 0 to suppress entirely.")

        logfile_group.add_argument(
            '-d', '--day', metavar='|'.join(day_values), dest='day', choices=day_values,
            help='Generate report for just today or yesterday')

        logfile_group.add_argument(
            '--deferral-detail', type=int, metavar='COUNT', dest='deferral_detail',
            action=NonNegativeItegerOptionAction,
            help='Limit detailed deferral reports to the top <COUNT>. 0 to suppress entirely.')

        logfile_group.add_argument(
            '--detail', type=int, metavar='COUNT', dest='detail',
            action=NonNegativeItegerOptionAction,
            help=(
                'Sets all --*-detail, -h and -u to <COUNT>. Is over-ridden by '
                'individual settings. --detail 0 suppresses *all* detail.'),)

        logfile_group.add_argument( 
            'logfile', metavar='FILE', nargs='*', help=(
                'The logfile(s) to analyze. If no file(s) specified, reads from stdin.'),)

        general_group = self.arg_parser.add_argument_group('General_options')

        general_group.add_argument(
            "-v", "--verbose", action="count", dest='verbose',
            help='Increase the verbosity level',
        )

        general_group.add_argument(
            "--help", action='help', dest='help',
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
    def perform_arg_parser(self):

        self.args = self.arg_parser.parse_args()

        if self.args.usage:
            self.arg_parser.print_usage(sys.stdout)
            self.exit(0)

        if self.args.verbose is not None and self.args.verbose > self.verbose:
            self.verbose = self.args.verbose

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
    def handle_error(
            self, error_message=None, exception_name=None, do_traceback=False):

        msg = str(error_message).strip()
        if not msg:
            msg = _('undefined error.')
        title = None

        if isinstance(error_message, Exception):
            title = error_message.__class__.__name__
        else:
            if exception_name is not None:
                title = exception_name.strip()
            else:
                title = _('Exception happened')
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

    # -------------------------------------------------------------------------
    def __call__(self):
        return self.run()

    # -------------------------------------------------------------------------
    def run(self):

        LOG.debug("And here wo go ...")


# =============================================================================

app = PostfixLogsumsApp()
if app.verbose:
    print(app)
app()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
