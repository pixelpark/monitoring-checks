#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@summary: Test script (and module) for unit tests on monitoring.py.

In this test case the base monitoring object is tested.

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2023 - 2026 Frank Brehm, Berlin
@license: GPL3
"""

import logging
import unittest
from pathlib import Path

from general import MonitoringScriptsTestcase, pp, get_arg_verbose, init_root_logger

LOG = logging.getLogger("test_monitoring_object")


# =============================================================================
class TestMonitoringObject(MonitoringScriptsTestcase):
    """Testcase class for testing  monitoring objectof monitoring.py."""

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        if self.verbose >= 1:
            print()

    # -------------------------------------------------------------------------
    def test_init(self):
        """Test init of a monitoring.MonitoringObjec."""
        LOG.info(self.get_method_doc())

        from monitoring import MonitoringObject

        base_obj = MonitoringObject()

        LOG.debug("Initialized object:\n" + pp(base_obj.as_dict()))

        states = (
            ("status_ok", 0),
            ("status_warning", 1),
            ("status_critical", 2),
            ("status_unknown", 3),
            ("status_dependent", 4),
        )

        for token in states:
            status = token[0]
            status_id = token[1]

            LOG.debug(f"Test {status} is {status_id} ...")
            got_id = getattr(base_obj, status)
            LOG.debug(f"Got ID {got_id}.")
            self.assertEqual(status_id, got_id)

        if self.verbose > 1:
            print()

        LOG.debug("Testing for states are readonly ...")
        for token in states:
            status = token[0]

            with self.assertRaises(AttributeError) as cm:
                setattr(base_obj, status, 99)
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

    suite.addTest(TestMonitoringObject("test_init", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
