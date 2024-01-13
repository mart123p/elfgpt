#!/bin/sh
/usr/bin/htpasswd -bc  /etc/nginx/.htpasswd montrehack ${NGINX_FRONTDOOR_PASSWORD}