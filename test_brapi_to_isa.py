import os
import unittest

import mock
from isatools import isatab
from isatools.model import Investigation

import brapi_to_isa
import mock_data


class ConvertTest(unittest.TestCase):
    """Run BrAPI 2 ISA conversion test on mocked data (from http://test-server.brapi.org)"""

    @mock.patch('brapi_to_isa.BrapiClient', autospec=True)
    def test_convert_study(self, client_mock):
        """Test conversion of BrAPI study to ISA study using mock data."""

        # Mock call to BrAPI study
        instance_mock = client_mock.return_value = mock.Mock()
        instance_mock.get_brapi_study.return_value = mock_data.mock_study

        study_id = mock_data.mock_study['studyDbId']
        investigation = Investigation()

        # Convert BrAPI study to ISA study
        (study, _) = brapi_to_isa.create_isa_study(study_id, investigation)

        assert instance_mock.get_brapi_study.called

        assert study is not None
        assert study.filename == f's_{study_id}.txt'
        assert len(study.assays) == 1
        assert study.assays[0].filename == f'a_{study_id}.txt'

    @mock.patch('brapi_to_isa.BrapiClient', autospec=True)
    def test_all_convert(self, client_mock):
        """Test the full conversion from BrAPI to ISA using mock data and validating using ISA validator."""
        # Mock API calls
        instance_mock = client_mock.return_value
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

        # TODO: use MIAPPE ISA configuration for validation here
        investigation_file_path = os.path.join(out_folder, 'i_investigation.txt')
        with open(investigation_file_path, 'r', encoding='utf-8') as i_fp:
            assert isatab.validate(i_fp)


if __name__ == '__main__':
    unittest.main()
