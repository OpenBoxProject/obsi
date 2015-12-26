#! /bin/bash
OBSI_DIR=$(pwd)
OPENBOX_CLICK_PACKAGE=$OBSI_DIR/openbox-click-package
BUILD_DIR="/tmp/build"
RE2_URL="https://github.com/google/re2.git"
RE2_TAG="2015-11-01"
CLICK_URL="https://github.com/kohler/click.git"
#CLICK_INSTALL_DIR=$HOME/click

function install_build_utils {
	apt-get update
	apt-get install build-essential python-dev g++ python-pip
}

function install_re2 {
	echo "[+] Clonning RE2"
	cd $BUILD_DIR
	git clone $RE2_URL
	cd re2
	git checkout $RE2_TAG
	echo "[+] Compiling RE2"
	make 
	echo "[+] Testing RE2"
	make test
	echo "[+] Installing RE2"
	make install 
	make testinstall
}

function install_click {
	echo "[+] Clonning Click"
	cd $BUILD_DIR
	git clone $CLICK_URL
	cd click
	echo "[+] Configuring Click"
 	./configure --disable-linuxmodule --disable-linux-symbols --disable-linuxmodule --disable-bsdmodule --enable-all-elements --enable-user-multithread --enable-stats=1 --enable-json --disable-test
	echo "[+] Compiling Click"
	make 
	echo "[+] Installing Click"
	make install	
}

function install_openbox_click_package {
	cd $OPENBOX_CLICK_PACKAGE
	echo "[+] Configuring OpenBox Click Package"
	autoconf 
	./configure
	echo "[+] Compiling OpenBox Click Package"
	make 
	echo "[+] Installing OpenBox Click Package"
	make install
}

function install_python_dependency {
	pip install tornado
	pip install psutil
}

install_build_utils
rm -rf $BUILD_DIR
mkdir $BUILD_DIR
install_click
install_re2
install_openbox_click_package
install_python_dependency