FROM python:3.6.1

#RUN git clone https://github.com/ISA-tools/isa-api && pip install ./isa-api
RUN pip install isatools requests

COPY *.py /

CMD ["python","/brapi_to_isa.py"]
