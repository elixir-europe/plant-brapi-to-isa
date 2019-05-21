import datetime
import argparse
import datetime
import errno
import logging
import os
import sys
import json
from collections import defaultdict

from isatools import isatab
from isatools.isajson import ISAJSONEncoder
from isatools.model import Investigation, OntologyAnnotation, Characteristic, Source, \
    Sample, Protocol, Process, StudyFactor, FactorValue, DataFile, ParameterValue, ProtocolParameter, plink, Person, Publication, Comment, Material

from brapi_client import BrapiClient
from brapi_to_isa_converter import BrapiToIsaConverter, att_test

__author__ = 'proccaserra (Philippe Rocca-Serra)'
__author__ = 'cpommier (Cyril Pommier)'
__author__ = 'bedroesb  (Bert Droesbeke)'
__author__ = 'gcornut (Guillaume Cornut)'
__author__ = 'terazus (Dominique Batista)'

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
parser.add_argument('-J', '--json', help="flag to activate json dump", action="store_true")
SERVER = 'https://test-server.brapi.org/brapi/v1/'

logger.debug('Argument List:' + str(sys.argv))
args = parser.parse_args()
TRIAL_IDS = args.trials
STUDY_IDS = args.studies
JSON_boolean = args.json

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


def create_study_sample_and_assay(client, brapi_study_id, isa_study,  sample_collection_protocol, phenotyping_protocol, OBSERVATIONUNITLIST):

    spat_dist_mapping_dictionary = {
        "X": "X",
        "Y": "Y",
        "blockNumber": "Block",
        "plotNumber": "plot",
        "plantNumber": "plant",
        "replicate": "replicate"
    }

    
    # connecting the correct observation level to the correct assayobject
    # NOTE observation level is temporarily stored inside isa_study.assays[i].characteristic_categories[0] better field available?
    obs_level_to_assay = {}
    for k,assay in enumerate(isa_study.assays):
        obs_level_to_assay[assay.characteristic_categories[0]] = k

    treatments = defaultdict(list)
    allready_converted_obs_unit = [] # Allow to handle multiyear observation units NOTE (INRA specific)
    for obs_unit in OBSERVATIONUNITLIST:
        if obs_unit['observationLevel']:
            i = obs_level_to_assay[obs_unit['observationLevel']]
            obslvl = obs_unit['observationLevel']
        else:
            i = 0
            obslvl = 'study'
        # Getting the relevant germplasm used for that observation event:
        # ---------------------------------------------------------------
        this_source = isa_study.get_source(obs_unit['germplasmName'])
        if this_source and obs_unit['observationUnitName'] not in allready_converted_obs_unit:
            this_isa_sample = Sample(
                name= obs_unit['observationUnitName'],
                derives_from=[this_source])
            allready_converted_obs_unit.append(obs_unit['observationUnitName'])
            
            c = Characteristic(category=OntologyAnnotation(term="Observation Unit Type"),
                                value=OntologyAnnotation(term=obslvl,
                                                                    term_source="",
                                                                    term_accession=""))
            this_isa_sample.characteristics.append(c)
            
            spat_dist = []
            for key in spat_dist_mapping_dictionary:
                if key in obs_unit and obs_unit[key]:
                    spat_dist.append('[' + spat_dist_mapping_dictionary[key] + ']' + obs_unit[key])
            if 'observationLevels' in obs_unit and obs_unit['observationLevels']:
                for lvl in obs_unit['observationLevels'].split(","):
                    a, b = lvl.split(":")
                    spat_dist.append('[' + a + ']' + b)
            spat_dist_str = '; '.join(spat_dist)
            if spat_dist:
                c = Characteristic(category=OntologyAnnotation(term="Spatial Distribution"),
                                    value=OntologyAnnotation(term=spat_dist_str,
                                                                        term_source="",
                                                                        term_accession=""))
                this_isa_sample.characteristics.append(c)

            # Looking for treatment in BRAPI and mapping to ISA samples 
            # ---------------------------------------------------------
            if 'treatments' in obs_unit:
                for treatment in obs_unit['treatments']:
                    if 'factor' in treatment and 'modality' in treatment:
                        if treatment['modality'] not in treatments[treatment['factor']]:
                            treatments[treatment['factor']].append(treatment['modality'])
                        f = StudyFactor(name=treatment['factor'], factor_type=OntologyAnnotation(term=treatment['factor']))
                        fv = FactorValue(factor_name=f,
                                        value=OntologyAnnotation(term=str(treatment['modality']),
                                                                term_source="",
                                                                term_accession=""))
                        this_isa_sample.factor_values.append(fv)
            isa_study.samples.append(this_isa_sample)

            # Creating the corresponding ISA sample entity for structure the document:
            # ------------------------------------------------------------------------
            sample_collection_process = Process(executes_protocol=sample_collection_protocol)
            sample_collection_process.inputs.append(this_source)
            sample_collection_process.outputs.append(this_isa_sample)
            isa_study.process_sequence.append(sample_collection_process)

        # Assays at observation unit level
        # --------------------------------
        
        # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
        
        isa_study.assays[i].samples.append(this_isa_sample)
        phenotyping_process = Process(executes_protocol=phenotyping_protocol)
        phenotyping_process.inputs.append(this_isa_sample)
        phenotyping_process.name = obs_unit["observationUnitDbId"] 

        # ---------- TRY out for characteristics column in assay file ----------------------------
        material = Material(name=obs_unit["observationUnitDbId"])
        c = Characteristic(category=OntologyAnnotation(term="Observation Unit Type"),
                                value=OntologyAnnotation(term=obslvl,
                                                                    term_source="",
                                                                    term_accession=""))
        material.characteristics.append(c)
        phenotyping_process.outputs.append(material)
        phenotyping_process.inputs.append(material)
        isa_study.assays[i].other_material.append(material)

        # ----------------------------------------------------------------------------------------

        # Adding Parameter Value[Collection Date] column
        col_date_pv = ParameterValue(
                category=ProtocolParameter(parameter_name=OntologyAnnotation(term="Collection Date")),
                value=OntologyAnnotation(term="", term_source="", term_accession=""))

        phenotyping_process.parameter_values.append(col_date_pv)

        # Adding Parameter Value[Sample Description] column
        sampl_des_pv = ParameterValue(
                category=ProtocolParameter(parameter_name=OntologyAnnotation(term="Sample Description")),
                value=OntologyAnnotation(term="", term_source="", term_accession=""))

        phenotyping_process.parameter_values.append(sampl_des_pv)
        
        # Adding Derived Data File column
        datafilename = 'd_' + str(brapi_study_id) + '_' + att_test(obs_unit, 'observationLevel') + '.txt'
        DER_datafile = DataFile(filename=datafilename,
                                        label="Derived Data File",
                                        generated_from=[this_isa_sample])
        phenotyping_process.outputs.append(DER_datafile)

        # Adding Raw Data File column
        RAW_datafile = DataFile(filename="",
                                        label="Raw Data File")
        phenotyping_process.outputs.append(RAW_datafile)
        
        isa_study.assays[i].process_sequence.append(phenotyping_process)
        plink(sample_collection_process, phenotyping_process)

        
    # Mapping treatments to ISA study Factor Value:
    # ---------------------------------------------
    for factor, modalities in treatments.items():
        f = StudyFactor(name=factor, factor_type=OntologyAnnotation(term=factor))
        modality = ";".join(modalities)
        f.comments.append(Comment(name="modality",value=modality))                
        isa_study.factors.append(f)

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
        "trialDbId": "trial_less_study_" + STUDY_IDS[0],
        "trialName": "NA",
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

        # FILL IN TRIAL INFORMATION
        investigation.identifier = trial['trialDbId']
        investigation.title = trial['trialName']
        if 'contacts' in trial:
            for brapicontact in trial['contacts']:
                #NOTE: brapi has just name attribute -> no seperate first/last name
                ContactName = brapicontact['name'].split(' ')
                contact = Person(first_name=ContactName[0], last_name=ContactName[1],
                affiliation=brapicontact['institutionName'], email=brapicontact['email'])
                investigation.contacts.append(contact)
        investigation.comments.append(Comment(name="MIAPPE version", value="1.1"))
        if 'publications' in trial:
            for brapipublic in trial['publications']:
                #This is BrAPI v1.3 specific (when older, skipped) 
                publication = Publication(doi=brapipublic['publicationPUI'])
                publication.status = OntologyAnnotation(term="published")
                investigation.publications.append(publication)
        # iterating through the BRAPI studies associated to a given BRAPI trial:
        for brapi_study in trial['studies']:
            germplasminfo = {}
            
            brapi_study_id = brapi_study['studyDbId']
            try:
                brapi_study['studyDbId'].encode('ascii')
            except:
                logger.debug("Study " + brapi_study['studyDbId'] + " contains a non ascii character and will be skipped.")
                continue
            else:
                #NOTE NEW: holding observationUnits in OBSERVATIONUNITLIST
                OBSERVATIONUNITLIST = []
                for i in client.get_study_observation_units(brapi_study_id):
                    OBSERVATIONUNITLIST.append(i)
                
                obs_level, obs_levels = converter.get_obs_levels(brapi_study_id, OBSERVATIONUNITLIST)
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
                    # Creating corresponding ISA biosources with is Creating isa characteristics from germplasm attributes.
                    # ------------------------------------------------------
                    source = Source(name=germ['germplasmName'], characteristics=converter.create_germplasm_chars(germ))
                    
                    if germ['germplasmDbId'] not in germplasminfo:
                        germplasminfo[germ['germplasmDbId']] = [germ['accessionNumber']]

                    # Associating ISA sources to ISA isa_study object
                    isa_study.sources.append(source)

                    germ_counter = germ_counter + 1

                # Now dealing with BRAPI observation units and attempting to create ISA samples
                create_study_sample_and_assay(client, brapi_study_id, isa_study,  sample_collection_protocol, phenotyping_protocol, OBSERVATIONUNITLIST)
                
                if JSON_boolean:
                    # Writing isa_study to ISA-JSON format:
                    # --------------------------------
                    try:
                        json.dumps(investigation, cls=ISAJSONEncoder, sort_keys=True, indent=4, separators=(',', ': '))
                        logger.info('ISA-JSON DUMP DONE!...')
                    except IOError as ioe:
                        logger.info('CONVERSION FAILED!...')
                        logger.info(str(ioe))

                else:
                    # Writing isa_study to ISA-Tab format:
                    # --------------------------------
                    try:
                        # isatools.isatab.dumps(investigation)  # dumps() writes out the ISA
                        # !!!: fix isatab.py to access other protocol_type values to enable Assay Tab serialization
                        # !!!: if Assay Table is missing the 'Assay Name' field, remember to check protocol_type used !!!
                        isatab.dump(isa_obj=investigation, output_path=output_directory)
                        logger.info('ISA-TAB DUMP DONE!...')
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
                        data_readings = converter.create_isa_obs_data_from_obsvars(OBSERVATIONUNITLIST, list(variables), level, germplasminfo, obs_levels)
                        logger.debug("Generating data files")
                        write_records_to_file(this_study_id=str(brapi_study_id), this_directory=output_directory, records=data_readings,
                                            filetype="d_", ObservationLevel=level)
                    except Exception as ioe:
                        print(ioe)
                        
    logger.info('CONVERSION FINISHED')

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
