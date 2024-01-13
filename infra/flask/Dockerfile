FROM node:18 as build
WORKDIR /workdir
COPY ./clientapp/ /workdir
RUN npm install && npm run build

FROM python:3.9-slim-buster
WORKDIR /app
COPY ./server/requirements.txt /app
RUN pip install -r requirements.txt && \
    useradd -u 1000 app-user

COPY ./server/ .

COPY --from=build /workdir/dist/elfgpt /app/static
RUN chown -R app-user:app-user /app/

USER app-user
EXPOSE 5000
ENV FLASK_APP=app.py

CMD ["flask", "run", "--host", "0.0.0.0"]