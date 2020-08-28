import time
import logging
import re
import os
import pandas as pd
import numpy as np
from progressbar import ETA, Bar, ProgressBar, SimpleProgress


from isatools.model import *
from isatools import logging as isa_logging
from isatools.io import isatab_configurator

logger = logging.getLogger("isadumper")
logger.setLevel(logging.INFO)

# REGEXES
_RX_I_FILE_NAME = re.compile(r'i_(.*?)\.txt')
_RX_DATA = re.compile(r'data\[(.*?)\]')
_RX_COMMENT = re.compile(r'Comment\[(.*?)\]')
_RX_DOI = re.compile(r'(10[.][0-9]{4,}(?:[.][0-9]+)*/(?:(?![%"#? ])\\S)+)')
_RX_PMID = re.compile(r'[0-9]{8}')
_RX_PMCID = re.compile(r'PMC[0-9]{8}')
_RX_CHARACTERISTICS = re.compile(r'Characteristics\[(.*?)\]')
_RX_PARAMETER_VALUE = re.compile(r'Parameter Value\[(.*?)\]')
_RX_FACTOR_VALUE = re.compile(r'Factor Value\[(.*?)\]')
_RX_INDEXED_COL = re.compile(r'(.*?)\.\d+')

# column labels
_LABELS_MATERIAL_NODES = ['Source Name', 'Sample Name', 'Extract Name',
                          'Labeled Extract Name']
_LABELS_DATA_NODES = ['Raw Data File', 'Raw Spectral Data File',
                      'Derived Spectral Data File', 'Derived Array Data File',
                      'Array Data File', 'Protein Assignment File',
                      'Peptide Assignment File',
                      'Post Translational Modification Assignment File',
                      'Acquisition Parameter Data File',
                      'Free Induction Decay Data File',
                      'Derived Array Data Matrix File', 'Image File',
                      'Derived Data File', 'Metabolite Assignment File']
_LABELS_ASSAY_NODES = ['Assay Name', 'MS Assay Name',
                       'Hybridization Assay Name', 'Scan Name',
                       'Data Transformation Name', 'Normalization Name']


# class ISADumper():
#
#     def __init__(self, endpoint: str, logger: logging.Logger):
#         self.logger = logger
#
#     def dump(investigation):
#         logger.info("Dumping to file")
#         return None

def dump(isa_obj, output_path, i_file_name='i_investigation.txt',
         skip_dump_tables=False, write_factor_values_in_assay_table=False):
    """Serializes ISA objects to ISA-Tab

    :param isa_obj: An ISA Investigation object
    :param output_path: Path to write the ISA-Tab files to
    :param i_file_name: Overrides the default name for the investigation file
    :param skip_dump_tables: Boolean flag on whether or not to write the
    study sample table files and assay table files
    :param write_factor_values_in_assay_table: Boolean flag indicating whether
    or not to write Factor Values in the assay table files
    :return: None
    """

    def build_comments(some_isa_study_object, some_associated_data_frame):
        """Build comments if multiple comments
        :param some_isa_study_object: Any of the Commentable ISA objects
        :param some_associated_data_frame: the data frames associated to the object (if implemented that ways)
        :return: the 2 input parameters augmented with the relevant information
        """
        if some_isa_study_object.comments is not None:
            for this_comment in sorted(some_isa_study_object.comments, key=lambda x: x.name):
                field = "Comment[" + this_comment.name + "]"
                some_associated_data_frame[field] = this_comment.value
        return some_isa_study_object, some_associated_data_frame

    def _build_roles_str(roles):
        """Build roles strings if multiple roles

        :param roles: A list of OntologyAnnotation objects describing the roles
        :return: Lists of strings corresponding to the list of role names,
        accession numbers and term source references.
        """
        log.debug('building roles from: %s', roles)
        if roles is None:
            roles = list()
        roles_names = ''
        roles_accession_numbers = ''
        roles_source_refs = ''
        for role in roles:
            roles_names += (role.term if role.term else '') + ';'
            roles_accession_numbers += \
                (role.term_accession if role.term_accession else '') + ';'
            roles_source_refs += \
                (role.term_source.name if role.term_source else '') + ';'
        if len(roles) > 0:
            roles_names = roles_names[:-1]
            roles_accession_numbers = roles_accession_numbers[:-1]
            roles_source_refs = roles_source_refs[:-1]
        log.debug('role_names: %s', roles)
        log.debug('roles_accession_numbers: %s', roles)
        log.debug('roles_source_refs: %s', roles)
        return roles_names, roles_accession_numbers, roles_source_refs

    def _build_ontology_reference_section(ontologies=list()):
        """Build ontology reference section DataFrame

        :param prefix: Section prefix - ''
        :param ontologies: List of Ontology objects describing the section's
        Ontology Resource
        :return: DataFrame corresponding to the ONTOLOGY REFERENCE section
        """
        log.debug('building ontology resource reference from: %s', ontologies)
        ontology_source_references_df_cols = ['Term Source Name',
                                              'Term Source File',
                                              'Term Source Version',
                                              'Term Source Description']

        seen_comments = {}
        # step1: going over each object and pulling associated comments to build a full list of those
        for ontology in ontologies:
            for comment in ontology.comments:
                if comment.name in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            ontology_source_references_df_cols.append('Comment[' + comment_name + ']')

        ontology_source_references_df = pd.DataFrame(columns=tuple(ontology_source_references_df_cols))

        for i, ontology in enumerate(ontologies):
            log.debug('%s iteration, item=%s', i, ontology)
            ontology_source_references_df_row = [
                ontology.name,
                ontology.file,
                ontology.version,
                ontology.description
            ]

            # for j, _ in enumerate(max_comment):
            #     log.debug('%s iteration, item=%s', j, _)
            #     try:
            #         if 'Comment[' + ontology.comments[j].name + ']' in ontology_source_references_df_cols:
            #             ontology_source_references_df_row.append(ontology.comments[j].value)
            #         else:
            #             ontology_source_references_df_row.append('')
            #     except IndexError:
            #         ontology_source_references_df_row.append('')
            common_names = []
            for comment in ontology.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in ontology.comments:
                        if element.name == key:
                            ontology_source_references_df_row.append(element.value)

                else:
                    ontology_source_references_df_row.append("")

            log.debug('row=%s', ontology_source_references_df_row)
            ontology_source_references_df.loc[i] = ontology_source_references_df_row

        return ontology_source_references_df.set_index('Term Source Name').T

    def _build_contacts_section_df(prefix='Investigation', contacts=list()):
        """Build contacts section DataFrame

        :param prefix: Section prefix - Investigation or Study
        :param contacts: List of Person objects describing the section's
        contacts
        :return: DataFrame corresponding to the CONTACTS section
        """
        log.debug('building contacts from: %s', contacts)
        contacts_df_cols = [prefix + ' Person Last Name',
                            prefix + ' Person First Name',
                            prefix + ' Person Mid Initials',
                            prefix + ' Person Email',
                            prefix + ' Person Phone',
                            prefix + ' Person Fax',
                            prefix + ' Person Address',
                            prefix + ' Person Affiliation',
                            prefix + ' Person Roles',
                            prefix + ' Person Roles Term Accession Number',
                            prefix + ' Person Roles Term Source REF']

        seen_comments = {}
        # step1: going over each object and pulling associated comments to build a full list of those
        for contact in contacts:
            for comment in contact.comments:
                if comment.name in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            contacts_df_cols.append('Comment[' + comment_name + ']')

        contacts_df = pd.DataFrame(columns=tuple(contacts_df_cols))

        for i, contact in enumerate(contacts):
            log.debug('%s iteration, item=%s', i, contact)
            roles_names, roles_accession_numbers, roles_source_refs = \
                _build_roles_str(contact.roles)
            contacts_df_row = [
                contact.last_name,
                contact.first_name,
                contact.mid_initials,
                contact.email,
                contact.phone,
                contact.fax,
                contact.address,
                contact.affiliation,
                roles_names,
                roles_accession_numbers,
                roles_source_refs
            ]
            # for j, _ in enumerate(max_comment.comments):
            #     log.debug('%s iteration, item=%s', j, _)
            #     try:
            #         contacts_df_row.append(contact.comments[j].value)
            #     except IndexError:
            #         contacts_df_row.append('')
            common_names = []
            for comment in contact.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in contact.comments:
                        if element.name == key:
                            contacts_df_row.append(element.value)

                else:
                    contacts_df_row.append("")

            log.debug('row=%s', contacts_df_row)
            contacts_df.loc[i] = contacts_df_row
        return contacts_df.set_index(prefix + ' Person Last Name').T

    def _build_publications_section_df(prefix='Investigation', publications=list()):
        """Build contacts section DataFrame

        :param prefix: Section prefix - Investigation or Study
        :param publications: List of Publications objects describing the
        section's publications
        :return: DataFrame corresponding to the PUBLICATIONS section
        """
        log.debug('building contacts from: %s', publications)
        publications_df_cols = [
            prefix + ' PubMed ID',
            prefix + ' Publication DOI',
            prefix + ' Publication Author List',
            prefix + ' Publication Title',
            prefix + ' Publication Status',
            prefix + ' Publication Status Term Accession Number',
            prefix + ' Publication Status Term Source REF']

        seen_comments = {}
        # step1: going over each object and pulling associated comments to build a full list of those
        for publication in publications:
            for comment in publication.comments:
                if comment.name in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            publications_df_cols.append('Comment[' + comment_name + ']')

        this_publications_df = pd.DataFrame(columns=tuple(publications_df_cols))

        for i, publication in enumerate(publications):
            log.debug('%s iteration, item=%s', i, publication)
            if publication.status is not None:
                status_term = publication.status.term
                status_term_accession = publication.status.term_accession
                if publication.status.term_source is not None:
                    status_term_source_name = \
                        publication.status.term_source.name
                else:
                    status_term_source_name = ''
            else:
                status_term = ''
                status_term_accession = ''
                status_term_source_name = ''
            publications_df_row = [
                publication.pubmed_id,
                publication.doi,
                publication.author_list,
                publication.title,
                status_term,
                status_term_accession,
                status_term_source_name,
            ]

            # for j, _ in enumerate(max_comment):
            #     log.debug('%s iteration, item=%s', j, _)
            #     try:
            #         if 'Comment[' + publication.comments[j].name + ']' in publications_df_cols:
            #             publications_df_row.append(publication.comments[j].value)
            #         else:
            #             publications_df_row.append('')
            #     except IndexError:
            #         publications_df_row.append('')
            # here, given an object, we create a list comments fields  associated to it

            common_names = []
            for comment in publication.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in publication.comments:
                        if element.name == key:
                            publications_df_row.append(element.value)

                else:
                    publications_df_row.append("")

            log.debug('row=%s', publications_df_row)
            this_publications_df.loc[i] = publications_df_row

        return this_publications_df.set_index(prefix + ' PubMed ID').T

    def _build_protocols_section_df(protocols=list()):
        """Build Protocol section DataFrame

                :param prefix: Section prefix - Investigation or Study
                :param protocols: List of Publications objects describing the
                section's protocols
                :return: DataFrame corresponding to the PROTOCOLS section
                """
        log.debug('building contacts from: %s', protocols)
        study_protocols_df_cols = [
            'Study Protocol Name',
            'Study Protocol Type',
            'Study Protocol Type Term Accession Number',
            'Study Protocol Type Term Source REF',
            'Study Protocol Description',
            'Study Protocol URI',
            'Study Protocol Version',
            'Study Protocol Parameters Name',
            'Study Protocol Parameters Name Term Accession Number',
            'Study Protocol Parameters Name Term Source REF',
            'Study Protocol Components Name',
            'Study Protocol Components Type',
            'Study Protocol Components Type Term Accession Number',
            'Study Protocol Components Type Term Source REF',
        ]

        seen_comments = {}
        # step1: going over each object and pulling associated comments to build a full list of those
        for protocol in protocols:
            for comment in protocol.comments:
                if comment.name in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            study_protocols_df_cols.append('Comment[' + comment_name + ']')

        this_study_protocols_df = pd.DataFrame(columns=tuple(study_protocols_df_cols))

        protocol_type_term = ''
        protocol_type_term_accession = ''
        protocol_type_term_source_name = ''

        for i, protocol in enumerate(protocols):
            parameters_names = ''
            parameters_accession_numbers = ''
            parameters_source_refs = ''
            for parameter in protocol.parameters:
                parameters_names += parameter.parameter_name.term + ';'
                parameters_accession_numbers \
                    += (parameter.parameter_name.term_accession
                        if parameter.parameter_name.term_accession is not None
                        else '') + ';'
                parameters_source_refs \
                    += (parameter.parameter_name.term_source.name
                        if parameter.parameter_name.term_source else '') + ';'
            if len(protocol.parameters) > 0:
                parameters_names = parameters_names[:-1]
                parameters_accession_numbers = \
                    parameters_accession_numbers[:-1]
                parameters_source_refs = parameters_source_refs[:-1]

            component_names = ''
            component_types = ''
            component_types_accession_numbers = ''
            component_types_source_refs = ''
            for component in protocol.components:
                component_names += component.name + ';'
                component_types += component.component_type.term + ';'
                component_types_accession_numbers += \
                    component.component_type.term_accession + ';'
                component_types_source_refs += \
                    component.component_type.term_source.name \
                        if component.component_type.term_source else '' + ';'
            if len(protocol.components) > 0:
                component_names = component_names[:-1]
                component_types = component_types[:-1]
                component_types_accession_numbers = \
                    component_types_accession_numbers[:-1]
                component_types_source_refs = component_types_source_refs[:-1]

            if protocol.protocol_type is not None:
                protocol_type_term = protocol.protocol_type.term
                protocol_type_term_accession = protocol.protocol_type.term_accession
            if protocol.protocol_type.term_source:
                protocol_type_term_source_name = protocol.protocol_type.term_source.name

            study_protocols_df_row = [
                protocol.name,
                protocol_type_term,
                protocol_type_term_accession,
                protocol_type_term_source_name,
                protocol.description,
                protocol.uri,
                protocol.version,
                parameters_names,
                parameters_accession_numbers,
                parameters_source_refs,
                component_names,
                component_types,
                component_types_accession_numbers,
                component_types_source_refs
            ]

            # here, given an object, we create a list comments fields  associated to it
            common_names = []
            for comment in protocol.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in protocol.comments:
                        if element.name == key:
                            study_protocols_df_row.append(element.value)

                else:
                    study_protocols_df_row.append("")

            log.debug('row=%s', study_protocols_df_row)
            this_study_protocols_df.loc[i] = study_protocols_df_row

        return this_study_protocols_df.set_index('Study Protocol Name').T

    def _build_assays_section_df(assays=list()):
        """Build Factors section DataFrame

                :param assays: List of Study Assay objects describing the
                section's assays
                :return: DataFrame corresponding to the STUDY ASSAY section
                """
        log.debug('building contacts from: %s', assays)
        study_assays_df_cols = [
            'Study Assay File Name',
            'Study Assay Measurement Type',
            'Study Assay Measurement Type Term Accession Number',
            'Study Assay Measurement Type Term Source REF',
            'Study Assay Technology Type',
            'Study Assay Technology Type Term Accession Number',
            'Study Assay Technology Type Term Source REF',
            'Study Assay Technology Platform'
        ]

        seen_comments = {}
        # step1: going over each object and pulling associated comments to build a full list of those
        for assay in assays:
            for comment in assay.comments:
                if comment.name in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            study_assays_df_cols.append('Comment[' + comment_name + ']')

        this_study_assays_df = pd.DataFrame(columns=tuple(study_assays_df_cols))

        for i, assay in enumerate(assays):
            study_assays_df_row = [
                assay.filename,
                assay.measurement_type.term,
                assay.measurement_type.term_accession,
                assay.measurement_type.term_source.name
                if assay.measurement_type.term_source else '',
                assay.technology_type.term,
                assay.technology_type.term_accession,
                assay.technology_type.term_source.name
                if assay.technology_type.term_source else '',
                assay.technology_platform
            ]

            # here, given an object, we create a list comments fields  associated to it
            common_names = []
            for comment in assay.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in assay.comments:
                        if element.name == key:
                            study_assays_df_row.append(element.value)

                else:
                    study_assays_df_row.append("")

            log.debug('row=%s', study_assays_df_row)
            this_study_assays_df.loc[i] = study_assays_df_row

        return this_study_assays_df.set_index('Study Assay File Name').T

    def _build_factors_section_df(factors=list()):
        """Build Factors section DataFrame

                :param factors: List of Study Factor objects describing the
                section's factor
                :return: DataFrame corresponding to the STUDY FACTORS section
                """
        log.debug('building contacts from: %s', factors)
        study_factors_df_cols = ['Study Factor Name',
                                 'Study Factor Type',
                                 'Study Factor Type Term Accession Number',
                                 'Study Factor Type Term Source REF']

        seen_comments = {}
        # step1: going over each object and pulling associated comments to build a full list of those
        for factor in factors:
            for comment in factor.comments:
                if comment.name  in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            study_factors_df_cols.append('Comment[' + comment_name + ']')

        this_study_factors_df = pd.DataFrame(columns=tuple(study_factors_df_cols))

        # step4: for each object, create a record
        for i, factor in enumerate(factors):

            if factor.factor_type is not None:
                factor_type_term = factor.factor_type.term
                factor_type_term_accession = factor.factor_type.term_accession
                if factor.factor_type.term_source is not None:
                    factor_type_term_term_source_name = \
                        factor.factor_type.term_source.name
                else:
                    factor_type_term_term_source_name = ''
            else:
                factor_type_term = ''
                factor_type_term_accession = ''
                factor_type_term_term_source_name = ''


            study_factors_df_row = [
                factor.name,
                factor_type_term,
                factor_type_term_accession,
                factor_type_term_term_source_name
                if factor.factor_type.term_source else ''
            ]

            # here, given an object, we create a list comments fields  associated to it
            common_names = []
            for comment in factor.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in factor.comments:
                        if element.name == key:
                            study_factors_df_row.append(element.value)

                else:
                    study_factors_df_row.append("")

            log.debug('row=%s', study_factors_df_row)
            this_study_factors_df.loc[i] = study_factors_df_row

        return this_study_factors_df.set_index('Study Factor Name').T

    def _build_design_descriptors_section(design_descriptors=list()):

        study_design_descriptors_df_cols = ['Study Design Type',
                                            'Study Design Type Term Accession Number',
                                            'Study Design Type Term Source REF']
        seen_comments = {}

        # step1: going over each object and pulling associated comments to build a full list of those
        for design_descriptor in design_descriptors:
            for comment in design_descriptor.comments:
                if comment.name  in seen_comments.keys():
                    seen_comments[comment.name].append(comment.value)
                else:
                    seen_comments[comment.name] = [comment.value]

        # step2: based on the list of unique Comments, create the relevant ISA headers
        for comment_name in seen_comments.keys():
            study_design_descriptors_df_cols.append('Comment[' + comment_name + ']')

        # step3: build a data frame based on the headers available from step 2
        this_study_design_descriptors_df = pd.DataFrame(columns=tuple(study_design_descriptors_df_cols))

        # step4: for each object, create a record
        for i, design_descriptor in enumerate(design_descriptors):
            study_design_descriptors_df_row = [
                design_descriptor.term,
                design_descriptor.term_accession,
                design_descriptor.term_source.name
                if design_descriptor.term_source else ''
            ]

            # here, given an object, we create a list comments fields  associated to it
            common_names = []
            for comment in design_descriptor.comments:
                common_names.append(comment.name)

            # now check which comments are associated to it out of the full possible range of Comments
            # if a match is found, get the value and add it to the record
            for key in seen_comments.keys():
                if key in common_names:
                    for element in design_descriptor.comments:
                        if element.name == key:
                            study_design_descriptors_df_row.append(element.value)

                else:
                    study_design_descriptors_df_row.append("")

            log.debug('row=%s', study_design_descriptors_df_row)
            this_study_design_descriptors_df.loc[i] = study_design_descriptors_df_row

        return this_study_design_descriptors_df.set_index('Study Design Type').T

    if not _RX_I_FILE_NAME.match(i_file_name):
        log.debug('investigation filename=', i_file_name)
        raise NameError('Investigation file must match pattern i_*.txt, got {}'
                        .format(i_file_name))

    if os.path.exists(output_path):
        fp = open(os.path.join(
            output_path, i_file_name), 'w', encoding='utf-8')
    else:
        log.debug('output_path=', i_file_name)
        raise FileNotFoundError("Can't find " + output_path)

    if not isinstance(isa_obj, Investigation):
        log.debug('object type=', type(isa_obj))
        raise NotImplementedError("Can only dump an Investigation object")

    # Process Investigation object first to write the investigation file
    investigation = isa_obj

    # Write ONTOLOGY SOURCE REFERENCE section
    ontology_source_references_df =_build_ontology_reference_section(ontologies=investigation.ontology_source_references)
    fp.write('ONTOLOGY SOURCE REFERENCE\n')
    #  Need to set index_label as top left cell
    ontology_source_references_df.to_csv(
        path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
        index_label='Term Source Name')

    #  Write INVESTIGATION section
    inv_df_cols = ['Investigation Identifier',
                   'Investigation Title',
                   'Investigation Description',
                   'Investigation Submission Date',
                   'Investigation Public Release Date']
    for comment in sorted(investigation.comments, key=lambda x: x.name):
        inv_df_cols.append('Comment[' + comment.name + ']')
    investigation_df = pd.DataFrame(columns=tuple(inv_df_cols))
    inv_df_rows = [
        investigation.identifier,
        investigation.title,
        investigation.description,
        investigation.submission_date,
        investigation.public_release_date
    ]
    for comment in sorted(investigation.comments, key=lambda x: x.name):
        inv_df_rows.append(comment.value)
    investigation_df.loc[0] = inv_df_rows
    investigation_df = investigation_df.set_index('Investigation Identifier').T
    fp.write('INVESTIGATION\n')
    investigation_df.to_csv(
        path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
        index_label='Investigation Identifier')

    # Write INVESTIGATION PUBLICATIONS section
    investigation_publications_df = _build_publications_section_df(prefix='Investigation',
                                                                   publications=investigation.publications)
    fp.write('INVESTIGATION PUBLICATIONS\n')
    investigation_publications_df.to_csv(
        path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
        index_label='Investigation PubMed ID')

    # Write INVESTIGATION CONTACTS section
    investigation_contacts_df = _build_contacts_section_df(
        contacts=investigation.contacts)
    fp.write('INVESTIGATION CONTACTS\n')
    investigation_contacts_df.to_csv(
        path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
        index_label='Investigation Person Last Name')

    # Write STUDY sections
    for study in investigation.studies:
        study_df_cols = ['Study Identifier',
                         'Study Title',
                         'Study Description',
                         'Study Submission Date',
                         'Study Public Release Date',
                         'Study File Name']
        if study.comments is not None:
            for comment in sorted(study.comments, key=lambda x: x.name):
                study_df_cols.append('Comment[' + comment.name + ']')
        study_df = pd.DataFrame(columns=tuple(study_df_cols))
        study_df_row = [
            study.identifier,
            study.title,
            study.description,
            study.submission_date,
            study.public_release_date,
            study.filename
        ]

        if study.comments is not None:
            for comment in sorted(study.comments, key=lambda x: x.name):
                study_df_row.append(comment.value)
        study_df.loc[0] = study_df_row
        study_df = study_df.set_index('Study Identifier').T
        fp.write('STUDY\n')
        study_df.to_csv(path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
                        index_label='Study Identifier')

        # Write STUDY DESIGN DESCRIPTORS section
        # study_design_descriptors_df = pd.DataFrame(
        #     columns=('Study Design Type',
        #              'Study Design Type Term Accession Number',
        #              'Study Design Type Term Source REF'))
        # for i, design_descriptor in enumerate(study.design_descriptors):
        #     study_design_descriptors_df.loc[i] = [
        #         design_descriptor.term,
        #         design_descriptor.term_accession,
        #         design_descriptor.term_source.name
        #         if design_descriptor.term_source else ''
        #     ]
        #
        #     build_comments(design_descriptor, study_design_descriptors_df.loc[i])
        #
        # study_design_descriptors_df = \
        #     study_design_descriptors_df.set_index('Study Design Type').
        study_design_descriptors_df = _build_design_descriptors_section(design_descriptors=study.design_descriptors)
        fp.write('STUDY DESIGN DESCRIPTORS\n')
        study_design_descriptors_df.to_csv(
            path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
            index_label='Study Design Type')

        # Write STUDY PUBLICATIONS section
        study_publications_df = _build_publications_section_df(
            prefix='Study', publications=study.publications)
        fp.write('STUDY PUBLICATIONS\n')
        study_publications_df.to_csv(
            path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
            index_label='Study PubMed ID')

        # Write STUDY FACTORS section
        study_factors_df = _build_factors_section_df(factors=study.factors)
        fp.write('STUDY FACTORS\n')
        study_factors_df.to_csv(
            path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
            index_label='Study Factor Name')

        # Write STUDY ASSAYS section
        # study_assays_df = pd.DataFrame(
        #     columns=(
        #         'Study Assay File Name',
        #         'Study Assay Measurement Type',
        #         'Study Assay Measurement Type Term Accession Number',
        #         'Study Assay Measurement Type Term Source REF',
        #         'Study Assay Technology Type',
        #         'Study Assay Technology Type Term Accession Number',
        #         'Study Assay Technology Type Term Source REF',
        #         'Study Assay Technology Platform',
        #     )
        # )
        # for i, assay in enumerate(study.assays):
        #     study_assays_df.loc[i] = [
        #         assay.filename,
        #         assay.measurement_type.term,
        #         assay.measurement_type.term_accession,
        #         assay.measurement_type.term_source.name
        #         if assay.measurement_type.term_source else '',
        #         assay.technology_type.term,
        #         assay.technology_type.term_accession,
        #         assay.technology_type.term_source.name
        #         if assay.technology_type.term_source else '',
        #         assay.technology_platform
        #     ]
        #     # a call to insert Comments in the Study Assay Type of the Investigation File
        #     build_comments(assay, study_assays_df)
        # study_assays_df = study_assays_df.set_index('Study Assay File Name').T

        study_assays_df= _build_assays_section_df(assays=study.assays)
        fp.write('STUDY ASSAYS\n')
        study_assays_df.to_csv(
            path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
            index_label='Study Assay File Name')

        # Write STUDY PROTOCOLS section
        study_protocols_df = _build_protocols_section_df(protocols=study.protocols)
        fp.write('STUDY PROTOCOLS\n')
        study_protocols_df.to_csv(
            path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
            index_label='Study Protocol Name')

        # Write STUDY CONTACTS section
        study_contacts_df = _build_contacts_section_df(
            prefix='Study', contacts=study.contacts)
        fp.write('STUDY CONTACTS\n')
        study_contacts_df.to_csv(
            path_or_buf=fp, mode='a', sep='\t', encoding='utf-8',
            index_label='Study Person Last Name')

    if skip_dump_tables:
        pass
    else:
        # pass
        t0 = time.perf_counter()
        write_study_table_files(investigation, output_path)
        t1 = time.perf_counter()
        print(t1-t0)
        write_assay_table_files(
            investigation, output_path, write_factor_values_in_assay_table)
        t2 = time.perf_counter()
        print(t2-t1)

    fp.close()
    return investigation

def write_study_table_files(inv_obj, output_dir):
    """Writes out study table files according to pattern defined by

    Source Name, [ Characteristics[], ... ],
    Protocol Ref*: 'sample collection', [ ParameterValue[], ... ],
    Sample Name, [ Characteristics[], ... ]
    [ FactorValue[], ... ]

    which should be equivalent to studySample.xml in default config

    :param inv_obj: An Investigation object containing ISA content
    :param output_dir: A path to a directory to write the ISA-Tab study files
    :return: None
    """
    if not isinstance(inv_obj, Investigation):
        raise NotImplementedError
    for study_obj in inv_obj.studies:
        if study_obj.graph is None:
            break
        protrefcount = 0
        protnames = dict()

        def flatten(l): return [item for sublist in l for item in sublist]
        columns = []

        # start_nodes, end_nodes = _get_start_end_nodes(study_obj.graph)
        paths = _all_end_to_end_paths(
            study_obj.graph,
            [x for x in study_obj.graph.nodes() if isinstance(x, Source)])
        sample_in_path_count = 0
        for node in _longest_path_and_attrs(paths):
            if isinstance(node, Source):
                olabel = "Source Name"
                columns.append(olabel)
                columns += flatten(
                    map(lambda x: get_characteristic_columns(olabel, x),
                        node.characteristics))
                columns += flatten(
                    map(lambda x: get_comment_column(
                        olabel, x), node.comments))
            elif isinstance(node, Process):
                olabel = "Protocol REF.{}".format(node.executes_protocol.name)
                columns.append(olabel)
                if node.executes_protocol.name not in protnames.keys():
                    protnames[node.executes_protocol.name] = protrefcount
                    protrefcount += 1
                columns += flatten(map(lambda x: get_pv_columns(olabel, x),
                                       node.parameter_values))
                if node.date is not None:
                    columns.append(olabel + ".Date")
                if node.performer is not None:
                    columns.append(olabel + ".Performer")
                columns += flatten(
                    map(lambda x: get_comment_column(
                        olabel, x), node.comments))

            elif isinstance(node, Sample):
                olabel = "Sample Name.{}".format(sample_in_path_count)
                columns.append(olabel)
                sample_in_path_count += 1
                columns += flatten(
                    map(lambda x: get_characteristic_columns(olabel, x),
                        node.characteristics))
                columns += flatten(
                    map(lambda x: get_comment_column(
                        olabel, x), node.comments))
                columns += flatten(map(lambda x: get_fv_columns(olabel, x),
                                       node.factor_values))

        omap = get_object_column_map(columns, columns)
        # load into dictionary
        df_dict = dict(map(lambda k: (k, []), flatten(omap)))
        if isa_logging.show_pbars:
            pbar = ProgressBar(min_value=0, max_value=len(paths),
                               widgets=['Writing {} paths: '
                               .format(len(paths)),
                                        SimpleProgress(),
                                        Bar(left=" |", right="| "),
                                        ETA()]).start()
        else:
            def pbar(x): return x
        for path in pbar(paths):
            for k in df_dict.keys():  # add a row per path
                df_dict[k].extend([""])

            sample_in_path_count = 0
            for node in path:
                if isinstance(node, Source):
                    olabel = "Source Name"
                    df_dict[olabel][-1] = node.name
                    for c in node.characteristics:
                        clabel = "{0}.Characteristics[{1}]".format(
                            olabel, c.category.term)
                        write_value_columns(df_dict, clabel, c)
                    for co in node.comments:
                        colabel = "{0}.Comment[{1}]".format(olabel, co.name)
                        df_dict[colabel][-1] = co.value

                elif isinstance(node, Process):
                    olabel = "Protocol REF.{}".format(
                        node.executes_protocol.name)
                    df_dict[olabel][-1] = node.executes_protocol.name
                    for pv in node.parameter_values:
                        pvlabel = "{0}.Parameter Value[{1}]".format(
                            olabel, pv.category.parameter_name.term)
                        write_value_columns(df_dict, pvlabel, pv)
                    if node.date is not None:
                        df_dict[olabel + ".Date"][-1] = node.date
                    if node.performer is not None:
                        df_dict[olabel + ".Performer"][-1] = node.performer
                    for co in node.comments:
                        colabel = "{0}.Comment[{1}]".format(olabel, co.name)
                        df_dict[colabel][-1] = co.value

                elif isinstance(node, Sample):
                    olabel = "Sample Name.{}".format(sample_in_path_count)
                    sample_in_path_count += 1
                    df_dict[olabel][-1] = node.name
                    for c in node.characteristics:
                        clabel = "{0}.Characteristics[{1}]".format(
                            olabel, c.category.term)
                        write_value_columns(df_dict, clabel, c)
                    for co in node.comments:
                        colabel = "{0}.Comment[{1}]".format(olabel, co.name)
                        df_dict[colabel][-1] = co.value
                    for fv in node.factor_values:
                        fvlabel = "{0}.Factor Value[{1}]".format(
                            olabel, fv.factor_name.name)
                        write_value_columns(df_dict, fvlabel, fv)
        if isinstance(pbar, ProgressBar):
            pbar.finish()

        DF = pd.DataFrame(columns=columns)
        DF = DF.from_dict(data=df_dict)
        DF = DF[columns]  # reorder columns
        DF = DF.sort_values(by=DF.columns[0], ascending=True)
        # arbitrary sort on column 0

        for dup_item in set([x for x in columns if columns.count(x) > 1]):
            for j, each in enumerate(
                    [i for i, x in enumerate(columns) if x == dup_item]):
                columns[each] = dup_item + str(j)

        DF.columns = columns  # reset columns after checking for dups

        for i, col in enumerate(columns):
            if "Comment[" in col:
                columns[i] = col[col.rindex(".") + 1:]
            elif col.endswith("Term Source REF"):
                columns[i] = "Term Source REF"
            elif col.endswith("Term Accession Number"):
                columns[i] = "Term Accession Number"
            elif col.endswith("Unit"):
                columns[i] = "Unit"
            elif "Characteristics[" in col:
                if "material type" in col.lower():
                    columns[i] = "Material Type"
                else:
                    columns[i] = col[col.rindex(".") + 1:]
            elif "Factor Value[" in col:
                columns[i] = col[col.rindex(".") + 1:]
            elif "Parameter Value[" in col:
                columns[i] = col[col.rindex(".") + 1:]
            elif col.endswith("Date"):
                columns[i] = "Date"
            elif col.endswith("Performer"):
                columns[i] = "Performer"
            elif "Protocol REF" in col:
                columns[i] = "Protocol REF"
            elif col.startswith("Sample Name."):
                columns[i] = "Sample Name"

        log.info("Rendered {} paths".format(len(DF.index)))

        DF_no_dups = DF.drop_duplicates()
        if len(DF.index) > len(DF_no_dups.index):
            log.info("Dropping duplicates...")
            DF = DF_no_dups

        log.info("Writing {} rows".format(len(DF.index)))
        # reset columns, replace nan with empty string, drop empty columns
        DF.columns = columns
        DF = DF.replace('', np.nan)
        DF = DF.dropna(axis=1, how='all')

        with open(os.path.join(output_dir, study_obj.filename), 'w') as out_fp:
            DF.to_csv(
                path_or_buf=out_fp, index=False, sep='\t', encoding='utf-8')

def write_assay_table_files(inv_obj, output_dir, write_factor_values=False):
    """Writes out assay table files according to pattern defined by

    Sample Name,
    Protocol Ref: 'sample collection', [ ParameterValue[], ... ],
    Material Name, [ Characteristics[], ... ]
    [ FactorValue[], ... ]

    :param inv_obj: An Investigation object containing ISA content
    :param output_dir: A path to a directory to write the ISA-Tab assay files
    :param write_factor_values: Flag to indicate whether or not to write out
    the Factor Value columns in the assay tables
    :return: None
    """

    if not isinstance(inv_obj, Investigation):
        raise NotImplementedError
    for study_obj in inv_obj.studies:
        for assay_obj in study_obj.assays:
            if assay_obj.graph is None:
                break
            protrefcount = 0
            protnames = dict()

            def flatten(l): return [item for sublist in l for item in sublist]
            columns = []

            # start_nodes, end_nodes = _get_start_end_nodes(assay_obj.graph)
            paths = _all_end_to_end_paths(
                assay_obj.graph, [x for x in assay_obj.graph.nodes()
                                  if isinstance(x, Sample)])
            if len(paths) == 0:
                log.info("No paths found, skipping writing assay file")
                continue
            if _longest_path_and_attrs(paths) is None:
                raise IOError(
                    "Could not find any valid end-to-end paths in assay graph")
            for node in _longest_path_and_attrs(paths):
                if isinstance(node, Sample):
                    olabel = "Sample Name"
                    columns.append(olabel)
                    columns += flatten(
                        map(lambda x: get_comment_column(olabel, x),
                            node.comments))
                    if write_factor_values:
                        columns += flatten(
                            map(lambda x: get_fv_columns(olabel, x),
                                node.factor_values))

                elif isinstance(node, Process):
                    olabel = "Protocol REF.{}".format(
                        node.executes_protocol.name)
                    columns.append(olabel)
                    if node.executes_protocol.name not in protnames.keys():
                        protnames[node.executes_protocol.name] = protrefcount
                        protrefcount += 1
                    columns += flatten(map(lambda x: get_pv_columns(olabel, x),
                                           node.parameter_values))
                    oname_label = None
                    if node.executes_protocol.protocol_type:
                        if node.executes_protocol.protocol_type.term in ["nucleic acid sequencing", "phenotyping"]:
                            oname_label = "Assay Name"
                        elif node.executes_protocol.protocol_type.term \
                                == "data collection":
                            oname_label = "Scan Name"
                        elif node.executes_protocol.protocol_type.term \
                                == "mass spectrometry":
                            oname_label = "MS Assay Name"
                        elif node.executes_protocol.protocol_type.term \
                                == "data transformation":
                            oname_label = "Data Transformation Name"
                        elif node.executes_protocol.protocol_type.term \
                                == "sequence analysis data transformation":
                            oname_label = "Normalization Name"
                        elif node.executes_protocol.protocol_type.term \
                                == "normalization":
                            oname_label = "Normalization Name"
                        if node.executes_protocol.protocol_type.term \
                                == "unknown protocol":
                            oname_label = "Unknown Protocol Name"
                        if oname_label is not None:
                            columns.append(oname_label)
                        elif node.executes_protocol.protocol_type.term \
                                == "nucleic acid hybridization":
                            columns.extend(
                                ["Hybridization Assay Name",
                                 "Array Design REF"])
                    if node.date is not None:
                        columns.append(olabel + ".Date")
                    if node.performer is not None:
                        columns.append(olabel + ".Performer")
                    columns += flatten(
                        map(lambda x: get_comment_column(olabel, x),
                            node.comments))
                    for output in [x for x in node.outputs if
                                   isinstance(x, DataFile)]:
                        columns.append(output.label)
                        columns += flatten(
                            map(lambda x: get_comment_column(output.label, x),
                                output.comments))

                elif isinstance(node, Material):
                    olabel = node.type
                    columns.append(olabel)
                    columns += flatten(
                        map(lambda x: get_characteristic_columns(olabel, x),
                            node.characteristics))
                    columns += flatten(
                        map(lambda x: get_comment_column(olabel, x),
                            node.comments))

                elif isinstance(node, DataFile):
                    pass  # handled in process

            omap = get_object_column_map(columns, columns)

            # load into dictionary
            df_dict = dict(map(lambda k: (k, []), flatten(omap)))

            if isa_logging.show_pbars:
                pbar = ProgressBar(min_value=0, max_value=len(paths),
                                   widgets=['Writing {} paths: '.format(
                                       len(paths)),
                                       SimpleProgress(),
                                       Bar(left=" |", right="| "),
                                       ETA()]).start()
            else:
                def pbar(x): return x
            for path in pbar(paths):
                for k in df_dict.keys():  # add a row per path
                    df_dict[k].extend([""])

                for node in path:

                    if isinstance(node, Process):
                        olabel = "Protocol REF.{}".format(
                            node.executes_protocol.name)
                        df_dict[olabel][-1] = node.executes_protocol.name
                        oname_label = None
                        if node.executes_protocol.protocol_type:
                            if node.executes_protocol.protocol_type.term == \
                                    "nucleic acid sequencing":
                                oname_label = "Assay Name"
                            elif node.executes_protocol.protocol_type.term == \
                                    "data collection":
                                oname_label = "Scan Name"
                            elif node.executes_protocol.protocol_type.term == \
                                    "mass spectrometry":
                                oname_label = "MS Assay Name"
                            elif node.executes_protocol.protocol_type.term == \
                                    "data transformation":
                                oname_label = "Data Transformation Name"
                            elif node.executes_protocol.protocol_type.term == \
                                    "sequence analysis data transformation":
                                oname_label = "Normalization Name"
                            elif node.executes_protocol.protocol_type.term == \
                                    "normalization":
                                oname_label = "Normalization Name"
                            if node.executes_protocol.protocol_type.term == \
                                    "unknown protocol":
                                oname_label = "Unknown Protocol Name"
                            if oname_label is not None:
                                df_dict[oname_label][-1] = node.name
                            elif node.executes_protocol.protocol_type.term == \
                                    "nucleic acid hybridization":
                                df_dict["Hybridization Assay Name"][-1] = \
                                    node.name
                                df_dict["Array Design REF"][-1] = \
                                    node.array_design_ref
                        if node.date is not None:
                            df_dict[olabel + ".Date"][-1] = node.date
                        if node.performer is not None:
                            df_dict[olabel + ".Performer"][-1] = node.performer
                        for pv in node.parameter_values:
                            pvlabel = "{0}.Parameter Value[{1}]".format(
                                olabel, pv.category.parameter_name.term)
                            write_value_columns(df_dict, pvlabel, pv)
                        for co in node.comments:
                            colabel = "{0}.Comment[{1}]".format(
                                olabel, co.name)
                            df_dict[colabel][-1] = co.value
                        for output in [x for x in node.outputs if
                                       isinstance(x, DataFile)]:
                            olabel = output.label
                            df_dict[olabel][-1] = output.filename
                            for co in output.comments:
                                colabel = "{0}.Comment[{1}]".format(
                                    olabel, co.name)
                                df_dict[colabel][-1] = co.value

                    elif isinstance(node, Sample):
                        olabel = "Sample Name"
                        df_dict[olabel][-1] = node.name
                        for co in node.comments:
                            colabel = "{0}.Comment[{1}]".format(
                                olabel, co.name)
                            df_dict[colabel][-1] = co.value
                        if write_factor_values:
                            for fv in node.factor_values:
                                fvlabel = "{0}.Factor Value[{1}]".format(
                                    olabel, fv.factor_name.name)
                                write_value_columns(df_dict, fvlabel, fv)

                    elif isinstance(node, Material):
                        olabel = node.type
                        df_dict[olabel][-1] = node.name
                        for c in node.characteristics:
                            clabel = "{0}.Characteristics[{1}]".format(
                                olabel, c.category.term)
                            write_value_columns(df_dict, clabel, c)
                        for co in node.comments:
                            colabel = "{0}.Comment[{1}]".format(
                                olabel, co.name)
                            df_dict[colabel][-1] = co.value

                    elif isinstance(node, DataFile):
                        pass  # handled in process

            if isinstance(pbar, ProgressBar):
                pbar.finish()

            DF = pd.DataFrame(columns=columns)
            DF = DF.from_dict(data=df_dict)
            DF = DF[columns]  # reorder columns
            try:
                DF = DF.sort_values(by=DF.columns[0], ascending=True)
            except ValueError as e:
                log.critical('Error thrown: column labels are: {}'.format(DF.columns))
                log.critical('Error thrown: data is: {}'.format(DF))
                raise e
            # arbitrary sort on column 0

            for dup_item in set([x for x in columns if columns.count(x) > 1]):
                for j, each in enumerate(
                        [i for i, x in enumerate(columns) if x == dup_item]):
                    columns[each] = ".".join([dup_item, str(j)])

            DF.columns = columns

            for i, col in enumerate(columns):
                if col.endswith("Term Source REF"):
                    columns[i] = "Term Source REF"
                elif col.endswith("Term Accession Number"):
                    columns[i] = "Term Accession Number"
                elif col.endswith("Unit"):
                    columns[i] = "Unit"
                elif "Characteristics[" in col:
                    if "material type" in col.lower():
                        columns[i] = "Material Type"
                    elif "label" in col.lower():
                        columns[i] = "Label"
                    else:
                        columns[i] = col[col.rindex(".") + 1:]
                elif "Factor Value[" in col:
                    columns[i] = col[col.rindex(".") + 1:]
                elif "Parameter Value[" in col:
                    columns[i] = col[col.rindex(".") + 1:]
                elif col.endswith("Date"):
                    columns[i] = "Date"
                elif col.endswith("Performer"):
                    columns[i] = "Performer"
                elif "Comment[" in col:
                    columns[i] = col[col.rindex(".") + 1:]
                elif "Protocol REF" in col:
                    columns[i] = "Protocol REF"
                elif "." in col:
                    columns[i] = col[:col.rindex(".")]

            log.debug("Rendered {} paths".format(len(DF.index)))
            if len(DF.index) > 1:
                if len(DF.index) > len(DF.drop_duplicates().index):
                    log.debug("Dropping duplicates...")
                    DF = DF.drop_duplicates()

            log.debug("Writing {} rows".format(len(DF.index)))
            # reset columns, replace nan with empty string, drop empty columns
            DF.columns = columns
            DF = DF.replace('', np.nan)
            DF = DF.dropna(axis=1, how='all')

            with open(os.path.join(
                    output_dir, assay_obj.filename), 'w') as out_fp:
                DF.to_csv(path_or_buf=out_fp, index=False, sep='\t',
                          encoding='utf-8')

def _all_end_to_end_paths(G, start_nodes):
    """Find all the end-to-end complete paths using a networkx algorithm that
    uses a modified depth-first search to generate the paths

    :param G: A DiGraph of all the assay graphs from the process sequences
    :param start_nodes: A list of start nodes
    :return: A list of paths from the start nodes
    """
    # we know graphs start with Source or Sample and end with Process
    paths = []
    num_start_nodes = len(start_nodes)
    message = 'Calculating for paths for {} start nodes: '.format(
        num_start_nodes)
    if isinstance(start_nodes[0], Source):
        message = 'Calculating for paths for {} sources: '.format(
            num_start_nodes)
    elif isinstance(start_nodes[0], Sample):
        message = 'Calculating for paths for {} samples: '.format(
            num_start_nodes)
    if isa_logging.show_pbars:
        pbar = ProgressBar(
            min_value=0, max_value=num_start_nodes, widgets=[
                message, SimpleProgress(), Bar(left=" |", right="| "),
                ETA()]).start()
    else:
        def pbar(x): return x
    for start in pbar(start_nodes):
        # Find ends
        if isinstance(start, Source):
            # only look for Sample ends if start is a Source
            for end in [x for x in nx.algorithms.descendants(G, start) if
                        isinstance(x, Sample) and len(G.out_edges(x)) == 0]:
                paths += list(nx.algorithms.all_simple_paths(G, start, end))
        elif isinstance(start, Sample):
            # only look for Process ends if start is a Sample
            for end in [x for x in nx.algorithms.descendants(G, start) if
                        isinstance(x, Process) and x.next_process is None]:
                paths += list(nx.algorithms.all_simple_paths(G, start, end))
    log.info("Found {} paths!".format(len(paths)))
    if len(paths) == 0:
        log.debug([x.name for x in start_nodes])
    return paths

def _longest_path_and_attrs(paths):
    """Function to find the longest paths and attributes to determine the
    most appropriate ISA-Tab header. This is calculated by adding up the length
    of each path with the number of attributes needed to describe each node in
    the graph.

    :param paths: List of end-to-end paths in the graphs
    :return: The longest path and attributes
    """
    longest = (0, None)
    for path in paths:
        length = len(path)
        for n in path:
            if isinstance(n, Source):
                length += len(n.characteristics)
            elif isinstance(n, Sample):
                length += (len(n.characteristics) + len(n.factor_values))
            elif isinstance(n, Material):
                length += (len(n.characteristics))
            elif isinstance(n, Process):
                length += len(
                    [o for o in n.outputs if isinstance(o, DataFile)])
                if n.date is not None:
                    length += 1
                if n.performer is not None:
                    length += 1
                if n.name != '':
                    length += 1
            if n.comments is not None:
                length += len(n.comments)
        if length > longest[0]:
            longest = (length, path)
    return longest[1]

def _all_end_to_end_paths(G, start_nodes):
    """Find all the end-to-end complete paths using a networkx algorithm that
    uses a modified depth-first search to generate the paths

    :param G: A DiGraph of all the assay graphs from the process sequences
    :param start_nodes: A list of start nodes
    :return: A list of paths from the start nodes
    """
    # we know graphs start with Source or Sample and end with Process
    paths = []
    num_start_nodes = len(start_nodes)
    message = 'Calculating for paths for {} start nodes: '.format(
        num_start_nodes)
    if isinstance(start_nodes[0], Source):
        message = 'Calculating for paths for {} sources: '.format(
            num_start_nodes)
    elif isinstance(start_nodes[0], Sample):
        message = 'Calculating for paths for {} samples: '.format(
            num_start_nodes)
    if isa_logging.show_pbars:
        pbar = ProgressBar(
            min_value=0, max_value=num_start_nodes, widgets=[
                message, SimpleProgress(), Bar(left=" |", right="| "),
                ETA()]).start()
    else:
        def pbar(x): return x
    for start in pbar(start_nodes):
        # Find ends
        if isinstance(start, Source):
            # only look for Sample ends if start is a Source
            for end in [x for x in nx.algorithms.descendants(G, start) if
                        isinstance(x, Sample) and len(G.out_edges(x)) == 0]:
                paths += list(nx.algorithms.all_simple_paths(G, start, end))
        elif isinstance(start, Sample):
            # only look for Process ends if start is a Sample
            for end in [x for x in nx.algorithms.descendants(G, start) if
                        isinstance(x, Process) and x.next_process is None]:
                paths += list(nx.algorithms.all_simple_paths(G, start, end))
    log.info("Found {} paths!".format(len(paths)))
    if len(paths) == 0:
        log.debug([x.name for x in start_nodes])
    return paths

def get_characteristic_columns(label, c):
    """Generates Characteristics columns for a given material

    :param label: Header label needed for the material type,
    e.g. "Extract Name"
    :param c: The Characteristic object of interest
    :return: List of column labels
    """
    columns = ["{0}.Characteristics[{1}]".format(label, c.category.term)]
    columns.extend(get_value_columns(columns[0], c))
    return columns

def get_value_columns(label, x):
    """Generates the appropriate columns based on the value of the object.
    For example, if the object's .value value is an OntologyAnnotation,
    the ISA-Tab requires extra columns Term Source REF and
    Term Accession Number

    :param label: Header label needed for the object type, e.g. "Sample Name"
    :param x: The object of interest, e.g. a Sample() object
    :return: List of column labels, e.g. ["Sample Name.Term Source REF",
    "Sample Name.Term Accession Number"]
    """
    if isinstance(x.value, (int, float)) and x.unit:
        if isinstance(x.unit, OntologyAnnotation):
            return map(lambda x: "{0}.{1}".format(label, x),
                       ["Unit", "Unit.Term Source REF",
                        "Unit.Term Accession Number"])
        else:
            return ["{0}.Unit".format(label)]
    elif isinstance(x.value, OntologyAnnotation):
        return map(lambda x: "{0}.{1}".format(label, x),
                   ["Term Source REF", "Term Accession Number"])
    else:
        return []

def get_object_column_map(isatab_header, df_columns):
    """Builds a mapping of headers to objects

    :param isatab_header: The list of ISA-Tab column names
    :param df_columns: The list of columns from the DataFrame
    :return: A list of column groups (also lists) splitting the header
    according to object type
    """
    if set(isatab_header) == set(df_columns):
        object_index = [
            i for i, x in enumerate(
                df_columns) if x in _LABELS_MATERIAL_NODES +
                               _LABELS_DATA_NODES or 'Protocol REF' in x]
    else:
        object_index = [
            i for i, x in enumerate(
                isatab_header) if x in _LABELS_MATERIAL_NODES +
                                  _LABELS_DATA_NODES + ['Protocol REF']]

    # group headers regarding objects delimited by object_index by slicing up
    # the header list
    object_column_map = []
    prev_i = object_index[0]

    for curr_i in object_index:  # collect each object's columns

        if prev_i == curr_i:
            pass  # skip if there's no diff, i.e. first one
        else:
            object_column_map.append(df_columns[prev_i:curr_i])
        prev_i = curr_i

    # finally collect last object's columns
    object_column_map.append(df_columns[prev_i:])
    return object_column_map

def write_value_columns(df_dict, label, x):
    """Adds values to the DataFrame dictionary when building the tables

    :param df_dict: The DataFrame dictionary to insert the relevant values
    :param label: Header label needed for the object
    :param x: Object of interest
    :return: None
    """
    if isinstance(x.value, (int, float)) and x.unit:
        if isinstance(x.unit, OntologyAnnotation):
            df_dict[label][-1] = x.value
            df_dict[label + ".Unit"][-1] = x.unit.term
            df_dict[label + ".Unit.Term Source REF"][-1] = \
                x.unit.term_source.name if x.unit.term_source else ""
            df_dict[label + ".Unit.Term Accession Number"][-1] = \
                x.unit.term_accession
        else:
            df_dict[label][-1] = x.value
            df_dict[label + ".Unit"][-1] = x.unit
    elif isinstance(x.value, OntologyAnnotation):
        df_dict[label][-1] = x.value.term
        df_dict[label + ".Term Source REF"][-1] = \
            x.value.term_source.name if x.value.term_source else ""
        df_dict[label + ".Term Accession Number"][-1] = \
            x.value.term_accession
    else:
        df_dict[label][-1] = x.value
