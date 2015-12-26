# OpenBox Service Instance

An OpenBox software-based service instance implementation. Since this project is under ongoing development, not all sources are available in this repository.

# Installation

Clone this repo (assuming it was cloned into the $HOME directory), run the following commands:
cd ~/obsi
sudo ./install.sh

Note: The installation script might prompt you to install additional packages.

# Running
(assuming it was cloned into the $HOME directory)
cd ~/obsi/openbox
vim config.py (and adjust any configuration parameters)
sudo python manager.py

If you want to run against a mock controller:
cd ~/obsi/tests
python mock_controller.py

# stopping
Just kill the process and the 2 subprocess it creates:
ps -fade | grep python 
sudo kill -9 <PID>
