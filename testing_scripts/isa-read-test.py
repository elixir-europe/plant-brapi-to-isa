import os
import errno
import isatools
import json
import requests

from isatools import isatab
from isatools.convert import isatab2json

directory_1 = '/Users/Philippe/Documents/Dropbox-Backup/Eurovis 2015 - Chronoglyph/ISATAB-datasets/BII-S-8_FP001RO-isatab-TEST'
inv_name_1 = 'i_fp001ro-investigation.txt'
isa_config_1 = '/Users/Philippe/Documents/git/Configuration-Files/isaconfig-default_v2014-01-16/'

directory_2 = '/Users/Philippe/Documents/git/ISAdatasets/tab/MTBLS404/'
inv_name_2 = 'i_sacurine.txt'
# isa_config_2 = '/Users/Philippe/Documents/git/Configuration-Files/isaconfig-seq_v2016-11-17-SRA1.5-august2014mod/'



try:
    # my_isa_read = isatab.load(open(os.path.join('/Users/Philippe/Downloads/ISAcreator-1.7.11-all/isatab files/SRA_assembly_test', 'i_investigation.txt')))
    my_isa_read = isatab.load(open(os.path.join(directory_1, inv_name_1)))
    print("reading in:",my_isa_read.studies)

    # my_json_report = isatab.validate(open(os.path.join('/Users/Philippe/Downloads/ISAcreator-1.7.11-all/isatab files/SRA_assembly_test', 'i_investigation.txt')), '/Users/Philippe/Documents/git/Configuration-Files/isaconfig-seq_v2016-11-17-SRA1.5-august2014mod/')

    # my_json_report = isatab.validate(open(os.path.join(directory_1,inv_name_1)), isa_config_1)
    # print(my_json_report)

    try:
        isa_json = isatab2json.convert(directory_2)
    except Exception as excep:
        print(excep)

except IOError as e:
    print(e)