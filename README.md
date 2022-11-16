# Optra Edge Python Flask Demo Skill

This demo skill shows how to access the various parts of the Optra Edge device in a Python Flask environment.
- A web UI using Flask and Waitress
- Audio through the headphone jack and HDMI
- Video to the HDMI interface
- Video from cameras to HDMI using Gstreamer
- Handling of Inputs from the portal
- Handling of Outputs to the portal
- Video streaming using OpenCV for both RTSP and USB
- Haar Cascade Classifier on camera video
  
This skill requires the following Privileges:
- Sound
- Web UI
- HDMI
- USB Cameras

After selecting these privileges, the raw config will look like this:

    {
        "HostConfig": {
            "Binds": [
                "/etc/asound.conf:/etc/asound.conf:rw",
                "/tmp/.X11-unix:/tmp/.X11-unix:rw",
                "/dev:/dev:ro"
            ],
            "Devices": [
                {
                    "CgroupPermissions": "rwm",
                    "PathInContainer": "/dev/snd",
                    "PathOnHost": "/dev/snd"
                }
            ],
            "DeviceCgroupRules": [
                "c 81:* rmw"
            ],
            "PortBindings": {
                "7000/tcp": [
                    {
                        "HostPort": "<User Selected Port>"
                    }
                ]
            },
            "Mounts": []
        }
    }

This skill uses the following Environment Variables that are set in the skill on the Portal:
- TZ: set to the Olson timezone format (America/New_York)
- DISPLAY: for HDMI output set to :0 

Also, Inputs and Outputs must be setup in the skill on the Portal.

# Prerequisites

## Docker

**Windows** and **Mac**: We've tested this project with [Docker Desktop](https://www.docker.com/products/docker-desktop).

**Linux**: Follow the instructions [here](https://docs.docker.com/engine/install/ubuntu/).

Once you have docker installed, you can verify your installation by running docker <em>hello world</em>.

```> docker run hello-world```

<hr>

## Docker buildx

To build multi-architecture docker images (for example, those that can be run on ARM-based devices), you'll need docker buildx. Docker buildx is a CLI plugin that extends the docker command line to include the buildx option. The latest versions of Docker include buildx as standard.  It was previously introduced in Docker version 19.03 as an experimental feature.  Instructions for enabling are [here](https://github.com/docker/cli/tree/master/experimental).

You can verify you have buildx support by running this command:

```> docker buildx ```

Linux users will need to run the following each time they reboot (for an explanation of why read [this](https://www.docker.com/blog/multi-platform-docker-builds/)):

- ```> docker run --rm --privileged docker/binfmt:a7996909642ee92942dcd6cff44b9b95f08dad64```
---

## Build and run
<hr>

Create an ```env.sh``` (Mac/Linux) or ```env.bat``` (Windows) in the project directory. The contents of this file will set environment variables necessary for the build. Here is an example:

```
#!/bin/bash

# In order to push your skill to your container registry,
# you'll need to define the following variables.

export registry=mycontainerregistry.example.io
export registry_username=myregistryusername
export registry_password=myregistrypassword

# Here you can name your skill and provide it with a tag.
export skill_name=python-flask-demo-skill
export skill_tag=0.0.1
```

After you've verified your environment variables, you can run the build by running:

```>./docker-build.sh``` (Mac or Linux)

```> docker-build.bat``` (Windows)
