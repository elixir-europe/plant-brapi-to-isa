import json
import logging
from collections import Iterable
from typing import List

import requests


def url_path_join(*args):
    """Join path(s) in URL using slashes"""
    return '/'.join(s.strip('/') for s in args)


class BrapiClient:
    """ Provide methods to the BRAPI
    """

    def __init__(self, endpoint: str, logger: logging.Logger):
        self.endpoint = endpoint
        self.logger = logger
        self.obs_unit_call = " "

    def get_phenotypes(self) -> Iterable:
        """Returns a phenotype information from a BrAPI endpoint."""
        yield from self.fetch_objects('GET', '/phenotype-search')

    def get_germplasms(self) -> Iterable:
        """Returns germplasm information from a BrAPI endpoint."""
        yield from self.fetch_objects('GET', '/germplasm-search')

    def get_study(self, study_id: str) -> dict:
        """"Given a BRAPI study object from a BRAPI endpoint server"""
        return self.fetch_object(f'/studies/{study_id}')

    def get_study_germplasms(self, study_id: str) -> Iterable:
        """"Given a BRAPI study identifier returns an array of germplasm objects"""
        yield from self.fetch_objects('GET', f'/studies/{study_id}/germplasm')

    def _get_obs_unit_call(self) -> str:
        """Choose which BrAPI call to use in order to fetch observation unit by study"""
        if self.obs_unit_call == " ":
            r = requests.get(self.endpoint + "calls?pageSize=100")
            if r.status_code != requests.codes.ok:
                self.logger.debug("\n\nERROR in get_obs_units_in_study " + r.status_code + r.json())
                raise RuntimeError("Non-200 status code")
            if any(el['call'] == 'studies/{studyDbId}/observationUnits' for el in r.json()['result']['data']):
                self.logger.debug(" GOT OBSERVATIONUNIT THE 1.1 WAY")
                self.obs_unit_call = "observationUnits"
            else:
                self.obs_unit_call = "observationunits"
        return self.obs_unit_call

    def get_study_observation_units(self, study_id: str) -> Iterable:
        """ Given a BRAPI study identifier, return an list of BRAPI observation units"""
        observation_unit_call = self._get_obs_unit_call()
        yield from self.fetch_objects('GET', f'/studies/{study_id}/{observation_unit_call}')

    def get_germplasm(self, germplasm_id: str) -> dict:
        """ Given a BRAPI germplasm identifiers, return an list of BRAPI germplasm attributes"""
        return self.fetch_object(f'/germplasm/{germplasm_id}')

    def get_study_observed_variables(self, study_id: str) -> Iterable:
        """" Given a BRAPI study identifier, returns a list of BRAPI observation Variables objects """
        yield from self.fetch_objects('GET', f'/studies/{study_id}/observationVariables')

    def get_trials(self, trial_ids: List[str]=None) -> Iterable:
        """"
        Return trials found in a given BRAPI endpoint server
        :param trial_ids if provided, this list of trial ids with restrict the list of fetched trials
        :return iterable of BrAPI trials (pared from JSON as python dict)
        """
        if not trial_ids:
            self.logger.info("Not enough parameters, provide TRIAL or STUDY IDs")
            exit (1)
        elif trial_ids == "all":
            self.logger.info("Return all trials")
            yield from self.fetch_objects('GET', '/trials')
        else:
            self.logger.info("Return  trials: " + str(trial_ids))
            for trial_id in trial_ids:
                yield self.fetch_object(f'/trials/{trial_id}')

    def fetch_object(self, path: str) -> dict:
        """
        Fetch single BrAPI object by path
        :param path URL path of the BrAPI call (ex '/studies/1', '/germplasm/2', ...)
        :return a BrAPI object parsed from JSON to python dict
        """
        url = url_path_join(self.endpoint, path)
        self.logger.debug('GET ' + url)
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
            logging.error("problem with request: ", r)
            raise RuntimeError("Non-200 status code")
        return r.json()["result"]

    def fetch_objects(self, method: str, path: str, params: dict=None, data: dict=None) -> Iterable:
        """
        Fetch BrAPI objects with pagination
        :param method HTTP method of the BrAPI call (GET, POST, PUT)
        :param path URL path of the BrAPI call (ex '/studies', '/germplasm-search', ...)
        :param params dict containing the query params for the BrAPI call
        :param data dict containing the request body (used for 'POST' calls)
        :return iterable of BrAPI objects parsed from JSON to python dict
        """
        page = 0
        pagesize = 1000
        maxcount = None
        # set a default dict for parameters
        params = params or {}
        url = url_path_join(self.endpoint, path)
        while maxcount is None or page < maxcount:
            params['page'] = page
            params['pageSize'] = pagesize
            self.logger.debug('retrieving page' + str(page)+ 'of'+ str(maxcount)+ 'from'+ str(url))
            self.logger.info("paging params:" + str(params))

            if method == 'GET':
                self.logger.debug("GETting" + url)
                r = requests.get(url, params=params, data=data)
            elif method == 'PUT':
                self.logger.debug("PUTting"+  url)
                r = requests.put(url, params=params, data=data)
            elif method == 'POST':
                # params['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
                # Chrome/41.0.2272.101 Safari/537.36"
                params['Accept'] = "application/json"
                params['Content-Type'] = "application/json"
                self.logger.debug("POSTing" + url)
                self.logger.debug("POSTing" + params + data)
                headers = {}
                r = requests.post(url, params=json.dumps(params).encode('utf-8'), json=data,
                                  headers=headers)
                self.logger.debug(r)
            else:
                raise RuntimeError(f"Unknown method: {method}")

            if r.status_code != requests.codes.ok:
                self.logger.error("problem with request: " + r)
                raise RuntimeError("Non-200 status code")
            maxcount = int(r.json()['metadata']['pagination']['totalPages'])
            # TODO: remove, hack to adress GnpIS bug, to be fixed in production by January 2019
            if '/observationUnits' in url:
                page = 1000

            for data in r.json()['result']['data']:
                yield data

            page += 1
