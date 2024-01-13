#!/bin/sh


redis-server --protected-mode no & #Start redis here

while true
do
    redis-cli SET "FLAG" "FLAG-B4d_php_15_3v3RywH3R3"
    exit_status=$?
    if [ $exit_status -eq 0 ]; then
        echo "Flag is set."
        break
    fi
    sleep 2
done
wait