#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# Common components used by various cbioportal scripts.
# ------------------------------------------------------------------------------


import os
import sys
import csv
import logging.handlers
from collections import OrderedDict
from subprocess import Popen, PIPE, STDOUT
from typing import Dict, Optional
import dsnparse
import pymysql
pymysql.install_as_MySQLdb()

# MySQLdb import should come after the install_as_MySQLdb() line above
import MySQLdb


# ------------------------------------------------------------------------------
# globals

ERROR_FILE = sys.stderr
OUTPUT_FILE = sys.stdout

# global variables to check `source_stable_id` for `genomic_profile_link`
expression_stable_ids = {}
gsva_scores_stable_id = ""
expression_zscores_source_stable_ids = {}
gsva_scores_source_stable_id = ""
gsva_pvalues_source_stable_id = ""
expression_zscores_filename = ""
gsva_scores_filename = ""
gsva_pvalues_filename = ""

IMPORT_STUDY_CLASS = "org.mskcc.cbio.portal.scripts.ImportCancerStudy"
UPDATE_STUDY_STATUS_CLASS = "org.mskcc.cbio.portal.scripts.UpdateCancerStudy"
REMOVE_STUDY_CLASS = "org.mskcc.cbio.portal.scripts.RemoveCancerStudy"
REMOVE_SAMPLES_CLASS = "org.mskcc.cbio.portal.scripts.RemoveSamples"
REMOVE_PATIENTS_CLASS = "org.mskcc.cbio.portal.scripts.RemovePatients"
IMPORT_CANCER_TYPE_CLASS = "org.mskcc.cbio.portal.scripts.ImportTypesOfCancers"
IMPORT_CASE_LIST_CLASS = "org.mskcc.cbio.portal.scripts.ImportSampleList"
ADD_CASE_LIST_CLASS = "org.mskcc.cbio.portal.scripts.AddCaseList"
UPDATE_CASE_LIST_CLASS = "org.mskcc.cbio.portal.scripts.UpdateCaseListsSampleIds"
VERSION_UTIL_CLASS = "org.mskcc.cbio.portal.util.VersionUtil"

PORTAL_PROPERTY_DATABASE_USER = 'db.user'
PORTAL_PROPERTY_DATABASE_PW = 'db.password'
PORTAL_PROPERTY_DATABASE_HOST = 'db.host'
PORTAL_PROPERTY_DATABASE_NAME = 'db.portal_db_name'
PORTAL_PROPERTY_DATABASE_URL = 'db.connection_string'
PORTAL_PROPERTY_DATABASE_USESSL = 'db.use_ssl'
PORTAL_PROPERTY_SPRING_DATABASE_USER = 'spring.datasource.username'
PORTAL_PROPERTY_SPRING_DATABASE_PW = 'spring.datasource.password'
PORTAL_PROPERTY_SPRING_DATABASE_URL = 'spring.datasource.url'
REQUIRED_DATABASE_PROPERTIES = [PORTAL_PROPERTY_SPRING_DATABASE_USER, PORTAL_PROPERTY_SPRING_DATABASE_PW, PORTAL_PROPERTY_SPRING_DATABASE_URL]

# provides a key for data types to metafile specification dict.
class MetaFileTypes(object):
    """how we differentiate between data types."""
    STUDY = 'meta_study'
    CANCER_TYPE = 'meta_cancer_type'
    SAMPLE_ATTRIBUTES = 'meta_clinical_sample'
    PATIENT_ATTRIBUTES = 'meta_clinical_patient'
    CNA_DISCRETE = 'meta_CNA'
    CNA_DISCRETE_LONG = 'meta_CNA_long'
    CNA_LOG2 = 'meta_log2CNA'
    CNA_CONTINUOUS = 'meta_contCNA'
    SEG = 'meta_segment'
    EXPRESSION = 'meta_expression'
    MUTATION = 'meta_mutations_extended'
    MUTATION_UNCALLED = 'meta_mutations_uncalled'
    METHYLATION = 'meta_methylation'
    PROTEIN = 'meta_protein'
    GISTIC_GENES = 'meta_gistic_genes'
    TIMELINE = 'meta_timeline'
    CASE_LIST = 'case_list'
    MUTATION_SIGNIFICANCE = 'meta_mutsig'
    GENE_PANEL_MATRIX = 'meta_gene_panel_matrix'
    GSVA_SCORES = 'meta_gsva_scores'
    GSVA_PVALUES = 'meta_gsva_pvalues'
    GENERIC_ASSAY_CONTINUOUS = 'meta_generic_assay_continuous'
    GENERIC_ASSAY_BINARY = 'meta_generic_assay_binary'
    GENERIC_ASSAY_CATEGORICAL = 'meta_generic_assay_categorical'
    STRUCTURAL_VARIANT = 'meta_structural_variants'
    SAMPLE_RESOURCES = 'meta_resource_sample'
    PATIENT_RESOURCES = 'meta_resource_patient'
    STUDY_RESOURCES = 'meta_resource_study'
    RESOURCES_DEFINITION = 'meta_resource_definition'


# fields allowed in each meta file type, maps to True if required
META_FIELD_MAP = {
    MetaFileTypes.CANCER_TYPE: {
        'genetic_alteration_type': True,
        'datatype': True,
        'data_filename': True
    },
    MetaFileTypes.STUDY: {
        'cancer_study_identifier': True,
        'type_of_cancer': True,
        'name': True,
        'description': True,
        'citation': False,
        'pmid': False,
        'groups': False,
        'add_global_case_list': False,
        'tags_file': False,
        'reference_genome': False
    },
    MetaFileTypes.SAMPLE_ATTRIBUTES: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'data_filename': True
    },
    MetaFileTypes.PATIENT_ATTRIBUTES: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'data_filename': True
    },
    MetaFileTypes.CNA_DISCRETE: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False,
        'pd_annotations_filename': False
    },
    MetaFileTypes.CNA_DISCRETE_LONG: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False,
        'namespaces': False
    },
    MetaFileTypes.CNA_LOG2: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False
    },
    MetaFileTypes.CNA_CONTINUOUS: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False
    },
    MetaFileTypes.SEG: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'reference_genome_id': True,
        'data_filename': True,
        'description': True
    },
    MetaFileTypes.MUTATION: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'normal_samples_list': False,
        'swissprot_identifier': False,
        'gene_panel': False,
        'variant_classification_filter': False,
        'namespaces': False
    },
    MetaFileTypes.MUTATION_UNCALLED: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': False,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'normal_samples_list': False,
        'swissprot_identifier': False,
        'gene_panel': False,
        'variant_classification_filter': False,
        'namespaces': False
    },
    MetaFileTypes.EXPRESSION: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'source_stable_id': False,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False
    },
    MetaFileTypes.METHYLATION: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False
    },
    MetaFileTypes.PROTEIN: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False
    },
    MetaFileTypes.GISTIC_GENES: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'reference_genome_id': True,
        'data_filename': True
    },
    MetaFileTypes.TIMELINE: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'data_filename': True
    },
    MetaFileTypes.CASE_LIST: {
        'cancer_study_identifier': True,
        'stable_id': True,
        'case_list_name': True,
        'case_list_description': True,
        'case_list_ids': True,
        'case_list_category': False # TODO this is used in org.mskcc.cbio.portal.model.AnnotatedPatientSets.getDefaultPatientList(), decide whether to keeep, see #494
    },
    MetaFileTypes.MUTATION_SIGNIFICANCE: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'data_filename': True
    },
    MetaFileTypes.GENE_PANEL_MATRIX: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'data_filename': True
    },
    MetaFileTypes.GSVA_PVALUES: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'source_stable_id': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'geneset_def_version': True
    },
    MetaFileTypes.GSVA_SCORES: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'source_stable_id': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'show_profile_in_analysis_tab': True,
        'geneset_def_version': True
    },
    MetaFileTypes.GENERIC_ASSAY_CONTINUOUS: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'generic_assay_type': True,
        'datatype': True,
        'stable_id': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'show_profile_in_analysis_tab': True,
        'generic_entity_meta_properties': False,
        'pivot_threshold_value': False,
        'value_sort_order': False,
        'patient_level': False
    },
    MetaFileTypes.GENERIC_ASSAY_BINARY: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'generic_assay_type': True,
        'datatype': True,
        'stable_id': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'show_profile_in_analysis_tab': True,
        'generic_entity_meta_properties': False,
        'patient_level': False
    },
    MetaFileTypes.GENERIC_ASSAY_CATEGORICAL: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'generic_assay_type': True,
        'datatype': True,
        'stable_id': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'show_profile_in_analysis_tab': True,
        'generic_entity_meta_properties': False,
        'patient_level': False
    },
    MetaFileTypes.STRUCTURAL_VARIANT: {
        'cancer_study_identifier': True,
        'genetic_alteration_type': True,
        'datatype': True,
        'stable_id': True,
        'show_profile_in_analysis_tab': True,
        'profile_name': True,
        'profile_description': True,
        'data_filename': True,
        'gene_panel': False,
        'namespaces': False
    },
    MetaFileTypes.SAMPLE_RESOURCES: {
        'cancer_study_identifier': True,
        'resource_type': True,
        'data_filename': True
    },
    MetaFileTypes.PATIENT_RESOURCES: {
        'cancer_study_identifier': True,
        'resource_type': True,
        'data_filename': True
    },
    MetaFileTypes.STUDY_RESOURCES: {
        'cancer_study_identifier': True,
        'resource_type': True,
        'data_filename': True
    },
    MetaFileTypes.RESOURCES_DEFINITION: {
        'cancer_study_identifier': True,
        'resource_type': True,
        'data_filename': True
    },
}

# order is important! This is the order in which they should be loaded:
INCREMENTAL_UPLOAD_SUPPORTED_META_TYPES = [
    MetaFileTypes.PATIENT_ATTRIBUTES,
    MetaFileTypes.SAMPLE_ATTRIBUTES,
    MetaFileTypes.MUTATION,
    MetaFileTypes.MUTATION_UNCALLED,
    MetaFileTypes.EXPRESSION,
    MetaFileTypes.CNA_DISCRETE,
    MetaFileTypes.CNA_CONTINUOUS,
    MetaFileTypes.CNA_LOG2,
    MetaFileTypes.METHYLATION,
    MetaFileTypes.PROTEIN,
    MetaFileTypes.GENERIC_ASSAY_CONTINUOUS,
    MetaFileTypes.GENERIC_ASSAY_BINARY,
    MetaFileTypes.GENERIC_ASSAY_CATEGORICAL,
    MetaFileTypes.TIMELINE,
    MetaFileTypes.GENE_PANEL_MATRIX,
    MetaFileTypes.STRUCTURAL_VARIANT,
    MetaFileTypes.SEG,
]

IMPORTER_CLASSNAME_BY_META_TYPE = {
    MetaFileTypes.STUDY: IMPORT_STUDY_CLASS,
    MetaFileTypes.CANCER_TYPE: IMPORT_CANCER_TYPE_CLASS,
    MetaFileTypes.SAMPLE_ATTRIBUTES: "org.mskcc.cbio.portal.scripts.ImportClinicalData",
    MetaFileTypes.PATIENT_ATTRIBUTES: "org.mskcc.cbio.portal.scripts.ImportClinicalData",
    MetaFileTypes.CNA_DISCRETE: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.CNA_DISCRETE_LONG: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.CNA_LOG2: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.CNA_CONTINUOUS: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.SEG: "org.mskcc.cbio.portal.scripts.ImportCopyNumberSegmentData",
    MetaFileTypes.EXPRESSION: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.MUTATION: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.MUTATION_UNCALLED: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.METHYLATION: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.PROTEIN: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.GISTIC_GENES: "org.mskcc.cbio.portal.scripts.ImportGisticData",
    MetaFileTypes.TIMELINE: "org.mskcc.cbio.portal.scripts.ImportTimelineData",
    MetaFileTypes.CASE_LIST: IMPORT_CASE_LIST_CLASS,
    MetaFileTypes.MUTATION_SIGNIFICANCE: "org.mskcc.cbio.portal.scripts.ImportMutSigData",
    MetaFileTypes.GENE_PANEL_MATRIX: "org.mskcc.cbio.portal.scripts.ImportGenePanelProfileMap",
    MetaFileTypes.GSVA_SCORES: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.GSVA_PVALUES: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.GENERIC_ASSAY_CONTINUOUS: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.GENERIC_ASSAY_BINARY: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.GENERIC_ASSAY_CATEGORICAL: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.STRUCTURAL_VARIANT: "org.mskcc.cbio.portal.scripts.ImportProfileData",
    MetaFileTypes.SAMPLE_RESOURCES: "org.mskcc.cbio.portal.scripts.ImportResourceData",
    MetaFileTypes.PATIENT_RESOURCES: "org.mskcc.cbio.portal.scripts.ImportResourceData",
    MetaFileTypes.STUDY_RESOURCES: "org.mskcc.cbio.portal.scripts.ImportResourceData",
    MetaFileTypes.RESOURCES_DEFINITION: "org.mskcc.cbio.portal.scripts.ImportResourceDefinition",
}

IMPORTER_REQUIRES_METADATA = {
    "org.mskcc.cbio.portal.scripts.ImportClinicalData" : True,
    "org.mskcc.cbio.portal.scripts.ImportCopyNumberSegmentData" : True,
    "org.mskcc.cbio.portal.scripts.ImportGisticData" : False,
    "org.mskcc.cbio.portal.scripts.ImportMutSigData" : False,
    "org.mskcc.cbio.portal.scripts.ImportProfileData" : True,
    "org.mskcc.cbio.portal.scripts.ImportTimelineData" : True,
    "org.mskcc.cbio.portal.scripts.ImportGenePanelProfileMap" : False,
    "org.mskcc.cbio.portal.scripts.ImportResourceData" : True,
    "org.mskcc.cbio.portal.scripts.ImportResourceDefinition" : True
}

# ------------------------------------------------------------------------------
# class definitions

class ValidationMessageFormatter(logging.Formatter):

    """Logging formatter with optional fields for data validation messages.

    These fields are:
    filename_ - the path to the file the message is about (if applicable)
    line_number - a line number within the above file (if applicable)
    column_number - a column number within the above file (if applicable)
    cause - the unexpected value found in the input (if applicable)

    If instead a message pertains to multiple values of one of these
    fields (as the result of aggregation by CollapsingLogMessageHandler),
    these will be expected in the field <fieldname>_list.
    """

    def format(self, record, *args, **kwargs):
        """Check consistency of expected fields and format the record."""
        if (
                (
                    hasattr(record, 'line_number') or
                    hasattr(record, 'line_number_list') or
                    hasattr(record, 'column_number') or
                    hasattr(record, 'column_number_list'))
                and not hasattr(record, 'filename_')):
            raise ValueError(
                'Tried to log about a line/column with no filename')
        return super(ValidationMessageFormatter, self).format(record,
                                                              *args,
                                                              **kwargs)

    @staticmethod
    def format_aggregated(record,
                          field_name,
                          single_fmt='%s',
                          multiple_fmt='[%s]',
                          join_string=', ',
                          max_join=3,
                          optional=False):
        """Format a human-readable string for a field or its <field>_list.

        From log records as generated by the flush() method of
        CollapsingLogMessageHandler. If the field was not aggregated, format
        it according to the format string `single_fmt`. If it was, coerce the
        first `max_join` values to strings, concatenate them separated by
        `join_string`, and format the result according to `multiple_fmt`.

        If `max_join` is None, join all values and apply no maximum length.

        If `optional` is True and both the field and its list are absent,
        return an empty string.
        """
        attr_val = getattr(record, field_name, None)
        attr_list = getattr(record, field_name + '_list', None)
        if attr_val is not None:
            attr_indicator = single_fmt % attr_val
        elif attr_list is not None:
            # treat None as 'format all of them, no maximum'
            if max_join is None:
                max_join = len(attr_list)
            string_list = list(str(val) for val in attr_list[:max_join])
            num_skipped = len(attr_list) - len(string_list)
            if num_skipped != 0:
                string_list.append('(%d more)' % num_skipped)
            attr_indicator = multiple_fmt % join_string.join(string_list)
        elif optional:
            attr_indicator = ''
        else:
            raise ValueError(
                "Tried to format an absent non-optional log field: '%s'" %
                field_name)
        return attr_indicator


class LogfileStyleFormatter(ValidationMessageFormatter):

    """Formatter for validation messages in a simple one-per-line format."""

    def __init__(self, study_dir):
        """Initialize a logging Formatter with an appropriate format string."""
        super(LogfileStyleFormatter, self).__init__(
            fmt='%(levelname)s: %(file_indicator)s:'
                '%(line_indicator)s%(column_indicator)s'
                ' %(message)s%(cause_indicator)s')
        self.study_dir = study_dir
        self.previous_filename = None

    def format(self, record):

        """Generate descriptions for optional fields and format the record."""


        if not hasattr(record, 'filename_'):
            record.file_indicator = '-'
        else:
            record.file_indicator = os.path.relpath(record.filename_.strip(),
                                                    self.study_dir)
        record.line_indicator = self.format_aggregated(
            record,
            'line_number',
            ' line %d:',
            ' lines [%s]:',
            optional=True)
        record.column_indicator = self.format_aggregated(
            record,
            'column_number',
            ' column %d:',
            ' columns [%s]:',
            optional=True)
        record.cause_indicator = self.format_aggregated(
            record,
            'cause',
            "; value encountered: '%s'",
            "; values encountered: ['%s']",
            join_string="', '",
            optional=True)

        # format the string based on these fields
        formatted_result = super(LogfileStyleFormatter, self).format(record)

        # prepend an empty line if the filename is different than before
        current_filename = getattr(record, 'filename_', '')
        if (self.previous_filename is not None and
                current_filename != self.previous_filename):
            formatted_result = '\n' + formatted_result
        self.previous_filename = current_filename

        return formatted_result


class CollapsingLogMessageHandler(logging.handlers.MemoryHandler):

    """Logging handler that aggregates repeated log messages into one.

    This collapses validation LogRecords based on the source code line that
    emitted them and their formatted message, and flushes the resulting
    records to another handler.
    """

    # TODO make it collapse messages on emit, instead of keeping it all in RAM
    def flush(self):

        """Aggregate LogRecords by message and send them to the target handler.

        Fields that occur with multiple different values in LogRecords
        emitted from the same line with the same message (and optional
        'filename_' attribute) will be collected in a field named
        <field_name>_list.
        """

        # group buffered LogRecords by their source code line and message
        grouping_dict = OrderedDict()
        for record in self.buffer:
            identifying_tuple = (record.module,
                                 record.lineno,
                                 getattr(record, 'filename_', None),
                                 record.getMessage())
            if identifying_tuple not in grouping_dict:
                grouping_dict[identifying_tuple] = []

            # add a tuple that keeps the relation between the line number,
            # the column number and the cause for the HTML report
            record.__dict__['value'] = (
                getattr(record, 'line_number', None),
                getattr(record, 'column_number', None),
                getattr(record, 'cause', None))

            grouping_dict[identifying_tuple].append(record)
        
        aggregated_buffer = []
        # for each list of same-message records
        for record_list in list(grouping_dict.values()):
            # make a dict to collect the fields for the aggregate record
            aggregated_field_dict = {}
            # for each field found in (the first of) the records
            for field_name in record_list[0].__dict__:
                # collect the values found for this field across the records.
                # Use the keys of an OrderedDict, as OrderedSet is for some
                # reason not to be found in the Python standard library.
                field_values = OrderedDict((record.__dict__[field_name], None)
                                           for record in record_list)
                # if this field has the same value in all records
                if len(field_values) == 1:
                    # use that value in the new dict
                    aggregated_field_dict[field_name] = field_values.popitem()[0]
                else:
                    # set a <field>_list field instead
                    aggregated_field_dict[field_name + '_list'] = \
                        list(field_values.keys())

            # add a new log record with these fields tot the output buffer
            aggregated_buffer.append(
                logging.makeLogRecord(aggregated_field_dict))

        # replace the buffer with the aggregated one and flush
        self.buffer = aggregated_buffer
        super(CollapsingLogMessageHandler, self).flush()

    def shouldFlush(self, record):
        """Collapse and flush every time a debug message is emitted."""
        return (record.levelno == logging.DEBUG or
                super(CollapsingLogMessageHandler, self).shouldFlush(record))


# ------------------------------------------------------------------------------
# sub-routines

def get_meta_file_type(meta_dictionary, logger, filename):
    """
     Returns one of the metatypes found in MetaFileTypes

     NB: a subset of these types (combined with allowed_data_types.txt)
     is also tracked in org.cbioportal.model.GeneticProfile.java. If you add
     things here, please make sure to update there as well if it regards a
     genetic profile data type.
    """
    # The following dictionary is required to define the MetaFileType for all
    # combinations, which are used in validateData to determine which validator
    # should be used. There is some redundancy with allowed_data_types.txt, which
    # also contains genetic alteration types and datatype combinations, but is used
    # to check if the correct stable id is used.
    # GENETIC_ALTERATION_TYPE    DATATYPE    meta
    alt_type_datatype_to_meta = {
        # cancer type
        ("CANCER_TYPE", "CANCER_TYPE"): MetaFileTypes.CANCER_TYPE,
        # clinical and timeline
        ("CLINICAL", "PATIENT_ATTRIBUTES"): MetaFileTypes.PATIENT_ATTRIBUTES,
        ("CLINICAL", "SAMPLE_ATTRIBUTES"): MetaFileTypes.SAMPLE_ATTRIBUTES,
        ("CLINICAL", "TIMELINE"): MetaFileTypes.TIMELINE,
        # rppa and mass spectrometry
        ("PROTEIN_LEVEL", "LOG2-VALUE"): MetaFileTypes.PROTEIN,
        ("PROTEIN_LEVEL", "Z-SCORE"): MetaFileTypes.PROTEIN,
        ("PROTEIN_LEVEL", "CONTINUOUS"): MetaFileTypes.PROTEIN,
        # cna
        ("COPY_NUMBER_ALTERATION", "DISCRETE"): MetaFileTypes.CNA_DISCRETE,
        ("COPY_NUMBER_ALTERATION", "DISCRETE_LONG"): MetaFileTypes.CNA_DISCRETE_LONG,
        ("COPY_NUMBER_ALTERATION", "CONTINUOUS"): MetaFileTypes.CNA_CONTINUOUS,
        ("COPY_NUMBER_ALTERATION", "LOG2-VALUE"): MetaFileTypes.CNA_LOG2,
        ("COPY_NUMBER_ALTERATION", "SEG"): MetaFileTypes.SEG,
        # expression
        ("MRNA_EXPRESSION", "CONTINUOUS"): MetaFileTypes.EXPRESSION,
        ("MRNA_EXPRESSION", "Z-SCORE"): MetaFileTypes.EXPRESSION,
        ("MRNA_EXPRESSION", "DISCRETE"): MetaFileTypes.EXPRESSION,
        # mutations
        ("MUTATION_EXTENDED", "MAF"): MetaFileTypes.MUTATION,
        ("MUTATION_UNCALLED", "MAF"): MetaFileTypes.MUTATION_UNCALLED,
        # others
        ("METHYLATION", "CONTINUOUS"): MetaFileTypes.METHYLATION,
        ("GENE_PANEL_MATRIX", "GENE_PANEL_MATRIX"): MetaFileTypes.GENE_PANEL_MATRIX,
        ("STRUCTURAL_VARIANT", "SV"): MetaFileTypes.STRUCTURAL_VARIANT,
        # cross-sample molecular statistics (for gene selection)
        ("GISTIC_GENES_AMP", "Q-VALUE"): MetaFileTypes.GISTIC_GENES,
        ("GISTIC_GENES_DEL", "Q-VALUE"): MetaFileTypes.GISTIC_GENES,
        ("MUTSIG", "Q-VALUE"): MetaFileTypes.MUTATION_SIGNIFICANCE,
        ("GENESET_SCORE", "GSVA-SCORE"): MetaFileTypes.GSVA_SCORES,
        ("GENESET_SCORE", "P-VALUE"): MetaFileTypes.GSVA_PVALUES,
        ("GENERIC_ASSAY", "LIMIT-VALUE"): MetaFileTypes.GENERIC_ASSAY_CONTINUOUS,
        ("GENERIC_ASSAY", "BINARY"): MetaFileTypes.GENERIC_ASSAY_BINARY,
        ("GENERIC_ASSAY", "CATEGORICAL"): MetaFileTypes.GENERIC_ASSAY_CATEGORICAL
    }
    result = None
    if 'genetic_alteration_type' in meta_dictionary and 'datatype' in meta_dictionary:
        genetic_alteration_type = meta_dictionary['genetic_alteration_type']
        data_type = meta_dictionary['datatype']
        if (genetic_alteration_type, data_type) in alt_type_datatype_to_meta:
            result = alt_type_datatype_to_meta[(genetic_alteration_type, data_type)]
        else:
            if meta_dictionary['datatype'] == 'FUSION':
                logger.error(
                    'The Fusion file format is deprecated. Consider adding the data in Structural Variant format.',
                    extra={'filename_': filename,
                               'cause': ('genetic_alteration_type: %s, '
                                     'datatype: %s' % (
                                         meta_dictionary['genetic_alteration_type'],
                                         meta_dictionary['datatype']))})
            else:
                logger.error(
                    'Could not determine the file type. Please check your meta files for correct configuration.',
                    extra={'filename_': filename,
                               'cause': ('genetic_alteration_type: %s, '
                                     'datatype: %s' % (
                                         meta_dictionary['genetic_alteration_type'],
                                         meta_dictionary['datatype']))})
    elif 'cancer_study_identifier' in meta_dictionary and 'type_of_cancer' in meta_dictionary:
        result = MetaFileTypes.STUDY
    elif 'type_of_cancer' in meta_dictionary:
        result = MetaFileTypes.CANCER_TYPE
    elif 'cancer_study_identifier' in meta_dictionary and 'resource_type' in meta_dictionary:
        if meta_dictionary['resource_type'] == 'PATIENT':
            result = MetaFileTypes.PATIENT_RESOURCES
        elif meta_dictionary['resource_type'] == 'SAMPLE':
            result = MetaFileTypes.SAMPLE_RESOURCES
        elif meta_dictionary['resource_type'] == 'STUDY':
            result = MetaFileTypes.STUDY_RESOURCES
        elif meta_dictionary['resource_type'] == 'DEFINITION':
            result = MetaFileTypes.RESOURCES_DEFINITION
    else:
        logger.error('Could not determine the file type. Did not find expected meta file fields. Please check your meta files for correct configuration.',
                         extra={'filename_': filename})
    return result


def validate_types_and_id(meta_dictionary, logger, filename):
    """Validate a genetic_alteration_type, datatype (and stable_id in some cases) 
    against predefined allowed combinations instead of reading from allowed_data_types.txt.
    """
    result = True

    # Define allowed combinations as a dictionary
    allowed_combinations = {
        ("COPY_NUMBER_ALTERATION", "DISCRETE", "cna"),
        ("COPY_NUMBER_ALTERATION", "DISCRETE_LONG", "cna"),
        ("COPY_NUMBER_ALTERATION", "DISCRETE", "cna_rae"),
        ("COPY_NUMBER_ALTERATION", "DISCRETE", "cna_consensus"),
        ("COPY_NUMBER_ALTERATION", "DISCRETE", "gistic"),
        ("COPY_NUMBER_ALTERATION", "DISCRETE_LONG", "gistic"),
        ("COPY_NUMBER_ALTERATION", "CONTINUOUS", "linear_CNA"),
        ("COPY_NUMBER_ALTERATION", "LOG2-VALUE", "log2CNA"),
        ("MUTATION_EXTENDED", "MAF", "mutations"),
        ("MUTATION_UNCALLED", "MAF", "mutations_uncalled"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna_U133"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_U133_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_U133_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_mrna_median_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_mrna_median_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_median_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "rna_seq_mrna"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "rna_seq_v2_mrna"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_v2_mrna_median_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_v2_mrna_median_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "rna_seq_v2_mrna_median_normals"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_v2_mrna_median_normals_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_v2_mrna_median_all_sample_ref_normal_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mirna"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mirna_median_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_merged_median_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna"),       
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_fpkm_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_fpkm_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_median_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "DISCRETE", "mrna_outliers"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna_seq_fpkm_capture"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_fpkm_capture_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_fpkm_capture_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "rna_seq_mrna_capture"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_mrna_capture_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "rna_seq_mrna_capture_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_fpkm_polya_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_fpkm_polya_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna_seq_fpkm_polya"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna_seq_cpm"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_cpm_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_cpm_Zscores"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna_seq_tpm"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_tpm_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_tpm_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_zbynorm"),
        ("MRNA_EXPRESSION", "CONTINUOUS", "mrna_seq_fpkm"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_all_sample_Zscores"),
        ("MRNA_EXPRESSION", "Z-SCORE", "mrna_seq_read_counts_Zscores"),
        ("METHYLATION", "CONTINUOUS", "methylation_hm27"),
        ("METHYLATION", "CONTINUOUS", "methylation_hm450"),
        ("METHYLATION", "CONTINUOUS", "methylation_epic"),
        ("METHYLATION", "CONTINUOUS", "methylation_promoters_rrbs"),
        ("PROTEIN_LEVEL", "LOG2-VALUE", "rppa"),
        ("PROTEIN_LEVEL", "Z-SCORE", "rppa_Zscores"),
        ("PROTEIN_LEVEL", "CONTINUOUS", "protein_quantification"),
        ("PROTEIN_LEVEL", "Z-SCORE", "protein_quantification_zscores"),
        ("PROTEIN_LEVEL", "LOG2-VALUE", "protein_quantification"),
        ("GENESET_SCORE", "GSVA-SCORE", "gsva_scores"),
        ("GENESET_SCORE", "P-VALUE", "gsva_pvalues"),
        ("GENERIC_ASSAY", "LIMIT-VALUE", "*"),
        ("GENERIC_ASSAY", "BINARY", "*"),
        ("GENERIC_ASSAY", "CATEGORICAL", "*"),
        ("STRUCTURAL_VARIANT", "SV", "structural_variants")
    }

    # Extract required fields
    if "genetic_alteration_type" in meta_dictionary and "datatype" in meta_dictionary and "stable_id" in meta_dictionary:
        genetic_alteration_type = meta_dictionary["genetic_alteration_type"]
        data_type = meta_dictionary["datatype"]
        stable_id = meta_dictionary["stable_id"]

        # Validate the combination
        if (genetic_alteration_type, data_type, stable_id) not in allowed_combinations and \
           (genetic_alteration_type, data_type, "*") not in allowed_combinations:
            logger.error(
                "Invalid genetic_alteration_type, datatype, and stable_id combination: (%s, %s, %s). "
                "Please check your meta files.",
                genetic_alteration_type, data_type, stable_id,
                extra={'filename_': filename,
                       'cause': stable_id}
            )
            result = False

    return result

def parse_metadata_file(filename,
                        logger,
                        study_id=None,
                        case_list=False,
                        gene_panel_list=None):

    """Validate a metafile and return a dictionary of values read from it and
    the meta_file_type according to get_meta_file_type.

    `meta_file_type` will be `None` if the file is invalid. If `case_list`
    is True, read the file as a case list instead of a meta file.

    :param filename: name of the meta file
    :param logger: the logging.Logger instance to log warnings and errors to
    :param study_id: (optional - set if you want study_id to be validated)
                    cancer study id found in previous files (or None). All subsequent
                    meta files should comply to this in the field 'cancer_study_identifier'
    :param case_list: whether this meta file is a case list (special case)
    :param gene_panel_list: (optional - set if you want this to be validated)
                           list of gene panels in the database
    """

    logger.debug('Starting validation of meta file', extra={'filename_': filename})

    # Read meta file
    meta_dictionary = OrderedDict()
    with open(filename, 'r') as metafile:
        for line_index, line in enumerate(metafile):
            # skip empty lines:
            if line.strip() == '':
                continue
            if ':' not in line:
                logger.error(
                    "Invalid %s file entry, no ':' found",
                    {True: 'case list', False: 'meta'}[case_list],
                    extra={'filename_': filename,
                           'line_number': line_index + 1})
                meta_dictionary['meta_file_type'] = None
                return dict(meta_dictionary)
            key_value = line.split(':', 1)
            if len(key_value) == 2:
                meta_dictionary[key_value[0]] = key_value[1].strip()

    # Determine meta file type
    if case_list:
        meta_file_type = MetaFileTypes.CASE_LIST
        meta_dictionary['meta_file_type'] = meta_file_type
    else:
        meta_file_type = get_meta_file_type(meta_dictionary, logger, filename)
        meta_dictionary['meta_file_type'] = meta_file_type
        # if type could not be inferred, no further validations are possible
        if meta_file_type is None:
            return dict(meta_dictionary)


    # Check for missing fields for this specific meta file type
    missing_fields = []
    for field in META_FIELD_MAP[meta_file_type]:
        mandatory = META_FIELD_MAP[meta_file_type][field]
        if field not in meta_dictionary and mandatory:
            logger.error("Missing field '%s' in %s file",
                         field,
                         {True: 'case list', False: 'meta'}[case_list],
                         extra={'filename_': filename})
            missing_fields.append(field)

    if missing_fields:
        # all further checks would depend on these fields being present
        meta_dictionary['meta_file_type'] = None
        return dict(meta_dictionary)

    # validate genetic_alteration_type, datatype, stable_id
    stable_id_mandatory = META_FIELD_MAP[meta_file_type].get('stable_id',
                                                             False)
    if stable_id_mandatory:
        valid_types_and_id = validate_types_and_id(meta_dictionary, logger, filename)
        if not valid_types_and_id:
            # invalid meta file type
            meta_dictionary['meta_file_type'] = None
            return dict(meta_dictionary)

    # check for extra unrecognized fields
    for field in meta_dictionary:
        if field not in META_FIELD_MAP[meta_file_type]:

            # Don't give warning for added 'meta_file_type'
            if field == "meta_file_type":
                pass
            else:
                logger.warning(
                    'Unrecognized field in %s file',
                    {True: 'case list', False: 'meta'}[case_list],
                    extra={'filename_': filename,
                           'cause': field})

    # check that cancer study identifiers across files so far are consistent.
    if (
            study_id is not None and
            'cancer_study_identifier' in meta_dictionary and
            study_id != meta_dictionary['cancer_study_identifier']):
        logger.error(
            "Cancer study identifier is not consistent across "
            "files, expected '%s'",
            study_id,
            extra={'filename_': filename,
                   'cause': meta_dictionary['cancer_study_identifier']})
        # not a valid meta file in this study
        meta_dictionary['meta_file_type'] = None
        return dict(meta_dictionary)

    # type-specific validations

    # Validate length of attributes in meta study file
    # TODO: do this for all other meta files as well
    meta_study_attribute_size_dict = {'cancer_study_identifier': 255,
                                      'type_of_cancer': 63,
                                      'name': 255,
                                      'description': 1024,
                                      'citation': 200,
                                      'pmid': 1024,
                                      'groups': 200,
                                      'short_name': 64
                                      }
    if meta_file_type == MetaFileTypes.STUDY:
        for attribute in meta_study_attribute_size_dict:
            if attribute in meta_dictionary:
                if len(meta_dictionary[attribute]) > meta_study_attribute_size_dict[attribute]:
                    logger.error("The maximum length of the '%s' "
                                 "value is %s" % (attribute,
                                                  meta_study_attribute_size_dict[attribute]),
                                 extra={'filename_': filename,
                                        'cause': meta_dictionary[attribute] + ' (%s)' % len(meta_dictionary[attribute])}
                                 )

    # Restrict the show_profile_in_analysis_tab value to false (https://github.com/cBioPortal/cbioportal/issues/5023)
    if meta_file_type in (MetaFileTypes.CNA_CONTINUOUS, MetaFileTypes.CNA_LOG2):
        if meta_dictionary['show_profile_in_analysis_tab'] != 'false':
            logger.error("The 'show_profile_in_analysis_tab' setting must be 'false', as this is only applicable for "
                        "CNA data of the DISCRETE type.",
                        extra={'filename_': filename,
                        'cause': 'show_profile_in_analysis_tab: %s' % meta_dictionary['show_profile_in_analysis_tab']})

    if meta_file_type in (MetaFileTypes.SEG, MetaFileTypes.GISTIC_GENES):
        # Todo: Restore validation for reference genome in segment files
        # Validation can be restored to normal when hg18 data on public portal and data hub has been
        # liftovered to hg19. It was decided in the data hub call of August 14 2018 to remove validation until then.
        valid_segment_reference_genomes = ['hg19','hg38']
        if meta_dictionary['reference_genome_id'] not in valid_segment_reference_genomes:
            logger.error(
                'Reference_genome_id is not %s',
                ' or '.join(valid_segment_reference_genomes),
                extra={'filename_': filename,
                       'cause': meta_dictionary['reference_genome_id']})
            meta_dictionary['meta_file_type'] = None

    if meta_file_type in [MetaFileTypes.MUTATION, MetaFileTypes.MUTATION_UNCALLED]:
        if ('swissprot_identifier' in meta_dictionary and
                meta_dictionary['swissprot_identifier'] not in ('name',
                                                               'accession')):
            logger.error(
                "Invalid swissprot_identifier specification, must be either "
                "'name' or 'accession'",
                extra={'filename_': filename,
                       'cause': meta_dictionary['swissprot_identifier']})
            meta_dictionary['meta_file_type'] = None

        # Check whether the gene panel property is included in the mutation meta file. This should be an error.
        if 'gene_panel' in meta_dictionary:
            logger.warning("Including the stable ID for gene panels in meta file might lead to incorrect "
                           "results for samples that are profiled but nu mutations are called. Consider adding a column"
                           " for mutation profile to gene panel matrix file",
                           extra={'filename_': filename,
                                  'cause': 'gene_panel: %s' % meta_dictionary['gene_panel']})

    # When validating
    if gene_panel_list:
        # Check whether the gene panel in the gene panel property field corresponds with a gene panel in the database
        if 'gene_panel' in meta_dictionary:
            if meta_dictionary['gene_panel'] not in gene_panel_list and meta_dictionary['gene_panel'] != 'NA':
                logger.error('Gene panel ID is not in database. Please import this gene panel before loading '
                             'study data.',
                             extra={'filename_': filename,
                                    'cause': meta_dictionary['gene_panel']})

    # Save information regarding `source_stable_id`, so that after all meta files are validated,
    # we can validate fields between meta files in validate_data_relations() in validateData.py
    global gsva_scores_stable_id
    global gsva_scores_source_stable_id
    global gsva_pvalues_source_stable_id
    global gsva_scores_filename
    global gsva_pvalues_filename

    # save all expression `stable_id` in a dictionary with their filenames
    if meta_file_type is MetaFileTypes.EXPRESSION:
        if 'stable_id' in meta_dictionary:
            expression_stable_ids[meta_dictionary['stable_id']] = filename

            # Save all zscore expression `source_stable_id` in dictionary with their filenames.
            # Multiple zscore expression files are possible, and we want to validate all their
            # source_stable_ids with expression stable ids
            if meta_dictionary['datatype'] == "Z-SCORE":
                if 'source_stable_id' in meta_dictionary:
                    expression_zscores_source_stable_ids[meta_dictionary['source_stable_id']] = filename

    # save stable_id and source_stable_id of GSVA Scores
    if meta_file_type is MetaFileTypes.GSVA_SCORES:
        gsva_scores_filename = filename
        if 'source_stable_id' in meta_dictionary:
            gsva_scores_source_stable_id = meta_dictionary['source_stable_id']

        # save 'stable_id' to check the 'source_stable_id' in GSVA_PVALUES file
        if 'stable_id' in meta_dictionary:
            gsva_scores_stable_id = meta_dictionary['stable_id']

    # save stable_id and source_stable_id of GSVA Pvalues
    if meta_file_type is MetaFileTypes.GSVA_PVALUES:
        gsva_pvalues_filename = filename
        if 'source_stable_id' in meta_dictionary:
            gsva_pvalues_source_stable_id = meta_dictionary['source_stable_id']

    logger.info('Validation of meta file complete', extra={'filename_': filename})

    return meta_dictionary


def run_java(*args):
    java_home = os.environ.get('JAVA_HOME', '')
    if java_home:
        java_command = os.path.join(java_home, 'bin', 'java')
    else:
        java_command = 'java'
    full_cmd = [java_command] + list(args)
    print(">", " ".join(full_cmd))
    process = Popen(full_cmd, stdout=PIPE, stderr=STDOUT,
                    universal_newlines=True)
    ret = []
    while process.poll() is None:
        line = process.stdout.readline()
        if line != '' and line.endswith('\n'):
            print(line.strip(), file=OUTPUT_FILE)
            ret.append(line[:-1])
    ret.append(process.returncode)
    # if cmd line parameters error:
    if process.returncode == 64 or process.returncode == 2:
        raise RuntimeError('Aborting. Step failed due to wrong parameters passed to subprocess.')
    # any other error:
    elif process.returncode != 0:
        raise RuntimeError('Aborting due to error while executing step.')
    return ret


def properties_error_message(display_name: str, property_name: str) -> str:
    return f"No {display_name} provided for database connection. Please set '{property_name}' in application.properties."


class PortalProperties(object):
    """ Properties object class, just has fields for db conn """

    def __init__(self, database_user, database_pw, database_url):
        self.database_user = database_user
        self.database_pw = database_pw
        self.database_url = database_url


def get_database_properties(properties_filename: str) -> Optional[PortalProperties]:

    properties = parse_properties_file(properties_filename)
    
    missing_properties = []
    for required_property in REQUIRED_DATABASE_PROPERTIES:
        if required_property not in properties or len(properties[required_property]) == 0:
            missing_properties.append(required_property)
    if missing_properties:
        print(
            'Missing required properties : (%s)' % (', '.join(missing_properties)),
            file=ERROR_FILE)
        return None

    if properties.get(PORTAL_PROPERTY_DATABASE_HOST) is not None \
        or properties.get(PORTAL_PROPERTY_DATABASE_NAME) is not None \
        or properties.get(PORTAL_PROPERTY_DATABASE_USESSL) is not None \
        or properties.get(PORTAL_PROPERTY_DATABASE_URL) is not None:
        print("""
            ----------------------------------------------------------------------------------------------------------------
            -- Connection error:
            -- You try to connect to the database using the deprecated 'db.host', 'db.portal_db_name' and 'db.use_ssl' or 'db.connection_string' properties.
            -- Please remove these properties and use the 'db.spring.datasource.url' property instead. See https://docs.cbioportal.org/deployment/customization/application.properties-reference/
            -- for assistance on building a valid connection string.
            ------------------------------------------------------------f---------------------------------------------------
        """, file=ERROR_FILE)
        return None

    return PortalProperties(properties[PORTAL_PROPERTY_SPRING_DATABASE_USER],
                            properties[PORTAL_PROPERTY_SPRING_DATABASE_PW],
                            properties[PORTAL_PROPERTY_SPRING_DATABASE_URL])


def parse_properties_file(properties_filename: str) -> Dict[str, str]:

    if not os.path.exists(properties_filename):
        print('properties file %s cannot be found' % properties_filename, file=ERROR_FILE)
        sys.exit(2)
        
    properties = {}
    with open(properties_filename, 'r') as properties_file:
        for line in properties_file:
            line = line.strip()
            # skip line if its blank or a comment
            if len(line) == 0 or line.startswith('#'):
                continue
            try:
                name, value = line.split('=', maxsplit=1)
            except ValueError:
                print(
                    'Skipping invalid entry in property file: %s' % line,
                    file=ERROR_FILE)
                continue
            properties[name] = value.strip()
    return properties


def get_db_cursor(portal_properties: PortalProperties):

    try:
        url_elements = dsnparse.parse(portal_properties.database_url)
        connection_kwargs = {
            "host": url_elements.host,
            "port": url_elements.port if url_elements.port is not None else 3306,
            "db": url_elements.paths[0],
            "user": portal_properties.database_user,
            "passwd": portal_properties.database_pw
        }
        if url_elements.query.get("useSSL") == "true":
            connection_kwargs['ssl_mode'] = 'REQUIRED'
            connection_kwargs['ssl'] = {"ssl_mode": True}
        else:
            if url_elements.query.get("get-server-public-key") == "true":
                connection_kwargs['ssl'] = {
                    'MYSQL_OPT_GET_SERVER_PUBLIC_KEY': True
                }
        connection = MySQLdb.connect(**connection_kwargs)
    except MySQLdb.Error as exception:
        print(exception, file=ERROR_FILE)
        message = (
            "--> Error connecting to server with URL: "
            + portal_properties.database_url)
        print(message, file=ERROR_FILE)
        raise ConnectionError(message) from exception
    if connection is not None:
        return connection, connection.cursor()
