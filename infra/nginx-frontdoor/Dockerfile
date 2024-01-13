FROM nginx:stable-alpine3.17

RUN apk --update --no-cache add \
    apache2-utils

COPY generate.sh /docker-entrypoint.d/11-generate.sh
RUN chmod +x /docker-entrypoint.d/11-generate.sh
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8000
