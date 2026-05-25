cd /workspace
git clone https://github.com/stamatak/standard-RAxML.git
cd standard-RAxML
make -f Makefile.gcc
rm *.o
make -f Makefile.SSE3.gcc
rm *.o
cd ..
wget https://github.com/iqtree/iqtree3/releases/download/v3.1.2/iqtree-3.1.2-Linux.tar.gz
tar -xzf iqtree-3.1.2-Linux.tar.gz