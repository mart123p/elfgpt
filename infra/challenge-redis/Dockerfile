FROM alpine:3.19
RUN apk --update --no-cache add \
    redis

COPY launch.sh /
RUN chmod +x /launch.sh

EXPOSE 6379
ENTRYPOINT ["/launch.sh"]