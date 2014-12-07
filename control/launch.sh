#!/bin/bash

tmux new -d -s sparkfun
tmux send-keys -t sparkfun 'cd ~/sparkfun-avc/control' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun './rooter test.py' c-m
