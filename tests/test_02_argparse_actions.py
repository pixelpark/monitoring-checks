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
import unittest
from pathlib import Path

from general import MonitoringScriptsTestcase, pp, get_arg_verbose, init_root_logger

LOG = logging.getLogger("test_argparse_actions")


# =============================================================================
class TestArgparseActions(MonitoringScriptsTestcase):
    """Testcase class for testing argparse actions of monitoring.py."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_directory_option(self):
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
        LOG.debug("Testing directories providing bad luck ...")
        bad_test_dirs = (
            ("uhu-banane", "--arbitrary-dir"),
            ("/uhu-banane", "--existing-dir"),
            ("/etc", "--writable-dir"),
        )

        for test_data in bad_test_dirs:
            if self.verbose > 1:
                print()
            test_dir = test_data[0]
            option = test_data[1]

            LOG.debug("Testing {o} => {d!r}".format(o=option, d=test_dir))

            with self.assertRaises(argparse.ArgumentError) as cm:
                args = parser.parse_args([option, test_dir])
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

    suite.addTest(TestArgparseActions("test_directory_option", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
