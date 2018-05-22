import datetime

import os,errno
import isatools
import json
import requests

from isatools.model import Investigation, OntologyAnnotation, OntologySource, Assay, Study, Characteristic, Source, \
    Sample, Protocol, Process, StudyFactor, FactorValue, DataFile, ParameterValue, Comment, ProtocolParameter

# SERVER = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
SERVER = 'https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/'
# SERVER = 'https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/'

GNPIS_BRAPI_V1 = 'https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/'
EU_SOL_BRAPI_V1 = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
PIPPA_BRAPI_V1 = "https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/"


###########################################################
# Get info from BrAPI
###########################################################


def get_brapi_trials(endpoint):
    """Returns all the trials from an endpoint."""
    page = 0
    pagesize = 10
    maxcount = None
    while maxcount is None or page*pagesize < maxcount:
        params = {'page': page, 'pageSize': pagesize}
        r = requests.get(endpoint+'trials', params=params)
        if r.status_code != requests.codes.ok:
            raise RuntimeError("Non-200 status code")
        maxcount = int(r.json()['metadata']['pagination']['totalCount'])
        for trial in r.json()['result']['data']:
            yield trial
        page += 1


def get_brapi_study_by_endpoint(endpoint, study_identifier):
    """Returns a study from an endpoint, given its id."""
    # dealing with differences in the endpoints
    url = ''
    if endpoint == GNPIS_BRAPI_V1:
        url = endpoint + 'studies/' + str(study_identifier)
    elif endpoint == PIPPA_BRAPI_V1:
        url = endpoint + 'studies-search/' + str(study_identifier)
    elif endpoint == EU_SOL_BRAPI_V1:
        url = endpoint + 'studies-search/' + str(study_identifier)

    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    this_study = r.json()['result']
    return this_study


def get_phenotypes(endpoint):
    """Returns a phenotype information from a BrAPI endpoint."""
    url = endpoint + "phenotype-search"
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    phenotypes = r.json()['result']['data']
    return phenotypes


def get_germplasms(endpoint):
    url = endpoint + "germplasm-search"
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    these_germplasms = r.json()['result']['data']
    return these_germplasms


def get_germplasm_by_endpoint(endpoint, germplasm_id):
    url = endpoint + "germplasm-search" + str(germplasm_id)
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    this_germplasm = r.json()['result']
    return this_germplasm


###########################################################
# Creating ISA objects
###########################################################


def create_isa_investigations(endpoint):
    """Create ISA investigations from a BrAPI endpoint, starting from the trials information"""
    investigations = []
    for trial in get_brapi_trials(endpoint):
        this_investigation = Investigation()
        this_investigation.identifier = trial['trialDbId']
        this_investigation.title = trial['trialName']
        # investigation.comments.append(Comment("Investigation Start Date", trial['startDate']))
        # investigation.comments.append(Comment("Investigation End Date", trial['endDate']))
        # investigation.comments.append(Comment("Active", trial['active']))

        for this_study in trial['studies']:
            this_study = create_isa_study(this_study['studyDbId'])
            this_investigation.studies.append(this_study)
            investigations.append(this_investigation)
    return investigations


def create_materials(endpoint):
    """Create ISA studies from a BrAPI endpoint, starting from the studies, where there is no trial information."""
    for phenotype in get_phenotypes(endpoint):
        print(phenotype)
        # for now, creating the sample name combining studyDbId and potDbId -
        # eventually this should be observationUnitDbId
        sample_name = phenotype['studyDbId']+"_"+phenotype['plotNumber']
        this_sample = Sample(name=sample_name)
        that_source = Source(phenotype['germplasmName'], phenotype['germplasmDbId'])
        this_sample.derives_from = that_source


def paging(url, params, data, method):
    page = 0
    pagesize = 1000  # VIB doesn't seem to respect it
    maxcount = None
    # set a default dict for parameters
    if params is None:
        params = {}
    while maxcount is None or page < maxcount:
        params['page'] = page
        params['pageSize'] = pagesize
        
        print('retrieving page', page, 'of', maxcount, 'from', url)
        print(params)
        if method == 'GET':
            print("GETing", url)
            r = requests.get(url, params=params, data=data)
        elif method == 'PUT':
            print("PUTing", url)
            r = requests.put(url, params=params, data=data)
        elif method == 'POST':
            # params['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
            # Chrome/41.0.2272.101 Safari/537.36"
            params['Accept'] = "application/json"
            params['Content-Type'] = "application/json"

            print("POSTing", url)
            print("POSTing", params, data)
            headers = {}
            r = requests.post(url, params=json.dumps(params).encode('utf-8'), json=data, headers=headers)
            print(r)
            
        if r.status_code != requests.codes.ok:
            print(r)
            raise RuntimeError("Non-200 status code")
            
        maxcount = int(r.json()['metadata']['pagination']['totalPages'])
        
        for data in r.json()['result']['data']:
            yield data
            
        page += 1


def load_trials():
    for trial in paging(SERVER + 'trials', None, None, 'GET'):
        yield trial


def get_study(study_identifier):
    r = requests.get(SERVER + 'studies/' + str(study_identifier))
    if r.status_code != requests.codes.ok:
        print(r)
        raise RuntimeError("Non-200 status code")
    return r.json()["result"]


def get_germplasm_in_study(study_identifier):

    r = requests.get('https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/studies/' + study_identifier +
                     '/germplasm')
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    all_germplasms = r.json()['result']['data']

    return all_germplasms

    # params={}
    # can't find anyone that implements /studies/{id}/germplasm
    # have to do it as an phenotype search instead
    # note that this will omit any germplasm that hasn't got an associated phenotype
    # germplasm = set()
    # indata = json.dumps({"studyDbIds":[studyId]})
    # print(indata)
    # params['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
    #  Chrome/41.0.2272.101 Safari/537.36"
    # params['Accept'] = "application/json"
    # params['Content-Type'] = "application/json;charset=utf-8"
    # request_url='https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/phenotypes-search'
    # headers = {}
    # r = requests.post(request_url, params=json.dumps(params),data=json.dumps({"studyDbIds":[studyId]}))
    # print("Post request response content: ", r.content)

    # for phenotype in paging(SERVER + 'phenotypes-search/', params, indata, 'POST'):
    #     germplasm.add(phenotype['germplasmDbId'])
    # return germplasm


def get_obs_units_in_study(study_identifier):
    r = requests.get('https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/studies/' + study_identifier +
                     '/observationUnits')
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    all_obs_units = r.json()['result']['data']

    return all_obs_units


def get_germplasm(germplasm_id):
    url = SERVER + 'germplasm/' + str(germplasm_id) + '/attributes'
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    # germplasm = r.json()['result']
    germplasm = r.json()['result']['data']
    
    # url = SERVER+'germplasm-search?germplasmDbId='+str(germplasm_id)
    # print('GETing',url)
    # r = requests.get(url)
    # if r.status_code != requests.codes.ok:
    #     raise RuntimeError("Non-200 status code")
    # germplasm = r.json()['result']['data'][0]

    return germplasm


def get_brapi_study(study_identifier):
    url = SERVER + 'studies/' + str(study_identifier)
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    this_study = r.json()['result']
    return this_study


# def create_isa_study(brapi_study_id):
#     brapi_study = get_brapi_study(brapi_study_id)
#     # print(brapi_study)
#     this_study = Study(filename="s_study.txt")
#     this_study.identifier = brapi_study['studyDbId']
#     if 'name' in brapi_study:
#         this_study.title = brapi_study['name']
#     elif 'studyName' in brapi_study:
#         this_study.title = brapi_study['studyName']
#
#     if brapi_study['startDate'] is None:
#         pass
#         study.comments.append(Comment(name="Study Start Date", value="YYYY-MM-DD"))
#     else:
#         study.comments.append(Comment(name="Study End Date", value=brapi_study['startDate']))
#
#     if brapi_study['endDate'] is None:
#         study.comments.append(Comment(name="Study End Date", value="YYYY-MM-DD"))
#     else:
#         study.comments.append(Comment(name="Study End Date", value=brapi_study['endDate']))
#
#     if 'location' in brapi_study and 'locationName' in brapi_study['location']:
#         study.comments.append(Comment("Study Geographical Location", brapi_study['location']['locationName']))
#     return this_study


def create_isa_study(brapi_study_id):
    """Returns an ISA study given a BrAPI endpoints and a BrAPI study identifier."""
    brapi_study = get_brapi_study(brapi_study_id)
    this_study = Study(filename="s_" + str(brapi_study_id) + ".txt")
    this_study.identifier = brapi_study['studyDbId']
    if 'name' in brapi_study:
        this_study.title = brapi_study['name']
    elif 'studyName' in brapi_study:
        this_study.title = brapi_study['studyName']

    this_study.comments.append(Comment(name="Study Start Date", value=brapi_study['startDate']))
    this_study.comments.append(Comment(name="Study End Date", value=brapi_study['endDate']))
    if brapi_study['location'] is not None and brapi_study['location']['name'] is not None :
        this_study.comments.append(Comment(name="Study Geographical Location",
                                       value=brapi_study['location']['name']))
    else:
        this_study.comments.append(Comment(name="Study Geographical Location",value=""))

    study_design = brapi_study['studyType']
    oa_st_design = OntologyAnnotation(term=study_design)
    this_study.design_descriptors = [oa_st_design]

    oref_tt = OntologySource(name="OBI", description="Ontology for Biomedical Investigation")
    oa_tt = OntologyAnnotation(term="phenotyping", term_accession="", term_source=oref_tt)
    oref_mt = OntologySource(name="OBI", description="Ontology for Biomedical Investigation")
    oa_mt = OntologyAnnotation(term="multi-technology", term_accession="", term_source=oref_mt)
    isa_assay_file = "a_" + str(brapi_study_id) + ".txt"
    this_assay = Assay(measurement_type=oa_tt, technology_type=oa_mt, filename=isa_assay_file)
    this_study.assays.append(this_assay)

    return this_study


def create_isa_characteristic(category, value):
    if category is None or len(category) == 0:
        return None
    if value is None or len(value) == 0:
        return None
    # return Characteristic(category, str(value))
    this_characteristic = Characteristic(category=OntologyAnnotation(term=str(category)),
                                         value=OntologyAnnotation(term=str(value), term_source="",
                                         term_accession=""))
    # print("category: ", this_characteristic.category.term, "value: ", this_characteristic.value.term)
    return this_characteristic


def get_study_observed_variables(brapi_study_id):
    r = requests.get('https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/studies/' + brapi_study_id +
                     '/observationVariables')
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    all_obsvars = r.json()['result']['data']

    return all_obsvars


def create_isa_tdf_from_obsvars(obsvars):
    records = []
    header_elements = ["Variable Name", "Variable Full Name", "Variable Description", "Crop", "Growth Stage", "Date",
                       "Method", "Method Description", "Method Formula", "Method Reference", "Scale", "Scale Data Type",
                       "Scale Valid Values", "Unit", "Trait Name", "Trait Term REF", "Trait Class", "Trait Entity",
                       "Trait Attribute"]

    tdf_header = '\t'.join(header_elements)
    print(tdf_header)
    records.append(tdf_header)

    for obs_var in obsvars:
        record_element = [str(obs_var['name']), str(obs_var['ontologyDbId']), str(obs_var['ontologyName']), str(obs_var['crop']),
                          str(obs_var['growthStage']), str(obs_var['date']), str(obs_var['method']['name']),
                          str(obs_var['method']['description']), str(obs_var['method']['formula']),
                          str(obs_var['method']['reference']), str(obs_var['scale']['name']), str(obs_var['scale']['dataType']),
                          str(obs_var['scale']['validValues']['categories']), str(obs_var['scale']['xref']),
                          str(obs_var['trait']['name']), str(obs_var['trait']['xref']), str(obs_var['trait']['class']),
                          str(obs_var['trait']['entity']), str(obs_var['trait']['attribute'])]

        record = '\t'.join(record_element)
        print(record)
        records.append(record)

    return records


def get_germplasm_chars(germplasm):
    charax_per_germplasm={}
    # def create_isa_source(germplasm_id):
    # g = get_germplasm(germplasm_id)
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
        # print("category: ", key)
        if item in valid_categories:
            these_characteristics.append(create_isa_characteristic(str(item), str(germplasm[item])))
        charax_per_germplasm[germplasm_id]=these_characteristics

    # return Source(germplasm_id, characteristics=these_characteristics)
    return charax_per_germplasm

# investigation = create_descriptor()
# investigation = Investigation()
# ugent doesnt have trials
# for trial in load_trials():
#    print(trial['trialDbId'])
#    for study in trial['studies']:
#        study = get_study(study['studyDbId'])

# study_id = 'VIB_study___49'

study_id = "POPYOMICS-POP2-F"  #"BTH_Orgeval_2003_SetA2" # 'BTH_Chaux_des_Prés_2000_SetB1' or 'BTH_Dijon_2000_SetA'

germplasms = get_germplasm_in_study(study_id)

# germplasms_chars = {}
# for germplasm in germplasms:
#     germplasms_chars = get_germplasm_chars(germplasm)
#
# print(germplasms_chars.keys())


obsunits = get_obs_units_in_study(study_id)

variable_records = create_isa_tdf_from_obsvars(get_study_observed_variables(study_id))
print("variables: ", variable_records)

directory = "outputdir/"
try:
    os.makedirs(directory)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

# tdf_file = 'out/' + study_id
with open(directory + 't_' + study_id +'.txt', 'w') as tdf:
    for element in variable_records:
        print(element)
        tdf.write(element+'\n')

tdf.close()

# this is really slow and broken, so cheat for now!
# all_germplasm = ('Zea_VIB___1','Zea_VIB___2','Zea_VIB___3','Zea_VIB___4')

# Creating ISA objects
investigation = Investigation()
study = create_isa_study(study_id)
investigation.studies.append(study)

# for germplasm in germplasms:
#     # print("found germplasm:",germplasm["germplasmDbId"])
#     source = create_isa_source(germplasm)
#     # source1 = Source(name=germplasm["germplasmDbId"])
#     study.sources.append(source)
#     sample = Sample(germplasm["germplasmDbId"])
#     #isa_sources.append(source)
#     # print(source)
#     # study.materials['sources'].append(source)
#     study.materials['samples'].append(sample)
#     # print(sample)
#     sample_collection_protocol = Protocol(name="sample collection",
#                                           protocol_type=OntologyAnnotation(term="sample collection"))
#     study.protocols.append(sample_collection_protocol)
#     sample_collection_process = Process(executes_protocol=sample_collection_protocol)
#
#     sample_collection_process.inputs.append(source)
#     sample_collection_process.outputs.append(sample)
#
#     study.process_sequence.append(sample_collection_process)


isa_sources = []
counter = 0

phenotyping_protocol = Protocol(name="phenotyping",  protocol_type=OntologyAnnotation(term="phenotyping"))
study.protocols.append(phenotyping_protocol)
assay = study.assays[0]

for ou in obsunits:
    characteristics = []
    factors = []

    if 'blockNumber' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="blockNumber"),
                           value=OntologyAnnotation(term=str(ou['blockNumber']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'plotNumber' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="plotNumber"),
                           value=OntologyAnnotation(term=str(ou['plotNumber']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'plantNumber' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="plantNumber"),
                           value=OntologyAnnotation(term=str(ou['plantNumber']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'replicate' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="replicate"),
                           value=OntologyAnnotation(term=str(ou['replicate']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'observationUnitDbId' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="observationUnitDbId"),
                           value=OntologyAnnotation(term=str(ou['observationUnitDbId']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'observationUnitName' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="observationUnitName"),
                           value=OntologyAnnotation(term=str(ou['observationUnitName']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'observationLevel' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="observationLevel"),
                           value=OntologyAnnotation(term=str(ou['observationLevel']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'observationLevels' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="observationLevels"),
                           value=OntologyAnnotation(term=str(ou['observationLevels']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'germplasmName' in ou.keys():
        c = Characteristic(category=OntologyAnnotation(term="germplasmName"),
                           value=OntologyAnnotation(term=str(ou['germplasmName']), term_source="",
                           term_accession=""))
        characteristics.append(c)

    if 'germplasmDbId' in ou.keys():

        for element in germplasms:
            if element['germplasmDbId'] == ou['germplasmDbId']:
                for key in element.keys():
                    print(key)
                    c = Characteristic(category=OntologyAnnotation(term=str(key)),
                                   value=OntologyAnnotation(term=str(element[key]), term_source="",
                                   term_accession=""))
                    characteristics.append(c)

        # c = Characteristic(category=OntologyAnnotation(term="germplasmDbId"),
        #                    value=OntologyAnnotation(term=str(ou['germplasmDbId']), term_source="",
        #                    term_accession=""))
        # characteristics.append(c)

    source = Source(name=ou['observationUnitDbId'], characteristics=characteristics)
    # print(source)
    study.sources.append(source)
    sample = Sample(name=ou["observationUnitDbId"])

    if 'treatments' in ou.keys():
        for element in ou['treatments']:
            for key in element.keys():
                f = StudyFactor(name=key, factor_type=OntologyAnnotation(term=key))
                if f not in study.factors:
                    study.factors.append(f)

                fv = FactorValue(factor_name=f, value=OntologyAnnotation(term=str(element[key]), term_source="",
                                                                              term_accession=""))
                sample.factor_values.append(fv)
    print(sample)

    if 'observations' in ou.keys():
        for ob in ou['observations']:
            phenotyping_process = Process(executes_protocol=phenotyping_protocol)
            phenotyping_process.name = "assay-name-{}".format(counter)
            phenotyping_process.inputs.append(sample)
            # print(ob['observations'])
            if 'season' in ou['observations'][0].keys():
                # if 'season' in phenotyping_protocol.parameter_list:
                #     pass
                # else:
                #     pp= ProtocolParameter(parameter_name=OntologyAnnotation(term="season"))
                #     phenotyping_protocol.add_param(pp)

                pv = ParameterValue(category=ProtocolParameter(parameter_name=OntologyAnnotation(term="season")),
                                    value=OntologyAnnotation(term=str(ou['observations'][0]['season']), term_source="",
                                                             term_accession=""))

                phenotyping_process.parameter_values.append(pv)

                if ou['observations'][0]['observationTimeStamp'] is not None:
                    phenotyping_process.date = str(ou['observations'][0]['observationTimeStamp'])
                else:
                    phenotyping_process.date = datetime.datetime.today().isoformat()

                if ou['observations'][0]['collector'] is not None:
                    phenotyping_process.performer = str(ou['observations'][0]['collector'])
                else:
                    phenotyping_process.performer = "none reported"

    datafile = DataFile(filename="phenotyping-data-{}".format(counter), label="Raw Data File")
    phenotyping_process.outputs.append(datafile)
    assay.data_files.append(datafile)
    assay.samples.append(sample)
    assay.process_sequence.append(phenotyping_process)
    assay.measurement_type = OntologyAnnotation(term="phenotyping")
    assay.technology_type = OntologyAnnotation(term="mixed techniques")

# attach the assay to the study
    if assay not in study.assays:
        study.assays.append(assay)

    study.samples.append(sample)
    # study.materials['samples'].append(sample)
    # print(sample)
    # print(element[key])

    # study.assays.append(Assay(filename="a_phenotyping.txt", measurement_type=OntologyAnnotation(term="phenotyping"),
    # technology_type=OntologyAnnotation(term="")))

    # if "sample collection" not in sample_collection_protocol.protocol_type:
    sample_collection_protocol = Protocol(name="sample collection",
                                          protocol_type=OntologyAnnotation(term="sample collection"))

    if sample_collection_protocol not in study.protocols:
        study.protocols.append(sample_collection_protocol)

    sample_collection_process = Process(executes_protocol=sample_collection_protocol)
    sample_collection_process.performer = "john smith"
    sample_collection_process.date_=datetime.datetime.today()
    sample_collection_process.inputs.append(source)
    sample_collection_process.outputs.append(sample)

    study.process_sequence.append(sample_collection_process)

    counter = counter+1
print("counter: ", counter)
print(study)


isatools.isatab.dump(investigation, output_path=directory)  # dumps() writes out the ISA
# as a string representation of the ISA-Tab
# isatools.isatab.dumps(investigation)
# isatools.isatab.dump(isa_obj=investigation, output_path='./out/')


#################################################################################
# Creating ISA-Tab from GNPIS_BRAPI_V1 date [old call was EU_SOL_BRAPI_V1 data ]
#################################################################################

# investigations = create_isa_investigations(GNPIS_BRAPI_V1) #EU_SOL_BRAPI_V1
#
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
