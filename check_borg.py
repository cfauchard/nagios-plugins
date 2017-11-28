#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check last borg backup for Nagios
# - perfdata for backup size
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 3, 0, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import os
import re
import datetime
import argparse
import subprocess

parser = argparse.ArgumentParser(
    description='check Borg backups for Nagios with perfdatas for size')
parser.add_argument("--version",
                    action='version',
                    version='%(prog)s ' + __version__)
parser.add_argument("--mintime",
                    type=int,
                    help="define borg min lock time",
                    default=48)
parser.add_argument("--maxtime",
                    type=int,
                    help="define borg maxlock time",
                    default=48)
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
parser.add_argument("--info",
                    action='store_true',
                    help="details backup flag")
parser.add_argument("--globalsize",
                    action='store_true',
                    help="global repository instead of archive volume flag")
parser.add_argument("--status",
                    action='store_true',
                    help="status in perfdata flag")
parser.add_argument("--include",
                    type=str,
                    help="include regex",
                    default="\.*")
parser.add_argument("--home",
                    type=str,
                    help="setting home directory for sudo calls")
parser.add_argument('repository',
                    help="Borg backup repository")
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

#
# Size format function
#
def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

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

limitbackupagec = datetime.timedelta(hours=args.delayc)
limitbackupagew = datetime.timedelta(hours=args.delayw)

re_sql = re.compile(".*\.sqlite$")
re_include = re.compile(args.include)
re_date = re.compile("(\S*)\s*.*, (....-..-.. ..:..:..)$")
re_archive = re.compile("^This archive:\s*(\S*)\s(..)\s*(\S*)\s(..)\s*(\S*)\s(..)$")
re_global = re.compile("^All archives:\s*(\S*)\s(..)\s*(\S*)\s(..)\s*(\S*)\s(..)$")
                        
lastbackupdate = datetime.datetime.strptime('1970-01-01', '%Y-%m-%d')
cr = 2

try:

    #
    # Setting HOME environment variable for sudo calls
    #
    if args.home:
        os.environ['HOME'] = args.home

    #
    # test borg lock time
    #
    if args.mintime:
        if datetime.datetime.now().hour >= args.mintime and datetime.datetime.now().hour < args.maxtime:
            exit(0)
        
    #
    # Openning Borg list process
    #
    borg_list_process = subprocess.Popen(
        [
            "borg",
            "list",
            args.repository
        ],
        stdout=subprocess.PIPE)

    #
    # read pipe for borg list
    #
    for buffer in borg_list_process.stdout:

        #
        # convert bytes array to string
        #
        line = str(buffer, 'utf-8')

        #
        # test include regex
        #
        if re_include and not re_include.match(line):
            if args.verbose:
                print("backup excluded: ", line)
        else:
            match_date = re_date.match(line)
            if match_date:
                backupname = match_date.group(1)
                backupdate = datetime.datetime.strptime(
                    match_date.group(2),
                    '%Y-%m-%d %H:%M:%S')
                backupage = datetime.datetime.now() - backupdate

                #
                # this is the last backup
                #
                if backupdate > lastbackupdate:
                    lastbackupname = backupname
                    lastbackupdate = backupdate
                    lastbackupage = backupage

                else:
                    if args.verbose:
                        print("not newest backup: " + backupname)

                if args.verbose:
                    print("getting informations for backup " + backupname)

    #
    # waiting borg list process
    #
    borg_list_process.wait()

    #
    # get detail backup informations
    #
    if args.info:
    
        #
        # search backup informations
        #
        borg_info_process = subprocess.Popen(
            [
                "borg",
                "info",
                args.repository + "::" + lastbackupname
            ],
            stdout = subprocess.PIPE
        )

        for buffer_info in borg_info_process.stdout:
            #
            # convert bytes array to string
            #
            line_info = str(buffer_info, 'utf-8')

            #
            # search backup by backupname or globaly
            #
            if args.globalsize:
                match_info = re_global.match(line_info)
            else:
                match_info = re_archive.match(line_info)

                if match_info:

                    if args.verbose:
                        print(
                            "%s: %s %s original, %s %s compressed, %s %s deduplicated" %
                            (
                                backupname,
                                match_info.group(1),
                                match_info.group(2),
                                match_info.group(3),
                                match_info.group(4),
                                match_info.group(5),
                                match_info.group(6)
                            )
                        )
                        lastbackup_original_size = bytes_fmt(
                            match_info.group(1),
                            match_info.group(2)
                        )
                        lastbackup_compressed_size = bytes_fmt(
                            match_info.group(3),
                            match_info.group(4)
                        )
                        lastbackup_deduplicated_size = bytes_fmt(
                            match_info.group(5),
                            match_info.group(6)
                        )

                        borg_info_process.wait()


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

    if args.info:
        print("%s last backup date: %s, age: %s, osize: %s csize: %s dsize: %s | osize=%d csize=%d dsize=%d" %
              (
                  lastbackupname,
                  lastbackupdate.isoformat(),
                  iso8601(lastbackupage),
                  sizeof_fmt(lastbackup_original_size),
                  sizeof_fmt(lastbackup_compressed_size),
                  sizeof_fmt(lastbackup_deduplicated_size),
                  lastbackup_original_size,
                  lastbackup_compressed_size,
                  lastbackup_deduplicated_size
              ),
              end=''
        )
    else:
        print("%s last backup date: %s, age: %s | " %
              (
                  lastbackupname,
                  lastbackupdate.isoformat(),
                  iso8601(lastbackupage),
              ),
              end=''
        )
        
    if args.status:
        print(" status=%d" % cr)
    else:
        print("")

# except NameError:
#     print("ERROR: no matching backup found")
#     cr = 2

except FileNotFoundError as eh:
    print(eh.strerror, eh.filename)
    cr = 2

exit(cr)
