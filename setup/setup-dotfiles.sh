set -u
set -e
pushd ~pi
git clone https://github.com/bskari/dotfiles .dotfiles
popd
pushd .dotfiles
bash setup.sh
popd
