#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on monitoring.py.

In this test case the base monitoring range is tested.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 - 2026 Frank Brehm, Berlin
@license: GPL3
"""

import logging
import unittest
from pathlib import Path

from general import MonitoringScriptsTestcase, pp, get_arg_verbose, init_root_logger

LOG = logging.getLogger("test_monitoring_range")


# =============================================================================
class TestMonitoringRange(MonitoringScriptsTestcase):
    """Testcase class for testing  monitoring orange of monitoring.py."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_init(self):
        """Test init of a monitoring.MonitoringRange."""
        LOG.info(self.get_method_doc())

        from monitoring.errors import InvalidRangeError
        from monitoring.obj import MonitoringObject
        from monitoring.range import MonitoringRange
        from monitoring.range import RangeAlertOn

        OUTSIDE = RangeAlertOn.OUTSIDE
        INSIDE = RangeAlertOn.INSIDE

        mon_range = MonitoringRange()

        LOG.debug("Initialized range:\n" + pp(mon_range.as_dict()))
        self.assertIsInstance(mon_range, MonitoringObject)

        bad_init_data = (
            ":",
            "1:~",
            "foo",
            "1-10",
	        "10:~",
	        "1-10:2.4",
            "2:1",
        )

        for token in bad_init_data:
            LOG.debug(f"Trying to init a MonitoringRange from {token!r} ...")

            with self.assertRaises(InvalidRangeError) as cm:
                mon_range = MonitoringRange(token)
                LOG.error("Wrong initialized range:\n" + pp(mon_range.as_dict()))
            e = cm.exception
            LOG.debug("{c} raised: {e}".format(c=e.__class__.__name__, e=e))

        if self.verbose > 1:
            print()

        good_init_data = (
            {"range_str": "6",
             "end": 6,
             "end_infinity": False,
            },
            {"range_str": "-7:23",
             "start": -7,
             "start_infinity": False,
             "end": 23,
             "end_infinity": False,
            },
            {"range_str": ":5.75",
             "end": 5.75,
             "end_infinity": False,
            },
            {"range_str": "~:-95.99",
             "start": None,
             "start_infinity": True,
             "end": -95.99,
             "end_infinity": False,
            },
            {"range_str": "10:",
             "start": 10,
             "start_infinity": False,
            },
            {"range_str": "123456789012345:",
             "start": 123456789012345,
             "start_infinity": False,
            },
            {"range_str": "~:0",
             "start": None,
             "start_infinity": True,
             "end": 0,
             "end_infinity": False,
            },
            {"range_str": "@0:657.8210567",
             "end": 657.8210567,
             "end_infinity": False,
             "alert_on": INSIDE,
            },
            {"range_str": "1:1",
             "start": 1,
             "start_infinity": False,
             "end": 1,
             "end_infinity": False,
            },
        )

        for test_data in good_init_data:
            if "start" not in test_data:
                test_data["start"] = 0
            if "start_infinity" not in test_data:
                test_data["start_infinity"] = False
            if "end" not in test_data:
                test_data["end"] = None
            if "end_infinity" not in test_data:
                test_data["end_infinity"] = True
            if "alert_on" not in test_data:
                test_data["alert_on"] = OUTSIDE

            msg = "Testing for range {range_str!r} -  start: {start!r}, "
            msg += "start_infinity: {start_infinity!r}, end: {end!r}, "
            msg += "end_infinity: {end_infinity!r}, alert_on: {alert_on!r}."
            LOG.debug(msg.format(**test_data))

            mon_range = MonitoringRange(test_data["range_str"])
            if self.verbose > 2:
                LOG.debug("Initialized range:\n" + pp(mon_range.as_dict()))
            LOG.debug("Generated range string: {!r}.".format(str(mon_range)))

            # self.assertEqual(str(mon_range), test_data["range_str"])
            self.assertEqual(mon_range.start, test_data["start"])
            self.assertEqual(mon_range.start_infinity, test_data["start_infinity"])
            self.assertEqual(mon_range.end, test_data["end"])
            self.assertEqual(mon_range.end_infinity, test_data["end_infinity"])
            self.assertEqual(mon_range.alert_on, test_data["alert_on"])


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestMonitoringRange("test_init", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
