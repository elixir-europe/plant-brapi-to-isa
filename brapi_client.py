import json
import logging
from collections.abc import Iterable
from typing import List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import re
from cachetools import cached, LRUCache, TTLCache


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
        self.obs_var_call = " "
        self.taxon = {}

    # def get_phenotypes(self) -> Iterable:
    #     """Returns a phenotype information from a BrAPI endpoint."""
    #     yield from self.fetch_objects('GET', '/phenotype-search')

    # def get_germplasms(self) -> Iterable:
    #     """Returns germplasm information from a BrAPI endpoint."""
    #     yield from self.fetch_objects('GET', '/germplasm-search')

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
                self.logger.debug("\n\nERROR in get_obs_units_in_study " + str(r.status_code) + str(r.json()))
                raise RuntimeError("Non-200 status code")
            elif r.json()['metadata']['pagination']['totalCount'] == 0:
                self.logger.debug(" EMPTY CALLS Call, assume OBSERVATIONUNIT THE 1.1 WAY")
                self.obs_unit_call = "observationUnits"
            elif any(el['call'] == 'studies/{studyDbId}/observationUnits' for el in r.json()['result']['data']):
                self.logger.debug(" GOT OBSERVATIONUNIT THE 1.1 WAY")
                self.obs_unit_call = "observationUnits"
            elif any(el['call'] == 'studies/{studyDbId}/observationunits' for el in r.json()['result']['data']):
                self.logger.debug(" GOT OBSERVATIONUNIT THE 1.2+ WAY")
                self.obs_unit_call = "observationunits"        
            else:
                if any(el['call'] == 'phenotypes-search' for el in r.json()['result']['data']):
                    self.logger.debug(" GOT NO STUDY OBSERVATIONUNIT CALL, TAKING PHENOTYPESEARCH INSTEAD")
                    self.obs_unit_call = "phenotypes-search"
                else:
                    self.logger.debug(" GOT NO STUDY OBSERVATIONUNIT CALL, QUITTING PROCESS")

        return self.obs_unit_call

    def _get_obs_var_call(self) -> str:
        """Choose which BrAPI call to use in order to fetch observation variables by study"""
        if self.obs_var_call == " ":
            r = requests.get(self.endpoint + "calls?pageSize=100")
            if r.status_code != requests.codes.ok:
                self.logger.debug("\n\nERROR in get_obs_var_in_study " + r.status_code + r.json())
                raise RuntimeError("Non-200 status code")
            elif r.json()['metadata']['pagination']['totalCount'] == 0:
                self.logger.debug(" EMPTY CALLS Call, assume OBSERVATIONVARIABLE THE 1.0 WAY")
                self.obs_var_call = "observationVariables"
            elif any(el['call'] == 'studies/{studyDbId}/observationVariables' for el in r.json()['result']['data']):
                self.logger.debug(" GOT OBSERVATIONVARIABLE THE 1.0 WAY")
                self.obs_var_call = "observationVariables"
            else:
                self.logger.debug(" GOT OBSERVATIONVARIABLE THE 1.1+ WAY")
                self.obs_var_call = "observationvariables"
        return self.obs_var_call
    
    # #NOTE: if phenotype search is needed in the future
    # def _get_observation_call(self) -> str:
    #     """ Given a BRAPI study identifier, return an list of BRAPI observation units"""
    #     r = requests.get(self.endpoint + "calls?pageSize=100")
    #     if any(el['call'] == 'phenotypes-search' for el in r.json()['result']['data']):
    #         self.logger.debug(" GOT PHENOTYPESEARCH THE 1.1/1.2 WAY")
    #         self.obs_call = "phenotypes-search"
    #     elif any(el['call'] == 'observationunits' for el in r.json()['result']['data']):
    #         self.logger.debug(" GOT OBSERVATIONUNITS THE 1.3 WAY")
    #         self.obs_call = "observationunits"
    #     return self.obs_call


    def get_study_observation_units(self, study_id: str) -> Iterable:
        """ Given a BRAPI study identifier, return an list of BRAPI observation units"""
        observation_unit_call = self._get_obs_unit_call()
        if observation_unit_call == 'phenotypes-search':
            yield from self.fetch_objects('GET', f'/phenotypes-search', params={'studyDbId':study_id})
        else:
            yield from self.fetch_objects('GET', f'/studies/{study_id}/{observation_unit_call}')
    
    # #NOTE: if phenotype search is needed in the future
    # def get_observations_units(self, study_id: str, ) -> Iterable:
    #     """ Given a BRAPI study identifier, return an list of observationUnits"""
    #     observation_call = self._get_observation_call()
    #     yield from self.fetch_objects('GET', f'/{observation_call}', params={'studyDbIds':study_id})

    @cached(cache=TTLCache(maxsize=4096, ttl=900))
    def get_germplasm(self, germplasm_id: str) -> dict:
        """ Given a BRAPI germplasm identifiers, return an list of BRAPI germplasm attributes"""
        return self.fetch_object(f'/germplasm/{germplasm_id}')

    def get_study_observed_variables(self, study_id: str) -> Iterable:
        """" Given a BRAPI study identifier, returns a list of BRAPI observation Variables objects """
        observation_var_call = self._get_obs_var_call()
        yield from self.fetch_objects('GET', f'/studies/{study_id}/{observation_var_call}')

    def get_trials(self, trial_ids: List[str]=None) -> Iterable:
        """"
        Return trials found in a given BRAPI endpoint server
        :param trial_ids if provided, this list of trial ids with restrict the list of fetched trials
        :return iterable of BrAPI trials (pared from JSON as python dict)
        """
        if not trial_ids:
            self.logger.info("Not enough parameters, provide TRIAL or STUDY IDs")
            exit (1)
        elif trial_ids == ["all"]:
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
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=15)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        r = session.get(url)
        # Covering internal server errors by retrying one more time
        if r.status_code == 500:
            time.sleep(5)
            r = requests.get(url)
        elif r.status_code != requests.codes.ok:
            logging.error("problem with request: " + str(r))
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
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=15)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        while maxcount is None or page < maxcount:
            params['page'] = page
            params['pageSize'] = pagesize
            self.logger.debug('retrieving page ' + str(page)+ ' of '+ str(maxcount)+ ' from '+ str(url))
            self.logger.info("paging params:" + str(params))

            if method == 'GET':
                self.logger.debug("GETting " + url)
                r = session.get(url, params=params, data=data)
            elif method == 'PUT':
                self.logger.debug("PUTting "+  url)
                r = session.put(url, params=params, data=data)
            elif method == 'POST':
                # params['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
                # Chrome/41.0.2272.101 Safari/537.36"
                params['Accept'] = "application/json"
                params['Content-Type'] = "application/json"
                self.logger.debug("POSTing " + url)
                self.logger.debug("POSTing " + str(params) + str(data))
                headers = {}
                r = session.post(url, params=json.dumps(params).encode('utf-8'), json=data,
                                  headers=headers)
                self.logger.debug(r)
            else:
                raise RuntimeError(f"Unknown method: {method}")
            if r.status_code == 504 and pagesize != 100:
                pagesize = 100
                self.logger.info("504 Gateway Timeout Error, testing with pagesize = 100") 
                continue
            elif r.status_code != requests.codes.ok:
                self.logger.error("problem with request: " + str(r))
                raise RuntimeError("Non-200 status code")
            maxcount = int(r.json()['metadata']['pagination']['totalPages'])

            for data in r.json()['result']['data']:
                yield data

            page += 1

    def get_taxonId(self, genus, species):
        scientific_name = '%20'.join([genus,species])
        if scientific_name in self.taxon:
            return self.taxon[scientific_name]
        
        link = "https://www.ebi.ac.uk/ena/taxonomy/rest/any-name/{}".format(scientific_name)
        self.logger.debug('GET ' + link)
        r = requests.get(link)
        if r.status_code != requests.codes.ok:
            self.logger.error("problem with request: " + str(r))
            raise RuntimeError("Non-200 status code")
        else:
            taxonId = r.json()[0]['taxId']
            self.taxon[scientific_name] = taxonId
            return taxonId
    
    def get_ontologies(self):
        ont = {}
        link = 'http://www.obofoundry.org/registry/ontologies.jsonld'
        self.logger.debug('GET ' + link)
        r = requests.get(link)
        if r.status_code != requests.codes.ok:
            self.logger.error("problem with request: " + str(r))
            raise RuntimeError("Non-200 status code")
        else:
            data = r.json()
        for ontology in data['ontologies']:
            if ontology['activity_status'] == "active":
                ont[ontology['id']] = [ontology['title'], ontology['ontology_purl']]
        return ont