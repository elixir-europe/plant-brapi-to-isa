import requests
import logging
import json


class BrapiClient:
    """ Provide methods to the BRAPI
    """

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def get_brapi_trials(self):
        """Returns all the trials from an endpoint."""
        page = 0
        pagesize = 10
        maxcount = None
        while maxcount is None or page * pagesize < maxcount:
            params = {'page': page, 'pageSize': pagesize}

            r = requests.get(self.endpoint + 'trials', params=params)
            if r.status_code != requests.codes.ok:
                raise RuntimeError("Non-200 status code")
            maxcount = int(r.json()['metadata']['pagination']['totalCount'])
            for this_trial in r.json()['result']['data']:
                yield this_trial
                # print("trial ", this_trial ," in page: ", page)
            page += 1
            # print("trial page: ", page)
            logging.info("trial page: ", page)

    def get_phenotypes(self):
        """Returns a phenotype information from a BrAPI endpoint."""
        url = self.endpoint + "phenotype-search"
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
            logging.error("check over here", r)
            logging.fatal('Could not decode response from server!')
            raise RuntimeError("Non-200 status code")
        phenotypes = r.json()['result']['data']
        return phenotypes

    def get_germplasms(self):
        """Returns germplasm information from a BrAPI endpoint."""
        url = self.endpoint + "germplasm-search"
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
            logging.error("check over here", r)
            logging.fatal('Could not decode response from server!')
            raise RuntimeError("Non-200 status code")
        these_germplasms = r.json()['result']['data']
        return these_germplasms

    def get_study(self, study_identifier):
        """"Given a BRAPI study object from a BRAPI endpoint server"""
        r = requests.get(self.endpoint + 'studies/' + str(study_identifier))
        if r.status_code != requests.codes.ok:
            print(r, self.endpoint)
            logging.error("problem with request get_study: ", r)
            raise RuntimeError("Non-200 status code")
        return r.json()["result"]

    def get_germplasm_in_study(self, study_identifier):
        """"Given a BRAPI study identifier returns an array of germplasm objects"""

        r = requests.get(self.endpoint + "studies/" + study_identifier + '/germplasm')
        num_pages = r.json()['metadata']['pagination']['totalPages']
        all_germplasms = []
        for page in range(0, num_pages):
            r = requests.get(self.endpoint + "studies/" + study_identifier +
                             '/germplasm', params={'page': page})

            logging.debug("from 'get_germplasm_in_study' function page:", page, "request:",
                          len(r.json()['result']['data']))
            if r.status_code != requests.codes.ok:
                raise RuntimeError("Non-200 status code")
            all_germplasms = all_germplasms + (r.json()['result']['data'])
        return all_germplasms

        # params={}
        # can't find anyone that implements /studies/{id}/germplasm
        # have to do it as an phenotype search instead
        # note that this will omit any germplasm that hasn't got an associated phenotype
        # germplasm = set()
        # indata = json.dumps({"studyDbIds":[studyId]})
        # print(indata)
        # params['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
        #  Chrome/41.0.2272.101 Safari/537.36"
        # params['Accept'] = "application/json"
        # params['Content-Type'] = "application/json;charset=utf-8"
        # request_url='https://urgi.versailles.inra.fr/gnpis-core-srv/brapi/v1/phenotypes-search'
        # headers = {}
        # r = requests.post(request_url, params=json.dumps(params),data=json.dumps({"studyDbIds":[studyId]}))
        # print("Post request response content: ", r.content)

        # for phenotype in paging(SERVER + 'phenotypes-search/', params, indata, 'POST'):
        #     germplasm.add(phenotype['germplasmDbId'])
        # return germplasm

    def get_obs_units_in_study(self, study_identifier):
        """ Given a BRAPI study identifier, return an list of BRAPI observation units"""
        r = requests.get(self.endpoint + "studies/" + study_identifier + '/observationunits')

        num_pages = r.json()['metadata']['pagination']['totalPages']
        all_obs_units = []
        for page in range(0, num_pages):
            r = requests.get(self.endpoint + "studies/" + study_identifier +
                             '/observationunits', params={'page': page})
            if r.status_code != requests.codes.ok:
                raise RuntimeError("Non-200 status code")

            all_obs_units = all_obs_units + (r.json()['result']['data'])
        # print("from function, nb obsunits:: ", len(all_obs_units))
        return all_obs_units

    def get_germplasm(self, germplasm_id):
        """ Given a BRAPI germplasm identifiers, return an list of BRAPI germplasm attributes"""
        r = requests.get(self.endpoint + 'germplasm/' + str(germplasm_id) + '/attributes')
        num_pages = r.json()['metadata']['pagination']['totalPages']
        all_germplasm_attributes = []
        for page in range(0, num_pages):
            r = requests.get(self.endpoint + 'germplasm/' + str(germplasm_id) + 'attributes', params={'page': page})
            # print("from get_germplasm_attributes function: ", page, "total count:", len(r.json()['result']['data']))
            if r.status_code != requests.codes.ok:
                raise RuntimeError("Non-200 status code")
            all_germplasm_attributes = all_germplasm_attributes + r.json()['result']['data']
        # print("from function, nb obsunits:: ", len(all_germplasm_attributes))
        # url = SERVER+'germplasm-search?germplasmDbId='+str(germplasm_id)
        # print('GETing',url)
        # r = requests.get(url)
        # if r.status_code != requests.codes.ok:
        #     raise RuntimeError("Non-200 status code")
        # germplasm = r.json()['result']['data'][0]

        return all_germplasm_attributes

    def get_brapi_study(self, study_identifier):
        """" Given a BRAPI study identifier,obtains a BRAPI study object """
        url = self.endpoint + 'studies/' + str(study_identifier)
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
            raise RuntimeError("Non-200 status code")
        this_study = r.json()['result']
        return this_study

    def get_study_observed_variables(self, brapi_study_id):
        """" Given a BRAPI study identifier, returns a list of BRAPI observation Variables objects """
        r = requests.get(self.endpoint + "studies/" + brapi_study_id + '/observationVariables')
        if r.status_code != requests.codes.ok:
            raise RuntimeError("Non-200 status code")
        all_obsvars = r.json()['result']['data']

        return all_obsvars

    def paging(self, url: object, params: object, data: object, method: object) -> object:
        """ "Housekeeping" function to deal with paging during http calls"""
        page = 0
        pagesize = 1000  # VIB doesn't seem to respect it
        maxcount = None
        # set a default dict for parameters
        if params is None:
            params = {}
        while maxcount is None or page < maxcount:
            params['page'] = page
            params['pageSize'] = pagesize
            print('retrieving page', page, 'of', maxcount, 'from', url)
            print(params)
            logging.info("paging params:", params)

            if method == 'GET':
                print("GETting", url)
                r = requests.get(url, params=params, data=data)
            elif method == 'PUT':
                print("PUTting", url)
                r = requests.put(url, params=params, data=data)
            elif method == 'POST':
                # params['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)
                # Chrome/41.0.2272.101 Safari/537.36"
                params['Accept'] = "application/json"
                params['Content-Type'] = "application/json"
                print("POSTing", url)
                print("POSTing", params, data)
                headers = {}
                r = requests.post(url, params=json.dumps(params).encode('utf-8'), json=data,
                                  headers=headers)
                print(r)

            if r.status_code != requests.codes.ok:
                print(r)
                logging.error("problem with request: ", r)
                raise RuntimeError("Non-200 status code")

            maxcount = int(r.json()['metadata']['pagination']['totalPages'])

            for data in r.json()['result']['data']:
                yield data

            page += 1

    def load_trials(self, TRIAL_IDS, logger):
        """" Return trials found in a given BRAPI endpoint server """

        url = self.endpoint+"trials"
        if not TRIAL_IDS:
            logger.info("Return all trials")
            for trial in self.paging(url, None, None, 'GET'):
                yield trial
        else:
            logger.info("Return  trials: " + str(TRIAL_IDS))
            for trial_id in TRIAL_IDS:
                url_with_ids = url + "/" + trial_id
                logger.debug(url_with_ids)
                r = requests.get(url_with_ids)
                if r.status_code != requests.codes.ok:
                    print(r)
                    logging.error("problem with request: ", r)
                    raise RuntimeError("Non-200 status code")
                yield r.json()['result']
