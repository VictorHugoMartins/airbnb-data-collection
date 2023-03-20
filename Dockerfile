FROM continuumio/miniconda3:4.5.4

COPY ./*.py .
COPY ./docker/requirements.txt ./

RUN apt-get update

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
