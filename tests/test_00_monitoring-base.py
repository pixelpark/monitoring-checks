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

    # -------------------------------------------------------------------------
    def test_to_unicode(self):
        """Test module function to_unicode()."""
        LOG.info(self.get_method_doc())

        from monitoring import to_unicode

        data = []
        data.append((None, None))
        data.append((1, 1))
        data.append(("a", "a"))
        data.append((b"a", "a"))

        for pair in data:

            src = pair[0]
            tgt = pair[1]
            result = to_unicode(src)
            LOG.debug("Testing to_unicode(%r) => %r, result %r", src, tgt, result)

            if isinstance(src, (str, bytes)):
                self.assertIsInstance(result, str)
            else:
                self.assertNotIsInstance(result, (str, bytes))

            self.assertEqual(tgt, result)

    # -------------------------------------------------------------------------
    def test_to_utf8(self):
        """Test module function to_utf8()."""
        LOG.info(self.get_method_doc())

        from monitoring import to_utf8

        data = []
        data.append((None, None))
        data.append((1, 1))
        data.append(("a", b"a"))
        data.append((b"a", b"a"))

        for pair in data:

            src = pair[0]
            tgt = pair[1]
            result = to_utf8(src)
            LOG.debug("Testing to_utf8(%r) => %r, result %r", src, tgt, result)

            if isinstance(src, (str, bytes)):
                self.assertIsInstance(result, bytes)
            else:
                self.assertNotIsInstance(result, (str, bytes))

            self.assertEqual(tgt, result)

    # -------------------------------------------------------------------------
    def test_to_str(self):
        """Test module function to_str()."""
        LOG.info(self.get_method_doc())

        from monitoring import to_str

        data = []
        data.append((None, None))
        data.append((1, 1))
        data.append(("a", "a"))
        data.append((b"a", "a"))

        for pair in data:

            src = pair[0]
            tgt = pair[1]
            result = to_str(src)
            LOG.debug("Testing to_str(%r) => %r, result %r", src, tgt, result)

            if isinstance(src, (str, bytes)):
                self.assertIsInstance(result, str)
            else:
                self.assertNotIsInstance(result, (str, bytes))

            self.assertEqual(tgt, result)


# =============================================================================
if __name__ == "__main__":

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestMonitoringBase("test_import", verbose))
    suite.addTest(TestMonitoringBase("test_to_unicode", verbose))
    suite.addTest(TestMonitoringBase("test_to_utf8", verbose))
    suite.addTest(TestMonitoringBase("test_to_str", verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
