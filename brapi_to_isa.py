import datetime
import argparse
import datetime
import errno
import logging
import os
import sys
import json
import copy

from isatools import isatab
from isatools.model import Investigation, OntologyAnnotation, Characteristic, Source, \
    Sample, Protocol, Process, StudyFactor, FactorValue, DataFile, ParameterValue, ProtocolParameter, plink, Person, Publication

from brapi_client import BrapiClient
from brapi_to_isa_converter import BrapiToIsaConverter

__author__ = 'proccaserra (Philippe Rocca-Serra)'

log_file = "brapilog.log"
# logging.basicConfig(filename=log_file,
#                     filemode='a',
#                     level=logging.DEBUG)
logger = logging.getLogger('brapi_converter')
logger.debug('This message should go to the log file')
logger.info('Starting now...')
logger.warning('And this, too')
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

file4log = logging.FileHandler(log_file)
file4log.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file4log.setFormatter(formatter)
logger.addHandler(file4log)

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--endpoint', help="a BrAPi server endpoint", type=str)
parser.add_argument('-t', '--trials', help="comma separated list of trial Ids. 'all' to get all trials (not recomended)", type=str, action='append')
parser.add_argument('-s', '--studies', help="comma separated list of study Ids", type=str, action='append')
SERVER = 'https://test-server.brapi.org/brapi/v1/'

logger.debug('Argument List:' + str(sys.argv))
args = parser.parse_args()
TRIAL_IDS = args.trials
STUDY_IDS = args.studies

if args.endpoint:
    SERVER = args.endpoint
logger.info("\n----------------\ntrials IDs to be exported : "
            + str(TRIAL_IDS) + "\nstudy IDs to be exported : "
            + str(STUDY_IDS) + "\nTarget endpoint :  "
            + str(SERVER) + "\n----------------" )

# SERVER = 'https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/'
# SERVER = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
# SERVER = 'https://pippa.psb.ugent.be/BrAPIPPA/brapi/v1/'
# SERVER = 'https://triticeaetoolbox.org/wheat/brapi/v1/'
# SERVER = 'https://cassavabase.org/brapi/v1/'

# GNPIS_BRAPI_V1 = 'https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/'
# EU_SOL_BRAPI_V1 = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
# PIPPA_BRAPI_V1 = "https://pippa.psb.ugent.be/BrAPIPPA/brapi/v1/"
# TRITI_BRAPI_V1 = 'https://triticeaetoolbox.org/wheat/brapi/v1/'
# CASSAVA_BRAPI_V1 = 'https://cassavabase.org/brapi/v1/'


#
# def get_brapi_study_by_endpoint(endpoint, study_identifier):
#     """Returns a study from an endpoint, given its id."""
#     # dealing with differences in the endpoints
#     url = ''
#     if endpoint == GNPIS_BRAPI_V1:
#         url = endpoint + 'studies/' + str(study_identifier)
#     elif endpoint == PIPPA_BRAPI_V1:
#         url = endpoint + 'studies-search/' + str(study_identifier)
#     elif endpoint == EU_SOL_BRAPI_V1:
#         url = endpoint + 'studies-search/' + str(study_identifier)
#     elif endpoint == CASSAVA_BRAPI_V1 :
#         url = endpoint + 'studies-search/' + str(study_identifier)
#     elif endpoint == TRITI_BRAPI_V1:
#         url = endpoint + 'studies/' + str(study_identifier)
#
#     r = requests.get(url)
#     if r.status_code != requests.codes.ok:
#         raise RuntimeError("Non-200 status code")
#     this_study = r.json()['result']
#     return this_study


# def get_germplasm_by_endpoint(endpoint, germplasm_id):
#     url = endpoint + "germplasm-search" + str(germplasm_id)
#     r = requests.get(url)
#     if r.status_code != requests.codes.ok:
#         raise RuntimeError("Non-200 status code")
#         logging.error(e)
#         logging.fatal('Could not decode response from server!')
#     this_germplasm = r.json()['result']
#     return this_germplasm

# def load_germplasms(study_identifier):
#     for germplasms in paging(SERVER + 'studies/' + study_identifier + '/germplasm', None, None, 'GET'):
#         yield germplasms

# def load_obsunits(study_identifier):
#     for obsunits in paging(SERVER + 'studies/' + study_identifier + '/observationUnits', None, None, 'GET'):
#         yield obsunits

#
# def get_germplasm_chars(germplasm):
#     """" Given a BRAPI Germplasm ID, retrieve the list of all attributes from BRAPI and returns a list of ISA
#      characteristics using MIAPPE tags for compliance + X-check against ISAconfiguration"""
#     # TODO: switch BRAPI tags to MIAPPE Tags
#
#     these_characteristics = []
#
#     germplasm_id = germplasm['germplasmDbId']
#     r = requests.get(SERVER + "germplasm/" + germplasm_id)
#     if r.status_code != requests.codes.ok:
#         raise RuntimeError("Non-200 status code")
#
#     all_germplasm_attributes = r.json()['result']
#
#     for key in all_germplasm_attributes.keys():
#
#         print("key:", key, "value:", str(all_germplasm_attributes[key]))
#         miappeKey = ""
#
#         if key == "accessionNumber":
#             miappeKey = "Material Source ID"
#             # print("key", key, "value", all_germplasm_attributes[key])
#             c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))
#
#         elif key == "commonCropName":
#             miappeKey = "Material Source ID"
#             # print("key", key, "value", all_germplasm_attributes[key])
#             c =create_isa_characteristic(key, str(all_germplasm_attributes[key]))
#
#         elif key == "genus":
#             miappeKey = "Genus"
#             # print("key", key, "value", all_germplasm_attributes[key])
#             c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))
#
#         elif key == "species":
#             miappeKey = "Species"
#             c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))
#
#         elif key == "subtaxa":
#             miappeKey = "Infraspecific Name"
#             c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))
#
#         elif key == "taxonIds":
#             miappeKey = "Organism"
#             taxinfo = []
#             for item in range(len(all_germplasm_attributes["taxonIds"])):
#                 taxinfo.append( all_germplasm_attributes[key][item]["sourceName"] + ":" + all_germplasm_attributes[key][item]["taxonId"])
#             ontovalue = ";".join(taxinfo)
#             c = create_isa_characteristic(miappeKey, ontovalue)
#
#         elif key == "donors":
#             miappeKey = "Donors"
#             donors = []
#             for item in range(len(all_germplasm_attributes["donors"])):
#                 donors.append( all_germplasm_attributes[key][item]["donorInstituteCode"] + ":" + all_germplasm_attributes[key][item]["donorAccessionNumber"])
#             ontovalue = ";".join(donors)
#             c = create_isa_characteristic(miappeKey, ontovalue)
#
#         elif key == "synonyms":
#             if isinstance(all_germplasm_attributes[key], list):
#                 ontovalue = ";".join(all_germplasm_attributes[key])
#                 c = create_isa_characteristic(key, ontovalue)
#
#         else:
#             c = create_isa_characteristic(key, str(all_germplasm_attributes[key]))
#
#         if c not in these_characteristics:
#                 these_characteristics.append(c)
#
#     return these_characteristics


def create_study_sample_and_assay(client, brapi_study_id, isa_study,  sample_collection_protocol, phenotyping_protocol):

    obsunit_to_isasample_mapping_dictionary = {
        "X": "X",
        "Y": "Y",
        "blockNumber": "Block Number",
        "plotNumber": "Plot Number",
        "plantNumber": "Plant Number",
        "observationLevel": "Observation unit type"
    }

    obsunit_to_isaassay_mapping_dictionary = {
        "X": "X",
        "Y": "Y",
        "blockNumber": "Block Number",
        "plotNumber": "Plot Number",
        "plantNumber": "Plant Number",
        "observationLevel": "Observation unit type"
    }
    for i in range(len(isa_study.assays)):
        allready_converted_obs_unit = [] # Allow to handle multiyear observation units
        for obs_unit in client.get_study_observation_units(brapi_study_id):
            if isa_study.assays[i].characteristic_categories[0] == obs_unit['observationLevel']:
                # Getting the relevant germplasm used for that observation event:
                # ---------------------------------------------------------------
                this_source = isa_study.get_source(obs_unit['germplasmName'])
                if this_source is not None and obs_unit['observationUnitName'] not in allready_converted_obs_unit:
                    this_isa_sample = Sample(
                        name= obs_unit['observationUnitName'],
                        derives_from=[this_source])
                    allready_converted_obs_unit.append(obs_unit['observationUnitName'])
                    for key in obs_unit.keys():
                        if key in obsunit_to_isasample_mapping_dictionary.keys():
                            if isinstance(obsunit_to_isasample_mapping_dictionary[key], str) and str(obs_unit[key]) is not None :
                                c = Characteristic(category=OntologyAnnotation(term=obsunit_to_isasample_mapping_dictionary[key]),
                                                value=OntologyAnnotation(term=str(obs_unit[key]),
                                                                            term_source="",
                                                                            term_accession=""))
                                this_isa_sample.characteristics.append(c)
                        if key in obsunit_to_isaassay_mapping_dictionary.keys():
                            if isinstance(obsunit_to_isaassay_mapping_dictionary[key], str):
                                c = Characteristic(category=OntologyAnnotation(term=obsunit_to_isaassay_mapping_dictionary[key]),
                                                value=OntologyAnnotation(term=str(obs_unit[key]),
                                                                            term_source="",
                                                                            term_accession=""))
                                #TODO: quick workaround used to store observation units characteristics
                                isa_study.assays[i].comments.append(c)

                    # Looking for treatment in BRAPI and mapping to ISA Study Factor Value
                    # --------------------------------------------------------------------
                    if 'treatments' in obs_unit.keys():
                        for element in obs_unit['treatments']:
                            for key in element.keys():
                                f = StudyFactor(name=key, factor_type=OntologyAnnotation(term=key))
                                if f not in isa_study.factors:
                                    isa_study.factors.append(f)

                                fv = FactorValue(factor_name=f,
                                                value=OntologyAnnotation(term=str(element[key]),
                                                                        term_source="",
                                                                        term_accession=""))
                                this_isa_sample.factor_values.append(fv)
                    isa_study.samples.append(this_isa_sample)

                    # Creating the corresponding ISA sample entity for structure the document:
                    # ------------------------------------------------------------------------
                    sample_collection_process = Process(executes_protocol=sample_collection_protocol)
                    sample_collection_process.performer = "n.a."
                    sample_collection_process.date = datetime.datetime.today().isoformat()
                    sample_collection_process.inputs.append(this_source)
                    sample_collection_process.outputs.append(this_isa_sample)
                    isa_study.process_sequence.append(sample_collection_process)

            seasons = {}
            for j in range(len((obs_unit['observations']))):
                # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
                phenotyping_process = Process(executes_protocol=phenotyping_protocol)
                phenotyping_process.inputs.append(this_isa_sample)

                # Creating relevant protocol parameter values associated with the protocol application:
                # -------------------------------------------------------------------------------------
                if 'season' in obs_unit['observations'][j]:
                    season = str(obs_unit['observations'][j]['season'])
                    if season and season not in seasons:
                        seasons[season] = str(obs_unit["observationUnitDbId"])
            if seasons:    
                for unique_season, DbId in seasons.items():
                    pv = ParameterValue(
                                category=ProtocolParameter(parameter_name=OntologyAnnotation(term="season")),
                                value=OntologyAnnotation(term=str(unique_season),
                                                        term_source="",
                                                        term_accession=""))
                    phenotyping_process.parameter_values.append(pv)
                    phenotyping_process.name = "assay-name_(" + DbId + ")" 
            else:
                pv = ParameterValue(
                            category=ProtocolParameter(parameter_name=OntologyAnnotation(term="season")),
                            value=OntologyAnnotation(term="none reported", term_source="", term_accession=""))
                phenotyping_process.parameter_values.append(pv)
                phenotyping_process.name = "assay-name_(" + obs_unit["observationUnitDbId"] + ")" 
            
            
            isa_study.assays[i].samples.append(this_isa_sample)
            isa_study.assays[i].process_sequence.append(phenotyping_process)
            plink(sample_collection_process, phenotyping_process)

def write_records_to_file(this_study_id, records, this_directory, filetype, ObservationLevel=''):
    logger.info('Writing to file')
    # tdf_file = 'out/' + this_study_id
    if ObservationLevel:
        ObservationLevel = '_' + ObservationLevel
    with open(this_directory + filetype + this_study_id + ObservationLevel + '.txt', 'w') as fh:
        for this_element in records:
            # print(this_element)
            fh.write(this_element + '\n')
    fh.close()


def get_output_path(path):
    path = "outputdir/" + path + "/"
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError as oserror:
        logger.exception(oserror)
        if oserror.errno != errno.EEXIST:
            raise
    return path

def get_trials( brapi_client : BrapiClient):
    global TRIAL_IDS
    global STUDY_IDS
    if TRIAL_IDS:
       return brapi_client.get_trials(TRIAL_IDS)
    elif STUDY_IDS:
        logger.debug("Got Study IDS : " + ','.join(STUDY_IDS))
        TRIAL_IDS = []
        for my_study_id in STUDY_IDS:
            my_study = brapi_client.get_study(my_study_id)
            if "trialDbId" in my_study.keys() and my_study["trialDbId"]:
              TRIAL_IDS += my_study["trialDbId"]
            elif "trialDbIds" in my_study.keys() and my_study["trialDbIds"]:
               TRIAL_IDS += my_study["trialDbIds"]
        logger.debug("Got the Following trial ids for the Study IDS : " + str(TRIAL_IDS))
        if len(TRIAL_IDS) > 0:
            return brapi_client.get_trials(TRIAL_IDS)
        else:
            return get_empty_trial()
    else:
        logger.info("Not enough parameters, provide TRIAL or STUDY IDs")
        exit (1)


def get_empty_trial():
    empty_trial = {
        "trialDbId": "trial_less_study_"+STUDY_IDS[0],
        "trialName": "N.A.",
        "trialType": "Project",
        "endDate": "",
        "startDate": "",
        "datasetAuthorship": {
        },
        "studies":[]
    }
    #empty_trial_json = json.loads(empty_trial)
    for my_study_id in STUDY_IDS:
        empty_trial["studies"].append({"studyDbId": my_study_id})
    yield from [empty_trial]


def main(arg):
    """ Given a SERVER value (and BRAPI isa_study identifier), generates an ISA-Tab document"""

    client = BrapiClient(SERVER, logger)
    converter = BrapiToIsaConverter(logger, SERVER)

    # iterating through the trials held in a BRAPI server:
    # for trial in client.get_trials(TRIAL_IDS):
    for trial in get_trials(client):
        logger.info('we start from a set of Trials')
        investigation = Investigation()

        output_directory = get_output_path( trial['trialName'])
        logger.info("Generating output in : "+ output_directory)

        if 'contacts' in trial.keys():
            for brapicontact in trial['contacts']:
                #NOTE: brapi has just name atribute -> no seperate first/last name
                ContactName = brapicontact['name'].split(' ')
                contact = Person(first_name=ContactName[0], last_name=ContactName[1],
                affiliation=brapicontact['institutionName'], email=brapicontact['email'])
                investigation.contacts.append(contact)

        # iterating through the BRAPI studies associated to a given BRAPI trial:
        for brapi_study in trial['studies']:
            germplasminfo = {}
            #NOTE keeping track of germplasm info for data file generation
            brapi_study_id = brapi_study['studyDbId']
            obs_level, obs_levels = converter.obs_level_s(brapi_study_id)
            # NB: this method always create an ISA Assay Type
            isa_study, investigation = converter.create_isa_study(brapi_study_id, investigation, obs_level.keys())

            investigation.studies.append(isa_study)

            # creating the main ISA protocols:
            sample_collection_protocol = Protocol(name="sample collection",
                                                  protocol_type=OntologyAnnotation(term="sample collection"))
            isa_study.protocols.append(sample_collection_protocol)

            # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
            # TODO: see https://github.com/ISA-tools/isa-api/blob/master/isatools/isatab.py#L886
            phenotyping_protocol = Protocol(name="phenotyping",
                                            protocol_type=OntologyAnnotation(term="nucleic acid sequencing"))
            isa_study.protocols.append(phenotyping_protocol)

            # Getting the list of all germplasms used in the BRAPI isa_study:
            germplasms = client.get_study_germplasms(brapi_study_id)

            germ_counter = 0
            
            # Iterating through the germplasm considered as biosource,
            # For each of them, we retrieve their attributes and create isa characteristics
            for germ in germplasms:
                # print("GERM:", germ['germplasmName']) # germplasmDbId
                # WARNING: BRAPIv1 endpoints are not consistently using these
                # depending on endpoints, attributes may have to swapped
                # get_germplasm_chars(germ)
                # Creating corresponding ISA biosources with is Creating isa characteristics from germplasm attributes.
                # ------------------------------------------------------
                source = Source(name=germ['germplasmName'], characteristics=converter.create_germplasm_chars(germ))
                
                if germ['germplasmDbId'] not in germplasminfo:
                    germplasminfo[germ['germplasmDbId']] = [germ['accessionNumber']]

                # Associating ISA sources to ISA isa_study object
                isa_study.sources.append(source)

                germ_counter = germ_counter + 1

            # Now dealing with BRAPI observation units and attempting to create ISA samples
            create_study_sample_and_assay(client, brapi_study_id, isa_study,  sample_collection_protocol, phenotyping_protocol)

            # Writing isa_study to ISA-Tab format:
            # --------------------------------
            try:
                # isatools.isatab.dumps(investigation)  # dumps() writes out the ISA
                # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
                # !!!: if Assay Table is missing the 'Assay Name' field, remember to check protocol_type used !!!
                isatab.dump(isa_obj=investigation, output_path=output_directory)
                logger.info('DONE!...')
            except IOError as ioe:
                logger.info('CONVERSION FAILED!...')
                logger.info(str(ioe))

            try:
                variable_records = converter.create_isa_tdf_from_obsvars(client.get_study_observed_variables(brapi_study_id))
                # Writing Trait Definition File:
                # ------------------------------
                write_records_to_file(this_study_id=str(brapi_study_id),
                                      this_directory=output_directory,
                                      records=variable_records,
                                      filetype="t_")
            except Exception as ioe:
                print(ioe)

            # Getting Variable Data and writing Measurement Data File
            # -------------------------------------------------------
            for level, variables in obs_level.items():
                try:
                    obsUnitList = []
                    for i in client.get_study_observation_units(brapi_study_id):
                        obsUnitList.append(i)
                    data_readings = converter.create_isa_obs_data_from_obsvars(obsUnitList, list(variables), level, germplasminfo, obs_levels)
                    logger.debug("Generating data files")
                    write_records_to_file(this_study_id=str(brapi_study_id), this_directory=output_directory, records=data_readings,
                                        filetype="d_", ObservationLevel=level)
                except Exception as ioe:
                    print(ioe)


#############################################
# MAIN METHOD TO START THE CONVERSION PROCESS
#############################################
""" starting up """
if __name__ == '__main__':
    try:
        main(arg=SERVER)
    except Exception as e:
        logging.exception(e)
        sys.exit(1)

#################################################################################
# Creating ISA-Tab from GNPIS_BRAPI_V1 date [old call was EU_SOL_BRAPI_V1 data ]
#################################################################################

# investigations = create_isa_investigations(GNPIS_BRAPI_V1)
# EU_SOL_BRAPI_V1

# if not os.path.exists("output"):
#     os.makedirs("output")
#
# if not os.path.exists("output/eu_sol"):
#     os.makedirs("output/eu_sol")
#
#
# for investigation in investigations:
#     directory = "output/eu_sol/trial_"+str(investigation.identifier)
#     if not os.path.exists(directory):
#         os.makedirs(directory)
#     isatools.isatab.dump(investigation, directory)
#
# ## Creating ISA-Tab from EU_SOL_BRAPI_V1 endpoint data [old call was on PIPPA endpoint data]
#
# create_materials(GNPIS_BRAPI_V1) #PIPPA_BRAPI_V1
