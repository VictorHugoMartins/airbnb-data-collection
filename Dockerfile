FROM continuumio/miniconda3:4.5.4

RUN apt-get update

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
