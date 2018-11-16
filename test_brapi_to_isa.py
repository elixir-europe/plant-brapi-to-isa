import logging
import os
import unittest
from functools import reduce

import mock
from isatools import isatab
from isatools.model import Investigation

import brapi_to_isa
import mock_data
from brapi_to_isa_converter import BrapiToIsaConverter
import requests_mock

logger = logging.getLogger()
endpoint = 'http://foo.com/'


class ConvertTest(unittest.TestCase):
    """Run BrAPI 2 ISA conversion test on mocked data (from http://test-server.brapi.org)"""

    def setUp(self):
        self.converter = BrapiToIsaConverter(logger, endpoint)

    @mock.patch('brapi_to_isa_converter.BrapiClient', autospec=True)
    def test_convert_study(self, client_mock):
        """Test conversion of BrAPI study to ISA study using mock data."""
        # Mock call to BrAPI study
        instance_mock = client_mock.return_value = mock.Mock()
        instance_mock.get_brapi_study.return_value = mock_data.mock_study
        instance_mock.get_obs_units_in_study.return_value = mock_data.mock_observation_units

        study_id = mock_data.mock_study['studyDbId']
        investigation = Investigation()

        # Convert BrAPI study to ISA study
        (study, _) = self.converter.create_isa_study(study_id, investigation)

        assert instance_mock.get_brapi_study.called

        assert study is not None
        assert study.filename == f's_{study_id}.txt'
        assert len(study.assays) == 1
        assert study.assays[0].filename == f'a_{study_id}_default.txt'

    @requests_mock.Mocker()
    def test_convert_germplasm(self, request_mock):
        """Test conversion of BrAPI germplasm to ISA characteristics"""
        germplasm1 = mock_data.mock_germplasms[0]
        req = request_mock.get(requests_mock.ANY, json=mock_data.mock_brapi_result(germplasm1))

        characteristics = self.converter.create_germplasm_chars(germplasm1)
        assert req.called
        assert characteristics
        assert len(characteristics) == 5

        # List all characteristic terms
        terms = dict(reduce(lambda acc, char: acc + [(char.category.term, char.value.term)],
                            characteristics,
                            []))

        assert terms['germplasmDbId'] == germplasm1['germplasmDbId']
        assert terms['germplasmName'] == germplasm1['germplasmName']
        assert terms['Infraspecific Name'] == germplasm1['subtaxa']
        assert terms['commonCropName'] == germplasm1['commonCropName']
        assert terms['Material Source ID'] == germplasm1['accessionNumber']

    def test_create_isa_characteristic(self):
        category = 'category'
        value = 'value'

        # Call
        characteristic = self.converter.create_isa_characteristic(category, value)

        # Assert
        assert characteristic
        assert characteristic.category.term == category
        assert characteristic.value.term == value
        assert characteristic.value.term_source == characteristic.value.term_accession == ''

    def test_create_tdf_records(self):
        variables = mock_data.mock_variables

        # Call
        tdf = self.converter.create_isa_tdf_from_obsvars(variables)

        # Assert
        assert tdf
        assert len(tdf) == len(variables) + 1

    def test_create_data_records(self):
        observation_units = mock_data.mock_observation_units

        # Call
        data = self.converter.create_isa_obs_data_from_obsvars(observation_units)

        # Assert
        assert data
        observation_count = reduce(
            lambda acc, observation_unit: acc + len(observation_unit['observations']), observation_units, 0
        )
        assert len(data) == observation_count + 1

    @requests_mock.Mocker()
    @mock.patch('brapi_to_isa.BrapiClient', autospec=True)
    @mock.patch('brapi_to_isa_converter.BrapiClient', autospec=True)
    def test_all_convert(self, request_mock, client_mock1, client_mock2):
        """Test the full conversion from BrAPI to ISA using mock data and validating using ISA validator."""
        # Mock API calls
        germplasm1 = mock_data.mock_germplasms[0]
        req = request_mock.get(requests_mock.ANY, json=mock_data.mock_brapi_result(germplasm1))
        instance_mock = client_mock1.return_value = client_mock2.return_value
        instance_mock.get_trials.return_value = mock_data.mock_trials
        instance_mock.get_brapi_trials.return_value = mock_data.mock_trials
        instance_mock.get_study.return_value = mock_data.mock_study
        instance_mock.get_brapi_study.return_value = mock_data.mock_study
        instance_mock.get_germplasm_in_study.return_value = mock_data.mock_germplasms
        instance_mock.get_obs_units_in_study.return_value = mock_data.mock_observation_units
        instance_mock.get_study_observed_variables.return_value = mock_data.mock_variables

        # Run full conversion
        brapi_to_isa.main(None)

        out_folder = brapi_to_isa.get_output_path(mock_data.mock_trials[0]['trialName'])
        assert os.path.exists(out_folder)
        assert req.called

        # TODO: use MIAPPE ISA configuration for validation here
        investigation_file_path = os.path.join(out_folder, 'i_investigation.txt')
        with open(investigation_file_path, 'r', encoding='utf-8') as i_fp:
            assert isatab.validate(i_fp)


if __name__ == '__main__':
    unittest.main()
