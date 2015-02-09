#!/bin/bash
set -u
set -e

pushd /home/pi

rust_file="$(
    curl -s https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa | \
    grep -P -o '([A-Za-z0-9_]+/){2}rust-201\d-\d\d-\d\d-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz' | \
    sort -n | \
    tail -n 1
)"
url="https://www.dropbox.com/sh/${rust_file}?dl=1"
echo "Downloading $url"
wget "${url}" -O rust.tar.gz
mkdir rust
mv rust.tar.gz rust
pushd rust
tar -xvzf rust.tar.gz --exclude=doc
rm rust.tar.gz
popd

cargo_file="$(
    curl -s https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa | \
    grep -P -o '([A-Za-z0-9_]+/){2}cargo-201\d-\d\d-\d\d-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz' | \
    sort -n | \
    tail -n 1
)"
url="https://www.dropbox.com/sh/${cargo_file}?dl=1"
echo "Downloading $url"
wget "${url}" -O cargo.tar.gz
mkdir cargo
mv cargo.tar.gz cargo
pushd cargo
tar -xvzf cargo.tar.gz --exclude=doc
rm cargo.tar.gz
popd

set +e
grep -q rust /home/pi/.bashrc
if [ "$?" -ne 0 ];
then
    'Adding rust and cargo to PATH'
    echo 'PATH="${PATH}:/home/pi/rust/bin:/home/pi/cargo/bin' >> /home/pi/.bashrc
fi

popd
