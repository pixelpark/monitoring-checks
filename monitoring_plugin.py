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
import pprint
import shutil
import traceback
import datetime

from pathlib import Path

if sys.version_info[0] != 3:
    print("This script is intended to use with Python3.", file=sys.stderr)
    print("You are using Python: {0}.{1}.{2}-{3}-{4}.\n".format(
        *sys.version_info), file=sys.stderr)
    sys.exit(1)

if sys.version_info[1] < 5:
    print("A minimal Python version of 3.5 is necessary to execute this script.", file=sys.stderr)
    print("You are using Python: {0}.{1}.{2}-{3}-{4}.\n".format(
        *sys.version_info), file=sys.stderr)
    sys.exit(1)

LOG = logging.getLogger(__name__)

__author__ = 'Frank Brehm <frank@brehm-online.com>'
__copyright__ = '(C) 2023 by Frank Brehm, Berlin'
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

    return fb_tools.common.pp(value, indent=indent, width=width, depth=depth)


# =============================================================================
class MonitoringException(Exception):

    pass


# =============================================================================
class MonitoringPlugin(object):

    errors = {
        'OK': 0,
        'WARNING': 1,
        'CRITICAL': 2,
        'UNKNOWN': 3,
        'DEPENDENT': 4,
    }
    error_codes = {}
    MonitoringPlugin.get_error_codes()

    # -------------------------------------------------------------------------
    @classmethod
    def get_error_codes(cls):

        ret = {}
        for name in cls.errors.keys():
            code = cls.errors[name]
            cls.error_codes[code] = name

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
            self._description = _("Unknown and undescriped monitoring plugin.")

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
            msg = _("Base directory {!r} does not exists.").format(str(value))
            self.handle_error(msg, self.appname)
        elif not base_dir_path.is_dir():
            msg = _("Path for base directory {!r} is not a directory.").format(str(value))
            self.handle_error(msg, self.appname)
        else:
            self._base_dir = base_dir_path

    # -----------------------------------------------------------
    @property
    def description(self):
        """Get a short text describing the application."""
        return self._description


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
    def _init_arg_parser(self):
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
    def exit(self, retval=-1, msg=None, trace=False):
        """
        Exit the current application.

        Universal method to call sys.exit(). If fake_exit is set, a
        FakeExitError exception is raised instead (useful for unittests.)

        @param retval: the return value to give back to theoperating system
        @type retval: int
        @param msg: a last message, which should be emitted before exit.
        @type msg: str
        @param trace: flag to output a stack trace before exiting
        @type trace: bool

        @return: None

        """
        retval = int(retval)
        trace = bool(trace)

        root_logger = logging.getLogger()
        has_handlers = False
        if root_logger.handlers:
            has_handlers = True

        if msg:
            if has_handlers:
                if retval:
                    LOG.error(msg)
                else:
                    LOG.info(msg)
            if not has_handlers:
                if hasattr(sys.stderr, 'buffer'):
                    sys.stderr.buffer.write(str(msg) + "\n")
                else:
                    sys.stderr.write(str(msg) + "\n")

        if trace:
            if has_handlers:
                if retval:
                    LOG.error(traceback.format_exc())
                else:
                    LOG.info(traceback.format_exc())
            else:
                traceback.print_exc()

        sys.exit(retval)

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
        except Exception as e:
            self.handle_error(str(e), e.__class__.__name__, True)
            self.exit_value = 99

        if self.verbose > 1:
            LOG.info(_("Ending."))

        try:
            self.post_run()
        except Exception as e:
            self.handle_error(str(e), e.__class__.__name__, True)
            self.exit_value = 97

        self.exit(self.exit_value)

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
