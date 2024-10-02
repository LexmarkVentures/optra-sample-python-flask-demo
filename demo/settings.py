#!/usr/bin/env python3
""" Settings for Demo of Python Flask application for Optra Edge
"""
import os
import json
import time
import requests
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse
from usbcaminfo import UsbCameraInfo
from camera import Camera


# pylint: disable=too-many-instance-attributes
@dataclass
class Settings:
    """Settings data class for all pages"""
    #
    # General Settings
    #
    twin: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    env_vars: str = ""
    device_has_hdmi: bool = field(init=False)

    #
    # Audio Page
    #
    what_to_say: str = "We love using Python on Lexmark's Optra Edge!"
    WE_HOLD_THESE_TRUTHS: ClassVar[str] = (
        "We hold these truths to be self-evident, "
        "that all men are created equal, "
        "that they are endowed by their Creator with "
        "certain unalienable Rights, "
        "that among these are Life, Liberty and the pursuit of Happiness."
    )
    volume: int = -20
    VOLUME_MAX: ClassVar[int] = 0
    VOLUME_MIN: ClassVar[int] = -127
    voice: str = "English"
    VOICES: ClassVar[list] = [
        "English",
        "Filipino",
        "Hindi",
        "Italian",
        "Spanish",
        "French",
        "German",
        "Ukranian",
    ]
    VOICE_TO_LANG: ClassVar[dict] = {
        "English":  "en",
        "Filipino": "tl",
        "French":   "fr",
        "German":   "de",
        "Hindi":    "hi",
        "Ukranian": "uk",
        "Spanish":  "es",
        "Italian":  "it",
    }
    lang: str = "en"
    AUDIO_DEVICES_LIST: ClassVar[dict] = {
        "null":                            "null",
        "default":                         "default",
        "default:CARD=Card":               "default",
        "headphones":                      "Headphone Jack",
        "hdmi_output":                     "HDMI",
        "dmix:CARD=tegrahdaxnx,DEV=7":     "VZ5000 HDMI",
        "dmix:CARD=tegrahda,DEV=3":        "VZ1000 HDMI",
        "dmix:CARD=jetsonxaviernxa,DEV=0": "VZ5000 Headphone Jack",
        "dmix:CARD=tegrasndt210ref,DEV=0": "VZ1000 Headphone Jack",
    }
    audio_output_device: str = "default"
    audio_output: str = "default"
    audio_outputs: list = field(default_factory=list)
    audio_devices: dict = field(default_factory=dict)

    #
    # Video Page
    #
    audio_output_video_device: str = "default"
    audio_output_video: str = "default"

    #
    # Inputs Page
    #
    inputs_time: str = ""

    #
    # Outputs Page
    #
    output1: str = "Output1"
    output2: str = "Output2"
    outmsg: str = ""

    #
    # Camera Page
    #
    camera: Camera = Camera()
    camera_source: str = ""
    camera_info: dict = field(default_factory=dict)
    camera_added_info: dict = field(default_factory=dict)
    selected_camera: str = ""
    camera_list: list = field(default_factory=list)
    camera_added_list: list = field(default_factory=list)
    selected_classifier: str = "none"
    camera_resolution: str = "default"
    CAMERA_RESOLUTIONS: ClassVar[list] = [
        "default",
        "320x240", "640x480", "800x600", "1024x768", "1280x960",
        "352x240", "640x360", "1024x576", "1280x720", "1920x1080", "2688x1520",
    ]
    camera_compression: str = "default"
    CAMERA_COMPRESSIONS: ClassVar[list] = [
        "default",
        "0",
        "5",
        "10",
        "15",
        "20",
        "30",
        "40",
        "50",
        "75",
        "100",
    ]
    fps_value: str = "default"
    FPS_VALUES: ClassVar[list] = [
        "default",
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "10",
        "15",
        "20",
        "25",
        "30",
        "60",
    ]
    camera_change: bool = False
    video_frame = None
    usb_camera_info = UsbCameraInfo()
    usb_cameras = usb_camera_info.get_devices_list()
    usb_camera_pixel_format: str = ""
    usb_camera_resolution: str = ""
    usb_camera_frame_rate: str = ""

    #
    # Method that runs after all variables are initialized
    #
    def __post_init__(self):
        self.populate_audio_outputs()
        self.init_env_vars()
        self.device_has_hdmi = self.env['OPTRA_DEVICE_MODEL'][0] == 'v'
        self.set_volume(self.volume)

    #
    # Support methods
    #
    def populate_audio_outputs(self):
        """Populate audio outputs from aplay."""
        self.audio_outputs = []
        lines = os.popen("aplay -L", 'r', 1).readlines()
        for line in lines:
            for key, value in self.AUDIO_DEVICES_LIST.items():
                if line.strip() == key:
                    self.audio_outputs.append(value)
                    self.audio_devices[value] = key
                    break

    def init_env_vars(self):
        """Initialize env_vars from the environment variables."""
        for key, value in os.environ.items():
            self.env[key] = value
        oenv = OrderedDict(sorted(self.env.items()))
        self.env_vars = json.dumps(oenv, indent=4)

    def populate_attached_cameras(self):
        """Populate the attached cameras from the module twin."""
        self.camera_info = {}
        self.camera_list = []

        if self.usb_cameras:
            self.camera_list = self.usb_cameras.copy()

        for key, value in (self.twin["desired"]
                                    ["device"]
                                    ["sensors"].items()):
            self.camera_info[key] = {"name": value["name"],
                                     "ip":   value["ip"]}
            self.camera_list.append(value["name"])

        self.camera_info.update(self.camera_added_info)
        self.camera_list.extend(self.camera_added_list)

        if self.camera_list and self.selected_camera not in self.camera_list:
            self.selected_camera = self.camera_list[0]

    def add_rtsp_camera(self, name, url):
        """Add an RTSP camera to the camera list."""
        self.camera_added_info[str(time.time())] = {"name": name,
                                                    "ip": url}
        self.camera_added_list.append(name)
        self.selected_camera = name
        self.populate_attached_cameras()

    def usb_camera_width(self):
        """Return the usb camera width from usb_camera_resolution."""
        return UsbCameraInfo.width_from_resolution(self.usb_camera_resolution)

    def usb_camera_height(self):
        """Return the usb camera height from usb_camera_resolution."""
        return UsbCameraInfo.height_from_resolution(self.usb_camera_resolution)

    def usb_camera_fractional_frame_rate(self):
        """Return the usb camera frame rate as a fraction."""
        return UsbCameraInfo.fractional_frame_rate(self.usb_camera_frame_rate)

    def set_camera_source(self):
        """Set the camera url based on the selected camera."""
        if Camera.is_usb_cam(self.selected_camera):
            self.camera_source = self.selected_camera
            return

        for value in self.camera_info.values():
            if value["name"] == self.selected_camera:
                self.camera_source = value["ip"]
                if "axis-media" in self.camera_source:
                    separator = "?"
                    if self.camera_resolution != "default":
                        self.camera_source = (
                            self.camera_source
                            + separator
                            + "resolution="
                            + self.camera_resolution
                        )
                        separator = "&"
                    if self.camera_compression != "default":
                        self.camera_source = (
                            self.camera_source
                            + separator
                            + "compression="
                            + self.camera_compression
                        )
                        separator = "&"
                    if self.fps_value != "default":
                        self.camera_source = (
                            self.camera_source
                            + separator
                            + "fps="
                            + self.fps_value
                        )
                        separator = "&"
                break

    def set_volume(self, vol):
        """Set the volume of the headphone jack."""
        self.volume = vol
        resp = requests.put('http://172.18.0.1:8080/webservices/noauth/settings',
                            data='{"AudioVolume":' + str(vol) + '.0}',
                            timeout=(3,5))
        logging.info("Status: %s", resp.status_code)
        logging.info("Content: %s",  resp.text)

    def set_voice(self, value):
        """Set the voice for the gtts-cli program."""
        self.voice = value
        if value is None:
            self.lang = "en"
        else:
            self.lang = self.VOICE_TO_LANG[value]

    def get_camera_source_with_obscured_password(self):
        """Return the camera_source with the password obscured."""
        parts = urlparse(self.camera_source)
        if parts.password is not None:
            # split out the host portion manually. We could use
            # parts.hostname and parts.port, but then you'd have to check
            # if either part is None. The hostname would also be lowercased.
            host_info = parts.netloc.rpartition('@')[-1]
            parts = parts._replace(
                netloc=f"{parts.username}:XXXXXXXX@{host_info}"
            )
            return parts.geturl()

        return self.camera_source
