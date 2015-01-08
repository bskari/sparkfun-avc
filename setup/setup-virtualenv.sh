set -u
set -e
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
pip-3.2 install virtualenvwrapper
pushd ~pi/sparkfun-avc/control
su -c "export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3;
	source /usr/local/bin/virtualenvwrapper.sh;
	mkvirtualenv sparkfun -p /usr/bin/python3;
	workon sparkfun;
	pip install -r requirements.txt;
	deactivate;
"
popd
pushd ~pi/sparkfun-avc/setup
make rooter
chown root:root rooter
chmod +s rooter
popd
