from isatools.model.v1 import *
import isatools.isatab
import os
import requests

EU_SOL_BRAPI_V1 = 'https://www.eu-sol.wur.nl/webapi/tomato/brapi/v1/'
PIPPA_BRAPI_V1 = "https://pippa.psb.ugent.be/pippa_experiments/brapi/v1/"

### Get info from BrAPI

def get_brapi_trials(endpoint):
    """Returns all the trials from an endpoint."""
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


def create_isa_study(endpoint, brapi_study_id):
    brapi_study = get_brapi_study(endpoint, brapi_study_id)
    study = Study(filename="s_study.txt")
    study.identifier = brapi_study['studyDbId']
    study.title = brapi_study['name']
    study.comments.append(Comment("Study Start Date", brapi_study['startDate']))
    study.comments.append(Comment("Study End Date", brapi_study['endDate']))
    study.comments.append(Comment("Study Geographical Location", brapi_study['location']['locationName']))
    return study

def get_phenotypes(endpoint):
    url = endpoint + "phenotype-search"
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise RuntimeError("Non-200 status code")
    study = r.json()['result']['data']
    return study


## Creating ISA objects
def create_isa_investigations(endpoint):
    investigations = []
    for trial in get_brapi_trials(endpoint):
        #print(trial)
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



def create_descriptor():
    """Returns a simple but complete ISA-Tab 1.0 descriptor for illustration."""

    # Create an empty Investigation object and set some values to the instance variables.

    investigation = Investigation()
    investigation.identifier = "i1"
    investigation.title = "My Simple ISA Investigation"
    investigation.description = "We could alternatively use the class constructor's parameters to set some default " \
                                "values at the time of creation, however we want to demonstrate how to use the " \
                                "object's instance variables to set values."
    investigation.submission_date = "2016-11-03"
    investigation.public_release_date = "2016-11-03"

    # Create an empty Study object and set some values. The Study must have a filename, otherwise when we serialize it
    # to ISA-Tab we would not know where to write it. We must also attach the study to the investigation by adding it
    # to the 'investigation' object's list of studies.

    study = Study(filename="s_study.txt")
    study.identifier = "s1"
    study.title = "My ISA Study"
    study.description = "Like with the Investigation, we could use the class constructor to set some default values, " \
                        "but have chosen to demonstrate in this example the use of instance variables to set initial " \
                        "values."
    study.submission_date = "2016-11-03"
    study.public_release_date = "2016-11-03"
    investigation.studies.append(study)

    # Some instance variables are typed with different objects and lists of objects. For example, a Study can have a
    # list of design descriptors. A design descriptor is an Ontology Annotation describing the kind of study at hand.
    # Ontology Annotations should typically reference an Ontology Source. We demonstrate a mix of using the class
    # constructors and setting values with instance variables. Note that the OntologyAnnotation object
    # 'intervention_design' links its 'term_source' directly to the 'obi' object instance. To ensure the OntologySource
    # is encapsulated in the descriptor, it is added to a list of 'ontology_source_references' in the Investigation
    # object. The 'intervention_design' object is then added to the list of 'design_descriptors' held by the Study
    # object.

    obi = OntologySource(name='OBI', description="Ontology for Biomedical Investigations")
    investigation.ontology_source_references.append(obi)
    intervention_design = OntologyAnnotation(term_source=obi)
    intervention_design.term = "intervention design"
    intervention_design.term_accession = "http://purl.obolibrary.org/obo/OBI_0000115"
    study.design_descriptors.append(intervention_design)


    # To create the study graph that corresponds to the contents of the study table file (the s_*.txt file), we need
    # to create a process sequence. To do this we use the Process class and attach it to the Study object's
    # 'process_sequence' list instance variable. Each process must be linked with a Protocol object that is attached to
    # a Study object's 'protocols' list instance variable. The sample collection Process object usually has as input
    # a Source material and as output a Sample material.

    # Here we create one Source material object and attach it to our study.

    source = Source(name='source_material')
    study.materials['sources'].append(source)

    # Then we create three Sample objects, with organism as Homo Sapiens, and attach them to the study. We use the utility function
    # batch_create_material() to clone a prototype material object. The function automatiaclly appends
    # an index to the material name. In this case, three samples will be created, with the names
    # 'sample_material-0', 'sample_material-1' and 'sample_material-2'.

    prototype_sample = Sample(name='sample_material', derives_from=source)
    ncbitaxon = OntologySource(name='NCBITaxon', description="NCBI Taxonomy")
    characteristic_organism = Characteristic(category=OntologyAnnotation(term="Organism"),
                                     value=OntologyAnnotation(term="Homo Sapiens", term_source=ncbitaxon,
                                                              term_accession="http://purl.bioontology.org/ontology/NCBITAXON/9606"))
    prototype_sample.characteristics.append(characteristic_organism)

    study.materials['samples'] = batch_create_materials(prototype_sample, n=3)  # creates a batch of 3 samples

    # Now we create a single Protocol object that represents our sample collection protocol, and attach it to the
    # study object. Protocols must be declared before we describe Processes, as a processing event of some sort
    # must execute some defined protocol. In the case of the class model, Protocols should therefore be declared
    # before Processes in order for the Process to be linked to one.

    sample_collection_protocol = Protocol(name="sample collection",
                                          protocol_type=OntologyAnnotation(term="sample collection"))
    study.protocols.append(sample_collection_protocol)
    sample_collection_process = Process(executes_protocol=sample_collection_protocol)

    # Next, we link our materials to the Process. In this particular case, we are describing a sample collection
    # process that takes one source material, and produces three different samples.
    #
    # (source_material)->(sample collection)->[(sample_material-0), (sample_material-1), (sample_material-2)]

    for src in study.materials['sources']:
        sample_collection_process.inputs.append(src)
    for sam in study.materials['samples']:
        sample_collection_process.outputs.append(sam)

    # Finally, attach the finished Process object to the study process_sequence. This can be done many times to
    # describe multiple sample collection events.

    study.process_sequence.append(sample_collection_process)

    # Next, we build n Assay object and attach two protocols, extraction and sequencing.

    assay = Assay(filename="a_assay.txt")
    extraction_protocol = Protocol(name='extraction', protocol_type=OntologyAnnotation(term="material extraction"))
    study.protocols.append(extraction_protocol)
    sequencing_protocol = Protocol(name='sequencing', protocol_type=OntologyAnnotation(term="material sequencing"))
    study.protocols.append(sequencing_protocol)

    # To build out assay graphs, we enumereate the samples from the study-level, and for each sample we create an
    # extraction process and a sequencing process. The extraction process takes as input a sample material, and produces
    # an extract material. The sequencing process takes the extract material and produces a data file. This will
    # produce three graphs, from sample material through to data, as follows:
    #
    # (sample_material-0)->(extraction)->(extract-0)->(sequencing)->(sequenced-data-0)
    # (sample_material-1)->(extraction)->(extract-1)->(sequencing)->(sequenced-data-1)
    # (sample_material-2)->(extraction)->(extract-2)->(sequencing)->(sequenced-data-2)
    #
    # Note that the extraction processes and sequencing processes are distinctly separate instances, where the three
    # graphs are NOT interconnected.

    for i, sample in enumerate(study.materials['samples']):

        # create an extraction process that executes the extraction protocol

        extraction_process = Process(executes_protocol=extraction_protocol)

        # extraction process takes as input a sample, and produces an extract material as output

        extraction_process.inputs.append(sample)
        material = Material(name="extract-{}".format(i))
        material.type = "Extract Name"
        extraction_process.outputs.append(material)

        # create a sequencing process that executes the sequencing protocol

        sequencing_process = Process(executes_protocol=sequencing_protocol)
        sequencing_process.name = "assay-name-{}".format(i)
        sequencing_process.inputs.append(extraction_process.outputs[0])

        # Sequencing process usually has an output data file

        datafile = DataFile(filename="sequenced-data-{}".format(i), label="Raw Data File")
        sequencing_process.outputs.append(datafile)

        # Ensure Processes are linked forward and backward. plink(from_process, to_process) is a function to set
        # these links for you. It is found in the isatools.model.v1 package

        plink(extraction_process, sequencing_process)

        # make sure the extract, data file, and the processes are attached to the assay

        assay.data_files.append(datafile)
        assay.materials['other_material'].append(material)
        assay.process_sequence.append(extraction_process)
        assay.process_sequence.append(sequencing_process)
        assay.measurement_type = OntologyAnnotation(term="gene sequencing")
        assay.technology_type = OntologyAnnotation(term="nucleotide sequencing")

    # attach the assay to the study

    study.assays.append(assay)
    return investigation


#### Creating ISA-Tab from EU_SOL_BRAPI_V1 data
# trials = get_brapi_trials(EU_SOL_BRAPI_V1)
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

phenotypes = get_phenotypes(PIPPA_BRAPI_V1)

for phenotype in phenotypes:
    print(phenotype)