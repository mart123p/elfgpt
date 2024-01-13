FROM python:3.9-slim-buster
WORKDIR /app
COPY ./server/requirements.txt /app
RUN pip install -r requirements.txt && useradd -u 1000 app-user

COPY ./server/ .

RUN chown -R app-user:app-user /app/
USER app-user
CMD ["celery", "--app", "workers.common.conf.celery", "beat", "--loglevel=info"]