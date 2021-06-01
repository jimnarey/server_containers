# Docker Wine App Template

## Notes

* Based on base-ubuntu-gui

* Installs 32bit (x86) architecture into Ubuntu

* Installs wine and winetricks

* Huge. Changing '--install-recommends' to '--no-install-recommends' in both the apt-get calls causes things to break. Need to isolate the problem and try to slim down the image. NB. images doing the same thing on Docker Hub are a similar size so there may not be much which can be done. 

* This method of installing wine requires the x86 arch. If the lines installing it in the Dockerfile are removed the install throws an error. Some adaptation or a different approach needed to get an x64 only (and hopefully smaller) ubuntu/wine/etc setup.

