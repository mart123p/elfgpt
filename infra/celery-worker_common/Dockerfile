FROM python:3.9-slim-buster
WORKDIR /app
COPY ./server/requirements.txt /app
RUN pip install -r requirements.txt

COPY ./server/ .

RUN pip install docker==7.0.0
# We run this container as root because of the docker socket
CMD ["celery", "--app", "workers.general.celery", "worker", "--loglevel=info", "-c", "2", "-Q", "common"]
