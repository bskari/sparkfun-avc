set -u
set -e
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
pip-3.2 install virtualenvwrapper
pushd ~pi/sparkfun-avc/setup
sudo -u pi bash setup-virtualenv-2.sh
popd
