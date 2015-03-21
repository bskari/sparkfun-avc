set -u
set -e
pushd ~pi
git clone https://github.com/bskari/dotfiles ~pi/.dotfiles
popd
pushd ~pi/.dotfiles
bash setup.sh
popd
