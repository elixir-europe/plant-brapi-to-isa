import os
import errno
import isatools
import json
import requests

from isatools import isatab
my_json_report = isatab.validate(open(os.path.join('/Users/Philippe/Downloads/ISAcreator-1.7.11-all/isatab files/SRA_assembly_test', 'i_investigation.txt')), '/Users/Philippe/Documents/git/Configuration-Files/isaconfig-seq_v2016-11-17-SRA1.5-august2014mod/')

try:
    my_isa_read = isatab.load(open(os.path.join('/Users/Philippe/Downloads/ISAcreator-1.7.11-all/isatab files/SRA_assembly_test', 'i_investigation.txt')))
    print(my_isa_read.studies)

except e as IOError:
    print(e)