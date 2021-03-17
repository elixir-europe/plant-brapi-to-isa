FROM python:3.6.1

COPY *.py /
COPY /isaconfig-phenotyping-basic /isaconfig-phenotyping-basic
COPY requirements.txt requirements.txt

RUN python3 -m pip install --upgrade pip && python3 -m pip install -r requirements.txt

ENTRYPOINT ["python", "/brapi_to_isa.py"]
