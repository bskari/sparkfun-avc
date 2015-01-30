rust_file="$(curl -s https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa | grep -P -o 'rust-201\d-\d\d-\d\d-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz' | sort -n | tail -n 1)"
wget "https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa/$(rust_file)" -o rust.tar.gz
tar -xvzf rust.tar.gz
rm rust.tar.gz
mv rust* rust

cargo_file="$(curl -s https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa | grep -P -o 'cargo-201\d-\d\d-\d\d-[a-f0-9]+-arm-unknown-linux-gnueabihf-[a-f0-9]+.tar.gz' | sort -n | tail -n 1)"
wget "https://www.dropbox.com/sh/qfbt03ys2qkhsxs/AACxFoD1OrxDXURzj5wX0IYUa/$(cargo_file)" -o cargo.tar.gz
tar -xvzf cargo.tar.gz
rm cargo.tar.gz
mv cargo* cargo

grep -q rust /home/pi/.bashrc
if [ "$?" -ne 0 ];
then
    'Adding rust and cargo to PATH'
    echo 'PATH="${PATH}:/home/pi/rust/bin:/home/pi/cargo/bin' >> /home/pi/.bashrc
fi
