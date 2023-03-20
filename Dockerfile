FROM python:3.11.1

WORKDIR app

COPY . /app

RUN apt-get update

RUN python -m pip install pip --upgrade
RUN pip install --upgrade pip
RUN pip install -r requirements.txt