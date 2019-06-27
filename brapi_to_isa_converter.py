from isatools.model import Investigation, OntologyAnnotation, OntologySource, Assay, Study, Characteristic, Source, \
    Sample, Comment, Person

from pycountry_convert import country_alpha3_to_country_alpha2 as a3a2
import copy
from collections import defaultdict
from brapi_client import BrapiClient

def att_test(dictionary, attribute):
    if attribute in dictionary and dictionary[attribute]:
        return str(dictionary[attribute])
    else:
        return ""

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


    def get_obs_levels(self, brapi_study_id, OBSERVATIONUNITLIST):
        # because not every obs level has the same variables, and this is not yet supported by brapi to filter on /
        # every observation will be checked for its variables and be linked to the obeservation level
        obs_level_in_study = defaultdict(set)
        obs_levels = defaultdict(set)
        for ou in OBSERVATIONUNITLIST:
            for obs in ou['observations']:
                if ou['observationLevel']:
                    obs_level_in_study[ou['observationLevel']].add(
                        obs['observationVariableName'])
                    if 'observationLevels' in ou.keys() and ou['observationLevels']:
                        for obslvl in ou['observationLevels'].split(","):
                            a, b = obslvl.split(":")
                            obs_levels[ou['observationLevel']].add(a)
                else:
                    obs_level_in_study['study'].add(
                        obs['observationVariableName'])

        self.logger.info("Observation Levels in study: " +
                         ",".join(obs_level_in_study.keys()))
        return obs_level_in_study, obs_levels

    def create_germplasm_chars(self, germplasm):
        """" Given a BRAPI Germplasm ID, retrieve the list of all attributes from BRAPI and returns a list of ISA
        characteristics using MIAPPE tags for compliance + X-check against ISAconfiguration"""
        # TODO: switch BRAPI tags to MIAPPE Tags

        returned_characteristics = []

        germplasm_id = germplasm['germplasmDbId']
        all_germplasm_attributes = self._brapi_client.get_germplasm(
            germplasm_id)

        if 'taxonId' in all_germplasm_attributes and all_germplasm_attributes['taxonId']:
            c = self.create_isa_characteristic(
                        'Organism', str(all_germplasm_attributes['taxonId']))
            returned_characteristics.append(c)
        else:
            if all_germplasm_attributes['genus'] or all_germplasm_attributes['species']:
                taxonId = self._brapi_client.get_taxonId(all_germplasm_attributes['genus'],all_germplasm_attributes['species'])
                if taxonId:
                    c = self.create_isa_characteristic(
                        'Organism', 'NCBI:'+ str(taxonId))
                    
                else:
                    if 'commonCropName' in all_germplasm_attributes and all_germplasm_attributes['commonCropName']:
                        c = self.create_isa_characteristic('Organism', all_germplasm_attributes['commonCropName'])
                    else:
                        c = self.create_isa_characteristic('Organism', "")

            else:
                if 'commonCropName' in all_germplasm_attributes and all_germplasm_attributes['commonCropName']:
                    c = self.create_isa_characteristic('Organism', all_germplasm_attributes['commonCropName'])
                else:
                    c = self.create_isa_characteristic('Organism', "")
            returned_characteristics.append(c)
        
        mapping_dictionnary = {
            "genus": "Genus",
            "species": "Species",
            "subtaxa": "Infraspecific Name",
            "accessionNumber": "Material Source ID",
            "germplasmPUI": "Material Source DOI",
        }


        for key in mapping_dictionnary:
            if key in all_germplasm_attributes and all_germplasm_attributes[key]:
                c = self.create_isa_characteristic(
                        mapping_dictionnary[key], str(all_germplasm_attributes[key]))
            else:
                c = self.create_isa_characteristic(
                    mapping_dictionnary[key], "")
            
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
            this_study.title = ""

        this_study.description = att_test(brapi_study, 'studyDescription')
        this_study.comments.append(Comment(name="Study Start Date", value=att_test(brapi_study, 'startDate')))
        this_study.comments.append(Comment(name="Study End Date", value=att_test(brapi_study, 'endDate')))
        this_study.comments.append(Comment(name="Study Experimental Site", value=att_test(brapi_study['location'], 'name')))
        study_design = att_test(brapi_study, 'studyType')
        oa_st_design = OntologyAnnotation(term=study_design)
        this_study.design_descriptors = [oa_st_design]
        this_study.comments.append(Comment(name="Trait Definition File", value="t_" + str(brapi_study_id) + ".txt"))
        
        # Adding Location information 
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
                Comment(name="Study Country", value=""))

        this_study.comments.append(Comment(name="Study Latitude", value=att_test(brapi_study['location'], 'latitude')))
        this_study.comments.append(Comment(name="Study Longitude", value=att_test(brapi_study['location'], 'longitude')))
        this_study.comments.append(Comment(name="Study Altitude",value=att_test(brapi_study['location'], 'altitude')))

        # Adding Contacts information
        if 'contacts' in brapi_study:
            for brapicontact in brapi_study['contacts']:
                #NOTE: brapi has just name attribute -> no separate first/last name
                ContactName = brapicontact['name'].split(' ')
                contact = Person(first_name=ContactName[0], last_name=ContactName[1],
                affiliation=att_test(brapicontact, 'institutionName'), email=att_test(brapicontact, 'email'))
                this_study.contacts.append(contact)

        # Adding dataLinks inforamtion
        if 'dataLinks' in brapi_study:
            for brapidata in brapi_study['dataLinks']:
                this_study.comments.append(Comment(name="Study Data File Link",value=brapidata['url']))
                this_study.comments.append(Comment(name="Study Data File Description",value=brapidata['type']))
                this_study.comments.append(Comment(name="Study Data File Version",value="NA in BrAPI"))

        # Declaring as many ISA Assay Types as there are BRAPI Observation Levels
        ###########################################################################
        for level in obs_levels_in_study:

            oref_mt = OntologySource(
                name="OBI", description="Ontology for Biomedical Investigation")
            oa_mt = OntologyAnnotation(
                term="phenotyping", term_accession="", term_source=oref_mt)
            oref_tt = OntologySource(
                name="OBI", description="Ontology for Biomedical Investigation")
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
            "Trait": [],
            "Method": [],
            "Method Description": [],
            "Reference Associated to the Method": [],
            "Scale": []
        }

        # decorating dictionairy
        for i, obs_var in enumerate(obsvars):
            elements['Variable ID'].append(att_test(obs_var, 'observationVariableDbId'))
            elements['Variable Name'].append(att_test(obs_var, 'name'))
            elements['Trait'].append(att_test(obs_var['trait'], 'name'))
            
            if att_test(obs_var['method'], 'name'):
                elements['Method'].append(att_test(obs_var['method'], 'name'))
            else:
                elements['Method'].append(att_test(obs_var, 'name'))
            
            if att_test(obs_var['method'], 'description'):
                elements['Method Description'].append(att_test(obs_var['method'], 'description'))
            else:
                elements['Method Description'].append(att_test(obs_var['trait'], 'description'))
            
            elements['Reference Associated to the Method'].append(att_test(obs_var['method'], 'reference'))
            elements['Scale'].append(att_test(obs_var['scale'], 'name'))

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

    def create_isa_obs_data_from_obsvars(self, obs_units, obs_variables, level, germplasminfo, obs_levels):
        data_records = []
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

        emptyRow = []  # Empty row that is later filled in with values -> fixed row size
        for i in range(len(head)):
            emptyRow.append("")

        for obs_unit in obs_units:
            if obs_unit['observationLevel'] == level:
                row = copy.deepcopy(emptyRow)
                # Get data from observationUnit
                for obs_unit_attribute in obs_unit.keys():
                    if obs_unit_attribute == "observationLevels" and obs_unit['observationLevels']:
                        # NOTE: INRA specific
                        for obslvls in obs_unit['observationLevels'].split(","):
                            a, b = obslvls.split(":")
                            row[head.index(
                                "observationLevels[{}]".format(a))] = b
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
                            row[head.index(obs_unit_attribute)] = "NA"

                rowbuffer = copy.deepcopy(row)

                for measurement in obs_unit['observations']:
                    # Get data from observation
                    for obs_attribute in obs_header:
                        if obs_attribute in measurement and measurement[obs_attribute]:
                            row[head.index(obs_attribute)
                                ] = measurement[obs_attribute]
                        else:
                            row[head.index(obs_attribute)
                                ] = "NA"
                            # DEBUG self.logger.info(obs_attribute + " does not exist in observation in observationUnit " + obs_unit['observationUnitDbId'])
                    if measurement["observationVariableName"] in head:
                        row[head.index(measurement["observationVariableName"])] = str(
                            measurement["value"])
                        data_records.append('\t'.join(row))
                        row = copy.deepcopy(rowbuffer)
                    #else:
                        # DEBUG self.logger.info(measurement["observationVariableName"] + " does not exist in observationVariable list ")

        return data_records
