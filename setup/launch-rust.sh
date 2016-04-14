#!/bin/bash

tmux new -d -s sparkfun
# Start the Python side of things
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc/setup' c-m
tmux send-keys -t sparkfun 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3' c-m
tmux send-keys -t sparkfun 'source /usr/local/bin/virtualenvwrapper.sh' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun 'sudo ~pi/.virtualenvs/sparkfun/bin/python -m rust -w' c-m
# We need to wait a few seconds before starting the Rust program because it
# expects to open and read commands from some Unix domain sockets which the
# Python side creates.
sleep 20
tmux new-window -t sparkfun
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc/control-rust' c-m
tmux send-keys -t sparkfun 'if [ ! -f target/debug/control-rust ] ; then sudo ipe-rw ; cargo build ; sudo ipe-ro ; fi' c-m
tmux send-keys -t sparkfun 'target/debug/control-rust --max-throttle 0.25' c-m
