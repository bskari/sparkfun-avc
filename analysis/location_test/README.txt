Runs a simple HTTPS server that connected clients connect to and log geolocation
data back. For determining feasability of using multiple smart phones for GPS.

Usage:
    bash keys.sh
    python cherry.py
    Connect phone to https://<server-ip>:4443
    Wait for data to collect
    python format.py
    Open resulting out.kml in Google Maps
