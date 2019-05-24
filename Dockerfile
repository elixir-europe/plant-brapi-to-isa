FROM python:3.6.1

RUN pip install isatools requests pycountry-convert cachetools

COPY *.py /
COPY /isaconfig-phenotyping-basic /isaconfig-phenotyping-basic

ENTRYPOINT python /brapi_to_isa.py