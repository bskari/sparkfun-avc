pushd ~pi/sparkfun-avc
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv sparkfun -p /usr/bin/python3
workon sparkfun
pip install -r requirements.txt
pip install git+git://github.com/bskari/RPIO#egg=RPIO
deactivate
popd
