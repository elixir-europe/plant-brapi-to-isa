import datetime
import errno
import logging
import os
import sys
import argparse

from isatools import isatab
from isatools.model import Investigation, OntologyAnnotation, OntologySource, Assay, Study, Characteristic, Source, \
    Sample, Protocol, Process, StudyFactor, FactorValue, DataFile, ParameterValue, Comment, ProtocolParameter, plink

from brapi_client import BrapiClient
from brapi_converter import BrapiToIsaConverter

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
parser.add_argument('-t', '--trials', help="comma separated list of trial Ids", type=str, action='append')
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
# SERVER = 'https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/'
# SERVER = 'https://triticeaetoolbox.org/wheat/brapi/v1/'
# SERVER = 'https://cassavabase.org/brapi/v1/'

# GNPIS_BRAPI_V1 = 'https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/'
# EU_SOL_BRAPI_V1 = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
# PIPPA_BRAPI_V1 = "https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/"
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


###########################################################
# Creating ISA objects
###########################################################

def write_records_to_file(this_study_id, records, this_directory, filetype):
    logger.info('Doing something')
    # tdf_file = 'out/' + this_study_id
    with open(this_directory + filetype + this_study_id + '.txt', 'w') as fh:
        for this_element in records:
            # print(this_element)
            fh.write(this_element + '\n')
    fh.close()


def get_output_path(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError as oserror:
        logger.exception(oserror)
        if oserror.errno != errno.EEXIST:
            raise
    return "outputdir/" + path + "/"


def main(arg):
    """ Given a SERVER value (and BRAPI study identifier), generates an ISA-Tab document"""

    client = BrapiClient(SERVER, logger)
    converter = BrapiToIsaConverter(logger, SERVER)

    # iterating through the trials held in a BRAPI server:
    for trial in client.get_trials(TRIAL_IDS):
        # print("Trial: ", trial['trialDbId'], "|", trial['trialName'])
        logger.info('we start from a set of Trials')
        investigation = Investigation()

        output_directory = get_output_path( trial['trialName'] )

        # iterating through the BRAPI studies associated to a given BRAPI trial:
        for study in trial['studies']:

            # NOTA BENE: ugent doesnt have trials
            # GNPIS endpoint exemplar studies ['BTH_Dijon_2000_SetA1'.
            # 'BTH_Chaux_des_Prés_2007_SetA1','BTH_Rennes_2003_TECH']
            # TRITI endpoint exemplar studies ['1', '35' ,'1558']
            # CASSAVA endpoint exemaple studies ['3638']
            # BRAPI TEST SERVER = 'https://test-server.brapi.org/brapi/v1/'



            #study = get_study(study['studyDbId'])
            study_id = study['studyDbId']
            # NB: this method always create an ISA Assay Type
            study, investigation = converter.create_isa_study(study_id, investigation)
            investigation.studies.append(study)

            # creating the main ISA protocols:
            sample_collection_protocol = Protocol(name="sample collection",
                                                  protocol_type=OntologyAnnotation(term="sample collection"))
            study.protocols.append(sample_collection_protocol)

            # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
            # TODO: see https://github.com/ISA-tools/isa-api/blob/master/isatools/isatab.py#L886
            phenotyping_protocol = Protocol(name="phenotyping",
                                            protocol_type=OntologyAnnotation(term="nucleic acid sequencing"))
            study.protocols.append(phenotyping_protocol)

            # Getting the ISA assay table generated by the 'create_isa_study' method by default
            this_assay = study.assays[0]

            # Getting the list of all germplasms used in the BRAPI study:
            germplasms = client.get_germplasm_in_study(study_id)

            germ_counter = 0

            # Iterating through the germplasm considered as biosource,
            # For eaich of them, we retrieve their attributes and create isa characteristics
            for germ in germplasms:
                # print("GERM:", germ['germplasmName']) # germplasmDbId
                # WARNING: BRAPIv1 endpoints are not consistently using these
                # depending on endpoints, attributes may have to swapped

                # Creating corresponding ISA biosources:
                # --------------------------------------
                source = Source(name=germ['germplasmName'])

                # Creating isa characteristics from germplasm attributes.
                # -------------------------------------------------------
                for key in germ.keys():

                    if isinstance(germ[key], list):
                        # print("HERE: ", germ[key])
                        ontovalue = ";".join(germ[key])
                        c = Characteristic(category=OntologyAnnotation(term=str(key)),
                                           value=OntologyAnnotation(term=ontovalue,
                                                                    term_source="",
                                                                    term_accession=""))
                    # elif germ[key].startswith("["):
                    #     print("THERE: ", germ[key])
                    #     germ[key] = ast.literal_leval(germ[key])
                    #     ontovalue = ";".join(germ[key])
                    #     c = Characteristic(category=OntologyAnnotation(term=str(key)),
                    #                        value=OntologyAnnotation(term=ontovalue,
                    #                                                 term_source="",
                    #                                                 term_accession=""))
                    else:
                        # print("normal: ", germ[key])
                        c = Characteristic(category=OntologyAnnotation(term=str(key)),
                                           value=OntologyAnnotation(term=str(germ[key]),
                                                                    term_source="",
                                                                    term_accession=""))
                    if key == 'accessionNumber':
                        c = Characteristic(category=OntologyAnnotation(term="Material Source ID"),
                                           value=OntologyAnnotation(term=str(germ[key]),
                                                                    term_source="",
                                                                    term_accession=""))
                    if key == 'accessionNumber':
                        c = Characteristic(category=OntologyAnnotation(term="Material Source ID"),
                                           value=OntologyAnnotation(term=str(germ[key]),
                                                                    term_source="",
                                                                    term_accession=""))

                    if c not in source.characteristics:
                        source.characteristics.append(c)

                # Associating ISA sources to ISA study object
                study.sources.append(source)

                germ_counter = germ_counter + 1

            # Now dealing with BRAPI observation units and attempting to create ISA samples
            #obsunits = []
            #try:
            #    obsunits = client.get_obs_units_in_study(study_id)
            #except Exception as excep:
            #    logger.exception(excep)
            #    print("error: ", excep)

            #for i in range(len(obsunits)):
            for obs_unit in client.get_obs_units_in_study(study_id):
                # Getting the relevant germplasm used for that observation event:
                # ---------------------------------------------------------------
                this_source = study.get_source(obs_unit['germplasmName'])
                logger.debug("testing for the source reference: ", this_source)

                if this_source is not None:
                    this_sample = Sample(
                        name=obs_unit['observationUnitDbId'] + "_" + obs_unit['observationUnitName'],
                        derives_from=[this_source])
                    # --------------------------
                    # print("ou: ", ou)

                    if 'X' in obs_unit.keys():
                        # print('KEY:', obs_unit['X'])
                        c = Characteristic(category=OntologyAnnotation(term="X"),
                                           value=OntologyAnnotation(term=str(obs_unit['X']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'Y' in obs_unit.keys():
                        # print('KEY:', obs_unit['X'])
                        c = Characteristic(category=OntologyAnnotation(term="Y"),
                                           value=OntologyAnnotation(term=str(obs_unit['Y']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'blockNumber' in obs_unit.keys():
                        # print('KEY:', obs_unit['X'])
                        c = Characteristic(category=OntologyAnnotation(term="blockNumber"),
                                           value=OntologyAnnotation(term=str(obs_unit['blockNumber']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'plotNumber' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="plotNumber"),
                                           value=OntologyAnnotation(term=str(obs_unit['plotNumber']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'plantNumber' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="plantNumber"),
                                           value=OntologyAnnotation(term=str(obs_unit['plantNumber']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'replicate' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="replicate"),
                                           value=OntologyAnnotation(term=str(obs_unit['replicate']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationUnitDbId' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationUnitDbId"),
                                           value=OntologyAnnotation(term=str(obs_unit['observationUnitDbId']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationUnitName' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationUnitName"),
                                           value=OntologyAnnotation(term=str(obs_unit['observationUnitName']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationLevel' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationLevel"),
                                           value=OntologyAnnotation(term=str(obs_unit['observationLevel']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationLevels' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationLevels"),
                                           value=OntologyAnnotation(term=str(obs_unit['observationLevels']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'germplasmName' in obs_unit.keys():
                        c = Characteristic(category=OntologyAnnotation(term="germplasmName"),
                                           value=OntologyAnnotation(term=str(obs_unit['germplasmName']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    # Looking for treatment in BRAPI and mapping to ISA Study Factor Value
                    # --------------------------------------------------------------------
                    if 'treatments' in obs_unit.keys():
                        for element in obs_unit['treatments']:
                            for key in element.keys():
                                f = StudyFactor(name=key, factor_type=OntologyAnnotation(term=key))
                                if f not in study.factors:
                                    study.factors.append(f)

                                fv = FactorValue(factor_name=f,
                                                 value=OntologyAnnotation(term=str(element[key]),
                                                                          term_source="",
                                                                          term_accession=""))
                                this_sample.factor_values.append(fv)
                    study.samples.append(this_sample)
                    # print("counting observations: ", i, "before: ", this_source.name)

                    # TODO: Add Comment[Factor Values] : iterate through BRAPI treatments to obtain all possible values for a given Factor
                else:
                    logger.info("Can't find a reference to known source for that observation unit:", this_source)

                # Creating the corresponding ISA sample entity for structure the document:
                # ------------------------------------------------------------------------
                sample_collection_process = Process(executes_protocol=sample_collection_protocol)
                sample_collection_process.performer = "bob"
                sample_collection_process.date = datetime.datetime.today().isoformat()
                sample_collection_process.inputs.append(this_source)
                sample_collection_process.outputs.append(this_sample)
                study.process_sequence.append(sample_collection_process)

                # Creating the relevant ISA protocol application / Assay from BRAPI Observation Events:
                # -------------------------------------------------------------------------------------
                # obs_counter = 0
                for j in range(len((obs_unit['observations']))):
                    # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
                    phenotyping_process = Process(executes_protocol=phenotyping_protocol)
                    phenotyping_process.name = "assay-name_(" + obs_unit["observationUnitName"] + ")_" + \
                                               str(j)
                    # print("assay name: ", j, "|", phenotyping_process.name)
                    phenotyping_process.inputs.append(this_sample)

                    # Creating relevant protocol parameter values associated with the protocol application:
                    # -------------------------------------------------------------------------------------
                    if 'season' in obs_unit['observations'][j].keys():
                        pv = ParameterValue(
                            category=ProtocolParameter(parameter_name=OntologyAnnotation(term="season")),
                            value=OntologyAnnotation(term=str(obs_unit['observations'][j]['season']),
                                                     term_source="",
                                                     term_accession=""))
                    else:
                        pv = ParameterValue(
                            category=ProtocolParameter(parameter_name=OntologyAnnotation(term="season")),
                            value=OntologyAnnotation(term="none reported", term_source="", term_accession=""))

                    phenotyping_process.parameter_values.append(pv)

                    # Getting and setting values for performer and date of the protocol application:
                    # -------------------------------------------------------------------------------------
                    if obs_unit['observations'][j]['observationTimeStamp'] is not None:
                        phenotyping_process.date = str(obs_unit['observations'][j]['observationTimeStamp'])
                    else:
                        # TODO: implement testing and use of datetime.datetime.today().isoformat()
                        phenotyping_process.date = "not available"
                    if obs_unit['observations'][j]['collector'] is not None:
                        phenotyping_process.performer = str(obs_unit['observations'][j]['collector'])
                    else:
                        phenotyping_process.performer = "none reported"

                    # Creating the ISA Raw Data Files associated with each ISA phenotyping assay:
                    # -----------------------------------------------------------------------
                    datafile = DataFile(filename="phenotyping-data.txt",
                                        label="Raw Data File",
                                        generated_from=[this_sample])
                    phenotyping_process.outputs.append(datafile)

                    # Creating processes and linking
                    this_assay.samples.append(this_sample)
                    # this_assay.process_sequence.append(sample_collection_process)
                    this_assay.process_sequence.append(phenotyping_process)
                    this_assay.data_files.append(datafile)
                    plink(sample_collection_process, phenotyping_process)

                    # For debugging purpose only, let's check it is fine:
                    # print("process:", this_assay.process_sequence[0].name)
                    # print("Assay Post addition", this_assay)

            # Writing study to ISA-Tab format:
            # --------------------------------
            try:
                # isatools.isatab.dumps(investigation)  # dumps() writes out the ISA
                # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
                # !!!: if Assay Table is missing the 'Assay Name' field, remember to check protocol_type used !!!
                isatab.dump(isa_obj=investigation, output_path=output_directory)
                logger.info('DONE!...')
            except IOError as ioe:
                print(ioe)
                logger.info('CONVERSION FAILED!...')

            try:
                variable_records = converter.create_isa_tdf_from_obsvars(get_study_observed_variables(study_id))
                # Writing Trait Definition File:
                # ------------------------------
                write_records_to_file(this_study_id=str(study_id),
                                      this_directory=output_directory,
                                      records=variable_records,
                                      filetype="t_")
            except Exception as ioe:
                print(ioe)

            # Getting Variable Data and writing Measurement Data File
            # -------------------------------------------------------
            try:
                data_readings = converter.create_isa_obs_data_from_obsvars(client.get_obs_units_in_study(study_id))
                write_records_to_file(this_study_id=str(study_id), this_directory=output_directory, records=data_readings,
                                      filetype="d_")
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
