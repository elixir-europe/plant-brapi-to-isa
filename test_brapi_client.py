import logging
import unittest

import requests_mock

import mock_data
from brapi_client import BrapiClient

logger = logging.getLogger()


class BrapiClientTest(unittest.TestCase):

    def setUp(self):
        self.endpoint = 'http://foo/'

    @requests_mock.Mocker()
    def test_get_study_fail(self, mock_session):
        # Mock
        mock_session.get(requests_mock.ANY, status_code=500)

        # Init
        client = BrapiClient(self.endpoint, logger)

        # Call / Assert
        self.assertRaises(RuntimeError, client.get_study, 'bar')

    @requests_mock.Mocker()
    def test_get_study_success(self, mock_session):
        # Mock
        result = mock_data.mock_brapi_result(mock_data.mock_study)
        mock_session.get(requests_mock.ANY, json=result)

        # Init
        client = BrapiClient(self.endpoint, logger)

        # Call
        actual_study = client.get_study('bar')
        # Assert
        assert actual_study == mock_data.mock_study

    @requests_mock.Mocker()
    def test_paging_get(self, mock_session):
        # Mock
        url = f'{self.endpoint}/studies'
        params = None
        data = None
        method = 'GET'
        results = mock_data.mock_brapi_results([mock_data.mock_study], 1)
        mock_session.get(url, json=results)

        # Init
        client = BrapiClient(self.endpoint, logger)

        # Call
        actual_results = list(client.paging(url, params, data, method))

        # Assert
        assert actual_results is not None
        assert len(actual_results) == 1
        assert actual_results[0] == mock_data.mock_study


if __name__ == '__main__':
    unittest.main()
