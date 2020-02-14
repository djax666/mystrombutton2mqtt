#!/bin/bash

openssl genrsa -des3 -out mosquitto_server.key 2048
openssl req -out mosquitto_server.csr -key mosquitto_server.key -new
openssl x509 -req -in mosquitto_server.csr -CA mosquitto_ca.crt -CAkey mosquitto_ca.key -CAcreateserial -out mosquitto_server.crt -days 3650


