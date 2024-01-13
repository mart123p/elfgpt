#!/bin/sh
htpasswd -bc  /etc/nginx/.htpasswd proxy ${NGINX_PROXY_PASSWORD}