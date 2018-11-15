import os
import unittest

import mock
import requests_mock
from isatools import isatab
from isatools.model import Investigation

import brapi_to_isa
import test_mock_data
from brapi_client import BrapiClient


class BrapiClientTest(unittest.TestCase):

    @requests_mock.mock()
    def test_get_study(self, mock_requests_session):
        # Init client with mock requests session
        client = BrapiClient('foo/', mock_requests_session)
        mock_requests_session.get('foo/studies/bar', text='baz')

        study_id = "bar"
        client.get_study(study_id)


class ConvertTest(unittest.TestCase):
    """Run BrAPI 2 ISA conversion test on mocked data (from http://test-server.brapi.org)"""

    @mock.patch('brapi_client.BrapiClient')
    def test_convert_study(self, BrapiClientMock):
        """Test conversion of BrAPI study to ISA study using mock data."""
        # Mock call to BrAPI study
        BrapiClientMock.get_brapi_study.return_value = test_mock_data.mock_study

        study_id = test_mock_data.mock_study['studyDbId']
        investigation = Investigation()

        # Convert BrAPI study to ISA study
        (study, _) = brapi_to_isa.create_isa_study(study_id, investigation)

        assert study is not None
        assert study.filename == f's_{study_id}.txt'
        assert len(study.assays) == 1
        assert study.assays[0].filename == f'a_{study_id}.txt'

    @mock.patch('brapi_client.BrapiClient')
    @mock.patch('brapi_to_isa.load_trials')
    def test_all_convert(self, load_trials_mock, brapi_client_mock):
        """Test the full conversion from BrAPI to ISA using mock data and validating using ISA validator."""
        args = []

        # Mock API calls
        load_trials_mock.return_value = test_mock_data.mock_trials
        brapi_client_mock.return_value.get_study.return_value = test_mock_data.mock_study
        brapi_client_mock.return_value.get_brapi_study.return_value = test_mock_data.mock_study
        brapi_client_mock.return_value.get_germplasm_in_study.return_value = test_mock_data.mock_germplasms
        brapi_client_mock.return_value.get_obs_units_in_study.return_value = test_mock_data.mock_observation_units
        brapi_client_mock.return_value.get_study_observed_variables.return_value = test_mock_data.mock_variables

        # Run full conversion
        brapi_to_isa.main(args)

        out_folder = os.path.join("outputdir", test_mock_data.mock_trials[0]['trialName'])
        assert os.path.exists(out_folder)

        # TODO: use MIAPPE ISA configuration for validation here
        investigation_file_path = os.path.join(out_folder, 'i_investigation.txt')
        with open(investigation_file_path, 'r', encoding='utf-8') as i_fp:
            assert isatab.validate(i_fp)


if __name__ == '__main__':
    unittest.main()
