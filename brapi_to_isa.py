from isatools.model.v1 import *
import isatools.isatab
import json
import os
import requests

URGI_BRAPI_V1 = 'https://urgi.versailles.inra.fr/E1DfertSn986wm-GnpISCore-srv/brapi/v1/'
EU_SOL_BRAPI_V1 = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
PIPPA_BRAPI_V1 = "https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/"
SERVER = 'https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/'

###########################################################
### Get info from BrAPI
###########################################################

def get_brapi_trials(endpoint):
    """Returns all the trials from a BrAPI endpoint."""
    page = 0
    pagesize = 10
    maxcount = None
    while maxcount == None or page*pagesize < maxcount:
        params = {'page':page,'pageSize':pagesize}
        r = requests.get(endpoint+'trials', params=params)
        if r.status_code != requests.codes.ok:
            raise RuntimeError("Non-200 status code")
        maxcount = int(r.json()['metadata']['pagination']['totalCount'])
        for trial in r.json()['result']['data']:
            yield trial
        page += 1

def get_brapi_study(endpoint, study_id):
    """Returns a study from an endpoint, given its id."""
    ###dealing with differences in the endpoints
    if (endpoint==EU_SOL_BRAPI_V1):
        url = endpoint + 'studies/' + str(study_id)
    elif (endpoint==PIPPA_BRAPI_V1):
        url = endpoint + 'studies-search/' + str(study_id)
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    study = r.json()['result']
    return study

def get_brapi_study(study_id):
    url = SERVER+'studies/'+str(study_id)
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    study = r.json()['result']
    return study


def get_phenotypes(endpoint):
    """Returns a phenotype information from a BrAPI endpoint."""
    url = endpoint + "phenotype-search"
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    phenotypes = r.json()['result']['data']
    return phenotypes

def get_germplasms(endpoint):
    """Returns all germplasms from a BrAPI endpoint."""
    url = endpoint + "germplasm-search"
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    germplasms = r.json()['result']['data']
    return germplasms

def get_germplasm(endpoint, germplasm_id):
    """Return a germplasm by id from a BrAPI endpoint."""
    url = endpoint + "germplasm-search" + str(germplasm_id)
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    germplasm = r.json()['result']
    return germplasm

###########################################################
## Creating ISA objects
###########################################################

def create_isa_investigations(endpoint):
    """Create ISA investigations from a BrAPI endpoint, starting from the trials information"""
    investigations = []
    for trial in get_brapi_trials(endpoint):
        investigation = Investigation()
        investigation.identifier = trial['trialDbId']
        investigation.title = trial['trialName']
        investigation.comments.append(Comment("Investigation Start Date", trial['startDate']))
        investigation.comments.append(Comment("Investigation End Date", trial['endDate']))
        investigation.comments.append(Comment("Active", trial['active']))

        for study in trial['studies']:
            study = create_isa_study(endpoint,study['studyDbId'])
            investigation.studies.append(study)
            investigations.append(investigation)
    return investigations


def create_isa(endpoint):
    """Create ISA studies from a BrAPI endpoint, starting from the studies, where there is no trial information."""
    study_dict = dict()
    investigations = []
    for phenotype in get_phenotypes(endpoint):
        print(phenotype)
        #creating a source per germplasm
        source = create_isa_source(phenotype['germplasmDbId'])
        ### for now, creating the sample name combining studyDbId and plotNumber - eventually this should be observationUnitDbId
        sample_name = phenotype['studyDbId'] + "_" + phenotype['plotNumber']
        sample = Sample(sample_name, derives_from=source)
        study_id = phenotype['studyDbId']
        try:
            study = study_dict[study_id]
        except KeyError:
            study = create_isa_study(phenotype['studyDbId'])
            study_dict.update({ (study_id, study) })
        study.materials['sources'].append(source)
        study.materials['samples'].append(sample)

        growth_protocol = Protocol(name="growth protocol",
                                          protocol_type=OntologyAnnotation(term="growth protocol"))
        study.protocols.append(growth_protocol)
        growth_process = Process(executes_protocol=growth_protocol)

        for src in study.materials['sources']:
            growth_process.inputs.append(src)
        for sam in study.materials['samples']:
            growth_process.outputs.append(sam)


        study.process_sequence.append(growth_process)
        assay = Assay(filename="a_assay.txt")
        study.assays.append(assay)


    for key, value in study_dict.items():
        investigation = Investigation()
        investigation.studies.append(study_dict[key])
        investigations.append(investigation)






    return investigations


def create_isa_study(endpoint, brapi_study_id):
    """Returns an ISA study given a BrAPI endpoints and a BrAPI study identifier."""
    brapi_study = get_brapi_study(endpoint, brapi_study_id)
    study = Study(filename="s_study.txt")
    study.identifier = brapi_study['studyDbId']
    study.title = brapi_study['name']
    study.comments.append(Comment("Study Start Date", brapi_study['startDate']))
    study.comments.append(Comment("Study End Date", brapi_study['endDate']))
    study.comments.append(Comment("Study Geographical Location", brapi_study['location']['locationName']))
    return study
   
    
def paging(url,params,data,method):
    page = 0
    pagesize = 1000 #VIB doesn't seem to respect it
    maxcount = None
    #set a default dict for parameters
    if params == None:
        params = {}
    while maxcount == None or page < maxcount:
        params['page'] = page
        params['pageSize'] = pagesize
        
        print('retrieving page',page,'of',maxcount,'from',url)
        
        if method == 'GET':
            print("GETing",url)
            r = requests.get(url, params=params,data=data)
        elif method == 'PUT':
            print("PUTing",url)
            r = requests.put(url, params=params,data=data)
        elif method == 'POST':
            print("POSTing",url)
            r = requests.post(url, params=params,data=data)
            
        if r.status_code != requests.codes.ok:
            print(r)
            raise RuntimeError("Non-200 status code")
            
        maxcount = int(r.json()['metadata']['pagination']['totalPages'])
        
        for data in r.json()['result']['data']:
            yield data
            
        page += 1

def load_trials():
    for trial in paging(SERVER+'trials', None, None, 'GET'):
        yield trial

def get_study(studyId):
    r = requests.get(SERVER+'studies/'+str(studyId))
    if r.status_code != requests.codes.ok:
        print(r)
        raise RuntimeError("Non-200 status code")
    return r.json()["result"]
    
def get_germplasm_in_study(studyId):
    #can't find anyone that implements /studies/{id}/germplasm
    #have to do it as an phenotype search instead
    #note that this will omit any germplasm that hasn't got an associated phenotype
    germplasm = set()
    for phenotype in paging(SERVER+'phenotype-search', None, json.dumps({"studyDbIds" : [ str(studyId) ]}), 'POST') :
        germplasm.add(phenotype['germplasmDbId'])
    return germplasm
    
def get_germplasm(germplasm_id):
    #url = SERVER+'germplasm/'+str(germplasm_id)
    #r = requests.get(url)
    #if r.status_code != requests.codes.ok:
    #    raise RuntimeError("Non-200 status code")
    #germplasm = r.json()['result']
    
    url = SERVER+'germplasm-search?germplasmDbId='+str(germplasm_id)
    print('GETing',url)
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    germplasm = r.json()['result']['data'][0]
    
    
    return germplasm

def create_isa_study(brapi_study_id):
    brapi_study = get_brapi_study(brapi_study_id)
    #print(brapi_study)
    study = Study(filename="s_study.txt")
    study.identifier = brapi_study['studyDbId']
    if 'name' in brapi_study:
        study.title = brapi_study['name']
    elif 'studyName' in brapi_study:
        study.title = brapi_study['studyName']
    
    study.comments.append(Comment("Study Start Date", brapi_study['startDate']))
    study.comments.append(Comment("Study End Date", brapi_study['endDate']))
    if 'location' in brapi_study and 'locationName' in brapi_study['location']:
        study.comments.append(Comment("Study Geographical Location", brapi_study['location']['locationName']))
    return study
    
    
def create_isa_characteristic(category, value):
    if category == None or len(category) == 0:
        return None
    if value == None or len(value) == 0:
        return None
    return Characteristic(category=OntologyAnnotation(term=category),
                   value=OntologyAnnotation(term=str(value)))

def create_isa_source(germplasm_id):
    """Given a germplasm_id, create an ISA Source object"""
    g = get_germplasm(germplasm_id)
    characteristics = []

    validcategories = set()
    # validcategories.add("germplasmSeedSource")
    # validcategories.add("typeOfGermplasmStorageCode")
    # validcategories.add("acquisitionDate")
    # validcategories.add("defaultDisplayName")
    # validcategories.add("germplasmPUI")
    # validcategories.add("synonyms")
    # validcategories.add("speciesAuthority")
    validcategories.add("species")
    validcategories.add("subtaxa")
    #validcategories.add("accessionNumber")
    validcategories.add("pedigree")
    # validcategories.add("subtaxaAuthority")
    # validcategories.add("instituteCode")
    # validcategories.add("germplasmName")
    # validcategories.add("instituteName")
    # validcategories.add("commonCropName")
    # validcategories.add("germplasmDbId")
    validcategories.add("genus")
    #validcategories.add("biologicalStatusOfAccessionCode")
    validcategories.add("countryOfOriginCode")

    for category in g:
        if category in validcategories:
            c = create_isa_characteristic(category, g[category])
            if (c !=None):
                characteristics.append(c)

    return Source(germplasm_id, characteristics = characteristics)

#investigation = create_descriptor()
#investigation = Investigation()

#ugent doesnt have trials
#for trial in load_trials():
#    print(trial['trialDbId'])
#    for study in trial['studies']:
#        study = get_study(study['studyDbId'])

# study_id = 'VIB_study___49'
# #germplasm = get_germplasm_in_study(study_id)
# #this is really slow and broken, so cheat for now!
# all_germplasm = ('Zea_VIB___1','Zea_VIB___2','Zea_VIB___3','Zea_VIB___4')
# print(all_germplasm)

## Creating ISA objects
# investigation = Investigation()
# study = create_isa_study(study_id)
# investigation.studies.append(study)
#
# for germplasm_id in all_germplasm:
#     print("create germplasm for",germplasm_id)
#     germplasm = create_isa_source(germplasm_id)
#     print(germplasm)
#     study.materials['sources'].append(germplasm)
#
# #isatools.isatab.dump(investigation, output_path='./out/')  # dumps() writes out the ISA as a string representation of the ISA-Tab
# isatools.isatab.dumps(investigation)
# isatools.isatab.dump(isa_obj=investigation, output_path='./out/')


#### Creating ISA-Tab from EU_SOL_BRAPI_V1 data
# investigations = create_isa_investigations(EU_SOL_BRAPI_V1)
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

### Creating ISA-Tab from PIPPA endpoint data

#create_materials(PIPPA_BRAPI_V1)


# germplasms = get_germplasms(PIPPA_BRAPI_V1)
# for germplasm in germplasms:
#     print(germplasm)


investigations = create_isa(PIPPA_BRAPI_V1)

if not os.path.exists("output"):
    os.makedirs("output")

if not os.path.exists("output/eu_sol"):
    os.makedirs("output/eu_sol")

for investigation in investigations:
    directory = "output/pippa/trial_"+str(investigation.identifier)
    if not os.path.exists(directory):
        os.makedirs(directory)
    isatools.isatab.dump(investigation, directory)

