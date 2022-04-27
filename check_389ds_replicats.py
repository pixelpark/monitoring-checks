#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Author: Frank Brehm <frank@brehm-online.com
#         Berlin, Germany, 2021
# Date:   2021-02-18
# By an idea of: Emmanuel BUU <emmanuel.buu@ives.fr> (c) IVèS
#                http://www.ives.fr/
#
# Usage: ./check_389ds_replicats.py -D cn=admin -H LDAP_SERVER -y PASSWORD_FILE
#        OK - check_389ds_replicats: Replication to <REPLICATION_PARTNER>, Last Operation <TIMESTAMP>, Status: Error (0) Replica acquired successfully: Incremental update succeeded.
#

from __future__ import print_function

import sys
import os
import logging
import argparse
import re
import pprint
import pathlib
import datetime
import traceback
import json
import ssl

from ssl import CERT_REQUIRED, CERT_NONE
from ldap3 import Tls, Server, Connection, Reader, ObjectDef
from ldap3 import IP_V4_PREFERRED, ROUND_ROBIN, AUTO_BIND_NONE, ALL_ATTRIBUTES
from ldap3 import SUBTREE
from ldap3.core.exceptions import LDAPPasswordIsMandatoryError
from ldap3.utils.log import set_library_log_detail_level, ERROR, BASIC, PROTOCOL, NETWORK, EXTENDED

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
__version__ = '0.4.1'


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

    default_ldap_port = 389
    default_ldap_port_ssl = 636
    default_ldap_use_ssl = False
    default_ldap_ssl_verify = CERT_REQUIRED
    default_timeout = 30

    default_ldap_base_dn = 'cn=config'

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
        self.status_code = 3
        self.status_msg = 'wtf?!?'
        self.ldap_use_ssl = self.default_ldap_use_ssl
        self.ldap_ssl_verify = self.default_ldap_ssl_verify
        self.ldap_port = self.default_ldap_port
        if self.ldap_use_ssl:
            self.ldap_port = self.default_ldap_port_ssl
        self.ldap_timeout = self.default_timeout
        self.ldap_base_dn = self.default_ldap_base_dn

        self.ldap = None

        if base_dir:
            self.base_dir = base_dir
        if not self._base_dir:
            self._base_dir = pathlib.Path(os.getcwd()).resolve()

        self.init_arg_parser()
        self.perform_arg_parser()
        self.init_logging()

        if self.verbose > 5:
            set_library_log_detail_level(EXTENDED)
        elif self.verbose > 4:
            set_library_log_detail_level(NETWORK)
        elif self.verbose > 3:
            set_library_log_detail_level(PROTOCOL)
        elif self.verbose > 2:
            set_library_log_detail_level(BASIC)
        else:
            set_library_log_detail_level(ERROR)

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
        if self.verbose < 4:
            res['bind_pw'] = '********'

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

        # Connection stuff
        ldap_group.add_argument(
            '-H', '--host', dest='host', required=True,
            help="The fqdn or address of the host to monitor."
        )

        ldap_group.add_argument(
            '-P', '--port', dest="port", type=int,
            help=("The used TCP/UDP port number when connecting to the LDAP server. "
                "Defaults to {pnssl}, if using ldap://, and to {pssl}, if "
                "using ldaps://.").format(
                    pnssl=self.default_ldap_port, pssl=self.default_ldap_port_ssl),
        )

        ldap_group.add_argument(
            '-S', '--ssl', dest='ssl', action="store_true",
            help="Using ldaps:// instead of ldap://."
        )

        ldap_group.add_argument(
            '--no-ssl-verify', dest='ssl_no_verify', action="store_true",
            help=("Disable the cert verify if ssl has been enabled. "
                "Default is to require the cert verify."),
        )

        ldap_group.add_argument(
            '-T', '--timeout', dest="timeout", type=int,
            help=("The timeout in seconds for all LDAP operations. "
                "Default: {} seconds.").format(self.ldap_timeout),
        )

        ldap_group.add_argument(
            '-D', '--bind-dn', dest='bind_dn', required=True,
            help="The DN of the user to use to connect to the LDAP server.",
        )

        # Password stuff
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

        if self.args.ssl:
            self.ldap_use_ssl = True
        if self.args.port:
            self.ldap_port = self.args.port
        elif self.ldap_use_ssl:
            self.ldap_port = self.default_ldap_port_ssl
        else:
            self.ldap_port = self.default_ldap_port
        if self.args.ssl_no_verify:
            self.ldap_ssl_verify = CERT_NONE
        if self.args.timeout:
            self.ldap_timeout = self.args.timeout

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
    def __call__(self):
        return self.run()

    # -------------------------------------------------------------------------
    def init_ldap(self):

        # Init Tls object
        tls = Tls(validate=self.ldap_ssl_verify)

        # Init LDAP Server object
        ldap_server = Server(
            self.host, port=self.ldap_port, use_ssl=self.ldap_use_ssl,
            tls = tls, mode=IP_V4_PREFERRED, connect_timeout=self.ldap_timeout)

        # Init LDAP connection object
        self.ldap = Connection(
            ldap_server, user=self.bind_dn, password=self.bind_pw,
            auto_bind=AUTO_BIND_NONE, lazy=True, auto_range=True,
            raise_exceptions=True
        )

        if self.verbose > 2:
            LOG.debug("LDAP connection: {}".format(pp(self.ldap)))

    # -------------------------------------------------------------------------
    def pre_run(self):

        self.init_ldap()

        LOG.debug("Binding local address for LDAP requests ...")
        try:
            self.ldap.bind()
        except LDAPPasswordIsMandatoryError as e:
            msg = "Please provide a password - " + str(e)
            self.handle_error(msg, e.__class__.__name__)
            self.exit(1)

    # -------------------------------------------------------------------------
    def ldap_search(self, obj_classes=None, query_filter='', dn=None, scope=SUBTREE, attributes=ALL_ATTRIBUTES):

        if not obj_classes:
            obj_classes = ['*']
        elif not isinstance(obj_classes, list):
            obj_classes = [obj_classes]

        oc_filter_list = []
        for oc in obj_classes:
            oc_filter_list.append('(objectClass={})'.format(oc))
        oc_filter = ''
        if len(oc_filter_list) == 1:
            oc_filter = oc_filter_list[0]
        else:
            oc_filter = '(|' + ''.join(oc_filter_list) + ')'

        used_filter = oc_filter
        if query_filter:
            used_filter = '(& ' + oc_filter + ' ' + query_filter + ' )'

        if dn is None:
            dn = self.ldap_base_dn

        if self.verbose > 1:
            msg = 'Searching:\n'
            msg += '  Filter:      {}\n'.format(used_filter)
            msg += '  Search base: {}\n'.format(dn)
            msg += '  Attributes:  {}'.format(pp(attributes))
            LOG.debug(msg)

        self.ldap.search(dn, used_filter, search_scope=scope, attributes=attributes)
        #entries = self.ldap.entries
        entries = []
        for entry in self.ldap.entries:
            e = {}
            e['entry_dn'] = entry.entry_dn
            for attr in entry:
                key = attr.key
                if key.lower() == 'objectclass':
                    e['objectClass'] = attr.values
                else:
                    e[key] = attr.values
            entries.append(e)

        if self.verbose > 2:
            LOG.debug("Found entries:\n{}".format(pp(entries)))

        return entries

    # -------------------------------------------------------------------------
    def post_run(self):
        """
        Dummy function to run after the main routine.
        Could be overwritten by descendant classes.

        """

        if self.verbose > 1:
            LOG.debug("executing post_run() ...")

        if self.ldap:
            LOG.debug("Unbinding from the LDAP servers ...")
            self.ldap.unbind()
        self.ldap = None

    # -------------------------------------------------------------------------
    def explore(self):

        LOG.debug("Trying to explore the state of the application agreements ...")

        agreement_class = "nsDS5ReplicationAgreement"
        entries = self.ldap_search(obj_classes=agreement_class, attributes=ALL_ATTRIBUTES)

        results = []
        msgs = []
        total_status = 0

        re_status = re.compile(r'^[^\(]*\((-?\d+)\)')

        for entry in entries:
            e = {}
            for key in entry:
                if key.lower() == 'nsds5replicalastupdatestatusjson':
                    for val in entry[key]:
                        e['last_update_status_data'] = json.loads(val)
                        break
                elif key.lower() == 'nsds5replicahost':
                    e['replica_host'] = entry[key][0]
                elif key.lower() == 'nsds5replicalastupdatestatus':
                    e['last_update_status'] = entry[key][0]
                elif key.lower() == 'nsds5replicalastupdatestart':
                    e['last_update_start'] = entry[key][0]
                elif key.lower() == 'nsds5replicalastupdateend':
                    e['last_update_end'] = entry[key][0]

            statuscode = None
            if 'last_update_status_data' in e:
                data = e['last_update_status_data']
                statuscode = int(data['repl_rc'])
            else:
                match = re_status.match(e['last_update_status'])
                if match:
                    statuscode = int(match.group(1))
            LOG.debug("Found status code {}".format(statuscode))
            e['status_code'] = statuscode

            if statuscode:
                total_status = 2

            results.append(e)

            dt = e['last_update_start'].isoformat(' ', 'seconds')
            msg = "Replication to {host}, Last Operation {lo}, Status: {st}.".format(
                    host=e['replica_host'], lo=dt, st=e['last_update_status'])
            msgs.append(msg)

        self.status_msg = '\n'.join(msgs)
        self.status_code = total_status

        if self.verbose > 1:
            LOG.debug("Result of searching:\n{}".format(pp(results)))

    # -------------------------------------------------------------------------
    def run(self):

        LOG.debug("And here wo go ...")

        self.pre_run()

        try:
            self.explore()
        except Exception as e:
            self.handle_error(str(e), e.__class__.__name__, True)
            msg = "Got a {cl} - {e}".format(cl=e.__class__.__name__, e=e)
            app.nagios_exit(3, msg)
        finally:
            self.post_run()

        LOG.debug("And here we end.")
        app.nagios_exit(self.status_code, self.status_msg)


# =============================================================================

app = Check389dsReplicatsApp()
if app.verbose:
    print(app)
app()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
