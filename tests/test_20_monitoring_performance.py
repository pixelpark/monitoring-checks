#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on monitoring.perf.

In this test case the MonitoringPerformance object is tested.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 - 2026 Frank Brehm, Berlin
@license: GPL3
"""

import logging
import unittest

from general import MonitoringScriptsTestcase
from general import get_arg_verbose
from general import init_root_logger
from general import pp

LOG = logging.getLogger("test_monitoring_performance")


# =============================================================================
class TestMonitoringPerformance(MonitoringScriptsTestcase):
    """Testcase class for testing  MonitoringPerformance object."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_init(self):
        """Test init of a monitoring.MonitoringPerformance."""
        LOG.info(self.get_method_doc())

        from monitoring import MonitoringPerformance
        from monitoring import MonitoringPerformanceError

        perf = MonitoringPerformance("sample", 0)

        if self.verbose > 2:
            LOG.debug("Initialized object:\n" + pp(perf.as_dict()))

        if self.verbose >= 1:
            print()

        LOG.info("Test init of MonitoringPerformance with bad arguments.")

        bad_init_data = (
            [],
            [""],
            ["", 0],
            [" "],
            [" ", 0],
            ["sample"],
            ["sample", "bla"],
        )

        for args in bad_init_data:
            LOG.debug(f"Trying to init MonitoringPerformance with: {pp(args)}.")
            with self.assertRaises((MonitoringPerformanceError, TypeError)) as cm:
                perf = MonitoringPerformance(*args)
                LOG.error(f"This should never be visible: {perf!r}.")
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

    suite.addTest(TestMonitoringPerformance("test_init", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
