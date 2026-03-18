#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on base classes of monitoring.py.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 - 2026 Frank Brehm, Berlin
@license: GPL3
"""

import logging
import unittest

from general import MonitoringScriptsTestcase, get_arg_verbose, init_root_logger

LOG = logging.getLogger("test_monitoring_base")


# =============================================================================
class TestMonitoringBase(MonitoringScriptsTestcase):
    """Testcase class for testing basic stuff of monitoring.py."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_import(self):
        """Test importing module monitoring."""
        LOG.info(self.get_method_doc())

        import monitoring

        LOG.debug(
            "Version of monitoring: {!r}".format(monitoring.__version__)
        )


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestMonitoringBase("test_import", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
