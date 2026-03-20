#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@summary: This module provides a basic monitoring check class.

@author:    Frank Brehm
@contact:   frank@brehm-online.com

@copyright: © 2023 - 2026 Frank Brehm, Berlin, Germany
@license: GPL3+
@date:      2026-03-20

"""

from __future__ import print_function

import argparse
import logging
import os
from pathlib import Path

# Own modules

LOG = logging.getLogger(__name__)

__version__ = "0.9.0"


# =============================================================================
class DirectoryOptionAction(argparse.Action):
    """An argparse action for directories."""

    # -------------------------------------------------------------------------
    def __init__(self, option_strings, must_exists=True, writeable=False, *args, **kwargs):
        """Initialise a DirectoryOptionAction object."""
        self.must_exists = bool(must_exists)
        self.writeable = bool(writeable)
        if self.writeable:
            self.must_exists = True

        super(DirectoryOptionAction, self).__init__(*args, **kwargs, option_strings=option_strings)

    # -------------------------------------------------------------------------
    def __call__(self, parser, namespace, given_path, option_string=None):
        """Parse the directory option."""
        path = Path(given_path)
        if not path.is_absolute():
            msg = "The path {!r} must be an absolute path.".format(given_path)
            raise argparse.ArgumentError(self, msg)

        if self.must_exists:

            if not path.exists():
                msg = "The directory {!r} does not exists.".format(str(path))
                raise argparse.ArgumentError(self, msg)

            if not path.is_dir():
                msg = "The given path {!r} exists, but is not a directory.".format(str(path))
                raise argparse.ArgumentError(self, msg)

            if not os.access(str(path), os.R_OK) or not os.access(str(path), os.X_OK):
                msg = "The given directory {!r} is not readable.".format(str(path))
                raise argparse.ArgumentError(self, msg)

            if self.writeable and not os.access(str(path), os.W_OK):
                msg = "The given directory {!r} is not writeable.".format(str(path))
                raise argparse.ArgumentError(self, msg)

        setattr(namespace, self.dest, path)


# =============================================================================
class LogFileOptionAction(argparse.Action):
    """An argparse action for logfiles."""

    # -------------------------------------------------------------------------
    def __init__(self, option_strings, must_exists=True, writeable=False, *args, **kwargs):
        """Initialise a LogFileOptionAction object."""
        self.must_exists = bool(must_exists)
        self.writeable = bool(writeable)
        super(LogFileOptionAction, self).__init__(*args, **kwargs, option_strings=option_strings)

    # -------------------------------------------------------------------------
    def __call__(self, parser, namespace, values, option_string=None):
        """Parse the logfile option."""
        if values is None:
            setattr(namespace, self.dest, None)
            return

        path = Path(values)
        logdir = path.parent

        # Checking the parent directory of the Logfile
        if self.must_exists:
            if not logdir.exists():
                msg = "Directory {!r} does not exists.".format(str(logdir))
                raise argparse.ArgumentError(self, msg)
            if not logdir.is_dir():
                msg = "Path {!r} exists, but is not a directory.".format(str(logdir))
                raise argparse.ArgumentError(self, msg)
            if self.writeable and not os.access(str(logdir), os.W_OK):
                msg = "The directory {!r} is not writeable.".format(str(logdir))
                raise argparse.ArgumentError(self, msg)

        # Checking logfile, if it is already existing
        if path.exists():
            if not path.is_file():
                msg = "File {!r} is not a regular file.".format(values)
                raise argparse.ArgumentError(self, msg)
            if not os.access(values, os.R_OK):
                msg = "File {!r} is not readable.".format(values)
                raise argparse.ArgumentError(self, msg)
            if self.writeable and not os.access(str(path), os.W_OK):
                msg = "The given file {!r} is not writeable.".format(values)
                raise argparse.ArgumentError(self, msg)
        elif self.must_exists:
            msg = "The file {!r} does not exists.".format(str(path))
            raise argparse.ArgumentError(self, msg)

        setattr(namespace, self.dest, path.resolve())


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
