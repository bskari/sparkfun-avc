#!/bin/bash

tmux new -d -s sparkfun
tmux send-keys -t sparkfun 'cd ~/sparkfun-avc/setup' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun './rooter ~/sparkfun-avc/control/test.py' c-m
