FROM debian:12
RUN apt-get update && apt-get install -y php-cli netcat-traditional \
    && mkdir -p /var/www/html \
    && rm -rf /var/lib/apt/lists/*

COPY files/ /var/www/html
COPY launch.sh /
RUN chmod 777 /var/www/html/access.log \
    && echo "FLAG-7r4D1710N4L_53CUR17y_15_571LL_4_7h1N6:x:1337:1337:FLAG-7r4D1710N4L_53CUR17y_15_571LL_4_7h1N6:/dev/null:/sbin/nologin" >> /etc/passwd \
    && chmod +x /launch.sh
EXPOSE 9000

ENTRYPOINT ["/launch.sh"]