#!/bin/sh
TAG=$1
RELEASE=$2
set -x

# location of your git repo
GITSRC=$WORKSPACE
SANDBOX=$WORKSPACE/sandbox
DEBIAN_REPO=/var/www/deb-repos

# select the galicaster version and the branch tag you want to checkout 
CLOG=$GITSRC/debian/changelog
ver=$(head -n1 $CLOG | grep -o "[0-9]*\.[0-9]*\.[0-9]*")
ds_ver=$(head -n1 $CLOG | grep -o "[0-9]*\.[0-9]*\.[0-9]*-uom[0-9]*")

# create a location for the deb build
rm -rf $SANDBOX/galicaster
mkdir -p $SANDBOX/galicaster

# get a clean copy of the code
cd ${GITSRC}
rm $SANDBOX/galicaster_${ver}.orig.*
git archive $TAG --format=tar --output=$SANDBOX/galicaster_${ver}.orig.tar
gzip $SANDBOX/galicaster_${ver}.orig.tar
cd $SANDBOX/galicaster

# unpack galicaster tarball to sandbox/galicaster
tar zxvf $SANDBOX/galicaster_${ver}.orig.tar.gz

# Build the package
dpkg-buildpackage -d

# update the repo
sudo cp $SANDBOX/galicaster_${ds_ver}_all.deb $DEBIAN_REPO/$RELEASE/all
cd $DEBIAN_REPO/$RELEASE
sudo sh -c 'dpkg-scanpackages all > all/Packages.gz'
