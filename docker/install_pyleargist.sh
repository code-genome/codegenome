#install pyleargist
apt-get install -y \
  git \
  python3-dev \
  libfftw3-dev ; \
  git clone https://github.com/vertexcover-io/pyleargist.git; \
  cd pyleargist; \
  pip3 install . ;\
  apt-get remove -y \
  libfftw3-dev; \
  cd .. ;\
  rm -rf pyleargist