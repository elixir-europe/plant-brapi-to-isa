FROM python:3.6.1

COPY *.py /
COPY /isaconfig-phenotyping-basic /isaconfig-phenotyping-basic
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "/brapi_to_isa.py"]