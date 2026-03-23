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

from general import MonitoringScriptsTestcase
from general import get_arg_verbose
from general import init_root_logger
from general import pp

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
            {
                "range_str": "6",
                "end": 6,
                "end_infinity": False,
            },
            {
                "range_str": "-7:23",
                "start": -7,
                "start_infinity": False,
                "end": 23,
                "end_infinity": False,
            },
            {
                "range_str": ":5.75",
                "end": 5.75,
                "end_infinity": False,
            },
            {
                "range_str": "~:-95.99",
                "start": None,
                "start_infinity": True,
                "end": -95.99,
                "end_infinity": False,
            },
            {
                "range_str": "10:",
                "start": 10,
                "start_infinity": False,
            },
            {
                "range_str": "123456789012345:",
                "start": 123456789012345,
                "start_infinity": False,
            },
            {
                "range_str": "~:0",
                "start": None,
                "start_infinity": True,
                "end": 0,
                "end_infinity": False,
            },
            {
                "range_str": "@0:657.8210567",
                "end": 657.8210567,
                "end_infinity": False,
                "alert_on": INSIDE,
            },
            {
                "range_str": "1:1",
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

    # -------------------------------------------------------------------------
    def test_operator_in(self):
        """Test of 'in' and 'not in' operators."""
        LOG.info(self.get_method_doc())

        from monitoring.range import MonitoringRange
        from monitoring.range import RangeAlertOn

        mon_range = MonitoringRange("6")
        LOG.debug("Initialized range:\n" + pp(mon_range.as_dict()))

        test_data = (
            (-0.1, False),
            (0, True),
            (0.1, True),
            (4, True),
            (5.99, True),
            (6, True),
            (6.01, False),
        )

        for token in test_data:
            val = token[0]
            exp = token[1]

            LOG.debug(f"Test value {val} in range {str(mon_range)!r}: {exp}")
            if exp:
                self.assertIn(val, mon_range)
            else:
                self.assertNotIn(val, mon_range)

        if self.verbose >= 1:
            print()
        mon_range = MonitoringRange("@6")
        LOG.debug("Initialized inverted range:\n" + pp(mon_range.as_dict()))

        test_data = (
            (-0.1, True),
            (0, False),
            (0.1, False),
            (4, False),
            (5.99, False),
            (6, False),
            (6.01, True),
        )

        for token in test_data:
            val = token[0]
            exp = token[1]

            LOG.debug(f"Test value {val} outside of range {str(mon_range)!r}: {exp}")
            if exp:
                self.assertIn(val, mon_range)
            else:
                self.assertNotIn(val, mon_range)

    # -------------------------------------------------------------------------
    def test_check_value(self):
        """Test checking different values."""
        LOG.info(self.get_method_doc())

        from monitoring.range import MonitoringRange
        from monitoring.range import RangeAlertOn

        test_data = (
            (
                "-7:23", (
                    (-23, False),
                    (-7, True),
                    (-1, True),
                    (0, True),
                    (4, True),
                    (23, True),
                    (23.1, False),
                    (79.999999, False),
                ),
            ),
            (
                ":5.75", (
                    (-1, False),
                    (0, True),
                    (4, True),
                    (5.75, True),
                    (5.7501, False),
                    (6, False),
                ),
            ),
            (
                "~:-95.99", (
                    (-1001341, True),
                    (-96, True),
                    (-95.999, True),
                    (-95.99, True),
                    (-95.989, False),
                    (-95, False),
                    (0, False),
                    (5.7501, False),
                ),
            ),
            (
                "10:", (
                    (-95.999, False),
                    (-1, False),
                    (0, False),
                    (9.91, False),
                    (10, True),
                    (11.11, True),
                    (123456789012346, True),
                ),
            ),
            (
                "123456789012345:", (
                    (-95.999, False),
                    (0, False),
                    (123456789012344.91, False),
                    (123456789012345, True),
                    (123456789012345.61, True),
                    (123456789012346, True),
                ),
            ),
            (
                "~:0", (
                    (-123456789012344.91, True),
                    (-1, True),
                    (0, True),
                    (.001, False),
                    (123456789012345, False),
                ),
            ),
            (
                "@0:657.8210567", (
                    (-134151, True),
                    (-1, True),
                    (0, False),
                    (.001, False),
                    (657.8210567, False),
                    (657.9, True),
                    (123456789012345, True),
                ),
            ),
            (
                "1:1", (
                    (-1, False),
                    (0, False),
                    (0.99, False),
                    (1, True),
                    (1.001, False),
                    (5.2, False),
                ),
            ),
        )

        for token in test_data:
            if self.verbose >= 1:
                print()

            range_str = token[0]
            test_tokens = token[1]

            mon_range = MonitoringRange(range_str)

            for test_pair in test_tokens:

                val = test_pair[0]
                exp = test_pair[1]
                if exp:
                    if mon_range.invert_match:
                        LOG.debug(f"Test value {val} outside of range {str(mon_range)!r}.")
                    else:
                        LOG.debug(f"Test value {val} in range {str(mon_range)!r}.")
                    self.assertIn(val, mon_range)
                else:
                    if mon_range.invert_match:
                        LOG.debug(f"Test value {val} in range {str(mon_range)!r}.")
                    else:
                        LOG.debug(f"Test value {val} not in range {str(mon_range)!r}.")
                    self.assertNotIn(val, mon_range)


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestMonitoringRange("test_init", verbose))
    suite.addTest(TestMonitoringRange("test_operator_in", verbose))
    suite.addTest(TestMonitoringRange("test_check_value", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 list
