#! /bin/bash
OBSI_DIR="~/obsi"
BUILD_DIR="/tmp/build"
RE2_URL="https://github.com/google/re2.git"
RE2_TAG="2015-11-01"

function install_re2 {
	echo "[+] Clonning RE2"
	cd $BUILD_DIR
	git clone $RE2_URL
	cd re2
	git checkout $RE2_TAG
	echo "[+] Installing RE2"
	make 
	make test
	make install 
	make testinstall
}

rm -rf $BUILD_DIR
mkdir $BUILD_DIR
install_re2