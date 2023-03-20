FROM continuumio/miniconda3:4.5.4

WORKDIR app

COPY . /app

RUN apt-get update

RUN pip install --upgrade pip
RUN pip install -r app/requirements.txt