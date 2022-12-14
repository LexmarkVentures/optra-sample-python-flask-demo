# Optra Edge Python Flask Demo Skill 
#
# Base image is Nvidia's l4t-base:r32.5.0 to match current
# Optra Edge Vision firmware
FROM  petedavidson887/l4t-base:r32.5.0
LABEL maintainer "Pete Davidson <pete@lexmark.com>"

ENV DEBIAN_FRONTEND=noninteractive

# Install the apps we need
#   - Some useful tools
#   - python 3.8
#   - Flask and other Python modules
#   - Set root password to root
#   - Add user optra to audio and vidwo groups
RUN apt-get update \
 && apt-get install -y alsa-base \
                       alsa-utils \
                       alsa-tools \
                       mpg123 \
                       x11-apps \
                       xterm \
                       vim \
                       v4l-utils \
                       x11-xserver-utils \
 && apt-get install -y python3.8 \
 && ln -sf /usr/bin/python3.8 /usr/bin/python3 \
 && apt-get install -y python3.8-dev \
                       python3-pip \
                       python3-tk  \
 && python3 -m pip install -U pip setuptools \
 && pip3 install flask[async] \
                 waitress \
                 requests \
                 jsonmerge \
                 pathlib \
                 gTTS \
                 psutil \
                 azure-iot-device \
                 opencv-python \
 && echo "root:root" | chpasswd \
 && adduser --ingroup audio optra \
 && usermod -a -G video optra

# Copy over our application
COPY demo /demo

# Change ownership of /demo to user optra
RUN chown -R optra:video /demo

# Set user to optra
USER optra

# Set workdir to /demo
WORKDIR /demo

# Start it up calling demo.py
CMD ./demo.py

# Appliction UI on port 7000
EXPOSE  7000
