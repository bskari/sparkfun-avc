#!/bin/bash
set -u
set -e

if [ -f location-test-private-key.pem ];
then
    echo 'Already created'
    exit 1
fi
openssl genrsa -out location-test-private-key.pem 1024
openssl req -new -key location-test-private-key.pem -out location-test-cert-req.csr
openssl x509 -req -days 3650 -in location-test-cert-req.csr -signkey location-test-private-key.pem -out location-test-new-certificate.pem
