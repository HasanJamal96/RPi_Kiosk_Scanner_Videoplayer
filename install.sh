#/bin/bash

sudo apt-get update
sudo apt install -y libdbus-glib-1-dev dbus libdbus-1-dev
sudo apt-get install -y fbi
pip install omxplayer-wrapper pathlib evdev
sudo pip install omxplayer-wrapper pathlib evdev
sudo cp ./pikiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start pikiosk.service
sudo systemctl enable pikiosk.service
