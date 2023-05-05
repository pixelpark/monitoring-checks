#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

# pygtail - a python "port" of logtail2
# Copyright (C) 2011 Brad Greenlee <brad@footle.org>
#
# Derived from logcheck <http://logcheck.org>
# Copyright (C) 2003 Jonathan Middleton <jjm@ixtab.org.uk>
# Copyright (C) 2001 Paul Slootman <paul@debian.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from __future__ import print_function

from os import fstat, stat
import os
from os.path import exists, getsize
import sys
import glob
import gzip
import io

__version__ = '0.16.0'

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
else:
    text_type = unicode                             # noqa


# ==============================================================================
def force_text(s, encoding='utf-8', errors='strict'):
    if isinstance(s, text_type):
        return s
    return s.decode(encoding, errors)


# ==============================================================================
class Offset:
    """Data-class to store file-offsets"""

    # --------------------------------------------------------------------------
    def __init__(self, counter, inode, offset):
        self.counter = counter
        self.inode = inode
        self.offset = offset

    # --------------------------------------------------------------------------
    def __eq__(self, other):
        return self.counter == other.counter and self.offset == other.offset

    # --------------------------------------------------------------------------
    def __lt__(self, other):
        return self.counter < other.counter or (
            self.counter == other.counter and self.offset < other.offset
        )

    # --------------------------------------------------------------------------
    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    # --------------------------------------------------------------------------
    def __gt__(self, other):
        return not self.__le__(other)

    # --------------------------------------------------------------------------
    def __ge__(self, other):
        return not self.__le__(other) or self.__eq__(other)

    # --------------------------------------------------------------------------
    def __repr__(self):
        return "Offset(counter=%d, inode=%d, offset=%d" % (
            self.counter,
            self.inode,
            self.offset,
        )


# ==============================================================================
class PygtailIteratorWithOffsets:

    # --------------------------------------------------------------------------
    def __init__(self, pygtail):
        self._pygtail = pygtail

    # --------------------------------------------------------------------------
    def __next__(self):
        return self.next()

    # --------------------------------------------------------------------------
    def __iter__(self):
        return self

    # --------------------------------------------------------------------------
    def next(self):
        next_line = self._pygtail.next()
        offset = self._pygtail._filehandle().tell()
        inode = fstat(self._pygtail._filehandle().fileno()).st_ino
        counter = self._pygtail._counter
        offset_instance = Offset(counter, inode, offset)
        return next_line, offset_instance

# ==============================================================================
class Pygtail(object):
    """
    Creates an iterable object that returns only unread lines.

    Keyword arguments:
    offset_file   File to which offset data is written (default: <logfile>.offset).
    paranoid      Update the offset file every time we read a line (as opposed to
                  only when we reach the end of the file (default: False))
    every_n       Update the offset file every n'th line (as opposed to only when
                  we reach the end of the file (default: 0))
    on_update     Execute this function when offset data is written (default False)
    copytruncate  Support copytruncate-style log rotation (default: True)
    log_patterns  List of custom rotated log patterns to match (default: None)
    full_lines    Only log when line ends in a newline `\n` (default: False)
    save_on_end   Automatically save the offset once the end of the file is reached (default: True)
    olddir        A directory containing the rotated logfiles, either as an absolute
                  path or relative to the parent directory of the logfile.
    """

    # --------------------------------------------------------------------------
    def __init__(self, filename, offset_file=None, paranoid=False, copytruncate=True,
                 every_n=0, on_update=False, read_from_end=False, log_patterns=None,
                 full_lines=False, save_on_end=True, encoding=None, olddir=None):
        self.filename = filename
        self.paranoid = paranoid
        self.every_n = every_n
        self.on_update = on_update
        self.copytruncate = copytruncate
        self.read_from_end = read_from_end
        self.log_patterns = log_patterns
        self.full_lines = full_lines
        self.save_on_end = save_on_end
        self.encoding = encoding
        self.olddir = None
        self.offset_file = offset_file or "%s.offset" % self.filename
        self.offset_file_inode = 0
        self.offset = 0
        self.since_update = 0
        self.fh = None
        self.rotated_logfile = None
        self._counter = 0

        # if offset file exists and non-empty, open and parse it
        if exists(self.offset_file) and getsize(self.offset_file):
            offset_fh = open(self.offset_file, "r")
            (self.offset_file_inode, self.offset) = \
                [int(line.strip()) for line in offset_fh]
            offset_fh.close()
            if self.offset_file_inode != stat(self.filename).st_ino or \
                    stat(self.filename).st_size < self.offset:
                # The inode has changed or filesize has reduced so the file
                # might have been rotated.
                # Look for the rotated file and process that if we find it.
                self.rotated_logfile = self._determine_rotated_logfile()
                # If copytruncate is enabled and we can't find the rotated logfile,
                # all we can do is reset.
                if self.copytruncate and self.rotated_logfile is None:
                    msg = "[pygtail] [WARN] log file was rotated to unknown location. Resetting."
                    sys.stderr.write(msg + "\n")
                    self.offset = 0
                    self.update_offset_file()

    # --------------------------------------------------------------------------
    def __del__(self):
        if self._filehandle():
            self._filehandle().close()

    # --------------------------------------------------------------------------
    def __iter__(self):
        return self

    # --------------------------------------------------------------------------
    def next(self):
        """
        Return the next line in the file, updating the offset.
        """
        try:
            line = self._get_next_line()
        except StopIteration:
            # we've reached the end of the file; if we're processing the
            # rotated log file or the file has been renamed, we can continue with the actual file;
            # otherwise update the offset file
            if self._is_new_file():
                self.rotated_logfile = None
                self.fh.close()
                self.offset = 0
                # open up current logfile and continue
                try:
                    line = self._get_next_line()
                except StopIteration:  # oops, empty file
                    if self.save_on_end:
                        self.update_offset_file()
                    raise
            else:
                if self.save_on_end:
                    self.update_offset_file()
                raise

        if self.paranoid:
            self.update_offset_file()
        elif self.every_n and self.every_n <= self.since_update:
            self.update_offset_file()

        return line

    # --------------------------------------------------------------------------
    def with_offsets(self):
        """Returns an iterator that yields lines with their internal offset state"""
        return PygtailIteratorWithOffsets(self)

    # --------------------------------------------------------------------------
    def __next__(self):
        """`__next__` is the Python 3 version of `next`"""
        return self.next()

    # --------------------------------------------------------------------------
    def readlines(self):
        """
        Read in all unread lines and return them as a list.
        """
        return [line for line in self]

    # --------------------------------------------------------------------------
    def read(self):
        """
        Read in all unread lines and return them as a single string.
        """
        lines = self.readlines()
        if lines:
            try:
                return ''.join(lines)
            except TypeError:
                return ''.join(force_text(line) for line in lines)
        else:
            return None

    # --------------------------------------------------------------------------
    def _is_closed(self):
        if not self.fh:
            return True
        try:
            return self.fh.closed
        except AttributeError:
            if isinstance(self.fh, gzip.GzipFile):
                # python 2.6
                return self.fh.fileobj is None
            else:
                raise

    # --------------------------------------------------------------------------
    def _filehandle(self):
        """
        Return a filehandle to the file being tailed, with the position set
        to the current offset.
        """
        if not self.fh or self._is_closed():
            self._counter += 1
            filename = self.rotated_logfile or self.filename
            if filename.endswith('.gz'):
                self.fh = gzip.open(filename, 'r')
            elif PY3:
                self.fh = open(filename, "r", 1, encoding=self.encoding)
            else:
                self.fh = io.open(filename, "r", 1, encoding=self.encoding)
            if self.read_from_end and not exists(self.offset_file):
                self.fh.seek(0, os.SEEK_END)
            else:
                self.fh.seek(self.offset)

        return self.fh

    # --------------------------------------------------------------------------
    def update_offset_file(self):
        """
        Update the offset file with the current inode and offset.
        """
        if self.on_update:
            self.on_update()
        offset = self._filehandle().tell()
        inode = fstat(self._filehandle().fileno()).st_ino
        fh = open(self.offset_file, "w")
        fh.write("%s\n%s\n" % (inode, offset))
        fh.close()
        self.since_update = 0

    # --------------------------------------------------------------------------
    def write_offset_to_file(self, offset):
        """Writes an `Offset` to the offset file"""
        if self.on_update:
            self.on_update()
        fh = open(self.offset_file, "w")
        fh.write("%s\n%s\n" % (offset.inode, offset.offset))
        fh.close()

    # --------------------------------------------------------------------------
    def _determine_rotated_logfile(self):
        """
        We suspect the logfile has been rotated, so try to guess what the
        rotated filename is, and return it.
        """
        rotated_filename = self._check_rotated_filename_candidates()
        if rotated_filename and exists(rotated_filename):
            if stat(rotated_filename).st_ino == self.offset_file_inode:
                return rotated_filename

            # if the inode hasn't changed, then the file shrank; this is expected with
            # copytruncate, otherwise print a warning
            if stat(self.filename).st_ino == self.offset_file_inode:
                if self.copytruncate:
                    return rotated_filename
                else:
                    sys.stderr.write(
                        "[pygtail] [WARN] file size of %s shrank, and copytruncate support is "
                        "disabled (expected at least %d bytes, was %d bytes).\n" %
                        (self.filename, self.offset, stat(self.filename).st_size))

        return None

    # --------------------------------------------------------------------------
    def _check_rotated_filename_candidates(self):
        """
        Check for various rotated logfile filename patterns and return the first
        match we find.
        """
        # break into directory and filename components to support cases where the
        # the file is prepended as part of rotation
        logdir = os.path.dirname(self.filename)
        log_basename = os.path.basename(self.filename)
        (log_stem, log_ext) = os.path.splitext(log_basename)

        # Checking olddir
        olddir = None
        if self.olddir:
            if os.path.isabs(self.olddir):
                olddir = self.olddir
            else:
                olddir = os.path.join(logdir, self.olddir)
            if not os.path.exists(olddir) or not os.path.isdir(olddir):
                olddir = logdir
        else:
            olddir = logdir

        # savelog(8)
        candidate = self.filename  +'.0'
        if exists(candidate) and exists(self.filename + '.1.gz') and \
                (stat(candidate).st_mtime > stat(self.filename + '.1.gz').st_mtime):
            return candidate

        # logrotate(8)
        candidate_globs = [
            os.path.join(olddir, log_basename) + ".1",
            os.path.join(olddir, log_basename) + ".1.[Gg][Zz]",
            # os.path.join(olddir, log_basename) + ".1.[Bb][Zz]2",
            # os.path.join(olddir, log_basename) + ".1.[Bb][Zz][Ii][Pp]2",
            # os.path.join(olddir, log_basename) + ".1.[Xx][Zz]",
        ]
        for globbing in candidate_globs:
            candidates = glob.glob(globbing)
            if candidates:
                candidates.sort()
                return candidates[-1]  # return most recent

        rotated_filename_patterns = [
            # logrotate dateext rotation scheme - `dateformat -%Y-%m-%d` + with `delaycompress`
            "-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
            # logrotate dateext rotation scheme - `dateformat -%Y-%m-%d` + without `delaycompress`
            "-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].[Gg][Zz]",
            # "-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].[Bb][Zz]2",
            # "-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].[Bb][Zz][Ii][Pp]2",
            # "-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].[Xx][Zz]",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d` + with `delaycompress`
            "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d` + without `delaycompress`
            "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Gg][Zz]",
            # "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Bb][Zz]2",
            # "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Bb][Zz][Ii][Pp]2",
            # "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Xx][Zz]",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d-%s` + with `delaycompress`
            "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-"
            "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d-%s` + without `delaycompress`
            "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-"
            "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Gg][Zz]",
            # "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-"
            # "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Bz][Zz]2",
            # "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-"
            # "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Bz][Zz][Ii][Pp]2",
            # "-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-"
            # "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].[Xz[Zz]",
            # for TimedRotatingFileHandler
            ".[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
        ]
        if self.log_patterns:
            rotated_filename_patterns.extend(self.log_patterns)

        for rotated_filename_pattern in rotated_filename_patterns:
            candidates = glob.glob(os.path.join(olddir, log_basename + rotated_filename_pattern))
            if candidates:
                candidates.sort()
                return candidates[-1]  # return most recent

        # no match
        return None

    # --------------------------------------------------------------------------
    def _is_new_file(self):
        # Processing rotated logfile or at the end of current file which has been renamed
        return self.rotated_logfile or \
            self._filehandle().tell() == fstat(self._filehandle().fileno()).st_size and \
            fstat(self._filehandle().fileno()).st_ino != stat(self.filename).st_ino

    # --------------------------------------------------------------------------
    def _get_next_line(self):
        curr_offset = self._filehandle().tell()
        line = self._filehandle().readline()
        if self.full_lines:
            if not line.endswith('\n'):
                self._filehandle().seek(curr_offset)
                raise StopIteration
        if not line:
            raise StopIteration
        self.since_update += 1
        return line


# ==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
