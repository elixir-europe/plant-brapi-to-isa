import datetime
import argparse
import datetime
import errno
import logging
import os
import sys

from isatools import isatab
from isatools.model import Investigation, OntologyAnnotation, OntologySource, Assay, Study, Characteristic, Source, \
    Sample, Protocol, Process, StudyFactor, FactorValue, DataFile, ParameterValue, Comment, ProtocolParameter, plink

from brapi_client import BrapiClient

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
if (args.endpoint):
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


###########################################################
# Get info from BrAPI
###########################################################


def create_germplasm_chars(germplasm):
    """" Given a BRAPI Germplasm ID, returns a list of ISA characteristics """
    # TODO: switch BRAPI tags to MIAPPE Tags
    charax_per_germplasm = {}

    germplasm_id = germplasm['germplasmDbId']
    these_characteristics = []

    valid_categories = set()
    valid_categories.add("germplasmSeedSource")
    valid_categories.add("typeOfGermplasmStorageCode")
    valid_categories.add("acquisitionDate")
    valid_categories.add("defaultDisplayName")
    valid_categories.add("germplasmPUI")
    valid_categories.add("synonyms")
    valid_categories.add("speciesAuthority")
    valid_categories.add("species")
    valid_categories.add("subtaxa")
    valid_categories.add("accessionNumber")
    valid_categories.add("pedigree")
    valid_categories.add("subtaxaAuthority")
    valid_categories.add("instituteCode")
    valid_categories.add("germplasmName")
    valid_categories.add("instituteName")
    valid_categories.add("commonCropName")
    valid_categories.add("germplasmDbId")
    valid_categories.add("genus")
    valid_categories.add("biologicalStatusOfAccessionCode")
    valid_categories.add("countryOfOriginCode")

    for item in germplasm.keys():
        print("there", item)
        if item in valid_categories:
            if item == "subtaxa":
                miameitem = "Infraspecific name"
                these_characteristics.append(create_isa_characteristic(str(miameitem), str(germplasm[item])))
            if item == "commonCropName":
                miameitem = "Organism"
                these_characteristics.append(create_isa_characteristic(str(miameitem), str(germplasm[item])))
            if item == "accessionNumber":
                miameitem = "accnum"
                print(miameitem)
                these_characteristics.append(create_isa_characteristic(str(miameitem), str(germplasm[item])))
            else:
                these_characteristics.append(create_isa_characteristic(str(item), str(germplasm[item])))

        charax_per_germplasm[germplasm_id] = these_characteristics

    # return Source(germplasm_id, characteristics=these_characteristics)
    return charax_per_germplasm


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


###########################################################
# Creating ISA objects
###########################################################


def create_isa_investigations(endpoint):
    """Create ISA investigations from a BrAPI endpoint, starting from the trials information"""
    client = BrapiClient(endpoint, logger)
    endpoint_investigations = []
    for this_trial in client.get_brapi_trials():
        this_investigation = Investigation()
        this_investigation.identifier = this_trial['trialDbId']
        this_investigation.title = this_trial['trialName']
        # investigation.comments.append(Comment("Investigation Start Date", trial['startDate']))
        # investigation.comments.append(Comment("Investigation End Date", trial['endDate']))
        # investigation.comments.append(Comment("Active", trial['active']))

        for this_study in this_trial['studies']:
            this_study = create_isa_study(this_study['studyDbId'])
            this_investigation.studies.append(this_study)
            endpoint_investigations.append(this_investigation)
    return endpoint_investigations


def create_materials(endpoint):
    """Create ISA studies from a BrAPI endpoint, starting from the studies, where there is no trial information."""
    client = BrapiClient(endpoint, logger)
    for phenotype in client.get_phenotypes():
        print(phenotype)
        # for now, creating the sample name combining studyDbId and potDbId -
        # eventually this should be observationUnitDbId
        sample_name = phenotype['studyDbId'] + "_" + phenotype['plotNumber']
        this_sample = Sample(name=sample_name)
        that_source = Source(phenotype['germplasmName'], phenotype['germplasmDbId'])
        this_sample.derives_from = that_source


# def load_germplasms(study_identifier):
#     for germplasms in paging(SERVER + 'studies/' + study_identifier + '/germplasm', None, None, 'GET'):
#         yield germplasms

# def load_obsunits(study_identifier):
#     for obsunits in paging(SERVER + 'studies/' + study_identifier + '/observationUnits', None, None, 'GET'):
#         yield obsunits


def get_germplasm_chars(germplasm):
    """" Given a BRAPI Germplasm ID, retrieve the list of all attributes from BRAPI and returns a list of ISA
     characteristics using MIAPPE tags for compliance + X-check against ISAconfiguration"""
    # TODO: switch BRAPI tags to MIAPPE Tags

    these_characteristics = []

    germplasm_id = germplasm['germplasmDbId']
    r = requests.get(SERVER + "germplasm/" + germplasm_id)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")

    all_germplasm_attributes = r.json()['result']

    for key in all_germplasm_attributes.keys():

        print("key:", key, "value:", str(all_germplasm_attributes[key]))
        miappeKey = ""

        if key == "accessionNumber":
            miappeKey = "Material Source ID"
            # print("key", key, "value", all_germplasm_attributes[key])
            c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))

        elif key == "commonCropName":
            miappeKey = "Material Source ID"
            # print("key", key, "value", all_germplasm_attributes[key])
            c =create_isa_characteristic(key, str(all_germplasm_attributes[key]))

        elif key == "genus":
            miappeKey = "Genus"
            # print("key", key, "value", all_germplasm_attributes[key])
            c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))

        elif key == "species":
            miappeKey = "Species"
            c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))

        elif key == "subtaxa":
            miappeKey = "Infraspecific Name"
            c = create_isa_characteristic(miappeKey, str(all_germplasm_attributes[key]))

        elif key == "taxonIds":
            miappeKey = "Organism"
            taxinfo = []
            for item in range(len(all_germplasm_attributes["taxonIds"])):
                taxinfo.append( all_germplasm_attributes[key][item]["sourceName"] + ":" + all_germplasm_attributes[key][item]["taxonId"])
            ontovalue = ";".join(taxinfo)
            c = create_isa_characteristic(miappeKey, ontovalue)

        elif key == "donors":
            miappeKey = "Donors"
            donors = []
            for item in range(len(all_germplasm_attributes["donors"])):
                donors.append( all_germplasm_attributes[key][item]["donorInstituteCode"] + ":" + all_germplasm_attributes[key][item]["donorAccessionNumber"])
            ontovalue = ";".join(donors)
            c = create_isa_characteristic(miappeKey, ontovalue)

        elif key == "synonyms":
            if isinstance(all_germplasm_attributes[key], list):
                ontovalue = ";".join(all_germplasm_attributes[key])
                c = create_isa_characteristic(key, ontovalue)

        else:
            c = create_isa_characteristic(key, str(all_germplasm_attributes[key]))

        if c not in these_characteristics:
                these_characteristics.append(c)

    return these_characteristics


def create_isa_study(brapi_study_id, investigation):
    """Returns an ISA study given a BrAPI endpoints and a BrAPI study identifier."""

    client = BrapiClient(SERVER, logger)
    brapi_study = client.get_brapi_study(brapi_study_id)

    this_study = Study(filename="s_" + str(brapi_study_id) + ".txt")
    this_study.identifier = brapi_study['studyDbId']

    if 'name' in brapi_study:
        this_study.title = brapi_study['name']
    elif 'studyName' in brapi_study:
        this_study.title = brapi_study['studyName']

    this_study.comments.append(Comment(name="Study Start Date", value=brapi_study['startDate']))
    this_study.comments.append(Comment(name="Study End Date", value=brapi_study['endDate']))

    if brapi_study['location'] is not None and brapi_study['location']['name'] is not None:
        this_study.comments.append(Comment(name="Experimental site name",
                                           value=brapi_study['location']['name']))
    else:
        this_study.comments.append(Comment(name="Experimental site name", value=""))

    if brapi_study['location'] is not None and brapi_study['location']['countryCode'] is not None:
        this_study.comments.append(Comment(name="geographical location (country)",
                                           value=brapi_study['location']['countryCode']))

    elif brapi_study['location'] is not None and brapi_study['location']['countryName'] is not None:
        this_study.comments.append(Comment(name="geographical location (country)",
                                           value=brapi_study['location']['countryName']))
    else:
        this_study.comments.append(Comment(name="geographical location (country)", value=""))

    if brapi_study['location'] is not None and brapi_study['location']['latitude'] is not None:
        this_study.comments.append(Comment(name="geographical location (latitude)",
                                           value=brapi_study['location']['latitude']))
    else:
        this_study.comments.append(Comment(name="geographical location (latitude)", value=""))

    if brapi_study['location'] is not None and brapi_study['location']['latitude'] is not None:
        this_study.comments.append(Comment(name="geographical location (longitude)",
                                           value=brapi_study['location']['longitude']))
    else:
        this_study.comments.append(Comment(name="geographical location (longitude)", value=""))

    if brapi_study['location'] is not None and brapi_study['location']['altitude'] is not None:
        this_study.comments.append(Comment(name="geographical location (altitude)",
                                           value=brapi_study['location']['altitude']))
    else:
        this_study.comments.append(Comment(name="geographical location (altitude)", value=""))

    # TODO: look at the brapi call https://app.swaggerhub.com/apis/PlantBreedingAPI/BrAPI/1.2#/Studies/get_studies__studyDbId__layout
    # mapping into ISA Comment [Observation unit level hierarchy] MIAPPE DM24 [BRAPI mapping:  Layout/obvservationLevel || Layout/observationReplicate ||Layout/blockNumber

    # TODO: 		<field header="Comment[Map of experimental design]" data-type="String" is-file-field="true" is-multiple-value="false" is-required="false" is-hidden="false" is-forced-ontology="false" section="INVESTIGATION">
    # 			<description>
    # 				<![CDATA[Representation of the experimental design, a GIS or excel file. BRAPI mapping: if Study/dataLinks/@type="experimental design map", then Study/dataLinks/@url || @name ]]>
    # 			</description>
    # 			<default-value/>
    # 		</field>

    study_design = brapi_study['studyType']
    oa_st_design = OntologyAnnotation(term=study_design)
    this_study.design_descriptors = [oa_st_design]

    oref_tt = OntologySource(name="OBI", description="Ontology for Biomedical Investigation")
    oa_tt = OntologyAnnotation(term="genome sequencing", term_accession="", term_source=oref_tt)
    oref_mt = OntologySource(name="OBI", description="Ontology for Biomedical Investigation")
    oa_mt = OntologyAnnotation(term="nucleic acid sequencing", term_accession="", term_source=oref_mt)
    isa_assay_file = "a_" + str(brapi_study_id) + ".txt"
    new_assay = Assay(measurement_type=oa_tt, technology_type=oa_mt, filename=isa_assay_file)
    this_study.assays.append(new_assay)
    if oref_mt not in investigation.ontology_source_references:
        investigation.ontology_source_references.append(oref_mt)
    if oref_tt not in investigation.ontology_source_references:
        investigation.ontology_source_references.append(oref_tt)
    return this_study, investigation


def create_isa_characteristic(my_key, my_value):
    """Given a pair of category and value, return an ISA Characteristics element """
    this_characteristic = Characteristic(category=OntologyAnnotation(term=str(my_key)),
                                         value=OntologyAnnotation(term=str(my_value), term_source="",
                                         term_accession=""))

    return this_characteristic


def create_isa_tdf_from_obsvars(obsvars):
    records = []
    header_elements = ["Variable Name", "Variable Full Name", "Variable Description", "Crop", "Growth Stage", "Date",
                       "Method", "Method Description", "Method Formula", "Method Reference", "Scale", "Scale Data Type",
                       "Scale Valid Values", "Unit", "Trait Name", "Trait Term REF", "Trait Class", "Trait Entity",
                       "Trait Attribute"]

    tdf_header = '\t'.join(header_elements)
    records.append(tdf_header)

    for obs_var in obsvars:
        record_element = [str(obs_var['name']), str(obs_var['ontologyDbId']), str(obs_var['ontologyName']),
                          str(obs_var['crop']),
                          str(obs_var['growthStage']), str(obs_var['date']), str(obs_var['method']['name']),
                          str(obs_var['method']['description']), str(obs_var['method']['formula']),
                          str(obs_var['method']['reference']), str(obs_var['scale']['name']),
                          str(obs_var['scale']['dataType']),
                          str(obs_var['scale']['validValues']['categories']), str(obs_var['scale']['xref']),
                          str(obs_var['trait']['name']), str(obs_var['trait']['xref']), str(obs_var['trait']['class']),
                          str(obs_var['trait']['entity']), str(obs_var['trait']['attribute'])]

        record = '\t'.join(record_element)
        records.append(record)

    return records


def create_isa_obs_data_from_obsvars(all_obs_units):
    # TODO: BH2018 - discussion with Cyril and Guillaume: Observation Values should be grouped by Observation Level {plot,block,plant,individual,replicate}
    # TODO: create as many ISA assays as there as declared ObservationLevel in the BRAPI message
    data_records = []
    header_elements = ["Assay Name", "Observation Identifier", "Trait Name", "Trait Value", "Performer", "Date",
                       "Comment[season]"]
    datafile_header = '\t'.join(header_elements)
    # print(datafile_header)
    data_records.append(datafile_header)
    # print("number of observation units: ", len(all_obs_units))
    for index in range(len(all_obs_units)):

        for item in range(len(all_obs_units[index]['observations'])):
            data_record = ("assay-name_(" + str(all_obs_units[index]["observationUnitName"]) + ")_" +
                           str(item) + "\t" +
                           str(all_obs_units[index]['observations'][item]['observationVariableDbId']) + "\t" +
                           str(all_obs_units[index]['observations'][item]['value']) + "\t" +
                           str(all_obs_units[index]['observations'][item]['observationTimeStamp']) + "\t" +
                           str(all_obs_units[index]['observations'][item]['collector']))
            # print("data_record # ", index, data_record)
            data_records.append(data_record)

    return data_records


def write_records_to_file(this_study_id, records, this_directory, filetype):
    logger.info('Doing something')
    # tdf_file = 'out/' + this_study_id
    with open(this_directory + filetype + this_study_id + '.txt', 'w') as fh:
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


def main(arg):
    """ Given a SERVER value (and BRAPI study identifier), generates an ISA-Tab document"""

    client = BrapiClient(SERVER, logger)

    # iterating through the trials held in a BRAPI server:
    for trial in client.get_trials(TRIAL_IDS):
        # print("Trial: ", trial['trialDbId'], "|", trial['trialName'])
        logger.info('we start from a set of Trials')
        investigation = Investigation()

        output_directory = get_output_path( trial['trialName'] )
        logger.info("Generating output in : "+ output_directory)

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
            study, investigation = create_isa_study(study_id, investigation)
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
                # get_germplasm_chars(germ)
                # Creating corresponding ISA biosources with is Creating isa characteristics from germplasm attributes.
                # ------------------------------------------------------
                source = Source(name=germ['germplasmName'], characteristics=get_germplasm_chars(germ))

                # Associating ISA sources to ISA study object
                study.sources.append(source)

                germ_counter = germ_counter + 1

            # Now dealing with BRAPI observation units and attempting to create ISA samples
            obsunits = []
            try:
                obsunits = client.get_obs_units_in_study(study_id)
            except Exception as excep:
                logger.exception(excep)
                print("error: ", excep)

            for i in range(len(obsunits)):
                # Getting the relevant germplasm used for that observation event:
                # ---------------------------------------------------------------
                this_source = study.get_source(obsunits[i]['germplasmName'])
                logger.debug("testing for the source reference: ", this_source)
                # print("SOURCE:", this_source)
                if this_source is not None:
                    this_sample = Sample(
                        name=obsunits[i]['observationUnitDbId'] + "_" + obsunits[i]['observationUnitName'],
                        derives_from=[this_source])
                    # --------------------------
                    # print("ou: ", ou)

                    if 'X' in obsunits[i].keys():
                        # print('KEY:', obsunits[i]['X'])
                        c = Characteristic(category=OntologyAnnotation(term="X"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['X']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'Y' in obsunits[i].keys():
                        # print('KEY:', obsunits[i]['X'])
                        c = Characteristic(category=OntologyAnnotation(term="Y"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['Y']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'blockNumber' in obsunits[i].keys():
                        # print('KEY:', obsunits[i]['X'])
                        c = Characteristic(category=OntologyAnnotation(term="Block Number"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['blockNumber']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'plotNumber' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="Plot Number"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['plotNumber']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'plantNumber' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="Plant Number"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['plantNumber']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'replicate' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="replicate"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['replicate']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationUnitDbId' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationUnitDbId"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['observationUnitDbId']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationUnitName' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationUnitName"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['observationUnitName']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationLevel' in obsunits[i].keys():
                        # TODO: if absent, a warning should be logged as this is a MIAPPE requirement
                        c = Characteristic(category=OntologyAnnotation(term="Observation unit type"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['observationLevel']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'observationLevels' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="observationLevels"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['observationLevels']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    if 'germplasmName' in obsunits[i].keys():
                        c = Characteristic(category=OntologyAnnotation(term="germplasmName"),
                                           value=OntologyAnnotation(term=str(obsunits[i]['germplasmName']),
                                                                    term_source="",
                                                                    term_accession=""))
                        this_sample.characteristics.append(c)

                    # Looking for treatment in BRAPI and mapping to ISA Study Factor Value
                    # --------------------------------------------------------------------
                    if 'treatments' in obsunits[i].keys():
                        for element in obsunits[i]['treatments']:
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

                # else:
                #     # print("normal: ", germ[key])
                #     c = Characteristic(category=OntologyAnnotation(term=str(key)),
                #                        value=OntologyAnnotation(term=str(germ[key]),
                #                                                 term_source="",
                #                                                 term_accession=""))
                # if key == 'accessionNumber':
                #     c = Characteristic(category=OntologyAnnotation(term="Material Source ID"),
                #                        value=OntologyAnnotation(term=str(germ[key]),
                #                                                 term_source="",
                #                                                 term_accession=""))
                #
                #
                # if c not in source.characteristics:
                #     source.characteristics.append(c)

            # Associating ISA sources to ISA study object
            study.sources.append(source)

            # germ_counter = germ_counter + 1

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
                #logger.debug("testing for the source reference: ", this_source)

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
                variable_records = create_isa_tdf_from_obsvars(client.get_study_observed_variables(study_id))
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
                data_readings = create_isa_obs_data_from_obsvars(client.get_obs_units_in_study(study_id))
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
