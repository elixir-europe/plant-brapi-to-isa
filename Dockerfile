FROM python:3.7.12

COPY *.py /
COPY /isaconfig-phenotyping-basic /isaconfig-phenotyping-basic
COPY requirements.txt requirements.txt

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["python", "/brapi_to_isa.py"]
