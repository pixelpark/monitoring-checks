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

import argparse
import copy
import datetime
import logging
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path
from shlex import quote
from subprocess import SubprocessError

DEFAULT_TERMINAL_WIDTH = 99
DEFAULT_TERMINAL_HEIGHT = 40

# Own modules
from .errors import FunctionNotImplementedError
from .errors import MonitoringException
from .functions import pp
from .functions import to_bytes
from .obj import MonitoringObject
from .perf import MonitoringPerformance

LOG = logging.getLogger(__name__)

__version__ = "0.10.0"


# =============================================================================
class MonitoringPlugin(MonitoringObject):
    """
    Class for an application object for a monitoring plugin.

    Monitoring plugins are checkscripts for Nagios/Icinga.
    """

    default_execution_timeout = 10

    # -------------------------------------------------------------------------
    @classmethod
    def get_generic_appname(cls, appname=None):
        """Get the base name of the currently running monitoring plugin."""
        if appname:
            v = str(appname).strip()
            if v:
                return v
        aname = sys.argv[0]
        aname = re.sub(r"\.py$", "", aname, flags=re.IGNORECASE)
        return os.path.basename(aname)

    # -------------------------------------------------------------------------
    def __init__(
        self,
        appname=None,
        verbose=0,
        version=None,
        base_dir=None,
        description=None,
        initialized=False,
    ):
        """Initialise the MonitoringPlugin object."""
        self._appname = self.get_generic_appname(appname)
        self._version = __version__
        if version:
            self._version = version + " (" + os.path.basename(__file__) + ": " + __version__ + ")"
        self._verbose = int(verbose)
        self._initialized = False
        self._base_dir = None
        self._status = 3
        self._status_msg = None
        self.perf_data = []
        self.execution_timeout = self.default_execution_timeout

        self.messages = {
            "warning": [],
            "critical": [],
            "ok": [],
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
        self.post_init()

        if self.verbose > 2:
            msg = "Current plugin properties:\n" + pp(self.as_dict())
            LOG.debug(msg)

    # -------------------------------------------------------------------------
    def post_init(self):
        """Execute some things after initialising the object."""
        self._perform_arg_parser()
        self.init_logging()

    # -------------------------------------------------------------------------
    def handle_error(self, error_message=None, exception_name=None, tb=None):
        """Handle an error gracefully."""
        msg = str(error_message).strip()
        if not msg:
            msg = "undefined error."
        title = None

        if isinstance(error_message, Exception):
            title = error_message.__class__.__name__
        else:
            if exception_name is not None:
                title = exception_name.strip()
            else:
                title = "Exception happened"
        msg = title + ": " + msg

        root_log = logging.getLogger()
        has_handlers = False
        if root_log.handlers:
            has_handlers = True

        if has_handlers:
            LOG.error(msg)
            if tb:
                LOG.error("Traceback:\n" + tb)
        else:
            curdate = datetime.datetime.now()
            curdate_str = "[" + curdate.isoformat(" ") + "]: "
            msg = curdate_str + msg + "\n"
            if hasattr(sys.stderr, "buffer"):
                sys.stderr.buffer.write(to_bytes(msg))
            else:
                sys.stderr.write(msg)
            if tb:
                print("Traceback:\n" + tb)

        return

    # -----------------------------------------------------------
    @property
    def appname(self):
        """Give the name of the current running application."""
        if hasattr(self, "_appname"):
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
        """Give the version string of the current object or application."""
        return getattr(self, "_version", __version__)

    # -----------------------------------------------------------
    @property
    def verbose(self):
        """Give the verbosity level."""
        return getattr(self, "_verbose", 0)

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
        """Give the initialisation of this object is complete."""
        return getattr(self, "_initialized", False)

    @initialized.setter
    def initialized(self, value):
        self._initialized = bool(value)

    # -----------------------------------------------------------
    @property
    def base_dir(self):
        """Give the base directory used for different purposes."""
        return self._base_dir

    @base_dir.setter
    def base_dir(self, value):
        base_dir_path = Path(value)
        if str(base_dir_path).startswith("~"):
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
        """Give the current numeric status of the plugin."""
        return self._status

    @status.setter
    def status(self, value):
        val = int(value)
        if val < 0 or val > 3:
            raise MonitoringException(
                "Invalid state {!r} given - mus be >= 0 an <= 4.".format(value)
            )
        self._status = val

    # -----------------------------------------------------------
    @property
    def status_msg(self):
        """Give the status message to show on output."""
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
        Typecast object structure into a string.

        @return: structure as string
        @rtype:  str
        """
        return pp(self.as_dict())

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Transform the elements of the object into a dict.

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """
        ret = super(MonitoringPlugin, self).as_dict()

        ret["appname"] = self.appname
        ret["arg_parser"] = self.arg_parser
        ret["args"] = copy.copy(self.args.__dict__)
        ret["base_dir"] = self.base_dir
        ret["description"] = self.verbose
        ret["initialized"] = self.initialized
        ret["perf_data"] = []
        ret["status"] = self.status
        ret["status_msg"] = self.status_msg
        ret["verbose"] = self.verbose
        ret["version"] = self.version

        for pdata in self.perf_data:
            ret["perf_data"].append(pdata.as_dict())

        return ret

    # -------------------------------------------------------------------------
    def _init_arg_parser(self):
        """
        Initiate the argument parser.

        @raise PBApplicationError: on some errors
        """
        self.arg_parser = argparse.ArgumentParser(
            prog=self.appname,
            description=self.description,
            add_help=False,
        )

        self.init_arg_parser()

        general_group = self.arg_parser.add_argument_group("General_options")

        general_group.add_argument(
            "-v",
            "--verbose",
            action="count",
            dest="verbose",
            help="Increase the verbosity level",
        )

        general_group.add_argument(
            "-h", "--help", action="help", dest="help", help="Show this help message and exit."
        )

        general_group.add_argument(
            "--usage",
            action="store_true",
            dest="usage",
            help="Display brief usage message and exit.",
        )

        v_msg = "Version of %(prog)s: {}".format(self.version)
        general_group.add_argument(
            "-V",
            "--version",
            action="version",
            version=v_msg,
            help="Show program's version number and exit.",
        )

    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """Can be overridden ..."""
        pass

    # -------------------------------------------------------------------------
    def _perform_arg_parser(self):
        """Evaluate the command line parameters."""
        self.args = self.arg_parser.parse_args()

        if self.args.usage:
            self.arg_parser.print_usage(sys.stdout)
            self.exit(0)

        if self.args.verbose is not None and self.args.verbose > self.verbose:
            self.verbose = self.args.verbose

        self.perform_arg_parser()

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):
        """Evaluate the command line parameters, can be overriddden."""
        pass

    # -------------------------------------------------------------------------
    def add_perfdata(
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
        Add a MonitoringPerformance object to self.perf_data.

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
            label=label,
            value=value,
            uom=uom,
            threshold=threshold,
            warning=warning,
            critical=critical,
            min_data=min_data,
            max_data=max_data,
        )

        self.perf_data.append(pdata)

    # -------------------------------------------------------------------------
    def nagios_exit(self, status_code, status_msg):
        """Exit the app with given status code and status message."""
        if status_code not in self.error_codes:
            ocode = status_code
            status_code = 3
            status_msg += " (Unknown status code {})".format(ocode)

        status_name = self.error_codes[status_code]

        msg = "{sn} - {app}: {msg}".format(sn=status_name, app=self.appname, msg=status_msg)
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
        format_str = ""
        if self.verbose:
            format_str = "[%(asctime)s]: "
        format_str += self.appname + ": "
        if self.verbose:
            if self.verbose > 1:
                format_str += "%(name)s(%(lineno)d) %(funcName)s() "
            else:
                format_str += "%(name)s "
        format_str += "%(levelname)s - %(message)s"
        formatter = logging.Formatter(format_str)

        # create log handler for console output
        lh_console = logging.StreamHandler(sys.stderr)
        lh_console.setLevel(log_level)
        lh_console.setFormatter(formatter)

        root_logger.addHandler(lh_console)

        return

    # -------------------------------------------------------------------------
    def all_perfoutput(self):
        """Generate a string with all formatted performance data."""
        if not self.perf_data:
            return ""

        return " ".join([x.perfoutput() for x in self.perf_data])

    # -------------------------------------------------------------------------
    def die(self, message, no_status_line=False):
        """Exit with status 'unknown' and without outputting performance data."""
        self.exit(self.status_unknown, message=message, no_status_line=no_status_line)

    # -------------------------------------------------------------------------
    def exit(self, status=None, message=None, no_status_line=False):  # noqa: A003
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
                message = "\n".join(lambda x: str(x).strip(), message)
            else:
                message = str(message).strip()

        LOG.debug("Exiting with status {s} ({c}): {m}".format(s=status, c=code, m=message))

        # Setup output
        output = ""
        if no_status_line:
            if message:
                output = message
            else:
                output = "[no message]"
        else:
            output = self.appname + " " + code
            lines = []
            if message:
                lines = message.splitlines()
                output += " - " + lines[0]
            pdata = self.all_perfoutput()
            if pdata:
                output += " | " + pdata
            if len(lines) > 1:
                output += "\n" + "\n".join(lines[1:])

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
        raise FunctionNotImplementedError("run", self.__class__.__name__)

    # -------------------------------------------------------------------------
    def _run(self):
        """
        Execute the main actions of the application.

        The visible start point of this object.

        @return: None
        """
        if not self.initialized:
            try:
                raise MonitoringException("The application is not completely initialized.")
            except Exception as e:  # noqa: 1887
                tb = ""
                for m in traceback.format_exc():
                    tb += m
                self.handle_error(str(e), e.__class__.__name__, tb)
                self.status = self.status_unknown
                self.die(str(e), no_status_line=True)

        try:
            self.pre_run()
        except Exception as e:  # noqa: 1887
            tb = ""
            for m in traceback.format_exc():
                tb += m
            self.handle_error(str(e), e.__class__.__name__, tb)
            self.exit(self.status_unknown)

        if not self.initialized:
            raise MonitoringException(
                "Object {!r} seems not to be completely initialized.".format(
                    self.__class__.__name__
                )
            )

        try:
            self.run()
        except MonitoringException as e:
            self.die(str(e), no_status_line=True)
        except Exception as e:  # noqa: 1887
            tb = ""
            for m in traceback.format_exc():
                tb += m
            self.handle_error(str(e), e.__class__.__name__, tb)
            self.status = self.status_unknown
            self.die(str(e), no_status_line=True)

        try:
            self.post_run()
        except MonitoringException as e:
            self.die(str(e), no_status_line=True)
        except Exception as e:  # noqa: 1887
            tb = ""
            for m in traceback.format_exc():
                tb += m
            self.handle_error(str(e), e.__class__.__name__, tb)
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
        """Call the main run method."""
        return self._run()

    # -------------------------------------------------------------------------
    def execute(self, cmd, shell=False, timeout=None):
        """Execute the given command."""
        if shell:
            cmd_str = cmd
        else:
            cmd_str = " ".join((quote(x) for x in cmd))
        LOG.debug("Executing: {}".format(cmd_str))

        if timeout is None:
            timeout = self.execution_timeout

        try:
            completed_process = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                timeout=timeout,
                encoding="utf-8",
                errors="surrogateescape"
            )
        except SubprocessError as e:
            if self.verbose > 2:
                LOG.debug("{c} happened: {e}".format(c=e.__class__.__name__, e=e))
            raise

        return completed_process

    # -------------------------------------------------------------------------
    def get_table(self, keys, headers, data):
        """
        Return a table of data.

        * The parameter 'keys' is a list of the keys of parameter headers and the items of data.
          If a key starts with the character '>', the appropriate column will be right aligned,
          and if it starts with '=', the column will be centered.
          If the key does start with '<' or it does not start with '>' or '=', the
          column will be left aligned.
        * The parameter 'headers' is a dict with the displayed header names.
          The keys of the dict must kontain the keys of the parameter 'keys'.
        * The parameter 'data' is a list of dicts with the data rows.
          The keys of each dict must kontain the keys of the parameter 'keys'.
        """
        alignments = {}
        used_keys = []

        for key in keys:
            if key.startswith(">"):
                used_key = key[1:]
                if used_key == "":
                    raise ValueError(f"Invalid key {key!r} given on calling print_table.")
                alignments[used_key] = "r"
                used_keys.append(used_key)
            elif key.startswith("="):
                used_key = key[1:]
                if used_key == "":
                    raise ValueError(f"Invalid key {key!r} given on calling print_table.")
                alignments[used_key] = "c"
                used_keys.append(used_key)
            elif key.startswith("<"):
                used_key = key[1:]
                if used_key == "":
                    raise ValueError(f"Invalid key {key!r} given on calling print_table.")
                alignments[used_key] = "l"
                used_keys.append(used_key)
            else:
                alignments[key] = "l"
                used_keys.append(key)

        if self.verbose > 3:
            LOG.debug("Table alignments: " + pp(alignments))

        return self._get_table(keys, alignments, headers, data)

    # -------------------------------------------------------------------------
    def _get_table(self, keys, alignments, headers, data):

        max_length = {}
        for key in keys:
            max_length[key] = len(headers[key])

        for row in data:
            for key in keys:
                if len(row[key]) > max_length[key]:
                    max_length[key] = len(row[key])
        if self.verbose > 3:
            LOG.debug("Field lengths: " + pp(max_length))

        template_array = []
        for key in keys:
            template_array.append(f"{{{key}}}")
        template = " ".join(template_array)
        if self.verbose > 3:
            LOG.debug(f"Line template: {template!r}")

        used_data = []

        if headers:
            new_row = {}
            for key in keys:
                val = headers[key]
                if alignments[key] == "r":
                    new_row[key] = val.rjust(max_length[key])
                elif alignments[key] == "c":
                    new_row[key] = val.center(max_length[key])
                else:
                    new_row[key] = val.ljust(max_length[key])
            if self.verbose > 3:
                LOG.debug("Header row: " + pp(new_row))
            used_data.append(new_row)

        for row in data:
            new_row = {}
            for key in keys:
                val = row[key]
                if alignments[key] == "r":
                    new_row[key] = val.rjust(max_length[key])
                elif alignments[key] == "c":
                    new_row[key] = val.center(max_length[key])
                else:
                    new_row[key] = val.ljust(max_length[key])
            used_data.append(new_row)
            if self.verbose > 3:
                LOG.debug("New row: " + pp(new_row))

        if self.verbose > 3:
            LOG.debug("Used data:\n" + pp(used_data))

        lines = [template.format(**row) for row in used_data]
        if self.verbose > 3:
            LOG.debug("Generated lines:\n" + pp(lines))

        return "\n".join(lines)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
