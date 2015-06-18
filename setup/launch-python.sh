#!/bin/bash

tmux new -d -s sparkfun
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc/setup' c-m
tmux send-keys -t sparkfun 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3' c-m
tmux send-keys -t sparkfun 'source /usr/local/bin/virtualenvwrapper.sh' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc' c-m
tmux send-keys -t sparkfun 'sudo ~pi/.virtualenvs/sparkfun/bin/python -m main -l /tmp/out.log --max-throttle=0.5 -k ~/sparkfun-avc/paths/sparkfun-avc-2015.kmz' c-m
