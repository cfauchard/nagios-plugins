#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check disk temperature with smartctl for Nagios
#
# Copyright (C) 2016-2018, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 2, 1, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import re
import argparse
import configparser
import subprocess

parser = argparse.ArgumentParser(description='check smartctl disk temperature for Nagios')
parser.add_argument("--version", action='version', version='%(prog)s ' + __version__)
parser.add_argument('configfile', help="configuration file")
args = parser.parse_args()

cr = 0

try:
    config = configparser.ConfigParser()
    config.read_file(open(args.configfile))
    status_line = ""
    perfdatas = ""

    for disk in config.get("general", "disks").split(","):
        temperature_regex = re.compile(config.get(config.get(disk, "disktype"), "temperature_regex"))
        output = subprocess.check_output([
            config.get("general", "command"),
            '-A',
            '-d',
            config.get(disk, "devicetype"),
            config.get(disk, "device")
        ]).decode()
        temperature = int(temperature_regex.search(output).group(1))

        if temperature > int(
                config.get(config.get(disk, "disktype"), "maxcrit")):
            cr = 2
        elif temperature > int(
                config.get(config.get(disk, "disktype"), "maxwarn")):
            cr = 1

        status_line = status_line + "%s:%d°C " % (disk, temperature)
        perfdatas = perfdatas + "%s=%d;%d;%d " % (
            disk,
            temperature,
            int(
                config.get(config.get(disk, "disktype"), "maxwarn")),
            int(
                config.get(config.get(disk, "disktype"), "maxcrit"))
        )

except FileNotFoundError as error:
    print("error opening file", error.filename, error.strerror)
    cr = 2

except configparser.DuplicateSectionError as error:
    print("error configuration file %s (duplicate section %s)" % (error.source, error.section))
    cr = 2

except configparser.NoOptionError as error:
    print("error configuration (mandatory option %s not found in section %s)" % (error.option, error.section))
    cr = 2

except configparser.NoSectionError as error:
    print("error configuration (section %s not found)" % (error.section))
    cr = 2

except subprocess.CalledProcessError as error:
    print("error call command: ", error.cmd)
    cr = 2

if cr == 0:
    status_line = "OK " + status_line
elif cr == 1:
    status_line = "WARNING " + status_line
else:
    status_line = "ERROR " + status_line

print(status_line + "|" + perfdatas)
exit(cr)
