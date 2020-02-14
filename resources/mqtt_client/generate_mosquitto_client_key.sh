#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: generate_mosquitto_client_key.sh client_name"
    exit 1
fi

openssl genrsa -des3 -out $1.key 2048
openssl req -out $1.csr -key $1.key -new
openssl x509 -req -in $1.csr -CA mosquitto_ca.crt -CAkey mosquitto_ca.key -CAcreateserial -out $1.crt -days 3650

