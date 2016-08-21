#!/bin/bash
set -u
set -e

if [ -f key.pem ];
then
    echo 'Already created'
    exit 1
fi
yes '' | openssl genrsa -out key.pem 1024
yes '' | openssl req -new -key key.pem -out req.csr
yes '' | openssl x509 -req -days 3650 -in req.csr -signkey key.pem -out cert.pem 
rm req.csr
