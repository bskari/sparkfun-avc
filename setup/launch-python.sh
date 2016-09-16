#!/bin/bash

tmux new -d -s sparkfun
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc/setup' c-m
tmux send-keys -t sparkfun 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3' c-m
tmux send-keys -t sparkfun 'source /usr/local/bin/virtualenvwrapper.sh' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun 'cp -R ~pi/sparkfun-avc /tmp' c-m
tmux send-keys -t sparkfun 'cd /tmp/sparkfun-avc' c-m
tmux send-keys -t sparkfun 'sudo ~pi/.virtualenvs/sparkfun/bin/python -m setup.set_time' c-m
tmux send-keys -t sparkfun 'sudo ~pi/.virtualenvs/sparkfun/bin/python -m main --max-throttle=0.5 -k sparkfun-avc-2016.kml' c-m
