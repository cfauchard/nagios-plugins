#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check directory size for Nagios
# - gziped or plain SQL text format
# - perfdata for backup size
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 1, 0, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import os
import re
import argparse

parser = argparse.ArgumentParser(
    description='check directory size for Nagios with perfdatas')
parser.add_argument(
    "--version",
    action='version',
    version='%(prog)s ' + __version__)
parser.add_argument(
    "--critical",
    help="define critical size (k,m,g,t)",
    default="750m")
parser.add_argument(
    "--warning",
    help="define warning size (k,m,g,t)",
    default="1g")
parser.add_argument(
    "--verbose",
    action='store_true',
    help="verbosity flag")
parser.add_argument(
    'directory',
    help="directory to check")
args = parser.parse_args()


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

#
# Size unformat function
#
def bytes_fmt(text_value):
    regex = re.compile('^(.*)(.)$')

    match = regex.match(text_value)

    if not match:
        return(-1)

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "k":
        return(value * 1024)
    elif unit == "m":
        return(value * 1024**2)
    elif unit == "g":
        return(value * 1024**3)
    elif unit == "t":
        return(value * 1024**4)

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

cr = 2

try:
    directory_size = get_size(args.directory)
    critical_size = bytes_fmt(args.critical)
    warning_size = bytes_fmt(args.warning)

    if directory_size > critical_size:
        status_line = "CRITICAL-size:"
        cr = 2
    elif directory_size > warning_size:
        status_line = "WARNING-size:"
        cr = 1
    else:
        status_line = "OK-size:"
        cr = 0

    print(
        "%s %s" % (
            status_line,
            sizeof_fmt(directory_size)
        )
    )

except NameError:
    print("ERROR: no MySQL backup found")
    cr = 2

except FileNotFoundError as eh:
    print(eh.strerror, eh.filename)
    cr = 2

exit(cr)
