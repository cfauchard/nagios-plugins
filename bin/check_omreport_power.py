#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check chassis power consumption with Dell omreport for Nagios with perfdatas
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 1, 0, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import argparse
import subprocess
import re

parser = argparse.ArgumentParser(description='check chassis power consumption with Dell omreport for Nagios with perfdatas')
parser.add_argument("--version", action='version', version='%(prog)s ' + __version__)
args = parser.parse_args()

cr = 0
omreport_command = "/opt/dell/srvadmin/bin/omreport"

regex_data_expr = "Reading           : (.*) W"
regex_warn_expr = "Warning Threshold : (.*) W"
regex_crit_expr = "Failure Threshold : (.*) W"

regex_data = re.compile(regex_data_expr)
regex_warn = re.compile(regex_warn_expr)
regex_crit = re.compile(regex_crit_expr)

status_line = ""
perfdatas = ""

try:
    output = subprocess.check_output([
        omreport_command,
        'chassis',
        'pwrmonitoring'
    ]).decode()

    power_data = int(regex_data.search(output).group(1))
    warn_power = int(regex_warn.search(output).group(1))
    crit_power = int(regex_crit.search(output).group(1))

    if power_data > crit_power:
        cr = 2
    elif power_data > warn_power:
        cr = 1

    status_line = status_line + "Chassis Power: %dW " % (power_data)
    perfdatas = perfdatas + "power=%d;%d;%d " % (
        power_data,
        warn_power,
        crit_power
    )


except FileNotFoundError as error:
    print("error opening file", error.filename, error.strerror)
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
