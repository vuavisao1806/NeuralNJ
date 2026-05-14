conda env create -f environment.yaml
conda activate NeuralNJ
cd RAxMLpy
sudo apt install build-essential cmake
sudo apt-get install autoconf automake libtool
sudo apt-get install libgmp3-dev libhts-dev libhtscodecs-dev
sudo apt install bison flex
pip install pybind11
python setup.py build
python setup.py install
export LD_LIBRARY_PATH="$(pwd)/build_plllib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH="$(pwd)/build_raxmllib:$LD_LIBRARY_PATH"
cd test
python test_raxmlpy.py
cd ..
cd ..