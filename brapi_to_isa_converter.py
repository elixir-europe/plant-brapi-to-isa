from isatools.model import Investigation, OntologyAnnotation, OntologySource, Assay, Study, Characteristic, Source, \
    Sample, Comment, Person

from pycountry_convert import country_alpha3_to_country_alpha2 as a3a2
import copy
from collections import defaultdict
from brapi_client import BrapiClient
import re

def att_test(dictionary, attribute, NA=""):
    if attribute in dictionary and dictionary[attribute]:
        if dictionary[attribute] in ['NA', 'na','Na', 'n.a.', 'N.A.', 'N.a.']:
            return NA
        return str(dictionary[attribute])
    else:
        return NA

# ENVIRONMENTAL PARAMETERS
# ------------------------

PAR_NAinData = "NA"
PAR_NAinBrAPI = "NA in BrAPI"
PAR_defaultObsLvl = "plant"
PAR_suppObsLvl = ['block', 'sub-block', 'plot', 'plant', 'study', 'pot', 'replication', 'replicate','individual', 'unit-parcel']

class BrapiToIsaConverter:
    """ Converter json coming out of the BRAPI to ISA object

    ..warning: you may want to tweak this class name
    ..warning: some methods may never be called by the main:
        - create_isa_investigation()
        - create_germplasm_chars()
        - create_materials()
    """

    def __init__(self, logger, endpoint):
        self.logger = logger
        self.endpoint = endpoint
        self._brapi_client = BrapiClient(self.endpoint, self.logger)
        self.ontologies = self._brapi_client.get_ontologies()


    def get_obs_levels(self, brapi_study_id, OBSERVATIONUNITLIST):
        # because not every obs level has the same variables, and this is not yet supported by brapi to filter on /
        # every observation will be checked for its variables and be linked to the obeservation level
        obs_level_in_study = defaultdict(set)
        obs_levels = defaultdict(set)
        lvlNotAvailable = False
        for ou in OBSERVATIONUNITLIST:
            for obs in ou['observations']:
                if 'observationLevel' in ou and ou['observationLevel']:
                    obs_level_in_study[ou['observationLevel'].lower()].add(
                        re.sub('[\s]+', '_', att_test(obs, 'observationVariableName', "NA variable name")))
                    if 'observationLevels' in ou.keys() and ou['observationLevels']:
                        for obslvl in ou['observationLevels'].split(","):
                            if len(obslvl.split(":")) == 2:
                                a, b = obslvl.split(":")
                                obs_levels[ou['observationLevel'].lower()].add(a)
                            elif len(obslvl.split(":")) == 1:
                                obs_levels[ou['observationLevel'].lower()].add(obslvl)
                else:
                    obs_level_in_study[PAR_defaultObsLvl].add(re.sub('[\s]+', '_', att_test(obs, 'observationVariableName', "NA variable")))
                    lvlNotAvailable = True
        if lvlNotAvailable:
            self.logger.info("This BrAPI endpoint does not contain observation levels. Please add 'observationLevel' to the observations. Default " + PAR_defaultObsLvl + " is taken as observation level.")
            self.logger.info("Following observation levels are supported: " + str(PAR_suppObsLvl) + ".")

        self.logger.info("Observation Levels in study: " +
                         ",".join(obs_level_in_study.keys()))
        return obs_level_in_study, obs_levels

    def organism_characteristic(self, all_germplasm_attributes, taxonId):
        """" Given a a dictionairy with the germplasm details, retrieve the organism characteristic"""

        #Testing for genus and species availability
        genus = att_test(all_germplasm_attributes, 'genus')
        species = att_test(all_germplasm_attributes, 'species')

        #Checking if taxonId is supplied or not, otherwise fetch it from www.ebi.ac.uk
        if not taxonId or not taxonId.isdigit():
            taxonId = self._brapi_client.get_taxonId(genus, species)
        if taxonId:
            return self.create_isa_characteristic('Organism', "NCBITAXON:{}".format(str(taxonId)))
        else:
            return self.create_isa_characteristic('Organism', att_test(all_germplasm_attributes, 'commonCropName', PAR_NAinData))

    def create_germplasm_chars(self, germplasm):
        """" Given a BRAPI Germplasm ID, retrieve the list of all attributes from BRAPI and returns a list of ISA
        characteristics using MIAPPE tags for compliance + X-check against ISAconfiguration"""
        # TODO: switch BRAPI tags to MIAPPE Tags

        returned_characteristics = []

        germplasm_id = germplasm['germplasmDbId']
        all_germplasm_attributes = self._brapi_client.get_germplasm(
            germplasm_id)

        if att_test(all_germplasm_attributes, 'taxonIds'):
            taxonId = ''
            for taxonid in all_germplasm_attributes['taxonIds']:
                if taxonid['sourceName'] in ['NCBITaxon', 'ncbiTaxon']:
                    c = self.organism_characteristic(
                        all_germplasm_attributes, taxonid['taxonId'])
            returned_characteristics.append(c)
            
        else:
            c = self.organism_characteristic(all_germplasm_attributes, "")
            returned_characteristics.append(c)

        mapping_dictionnary = {
            "genus": "Genus",
            "species": "Species",
            "subtaxa": "Infraspecific Name",
            "accessionNumber": "Material Source ID",
            "germplasmPUI": "Material Source DOI",
        }

        for key in mapping_dictionnary:
            c = self.create_isa_characteristic(
                mapping_dictionnary[key], str(att_test(all_germplasm_attributes, key)))
            returned_characteristics.append(c)

        return returned_characteristics

    def create_isa_study(self, brapi_study_id, investigation, obs_levels_in_study):
        """Returns an ISA study given a BrAPI endpoints and a BrAPI study identifier."""

        brapi_study = self._brapi_client.get_study(brapi_study_id)
        
        # Adding study information on investigation level
        ###########################################################################
        this_study = Study(filename="s_" + str(brapi_study_id) + ".txt")

        # Adding general study information
        this_study.identifier = brapi_study.get('studyDbId', "")

        if 'name' in brapi_study:
            this_study.title = brapi_study['name']
        elif 'studyName' in brapi_study:
            this_study.title = brapi_study['studyName']
        else:
            this_study.title = PAR_NAinData

        this_study.description = att_test(brapi_study, 'studyDescription', PAR_NAinData)

        oa_st_design = OntologyAnnotation(term=att_test(brapi_study, 'studyType', PAR_NAinData))
        oa_st_design.comments.append(Comment(name="Study Design Description", value=PAR_NAinBrAPI))
        oa_st_design.comments.append(Comment(name="Observation Unit Level Hierarchy", value=PAR_NAinBrAPI))
        oa_st_design.comments.append(Comment(name="Observation Unit Description", value=PAR_NAinBrAPI))
        oa_st_design.comments.append(Comment(name="Map of Experimental Design", value=PAR_NAinBrAPI))  
        this_study.design_descriptors = [oa_st_design]

        this_study.comments.append(Comment(name="Study Start Date", value=att_test(brapi_study, 'startDate')))
        this_study.comments.append(Comment(name="Study End Date", value=att_test(brapi_study, 'endDate')))
        this_study.comments.append(Comment(name="Trait Definition File", value="t_" + str(brapi_study_id) + ".txt"))
        this_study.comments.append(Comment(name="Description of Growth Facility",value=PAR_NAinBrAPI))
        this_study.comments.append(Comment(name="Type of Growth Facility",value=PAR_NAinBrAPI))
        this_study.comments.append(Comment(name="Study Contact Institution",value=PAR_NAinBrAPI))
        
        # Adding Location information 
        if 'location' in brapi_study and brapi_study['location']:
            this_study.comments.append(Comment(name="Study Experimental Site", value=att_test(brapi_study['location'], 'name', PAR_NAinData)))

            if 'countryCode' in brapi_study['location'] and brapi_study['location']['countryCode']:
                if len(brapi_study['location']['countryCode']) == 3:
                    this_study.comments.append(Comment(name="Study Country",
                                                    value=a3a2(brapi_study['location']['countryCode'])))
                elif len(brapi_study['location']['countryCode']) == 2:
                    this_study.comments.append(Comment(name="Study Country",
                                                    value=brapi_study['location']['countryCode']))
            elif 'countryName' in brapi_study['location'] and brapi_study['location']['countryName']:
                this_study.comments.append(Comment(name="Study Country",
                                                value=brapi_study['location']['countryName']))
            else:
                this_study.comments.append(
                    Comment(name="Study Country", value=PAR_NAinData))

            this_study.comments.append(Comment(name="Study Latitude", value=att_test(brapi_study['location'], 'latitude')))
            this_study.comments.append(Comment(name="Study Longitude", value=att_test(brapi_study['location'], 'longitude')))
            this_study.comments.append(Comment(name="Study Altitude",value=att_test(brapi_study['location'], 'altitude')))
        else:
            self.logger.info("BrAPI study " + brapi_study['studyDbId'] + "has no location attribute, this is mandatory to be MIAPPE compliant.")

        # Adding Contacts information
        if att_test(brapi_study,'contacts' ):
            for brapicontact in brapi_study['contacts']:
                #NOTE: brapi has just name attribute -> no separate first/last name
                ContactName = brapicontact['name'].split(' ')
                role = OntologyAnnotation(term=att_test(brapicontact, 'type', PAR_NAinData))
                contact = Person(first_name=ContactName[0], last_name=ContactName[1],
                affiliation=att_test(brapicontact, 'institutionName', PAR_NAinData), email=att_test(brapicontact, 'email'), address=PAR_NAinBrAPI, roles=[role])
                this_study.contacts.append(contact)

        # Adding dataLinks inforamtion
        if att_test(brapi_study,'dataLinks'):
            for brapidata in brapi_study['dataLinks']:
                this_study.comments.append(Comment(name="Study Data File Link",value=brapidata['url']))
                this_study.comments.append(Comment(name="Study Data File Description",value=brapidata['type']))
                this_study.comments.append(Comment(name="Study Data File Version",value=PAR_NAinBrAPI))

        # Declaring as many ISA Assay Types as there are BRAPI Observation Levels
        ###########################################################################
        for level in obs_levels_in_study:
            if level not in PAR_suppObsLvl:
                self.logger.info("The observation level " + level + " is not supported by MIAPPE at this moment and will not be validated.")
                self.logger.info("Following observation levels are supported: " + str(PAR_suppObsLvl) + ".")

            oref_mt = OntologySource(
                name="OBI", description=self.ontologies["obi"][0], file=self.ontologies["obi"][1])
            oa_mt = OntologyAnnotation(
                term="phenotyping", term_accession="", term_source=oref_mt)
            oref_tt = OntologySource(
                name="OBI", description=self.ontologies["obi"][0], file=self.ontologies["obi"][1])
            oa_tt = OntologyAnnotation(
                term=level + " level analysis", term_accession="", term_source=oref_tt)
            
            isa_assay_file = "a_" + str(brapi_study_id) + "_" + level + ".txt"
            new_assay = Assay(measurement_type=oa_mt,
                              technology_type=oa_tt, filename=isa_assay_file)
            new_assay.characteristic_categories.append(level)

            this_study.assays.append(new_assay)

            if oref_mt not in investigation.ontology_source_references:
                investigation.ontology_source_references.append(oref_mt)
            if oref_tt not in investigation.ontology_source_references:
                investigation.ontology_source_references.append(oref_tt)

        self.logger.info("Number of ISA assays: " + str(len(this_study.assays)))

        return this_study, investigation

    def create_isa_characteristic(self, my_category, my_value):
        """Given a pair of category and value, return an ISA Characteristics element """
        this_characteristic = Characteristic(category=OntologyAnnotation(term=str(my_category)),
                                             value=OntologyAnnotation(term=str(my_value), term_source="",
                                                                      term_accession=""))

        return this_characteristic

    def create_isa_tdf_from_obsvars(self, obsvars):
        records = []
        elements = {
            "Variable ID": [],
            "Variable Name": [],
            "Variable Accession Number": [],
            "Trait": [],
            "Trait Accession Number": [],
            "Method": [],
            "Method Accession Number": [],
            "Method Description": [],
            "Reference Associated to the Method": [],
            "Scale": []
        }

        # decorating dictionairy
        for i, obs_var in enumerate(obsvars):
            obs_var_id = re.search('([a-zA-Z]*):[0-9]*', att_test(obs_var, 'observationVariableDbId'))
            obs_var_name = att_test(obs_var, 'name')
            obs_var_trait_id = re.search('([a-zA-Z]*):[0-9]*', att_test(obs_var['trait'], 'traitDbId'))
            obs_var_method_id = re.search('([a-zA-Z]*):[0-9]*', att_test(obs_var['method'], 'methodDbId'))

            elements['Variable ID'].append(re.sub('[\s]+', '_', obs_var_name))
            
            if obs_var_id and obs_var_id.group(1).lower() in self.ontologies:
                if att_test(obs_var, 'synonyms'):  
                    elements['Variable Name'].append('; '.join(obs_var['synonyms']))

                elements['Variable Accession Number'].append(obs_var_id.group(0).upper())

            else:
                if att_test(obs_var, 'synonyms'):  
                    elements['Variable Name'].append('; '.join(obs_var['synonyms']) + ' (BrAPI variableDbId: ' + att_test(obs_var, 'observationVariableDbId', 'NA') + ')')
                else: 
                     elements['Variable Name'].append('(BrAPI variableDbId: ' + att_test(obs_var, 'observationVariableDbId', 'NA') + ')')

            elements['Trait'].append(att_test(obs_var['trait'], 'name'))

            if obs_var_trait_id and obs_var_trait_id.group(1).lower() in self.ontologies:
                elements['Trait Accession Number'].append(obs_var_trait_id.group(0).upper())

            elements['Method'].append(att_test(obs_var['method'], 'name', att_test(obs_var, 'name', PAR_NAinData)))
            
            elements['Method Description'].append(att_test(obs_var['method'], 'description', att_test(obs_var['trait'], 'description', PAR_NAinData)))
            
            if obs_var_method_id and obs_var_method_id.group(1).lower() in self.ontologies:
                elements['Method Accession Number'].append(obs_var_method_id.group(0).upper())

            elements['Reference Associated to the Method'].append(att_test(obs_var['method'], 'reference'))
            elements['Scale'].append(att_test(obs_var['scale'], 'name', PAR_NAinData))

        # Deleting empty columns
        data_elements = []
        header_elements = []
        for key, value in elements.items():
            if len(value) != value.count(''):
                data_elements.append(value)
                header_elements.append(key)
        
        # dumping header
        records.append('\t'.join(header_elements))
        # transposingdata
        data_elements = list(map(list, zip(*data_elements)))
        # dumping data 
        for line in data_elements:
            records.append('\t'.join(line))

        return records

    def create_isa_obs_data_from_obsvars(self, obs_units, obs_variables, level, germplasminfo, obs_levels, FLATTEN_boolean):
        data_records = []
        data_records_flat = []
        obs_levels_header = []
        for obslvl in obs_levels[level]:
            obs_levels_header.append("observationLevels[{}]".format(obslvl))
        # headers belonging observation unit
        obs_unit_header = ["observationUnitDbId", "observationUnitXref",
                           "X", "Y", "germplasmDbId", "germplasmName"]
        # headers belonging germplasm
        germpl_header = ["accessionNumber"]
        # headers belonging observation
        obs_header = ["season", "observationTimeStamp"]
        # adding variables headers
        head = obs_levels_header + obs_unit_header + \
            germpl_header + obs_header + obs_variables

        datafile_header = '\t'.join(head)
        data_records.append(datafile_header)
        data_records_flat.append(datafile_header)

        emptyRow = []  # Empty row that is later filled in with values -> fixed row size
        for i in range(len(head)):
            emptyRow.append("")

        for obs_unit in obs_units:
            if ('observationLevel' in obs_unit and obs_unit['observationLevel'].lower() == level) or (level == PAR_defaultObsLvl):
                row = copy.deepcopy(emptyRow)
                for obs_unit_attribute in obs_unit.keys():
                    if obs_unit_attribute == "observationLevels" and obs_unit['observationLevels']:
                        for obslvls in obs_unit['observationLevels'].split(","):
                            if len(obslvl.split(":")) == 2:
                                a, b = obslvls.split(":")
                                row[head.index(
                                    "observationLevels[{}]".format(a))] = b
                            if len(obslvl.split(":")) == 1:
                                row[head.index(
                                    "observationLevels[{}]".format(obslvl))] = obslvl
                    if obs_unit_attribute in obs_unit_header:
                        if obs_unit[obs_unit_attribute]: 
                            outp = []
                            if obs_unit_attribute == "observationUnitXref":
                                # NOTE: INRA specific
                                for item in obs_unit[obs_unit_attribute]:
                                    if item["id"]:
                                        outp.append("{!s}:{!r}".format(
                                            item["source"], item["id"]))
                                row[head.index("observationUnitXref")
                                    ] = ';'.join(outp)
                            else:
                                row[head.index(obs_unit_attribute)
                                    ] = obs_unit[obs_unit_attribute]
                            if obs_unit_attribute == "germplasmDbId":
                                row[head.index(
                                    "accessionNumber")] = germplasminfo[obs_unit[obs_unit_attribute]][0]
                        else:
                            row[head.index(obs_unit_attribute)] = PAR_NAinData

                rowbuffer = copy.deepcopy(row)
                rowbuffer_flat = copy.deepcopy(row)

                timestamps ={}
                for measurement in obs_unit['observations']:
                    if FLATTEN_boolean and att_test(measurement, 'observationTimeStamp'):
                        if measurement['observationTimeStamp'] not in timestamps:
                            timestamps[measurement['observationTimeStamp']] = copy.deepcopy(rowbuffer)
                        for obs_attribute in obs_header:
                            if obs_attribute in measurement and measurement[obs_attribute]:
                                timestamps[measurement['observationTimeStamp']][head.index(obs_attribute)
                                    ] = measurement[obs_attribute]
                            else:
                                timestamps[measurement['observationTimeStamp']][head.index(obs_attribute)
                                    ] = PAR_NAinData
                                # DEBUG self.logger.info(obs_attribute + " does not exist in observation in observationUnit " + obs_unit['observationUnitDbId'])
                        if re.sub('[\s]+', '_', att_test(measurement, 'observationVariableName', "NA variable")) in head:
                            timestamps[measurement['observationTimeStamp']][head.index(re.sub('[\s]+', '_', measurement["observationVariableName"]))] = str(
                                measurement["value"])
                    
                    # Get data from observation
                    for obs_attribute in obs_header:
                        if obs_attribute in measurement and measurement[obs_attribute]:
                            row[head.index(obs_attribute)
                                ] = measurement[obs_attribute]
                        else:
                            row[head.index(obs_attribute)
                                ] = PAR_NAinData
                            # DEBUG self.logger.info(obs_attribute + " does not exist in observation in observationUnit " + obs_unit['observationUnitDbId'])
                    if re.sub('[\s]+', '_', att_test(measurement, 'observationVariableName', "NA variable")) in head:
                        row[head.index(re.sub('[\s]+', '_', measurement["observationVariableName"]))] = str(
                            measurement["value"])
                        data_records.append('\t'.join(row))
                        row = copy.deepcopy(rowbuffer)
                    #else:
                        # DEBUG self.logger.info(measurement["observationVariableName"] + " does not exist in observationVariable list ")
                if timestamps:
                    for lines in timestamps.values():
                        data_records_flat.append('\t'.join(lines))

        return data_records, data_records_flat
