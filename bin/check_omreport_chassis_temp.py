#!/usr/bin/env python3
# coding: utf8
# -----------------------------------------------------------------
# check chassis temperature with Dell omreport for Nagios with perfdatas
#
# Copyright (C) 2016-2017, Christophe Fauchard
# -----------------------------------------------------------------

__version_info__ = (0, 1, 0, 'b1')
__version__ = '.'.join(map(str, __version_info__))

import argparse
import subprocess
import re

parser = argparse.ArgumentParser(description='check chassis temperature with Dell omreport for Nagios with perfdatas')
parser.add_argument("--version", action='version', version='%(prog)s ' + __version__)
args = parser.parse_args()

cr = 0
omreport_command = "/opt/dell/srvadmin/bin/omreport"

regex_chassis_temp_expr = "Reading                   : (.*) C"
regex_min_warn_expr = "Minimum Warning Threshold : (.*) C"
regex_min_crit_expr = "Minimum Failure Threshold : (.*) C"
regex_max_warn_expr = "Maximum Warning Threshold : (.*) C"
regex_max_crit_expr = "Maximum Failure Threshold : (.*) C"

regex_chassis_temp = re.compile(regex_chassis_temp_expr)
regex_min_warn = re.compile(regex_min_warn_expr)
regex_min_crit = re.compile(regex_min_crit_expr)
regex_max_warn = re.compile(regex_max_warn_expr)
regex_max_crit = re.compile(regex_max_crit_expr)

status_line = ""
perfdatas = ""

try:
    output = subprocess.check_output([
        omreport_command,
        'chassis',
        'temps'
    ]).decode()

    reading_temperature = float(regex_chassis_temp.search(output).group(1))
    min_warn_temperature = float(regex_min_warn.search(output).group(1))
    min_crit_temperature = float(regex_min_crit.search(output).group(1))
    max_warn_temperature = float(regex_max_warn.search(output).group(1))
    max_crit_temperature = float(regex_max_crit.search(output).group(1))

    if reading_temperature < min_crit_temperature or reading_temperature > max_crit_temperature:
        cr = 2
    elif reading_temperature < min_warn_temperature or reading_temperature > max_warn_temperature:
        cr = 1

    status_line = status_line + "Chassis temperature: %.01f°C " % (reading_temperature)
    perfdatas = perfdatas + "chassis=%.01f;%.01f;%.01f " % (
        reading_temperature,
        max_warn_temperature,
        max_crit_temperature
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
