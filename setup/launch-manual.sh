#!/bin/bash

tmux new -d -s sparkfun
# Start the GPS daemon
tmux send-keys -t sparkfun 'sudo killall gpsd' c-m
tmux send-keys -t sparkfun 'sudo gpsd /dev/ttyAMA0 -F /var/run/gpsd.sock' c-m
# Start up the manual control
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc/setup' c-m
tmux send-keys -t sparkfun 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3' c-m
tmux send-keys -t sparkfun 'source /usr/local/bin/virtualenvwrapper.sh' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun 'sudo ~pi/.virtualenvs/sparkfun/bin/python -m control.manual' c-m
