#!/usr/bin/env bash
echo "..."
echo "If this doesn't find pip or python then you need to get them from https://www.python.org/downloads/"
echo "..."
echo "..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install required packages. Please check your Python and pip installation."
    echo "For some linux distributions you may need to install python3-pip and some development libraries."
    echo "For example, on Debian/Ubuntu you can run:"
    echo "1) For pip:"
    echo "sudo apt-get install python3-pip"
    echo "2) For development libraries:"
    echo "sudo apt-get install libgtk-3-dev libpython3-dev"
    echo "3) For more/faster functionality you may need to install additional libraries:"
    echo "sudo apt install libagg-dev libpotrace-dev cmake libeigen3-dev"
    exit 1
fi
read -p "Do you want to install optional (but helpful) packages (Y/N)? [N]: " choice
choice=${choice:0:1}
if [[ "$choice" == "Y" || "$choice" == "y" ]]; then
    pip3 install -r requirements-optional-linux.txt
    if [[ $? -ne 0 ]]; then
        echo "Warning: Optional package installation failed. Some features may not be available."
    fi
else
    echo "Okay, skip these for now"
fi

python3 meerk40t.py 2>/dev/null
read -p "Press enter to continue..."
