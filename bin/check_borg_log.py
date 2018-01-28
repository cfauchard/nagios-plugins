#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check last borg backup for Nagios
# - perfdata for backup size
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 1, 0, 'b0')
__version__ = '.'.join(map(str, __version_info__))

import os
import re
import datetime
import argparse
import sys

#
# Size format function
#
def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)

#
# Size unformat function
#
def bytes_fmt(text_value, unit):
    value = float(text_value)

    if unit == "kB":
        return(value * 1024)
    elif unit == "MB":
        return(value * 1024**2)
    elif unit == "GB":
        return(value * 1024**3)
    elif unit == "TB":
        return(value * 1024**4)

parser = argparse.ArgumentParser(
    description='check Borg backups logs for Nagios with perfdatas for size')
parser.add_argument("--version",
                    action='version',
                    version='%(prog)s ' + __version__)
parser.add_argument("--delayc",
                    type=int,
                    help="define delay hours for critical",
                    default=48)
parser.add_argument("--delayw",
                    type=int,
                    help="define delay hours for warning",
                    default=24)
parser.add_argument("--verbose",
                    action='store_true',
                    help="verbosity flag")
parser.add_argument('borglogfile',
                    help="Borg log file")
args = parser.parse_args()

#
# define parse log regex
#
re_name = re.compile("Archive name: (.*)")
re_start_date = re.compile("Time\s\(start\):\s*(\S*)\s*.*, (....-..-.. ..:..:..)")
re_end_date = re.compile("Time\s\(end\):\s*(\S*)\s*.*, (....-..-.. ..:..:..)")
re_archive = re.compile(
    "This archive:\s*(\S*)\s(..)\s*(\S*)\s(..)\s*(\S*)\s(..)")
re_global = re.compile(
    "All archives:\s*(\S*)\s(..)\s*(\S*)\s(..)\s*(\S*)\s(..)"
)
lastbackupdate = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')
cr = 0

limitbackupagec = datetime.timedelta(hours=args.delayc)
limitbackupagew = datetime.timedelta(hours=args.delayw)

#
# Openning and load borg log file
#
fd_borg_log = open(args.borglogfile, "r")
borg_log_data = fd_borg_log.read()

#
# search archive name
#
match_name = re_name.search(borg_log_data)
if match_name:
    name = match_name.group(1)
    if args.verbose:
        print("Archive name: %s" % (name))
else:
    if args.verbose:
        print("archive name not found")
    cr = 2

#
# search archive start date
#
match_start_date = re_start_date.search(borg_log_data)
if match_start_date:
    start_date = datetime.datetime.strptime(
        match_start_date.group(2),
        '%Y-%m-%d %H:%M:%S')
    if args.verbose:
        print("start date: %s" % (start_date))
else:
    if args.verbose:
        print("archive start date not found")
    cr = 2

#
# search archive end date
#
match_end_date = re_end_date.search(borg_log_data)
if match_end_date:
    end_date = datetime.datetime.strptime(
        match_end_date.group(2),
        '%Y-%m-%d %H:%M:%S')
    backupage = datetime.datetime.now() - end_date

    if args.verbose:
        print("end date: %s" % (end_date))
        print("backup age: %s" % (backupage))
        print("warning backup age: %s" % (limitbackupagew))
        print("critical backup age: %s" % (limitbackupagec))
else:
    if args.verbose:
        print("archive end date not found")
    cr = 2

#
# search archive sizes
#
match_archive = re_archive.search(borg_log_data)
if match_archive:
    archive_osize = bytes_fmt(
        match_archive.group(1),
        match_archive.group(2)
    )
    archive_csize = bytes_fmt(
        match_archive.group(3),
        match_archive.group(4)
    )

    archive_dsize = bytes_fmt(
        match_archive.group(5),
        match_archive.group(6)
    )
    if args.verbose:
        print("archive original size: %s" % (sizeof_fmt(archive_osize)))
        print("archive compressed size: %s" % (sizeof_fmt(archive_csize)))
        print("archive deduplicated size: %s" % (sizeof_fmt(archive_dsize)))
else:
    if args.verbose:
        print("archive sizes not found")
    cr = 2

#
# search global repository sizes
#
match_global = re_global.search(borg_log_data)
if match_global:
    global_osize = bytes_fmt(
        match_global.group(1),
        match_global.group(2)
    )
    global_csize = bytes_fmt(
        match_global.group(3),
        match_global.group(4)
    )
    global_dsize = bytes_fmt(
        match_global.group(5),
        match_global.group(6)
    )
    if args.verbose:
        print("global original size: %s" % (sizeof_fmt(global_osize)))
        print("global compressed size: %s" % (sizeof_fmt(global_csize)))
        print("global deduplicated size: %s" % (sizeof_fmt(global_dsize)))
else:
    if args.verbose:
        print("global sizes not found")
    cr = 2

if backupage > limitbackupagec:
    if args.verbose:
        print("CRITICAL: backup age too large: %s" % (backupage))
    cr = 2
elif backupage > limitbackupagew:
    if args.verbose:
        print("WARNING: backup age too large: %s" % (backupage))
    if cr < 1:
        cr = 1
else:
    if args.verbose:
        print("OK: backup age")

#
# close borg log file
#
fd_borg_log.close()

#
# build output
#
if cr == 2:
    sys.stdout.write("CRITICAL: ")
elif cr == 1:
    sys.stdout.write("WARNING: ")
else:
    sys.stdout.write("OK: ")
sys.stdout.write(name)

print(" | osize=%s csize=%s dsize=%s gosize=%s gcsize=%s gdsize=%s" % (
    sizeof_fmt(archive_osize),
    sizeof_fmt(archive_csize),
    sizeof_fmt(archive_dsize),
    sizeof_fmt(global_osize),
    sizeof_fmt(global_csize),
    sizeof_fmt(global_dsize)
))

exit(cr)
