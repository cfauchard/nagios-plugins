#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check mediawiki export for Nagios
# - perfdata for backup size
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 1, 0, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import os
import re
import datetime
import argparse

parser = argparse.ArgumentParser(
    description='check SQLite3 backups for Nagios with perfdatas for size')
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
parser.add_argument("--status",
                    action='store_true',
                    help="status in perfdata flag")
parser.add_argument('directory',
                    help="SQLite export directory")
args = parser.parse_args()


def iso8601(value):
    # split seconds to larger units
    seconds = value.total_seconds()
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    days, hours, minutes = map(int, (days, hours, minutes))
    seconds = round(seconds, 6)

    # build date
    date = ''
    if days:
        date = '%sD' % days

    # build time
    time = u'T'
    # hours
    bigger_exists = date or hours
    if bigger_exists:
        time += '{:02}H'.format(hours)
    # minutes
    bigger_exists = bigger_exists or minutes
    if bigger_exists:
        time += '{:02}M'.format(minutes)
    # seconds
    if seconds.is_integer():
        seconds = '{:02}'.format(int(seconds))
    else:
        # 9 chars long w/leading 0, 6 digits after decimal
        seconds = '%09.6f' % seconds
    # remove trailing zeros
    seconds = seconds.rstrip('0')
    time += '{}S'.format(seconds)
    return u'P' + date + time


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


limitbackupagec = datetime.timedelta(hours=args.delayc)
limitbackupagew = datetime.timedelta(hours=args.delayw)
page_number = 0
export_size = 0

re_wikitext = re.compile(".*\.wikitext$")

lastbackupdate = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')

try:

    for filename in os.listdir(args.directory):
        filepath = os.path.join(args.directory, filename)
        if os.path.isfile(filepath):

            filesize = os.path.getsize(filepath)
            filedate = datetime.datetime.fromtimestamp(
                os.path.getctime(filepath))

            if filesize == 0:
                if args.verbose:
                    print("Empty file: ", filepath)
            else:
                if re_wikitext.match(filename):
                    if args.verbose:
                        print("Wikitext page file detected: ", filename)

                    page_number += 1
                    export_size += filesize
                    backupdate = filedate
                    backupage = datetime.datetime.now() - backupdate

                    if backupdate > lastbackupdate:
                        lastbackupdate = backupdate
                        lastbackupsize = filesize
                        lastbackupage = backupage

                    if args.verbose:
                        print("backupdate: ", backupdate.isoformat())
                        print("backup SQLite ok (size %s, date %s)" %
                              (sizeof_fmt(filesize), backupdate))
                   
    if lastbackupage > limitbackupagec:
        if args.verbose:
            print("ERROR: last backup out of date")
        print("ERROR ", end='')
        cr = 2
    elif lastbackupage > limitbackupagew:
        if args.verbose:
            print("WARNING: last backup out of date")
        print("WARNING ", end='')
        cr = 1
    else:
        if args.verbose:
            print("last backup OK")
        print("OK ", end='')
        cr = 0

    print("%s last export date: %s, age: %s, size: %s, pages: %d | size=%d pages=%d" %
          (
              args.directory,
              lastbackupdate.isoformat(),
              iso8601(lastbackupage),
              sizeof_fmt(export_size),
              page_number,
              export_size,
              page_number
          ),
          end=''
          )

    if args.status:
        print(" status=%d" % cr)
    else:
        print("")

except NameError:
    print("ERROR: no SQLite export found")
    cr = 2

except FileNotFoundError as eh:
    print(eh.strerror, eh.filename)
    cr = 2

exit(cr)
