#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import logging
import argparse
import re
import pprint
import pathlib
import datetime

import ldap3

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

__author__ = 'Frank Brehm <frank@brehm-online.com>'
__copyright__ = '(C) 2021 by Frank Brehm, Berlin'
__version__ = '0.1.0'


# =============================================================================
def pp(value, indent=4, width=99, depth=None):
    """
    Returns a pretty print string of the given value.

    @return: pretty print string
    @rtype: str
    """

    pretty_printer = pprint.PrettyPrinter(
        indent=indent, width=width, depth=depth)
    return pretty_printer.pformat(value)


# =============================================================================
def get_error_codes(errors):

    error_codes = {}
    for name in errors.keys():
        code = errors[name]
        error_codes[code] = name

    return error_codes

# =============================================================================
class Check389dsReplicatsApp(object):

    errors = {
        'OK': 0,
        'WARNING': 1,
        'CRITICAL': 2,
        'UNKNOWN': 3,
        'DEPENDENT': 4,
    }

    error_codes = get_error_codes(errors)

    # -------------------------------------------------------------------------
    @classmethod
    def get_error_codes(cls):

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
            self, appname=None, verbose=0, version=__version__, base_dir=None):

        self._appname = self.get_generic_appname(appname)
        self._version = version
        self._verbose = int(verbose)
        self._initialized = False
        self._base_dir = None

        self.host  = None
        self.bind_dn = None
        self.bind_pw = None
        self.status_code = 0

        if base_dir:
            self.base_dir = base_dir
        if not self._base_dir:
            self._base_dir = pathlib.Path(os.getcwd()).resolve()

        self.init_arg_parser()
        self.perform_arg_parser()

        self.initialized = True

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
        base_dir_path = pathlib.Path(value)
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
        res['initialized'] = self.initialized
        res['base_dir'] = self.base_dir

        return res
    # -------------------------------------------------------------------------
    def init_arg_parser(self):
        """
        Local called method to initiate the argument parser.

        @raise PBApplicationError: on some errors

        """

        description = ("This is script for getting the replication state "
                "of an 389ds LDAP server.")

        self.arg_parser = argparse.ArgumentParser(
            prog=self.appname,
            description=description,
            add_help=False,
        )

        ldap_group = self.arg_parser.add_argument_group('LDAP options')

        ldap_group.add_argument(
            '-H', '--host', dest='host', required=True,
            help="The fqdn or address of the host to monitor."
        )

        ldap_group.add_argument(
            '-D', '--bind-dn', dest='bind_dn', required=True,
            help="The DN of the user to use to connect to the LDAP server.",
        )

        pwgroup = ldap_group.add_mutually_exclusive_group(required=True)

        pwgroup.add_argument(
            '-W', '--password', dest='password',
            help="The password of the user to connect to the LDAP server.",
        )

        pwgroup.add_argument(
            '-y', '--password-file', dest='password_file', type=pathlib.Path,
            help=("A path to an existing file containing the password "
                "of the user to connect to the LDAP server."),
        )

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
    def perform_arg_parser(self):

        self.args = self.arg_parser.parse_args()

        if self.args.usage:
            self.arg_parser.print_usage(sys.stdout)
            self.exit(0)

        if self.args.verbose is not None and self.args.verbose > self.verbose:
            self.verbose = self.args.verbose

        self.host = self.args.host
        self.bind_dn = self.args.bind_dn

        if self.args.password:
            self.bind_pw = self.args.password
        elif self.args.password_file:
            self.bind_pw = self.read_pw_file(self.args.password_file)
        else:
            self.arg_parser.print_usage(sys.stderr)
            self.exit(1)

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
    def read_pw_file(self, pw_file):

        if not pw_file.exists():
            self.nagios_exit(3, 'Password file {!r} does not exists.'.format(str(pw_file)))
        if not pw_file.is_file():
            self.nagios_exit(3, 'Password file {!r} is not a regular file.'.format(str(pw_file)))
        if not os.access(str(pw_file), os.R_OK):
            self.nagios_exit(3, 'No read access to password file {!r}.'.format(str(pw_file)))

        re_pw = re.compile(r'^\s*(\S(?:.*\S)?)\s*$')

        pw = None
        with pw_file.open(encoding='utf-8', errors='surrogateescape') as fh:
            for line in fh.readlines():
                match = re_pw.match(line)
                if match:
                    pw = match.group(1)
                    break

        if pw is None:
            self.nagios_exit(3, 'Did not found a password in file {!r}.'.format(str(pw_file)))

        return pw


# =============================================================================

app = Check389dsReplicatsApp()
if app.verbose:
    print(app)

app.nagios_exit(3, 'wtf?!?')

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
