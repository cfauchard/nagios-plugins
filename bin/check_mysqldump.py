#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check mysqldump backups for Nagios
# - gziped or plain SQL text format
# - perfdata for backup size
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 2, 0, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import os
import re
import gzip
import datetime
import argparse

parser = argparse.ArgumentParser(description='check MySQL backups for Nagios with perfdatas for backup size')
parser.add_argument("--version", action='version', version='%(prog)s ' + __version__)
parser.add_argument("--delayc", type=int, help="define delay hours for critical", default=48)
parser.add_argument("--delayw", type=int, help="define delay hours for warning", default=24)
parser.add_argument("--verbose", action='store_true', help="verbosity flag")
parser.add_argument("--include", type=str, help="include regex", default="\.*")
parser.add_argument('directory', help="mysqldump backup directory")
parser.add_argument('database', help="MySQL database name")
args = parser.parse_args()

def iso8601(value):
    # split seconds to larger units
    seconds = value.total_seconds()
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    days, hours, minutes = map(int, (days, hours, minutes))
    seconds = round(seconds, 6)

    ## build date
    date = ''
    if days:
        date = '%sD' % days

    ## build time
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
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

limitbackupagec = datetime.timedelta(hours=args.delayc)
limitbackupagew = datetime.timedelta(hours=args.delayw)

re_gzip = re.compile(".*\.gz$")
re_sql = re.compile(".*\.sql$")
re_dump = re.compile("^-- Dump completed on (.*)$")
re_include = re.compile(args.include)
re_database = re.compile(args.database)

lastbackupdate = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')

try:

    for filename in os.listdir(args.directory):
        filepath = os.path.join(args.directory, filename)
        if os.path.isfile(filepath):

            filesize = os.path.getsize(filepath)

            if filesize == 0:
                if args.verbose:
                    print("Empty file: ", filepath)

            elif not re_include.match(filename):
                if args.verbose:
                    print("File excluded: ", filename)

            elif not re_database.search(filename):
                if args.verbose:
                    print("Not configured database")

            else:
                if re_gzip.match(filename):
                    if args.verbose:
                        print("gzip file detected: ", filename)
                    fh = gzip.open(filepath)
                elif re_sql.match(filename):
                    if args.verbose:
                        print("SQL file detected: ", filename)
                    fh = open(filepath, 'rb')

                fh.seek(-2, 2)  # Jump to the second last byte.
                while fh.read(1) != b"\n":  # Until EOL is found...
                    fh.seek(-2, 1)  # ...jump back the read byte plus one more.
                lastline = fh.readline().decode()  # Read last line.

                match = re_dump.match(lastline)
                if match:
                    backupdate = datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    backupage = datetime.datetime.now() - backupdate

                    if backupdate > lastbackupdate:
                        lastbackupdate = backupdate
                        lastbackupsize = filesize
                        lastbackupage = backupage

                    if args.verbose:
                        print("backupdate: ", backupdate.isoformat())
                        print("dump ok (size %s, date %s): %s" % (sizeof_fmt(filesize), backupdate, lastline))
                else:
                    if args.verbose:
                        print("ERROR dump: ", filepath)

                fh.close()

    if lastbackupage > limitbackupagec:
        if args.verbose:
            print("ERROR: last backup out of date")
        print("ERROR ", end='')
        cr = 3
    elif lastbackupage > limitbackupagew:
        if args.verbose:
            print("WARNING: last backup out of date")
        print("WARNING ", end='')
        cr = 2
    else:
        if args.verbose:
            print("last backup OK")
        print("OK ", end='')
        cr = 0

    print("last backup date: %s, age: %s, size: %s|size=%d" %
          (lastbackupdate.isoformat(),
           iso8601(lastbackupage),
           sizeof_fmt(lastbackupsize),
           lastbackupsize))

except NameError:
    print("ERROR: no MySQL backup found")
    cr = 3

except FileNotFoundError as eh:
    print(eh.strerror, eh.filename)
    cr = 3

exit(cr)
