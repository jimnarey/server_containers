#!/usr/bin/bash

rm -rf ~/.wine
export WINEARCH=win32
export WINEPREFIX=~/.wine
winecfg /v win7
winetricks gdiplus msxml3
wine ~/install.exe
