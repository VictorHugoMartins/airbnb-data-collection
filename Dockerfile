FROM python:3.8.10

WORKDIR app

COPY . /app

RUN apt-get update

RUN python -m pip install pip --upgrade
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
CMD ["bokeh", "serve", "--address", "0.0.0.0", "--port", "3000",  "--allow-websocket-origin=airbnbnbookingscrap.up.railway.app", "--use-xheaders", "dashboard.py"]
