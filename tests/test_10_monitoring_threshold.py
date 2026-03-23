#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on monitoring.threshold.

In this test case the MonitoringThreshold object is tested.

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

LOG = logging.getLogger("test_monitoring_threshold")


# =============================================================================
class TestMonitoringThreshold(MonitoringScriptsTestcase):
    """Testcase class for testing  MonitoringThreshold object."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_init(self):
        """Test init of a monitoring.MonitoringThreshold."""
        LOG.info(self.get_method_doc())

        from monitoring import MonitoringThreshold

        threshold = MonitoringThreshold()

        if self.verbose > 2:
            LOG.debug("Initialized object:\n" + pp(threshold.as_dict()))

        LOG.debug("Test, whether warning is not set.")
        self.assertFalse(threshold.warning.is_set)

        LOG.debug("Test, whether critical is not set.")
        self.assertFalse(threshold.critical.is_set)

        if self.verbose >= 1:
            print()

        LOG.debug("Set warning and critical to ''.")
        threshold.set_thresholds(warning="", critical="")

        LOG.debug("Test, whether warning is not set.")
        self.assertFalse(threshold.warning.is_set)

        LOG.debug("Test, whether critical is not set.")
        self.assertFalse(threshold.critical.is_set)

    # -------------------------------------------------------------------------
    def test_use_ranges(self):
        """Test init of a monitoring.MonitoringThreshold with ranges."""
        LOG.info(self.get_method_doc())

        from monitoring import MonitoringThreshold

        warn_value = 80
        crit_value = 90

        threshold = MonitoringThreshold(warning=f"{warn_value}", critical=f"{crit_value}")

        if self.verbose > 2:
            LOG.debug("Initialized object:\n" + pp(threshold.as_dict()))

        LOG.debug("Test, whether warning is set.")
        self.assertTrue(threshold.warning.is_set)

        LOG.debug("Test, whether critical is set.")
        self.assertTrue(threshold.critical.is_set)

        LOG.debug("Test, whether warning.start == 0.")
        self.assertEqual(threshold.warning.start, 0)

        LOG.debug(f"Test, whether warning.end == {warn_value}.")
        self.assertEqual(threshold.warning.end, warn_value)

        LOG.debug("Test, whether critical.start == 0.")
        self.assertEqual(threshold.critical.start, 0)

        LOG.debug(f"Test, whether critical.end == {crit_value}.")
        self.assertEqual(threshold.critical.end, crit_value)

    # -------------------------------------------------------------------------
    def test_bad_ranges(self):
        """Test init of a monitoring.MonitoringThreshold with bad ranges."""
        LOG.info(self.get_method_doc())

        from monitoring import MonitoringThreshold
        from monitoring import InvalidRangeError

        LOG.debug("Try create Threshold wih warning='total', critical='rubbish'.")
        with self.assertRaises(InvalidRangeError) as cm:
            threshold = MonitoringThreshold(warning="total", critical="rubbish")
            LOG.error(f"This should never be visible: {threshold!r}.")
        e = cm.exception
        LOG.debug("{c} raised: {e}".format(c=e.__class__.__name__, e=e))

    # -------------------------------------------------------------------------
    def test_get_status(self):
        """Test get status of a monitoring.MonitoringThreshold by a value."""
        LOG.info(self.get_method_doc())

        from monitoring import MonitoringThreshold

        test_data = (
            {
                "warning": "5:33",
                "tests": (
                    (-1, "WARNING"),
                    (4, "WARNING"),
                    (4.9999, "WARNING"),
                    (5, "OK"),
                    (14.21, "OK"),
                    (33, "OK"),
                    (33.01, "WARNING"),
                    (10231, "WARNING"),
                ),
            },
            {
                "warning": "~:30",
                "critical": "~:60",
                "tests": (
                    (-1, "OK"),
                    (4, "OK"),
                    (29.999999, "OK"),
                    (30, "OK"),
                    (30.1, "WARNING"),
                    (59.9, "WARNING"),
                    (60, "WARNING"),
                    (60.00001, "CRITICAL"),
                    (10231, "CRITICAL"),
                ),
            },
            {
                "critical": "~:25",
                "tests": (
                    (-1, "OK"),
                    (4, "OK"),
                    (24.999999, "OK"),
                    (25, "OK"),
                    (25.001, "CRITICAL"),
                    (31001, "CRITICAL"),
                ),
            },
            {
                "warning": "10:25",
                "critical": "~:25",
                "tests": (
                    (-1, "WARNING"),
                    (4, "WARNING"),
                    (4.9999, "WARNING"),
                    (10, "OK"),
                    (14.21, "OK"),
                    (25, "OK"),
                    (25.01, "CRITICAL"),
                    (31001, "CRITICAL"),
                ),
            },
            {
                "warning": "@10:25",
                "critical": "10:",
                "tests": (
                    (-1, "CRITICAL"),
                    (4, "CRITICAL"),
                    (4.9999, "CRITICAL"),
                    (10, "WARNING"),
                    (14.21, "WARNING"),
                    (25, "WARNING"),
                    (25.01, "OK"),
                    (31001, "OK"),
                ),
            },
        )

        for test_token in test_data:
            if self.verbose >= 1:
                print()

            if "warning" in test_token:
                w = test_token["warning"]
            else:
                w = None

            if "critical" in test_token:
                c = test_token["critical"]
            else:
                c = None

            LOG.info(f"Testing threshold with warning={w!r} and critical={c!r}.")
            threshold = MonitoringThreshold(warning=w, critical=c)

            for test_pair in test_token["tests"]:
                val = test_pair[0]
                exp = test_pair[1]
                status_exp = threshold.errors[exp]

                LOG.debug(f"Test threshold against {val} => {status_exp} ({exp!r}).")
                status_got = threshold.get_status(val)
                LOG.debug(f"Got status {status_got}.")
                self.assertEqual(status_exp, status_got)


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestMonitoringThreshold("test_init", verbose))
    suite.addTest(TestMonitoringThreshold("test_use_ranges", verbose))
    suite.addTest(TestMonitoringThreshold("test_bad_ranges", verbose))
    suite.addTest(TestMonitoringThreshold("test_get_status", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
