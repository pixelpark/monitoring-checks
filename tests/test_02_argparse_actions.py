#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on monitoring.py.

In this test case the argparse actions are tested.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 - 2026 Frank Brehm, Berlin
@license: GPL3
"""

import argparse
import logging
import os
import shutil
import sys
import unittest
from pathlib import Path

from general import MonitoringScriptsTestcase
from general import get_arg_verbose
from general import init_root_logger
from general import pp

LOG = logging.getLogger("test_argparse_actions")


# =============================================================================
@unittest.skipIf(
    sys.version_info.major < 3 or sys.version_info.minor < 9,
    "argparse_action tests ar not supported in Python < 3.9",
)
class TestArgparseActions(MonitoringScriptsTestcase):
    """Testcase class for testing argparse actions of monitoring.py."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

        self.protected_dir = self.tests_dir / ".protected-dir"
        self.protected_file = self.tests_dir / ".protected-file"
        self.test_log = self.tests_dir / "test.log"

    # -------------------------------------------------------------------------
    def tearDown(self):
        """Tear down routine for calling each particular test method."""
        if self.protected_dir.exists():
            if self.verbose > 1:
                print()
            LOG.debug(f"Removing {str(self.protected_dir)!r} ...")
            self.protected_dir.rmdir()

        if self.protected_file.exists():
            if self.verbose > 1:
                print()
            LOG.debug(f"Removing {str(self.protected_file)!r} ...")
            self.protected_file.unlink()

    # -------------------------------------------------------------------------
    def test_directory_action(self):
        """Test monitoring.DirectoryOptionAction."""
        LOG.info(self.get_method_doc())

        from monitoring import DirectoryOptionAction

        parser = argparse.ArgumentParser(
            prog=self.appname,
            exit_on_error=False,
            description="Testing DirectoryOptionAction...",
        )

        parser.add_argument(
            "--arbitrary-dir",
            metavar="DIRECTORY",
            must_exists=False,
            action=DirectoryOptionAction,
            help="An arbitrary directory.",
        )

        parser.add_argument(
            "--existing-dir",
            metavar="DIRECTORY",
            action=DirectoryOptionAction,
            help="An existing directory.",
        )

        parser.add_argument(
            "--writable-dir",
            metavar="DIRECTORY",
            action=DirectoryOptionAction,
            writeable=True,
            help="An existing writable directory.",
        )

        if self.verbose > 1:
            print()

        LOG.debug("Testing directories providing good luck ...")
        good_test_dirs = (
            ("/uhu-banane", "--arbitrary-dir"),
            (str(Path.cwd()), "--existing-dir"),
            (str(Path.cwd()), "--writable-dir"),
        )

        for test_data in good_test_dirs:
            if self.verbose > 1:
                print()
            test_dir = test_data[0]
            option = test_data[1]
            arg = option.replace("--", "", 1).replace("-", "_")

            LOG.debug("Testing {o} => {d!r}".format(o=option, d=test_dir))

            args = parser.parse_args([option, test_dir])
            got_dir = getattr(args, arg)
            LOG.debug("Got directory: {!r}.".format(got_dir))
            self.assertIsInstance(got_dir, Path)
            self.assertEqual(test_dir, str(got_dir))

        if self.verbose > 1:
            print()

        LOG.debug(f"Creating {str(self.protected_dir)!r} ...")
        self.protected_dir.mkdir(mode=0o000)

        LOG.debug("Testing directories providing bad luck ...")
        bad_test_dirs = [
            ("uhu-banane", "--arbitrary-dir"),
            ("/uhu-banane", "--existing-dir"),
        ]

        if os.geteuid() != 0:
            bad_test_dirs.append((str(self.protected_dir), "--writable-dir"))

        for test_data in bad_test_dirs:
            if self.verbose > 1:
                print()
            test_dir = test_data[0]
            option = test_data[1]

            LOG.debug(f"Testing {option} => {test_dir!r}")

            with self.assertRaises(argparse.ArgumentError) as cm:
                args = parser.parse_args([option, test_dir])
                LOG.error("Got parsed arguments: " + pp(args))
            e = cm.exception
            LOG.debug("{c} raised: {e}".format(c=e.__class__.__name__, e=e))

    # -------------------------------------------------------------------------
    def test_logfile_action(self):
        """Test monitoring.LogFileOptionAction."""
        LOG.info(self.get_method_doc())

        from monitoring import LogFileOptionAction

        parser = argparse.ArgumentParser(
            prog=self.appname,
            exit_on_error=False,
            description="Testing LogFileOptionAction...",
        )

        parser.add_argument(
            "--arbitrary-logfile",
            metavar="FILE",
            must_exists=False,
            writeable=False,
            action=LogFileOptionAction,
            help="An arbitrary logfile.",
        )

        parser.add_argument(
            "--arbitrary-rw-logfile",
            metavar="FILE",
            must_exists=False,
            writeable=True,
            action=LogFileOptionAction,
            help="An arbitrary writeable logfile.",
        )

        parser.add_argument(
            "--existing-logfile",
            metavar="FILE",
            must_exists=True,
            writeable=False,
            action=LogFileOptionAction,
            help="An existing logfile.",
        )

        parser.add_argument(
            "--existing-rw-logfile",
            metavar="FILE",
            must_exists=True,
            writeable=True,
            action=LogFileOptionAction,
            help="An existing writeable logfile.",
        )

        if self.verbose > 1:
            print()

        LOG.debug("Testing logfiles providing good luck ...")
        good_test_logfiles = (
            ("/var/log/uhu-banane.log", "--arbitrary-logfile"),
            ("/bla-blub/uhu-banane.log", "--arbitrary-logfile"),
            (str(self.tests_dir / "test-new.log"), "--arbitrary-rw-logfile"),
            (str(self.test_log), "--existing-logfile"),
            (str(self.test_log), "--existing-rw-logfile"),
        )

        for test_data in good_test_logfiles:
            if self.verbose > 1:
                print()
            test_file = test_data[0]
            option = test_data[1]
            arg = option.replace("--", "", 1).replace("-", "_")

            LOG.debug("Testing {o} => {d!r}".format(o=option, d=test_file))

            args = parser.parse_args([option, test_file])
            got_file = getattr(args, arg)
            LOG.debug("Got logfile: {!r}.".format(got_file))
            self.assertIsInstance(got_file, Path)
            self.assertEqual(test_file, str(got_file))

        if self.verbose > 1:
            print()

        LOG.debug(f"Creating {str(self.protected_file)!r} ...")
        shutil.copyfile(str(self.test_log), str(self.protected_file))
        self.protected_file.chmod(0o400)

        LOG.debug("Testing logfiles providing bad luck ...")

        bad_test_logfiles = [
            ("/dev/null", "--arbitrary-logfile"),
            ("/bla-blub/uhu-banane.log", "--existing-logfile"),
            ("/var/log/messages/uhu-banane.log", "--existing-logfile"),
            ("/var/log/uhu-banane.log", "--existing-logfile"),
        ]

        if os.geteuid() != 0:
            bad_test_logfiles.append((str(self.protected_file), "--existing-rw-logfile"))
            bad_test_logfiles.append(("/etc/shadow", "--arbitrary-logfile"))

        for test_data in bad_test_logfiles:
            if self.verbose > 1:
                print()
            test_file = test_data[0]
            option = test_data[1]

            LOG.debug("Testing {o} => {d!r}".format(o=option, d=test_file))

            with self.assertRaises(argparse.ArgumentError) as cm:
                args = parser.parse_args([option, test_file])
                LOG.error("Got parsed arguments: " + pp(args))
            e = cm.exception
            LOG.debug("{c} raised: {e}".format(c=e.__class__.__name__, e=e))


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestArgparseActions("test_directory_action", verbose))
    suite.addTest(TestArgparseActions("test_logfile_action", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
