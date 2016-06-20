# Team Mario Sparkfun AVC

This is my code for the Sparkfun AVC, starting from 2014. My entry consisted of
a Tamiya Grasshopper RC car with a Raspberry Pi 2 and a compass/GPS module. The
main code is written in Python; I found that the Python was too slow while
running on a Raspberry Pi A+, and so had started porting it to Rust, but after
the release of the Pi 2, I switched back to Python.

The setup code will set up the Pi to act as a WiFi access point. The code also
includes a remote monitor that runs as a web server. Any WiFi client can
connect to this server and view live telemetry data using WebSockets, as well
as start and stop the vehicle.

## Using the code

To get a full installation ready, including setting up the Pi to act as an
access point and starting the code on boot, download a copy of Minibian, copy
it to an SD card, install Git, clone this repo, and then run
[setup.sh](setup/setup.sh).

The main Python code is in the [control folder](control). To use
it in your own project, you will need to change the
[Driver](control/driver.py) class to control your specific
vehicle, and the [Telemetry](control/telemetry.py)
class to read data from your sensors. For simplicity, I tried to keep all
readings using meters so that I wouldn't need to convert latitude and
longitude, so my example class converts latitude and longitude readings to
distance from a centrally chosen waypoint.

The monitoring code is in the [monitor folder](monitor). It uses
CherryPy to run as a webserver by default on port 8080. You will need to write
a Python class that reads and sends some telemetry to the monitor periodically.
My example is in [TelemetryDumper](control/telemetry_dumper.py).

The file [main](main.py) is used to start all the various parts
of the code and link them all together. It's a good example if you want to just
use some parts.

There is also an incomplete but still in progress [Rust
port](../../tree/rust/). The development of that port is in the
branch named *rust*.
