#!/usr/bin/bash

rm -rf ~/.wine
export WINEPREFIX=~/.wine
winecfg /v win7
wine regedit comport.reg
wine ~/LightBurn-v1.7.06.exe
