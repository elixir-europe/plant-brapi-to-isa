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
    def test_get_trial_fail_on_second_page(self, mock_requests):
        """
        Testing scenario when server error on second page
        """
        # Mock
        total_count = len(mock_data.mock_trials) + 1
        total_pages = 2
        page1 = mock_data.mock_brapi_results(mock_data.mock_trials, total_pages, total_count)
        req = mock_requests.register_uri(
            requests_mock.ANY, requests_mock.ANY,
            # First page works with json response, second page fails with HTTP code
            [{"json": page1}, {"status_code": 500}]
        )

        # Init
        client = BrapiClient(self.endpoint, logger)

        # Call
        trial_it = iter(client.get_trials(None))

        # Assert first page can be fetched
        for i in range(total_count-1):
            assert trial_it.__next__()

        # Assert second page fails
        self.assertRaises(RuntimeError, trial_it.__next__)

        # Assert same request executed twice (for each page)
        assert req.call_count == 2

    @requests_mock.Mocker()
    def test_get_study_fail(self, mock_requests):
        # Mock
        mock_requests.get(requests_mock.ANY, status_code=500)

        # Init
        client = BrapiClient(self.endpoint, logger)

        # Call / Assert
        self.assertRaises(RuntimeError, client.get_study, 'bar')

    @requests_mock.Mocker()
    def test_get_study_success(self, mock_requests):
        # Mock
        result = mock_data.mock_brapi_result(mock_data.mock_study)
        mock_requests.get(requests_mock.ANY, json=result)

        # Init
        client = BrapiClient(self.endpoint, logger)

        # Call
        actual_study = client.get_study('bar')
        # Assert
        assert actual_study == mock_data.mock_study

    @requests_mock.Mocker()
    def test_paging_get(self, mock_requests):
        # Mock
        url = f'{self.endpoint}/studies'
        params = None
        data = None
        method = 'GET'
        results = mock_data.mock_brapi_results([mock_data.mock_study])
        mock_requests.get(url, json=results)

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
