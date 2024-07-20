
<!-- apt install libmpg123-0:i386 -->

rm -rf ~/.wine
export WINEARCH=win32
export WINEPREFIX=~/.wine
<!-- winecfg (choose windows 7 and exit) -->
export WINEARCH=win32
winetricks gdiplus msxml3

Add a string entry under HKEY_LOCAL_MACHINE\Software\Wine\Ports with a key of COM10 and a value of /dev/ttyUSB0 (or /dev/ttyACM0 if it is the case) to access the arduino USB port from wine and then create the symlink for it. The former is saved in .wine/system.reg

<!-- wine regedit -->

wine regedit comport.reg

rm ~/.wine/dosdevices/com10
ln -s /dev/ttyUSB0 ~/.wine/dosdevices/com10

<!-- Add yourself to dialout group so you can access the USB port (if you're not already)
$ sudo usermod -a -G dialout $USER -->


wine install.exe
wine "C:Program Files/LaserGRBL/laserGRBL.exe"