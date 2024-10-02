#!/usr/bin/env python3
"""Python Flask application for Optra Edge Python Skill Demo"""
import os
from time import sleep
import asyncio
import json
import subprocess
from datetime import datetime
from logging.config import dictConfig
from flask import Flask, redirect, url_for, request, render_template, Response
from flask.logging import create_logger
import requests
import urllib3
import psutil
from version import __version__
from azure_iot import get_twin, send_outputs
from camera import Camera
from settings import Settings


app = Flask(__name__)


def gen(camera):
    """Video streaming generator function."""

    # Start the frame capture
    settings.camera.start(
        settings.camera_source,
        settings.usb_camera_pixel_format,
        settings.usb_camera_resolution,
        settings.usb_camera_frame_rate,
        settings.selected_classifier
    )

    try:
        yield b'--frame\r\n'
        while True:
            frame = camera.get_frame()
            yield (
                b'Content-Type: image/jpeg\r\n\r\n'
                + frame
                + b'\r\n--frame\r\n'
            )
    finally:
        app.logger.info("Video stream disconnected")


def say_it(statement):
    """Say the statement on the selected audio device."""
    os.system(
        "gtts-cli \""
        + statement
        + "\" --lang "
        + settings.lang
        + " | mpg123 -a "
        + settings.audio_output_device
        + " - &"
    )


def play_it(file):
    """Play the file on HDMI and selected audio device."""
    os.system(
        "mpg123 -a "
        + settings.audio_output_device
        + " "
        + file
        + " &"
    )


def stop_all_videos():
    """Stop all the playing videos."""
    for proc in psutil.process_iter():
        if proc.name() == "cmdloop" or proc.name() == "gst-launch-1.0":
            app.logger.info("Killing %s", str(proc.pid))
            os.system("kill " + str(proc.pid))


def make_tree(path):
    """Create tree of file system."""
    tree = dict(name=os.path.basename(path), children=[])
    try:
        lst = os.listdir(path)
    except OSError:
        pass #ignore errors
    else:
        for name in lst:
            full_path_name = os.path.join(path, name)
            if os.path.isdir(full_path_name):
                tree['children'].append(make_tree(full_path_name))
            else:
                tree['children'].append(dict(name=name))
    return tree


@app.before_request
def before_request_callback():
    """Runs before a request."""
    app.logger.info("Before request: %s %s", request.method, request.path)

    # If we received a GET for any path other than /video_feed,
    # /catpure_image, or any /static path, then we need
    # to stop the video capture
    if (
        request.method == "GET"
        and request.path != "/video_feed"
        and request.path != "/capture_image"
        and request.path[0:7] != "/static"
    ):
        settings.camera.stop()


@app.after_request
def after_request_callback(response):
    """Runs after a request."""
    app.logger.info("After request: %s %s", request.method, request.path)
    return response


###########################
#
# Home Page
#
###########################
@app.route('/')
def index():
    """Render the home page."""
    return render_template("index.html",
                           envvars=settings.env_vars)


###########################
#
# Audio Page
#
###########################
@app.route('/audio', methods=['GET', 'POST'])
def audio():
    """Render the audio page."""
    if request.method == 'POST':
        settings.what_to_say = request.form.get('whattosay')
        say_it(settings.what_to_say)
        return redirect(url_for('audio'))

    return render_template("audio.html",
                           whattosay=settings.what_to_say,
                           min=settings.VOLUME_MIN,
                           max=settings.VOLUME_MAX,
                           volume=settings.volume,
                           voice=settings.voice,
                           voices=settings.VOICES,
                           audioOutput=settings.audio_output,
                           audioOutputs=settings.audio_outputs)


#
# Declaration
#
@app.route('/declaration')
def declaration():
    """Say the Declaration."""
    say_it(settings.WE_HOLD_THESE_TRUTHS)
    return redirect(url_for('audio'))


#
# Bach
#
@app.route('/bach')
def bach():
    """Play Bach."""
    play_it("audio/BWV1068.mp3")
    return redirect(url_for('audio'))


#
# Vivaldi
#
@app.route('/vivaldi')
def vivaldi():
    """Play Vivaldi"""
    play_it("audio/Vivaldi.mp3")
    return redirect(url_for('audio'))


#
# Volume
#
@app.route('/change_volume/<return_to>', methods=['POST'])
def change_volume(return_to):
    """Change the volume of the headphone jack."""
    settings.set_volume(request.form.get('volume'))
    return redirect(url_for(return_to))


#
# Audio Output
#
@app.route('/change_audio_output/<return_to>', methods=['POST'])
def change_audio_output(return_to):
    """Change the audio output device."""
    if return_to == "audio":
        settings.audio_output = request.form.get('audioOutput')
        for key, value in settings.audio_devices.items():
            if key == settings.audio_output:
                settings.audio_output_device = value
                break
    else:
        settings.audio_output_video = request.form.get('audioOutput')
        for key, value in settings.audio_devices.items():
            if key == settings.audio_output_video:
                settings.audio_output_video_device = value
                break
    return redirect(url_for(return_to))


#
# Voice
#
@app.route('/change_voice', methods=['POST'])
def change_voice():
    """Change the voice."""
    settings.set_voice(request.form.get('voice'))
    return redirect(url_for('audio'))


#
# Stop Audio
#
@app.route('/stopaudio')
def stopaudio():
    """Stop the audio"""
    for proc in psutil.process_iter():
        if proc.name() == "mpg123" or proc.name() == "gtts-cli":
            os.system("kill " + str(proc.pid))
    return redirect(url_for('audio'))


###########################
#
# Video Page
#
###########################
@app.route('/video')
def video():
    """Render the Video page."""
    if settings.device_has_hdmi:
        warning = ""
    else:
        warning = ("Warning: This device ("
                   + settings.env['OPTRA_DEVICE_MODEL']
                   + ") does not have HDMI hardware.")
    return render_template("video.html",
                           min=settings.VOLUME_MIN,
                           max=settings.VOLUME_MAX,
                           volume=settings.volume,
                           audioOutput=settings.audio_output_video,
                           audioOutputs=settings.audio_outputs,
                           warning=warning)


#
# Run xclock
#
@app.route('/xclock')
def xclock():
    """Display xclock on HDMI."""
    # Hide the mouse pointer
    os.system("xsetroot -cursor blank_pointer.xbm blank_pointer.xbm")
    os.system("xclock -bg grey &")
    return redirect(url_for('video'))


#
# Run xlogo
#
@app.route('/xlogo')
def xlogo():
    """Display xlogo on HDMI."""
    # Hide the mouse pointer
    os.system("xsetroot -cursor blank_pointer.xbm blank_pointer.xbm")
    os.system("xlogo -bg forestgreen -fg limegreen &")
    return redirect(url_for('video'))


#
# Run xterm
#
@app.route('/xterm')
def xterm():
    """Display xterm on HDMI."""
    # Hide the mouse pointer
    os.system("xsetroot -cursor blank_pointer.xbm blank_pointer.xbm")
    os.system("xterm -fa default -rv -fs 32 -e top -c &")
    return redirect(url_for('video'))


#
# Play video
#
@app.route('/playvideo')
def playvideo():
    """Play a video on HDMI."""
    stop_all_videos()

    # Hide the mouse pointer
    os.system("xsetroot -cursor blank_pointer.xbm blank_pointer.xbm")

    videofile = request.args.get('videofile', default='earth.mp4')
    stream = request.args.get('stream')
    if stream is None or stream=="":
        uri = "file:///demo/video/" + videofile
    else:
        uri = stream
    """
    command = (
        "gst-launch-1.0 filesrc"
            + " location=/demo/video/"
            + videofile
            + " ! qtdemux name=demux"
            + " demux.audio_0"
                + " ! queue"
                + " ! decodebin"
                + " ! audioconvert"
                + " ! audioresample"
                + " ! alsasink device=" + settings.audio_output_video_device
            + " demux.video_0"
                + " ! queue"
                + " ! decodebin"
                + " ! videoconvert"
                + " ! videoscale"
                + " ! autovideosink"
    )
    """
    command = (
        "gst-launch-1.0 playbin3"
            + " uri="
            + uri
            + " audio-sink=\"alsasink device=" + settings.audio_output_video_device + "\""
    )

    app.logger.info(command)
    os.system("/demo/cmdloop '" + command + "' &")
    return redirect(url_for('video'))


#
# Play camera
#
@app.route('/playcamera')
def playcamera():
    """Play selected camera on HDMI."""

    # Check for a slected camera
    if not settings.camera_source:
        app.logger.info("No camera selected")
        return redirect(url_for('cameras'))

    stop_all_videos()

    # Hide the mouse pointer
    os.system("xsetroot -cursor blank_pointer.xbm blank_pointer.xbm")

    if Camera.is_usb_cam(settings.selected_camera):

        #
        # USB Cameras
        #
        width = settings.usb_camera_width()
        height = settings.usb_camera_height()
        pixel_format = settings.usb_camera_pixel_format

        # Set the Frame Rate as a fraction for gstreamer
        frame_rate = settings.usb_camera_fractional_frame_rate()

        # Fix pixel_format for gstreamer (YUYV == YUY2)
        if pixel_format == "YUYV":
            pixel_format = "YUY2"

        if settings.usb_camera_pixel_format == "MJPG":
            capture_type = "image/jpeg"
            decoding = " ! nvjpegdec ! 'video/x-raw'"
        else:
            capture_type = "video/x-raw"
            decoding = ""

        command = (
            "gst-launch-1.0 v4l2src"
                + " device='" + settings.camera_source + "'"
                + " ! '" + capture_type
                    + ", width=" + width
                    + ", height=" + height
                    + ", framerate=" + frame_rate
                    + ", format=" + pixel_format + "'"
                + decoding
                + " ! nvvidconv"
                + " ! 'video/x-raw(memory:NVMM), format=NV12'"
                + " ! autovideosink"
        )

    else:

        #
        # RTSP Cameras
        #
        command = (
            "gst-launch-1.0 rtspsrc "
                + "location='" + settings.camera_source + "'"
                + " ! decodebin"
                + " ! autovideosink"
        )

    app.logger.info(command)
    os.system(command + " &")
    return redirect(url_for('video'))


#
# Stop X apps
#
@app.route('/stopx')
def stopx():
    """Stop all X Apps."""
    for proc in psutil.process_iter():
        if proc.name() == "xclock" or \
           proc.name() == "xlogo" or \
           proc.name() == "xterm":
            os.system("kill " + str(proc.pid))

    # Bring back the mouse pointer
    os.system("xsetroot -cursor_name left_ptr")
    return redirect(url_for('video'))


#
# Stop video
#
@app.route('/stopvideo')
def stopvideo():
    """Stop all videos"""
    stop_all_videos()

    # Bring back the mouse pointer
    os.system("xsetroot -cursor_name left_ptr")
    return redirect(url_for('video'))


###########################
#
# Inputs Page
#
###########################
@app.route('/inputs', methods=['GET', 'POST'])
async def inputs():
    """Render the Inputs page."""
    if request.method == 'POST':
        settings.twin = await get_twin()
        settings.inputs_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        settings.populate_attached_cameras()
        return redirect(url_for('inputs'))

    inputs_list = json.dumps(settings.twin["desired"]["inputs"], indent=4)
    full_twin = json.dumps(settings.twin, indent=4)
    return render_template("inputs.html",
                           inputs=inputs_list,
                           inputsTime=settings.inputs_time,
                           fullTwin=full_twin)


###########################
#
# Outputs Page
#
###########################
@app.route('/outputs', methods=['GET', 'POST'])
async def outputs():
    """Render the Optputs page."""
    if request.method == 'POST':
        settings.output1 = request.form.get('output1')
        settings.output2 = request.form.get('output2')
        msg = {}
        msg["output1"] = settings.output1
        msg["output2"] = settings.output2
        sent = await send_outputs(msg)
        settings.outmsg = ("Sent:\n"
                           + json.dumps(sent, indent=4)
                           + "\n\n"
                           + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        return redirect(url_for('outputs'))

    return render_template("outputs.html",
                           output1=settings.output1,
                           output2=settings.output2,
                           outmsg=settings.outmsg)


###########################
#
# Cameras Page
#
###########################
@app.route('/cameras')
def cameras():
    """Render the Cameras page."""

    settings.set_camera_source()
    camera_source = settings.get_camera_source_with_obscured_password()
    app.logger.info("Camera source is: %s", settings.camera_source)
    classifier_list = ["none"] + Camera.available_classifiers()
    pixel_formats = []
    usb_camera_resolutions = []
    usb_camera_frame_rates = []

    pixel_formats = (
        settings.usb_camera_info.get_format_list(
            settings.selected_camera
        )
    )
    if pixel_formats:
        if settings.usb_camera_pixel_format not in pixel_formats:
            settings.usb_camera_pixel_format = pixel_formats[0]
        usb_camera_resolutions = (
            settings.usb_camera_info.get_resolution_list(
                settings.selected_camera,
                settings.usb_camera_pixel_format
            )
        )
        if usb_camera_resolutions:
            if settings.usb_camera_resolution not in usb_camera_resolutions:
                settings.usb_camera_resolution = usb_camera_resolutions[0]
            usb_camera_frame_rates = (
                settings.usb_camera_info.get_fps_list(
                    settings.selected_camera,
                    settings.usb_camera_pixel_format,
                    settings.usb_camera_resolution
                )
            )
        else:
            settings.usb_camera_resolution = ""

    if usb_camera_frame_rates:
        if settings.usb_camera_frame_rate not in usb_camera_frame_rates:
            settings.usb_camera_frame_rate = usb_camera_frame_rates[0]
    else:
        settings.usb_camera_frame_rate = ""

    return render_template(
        "cameras.html",
        cameraSource=camera_source,
        cameraList=settings.camera_list,
        selectedCamera=settings.selected_camera,
        classifierList=classifier_list,
        selectedClassifier=settings.selected_classifier,
        cameraResolutions=settings.CAMERA_RESOLUTIONS,
        cameraResolution=settings.camera_resolution,
        cameraCompressions=settings.CAMERA_COMPRESSIONS,
        cameraCompression=settings.camera_compression,
        fpsValues=settings.FPS_VALUES,
        fpsValue=settings.fps_value,
        pixelFormats=pixel_formats,
        pixelFormat=settings.usb_camera_pixel_format,
        usbCameraResolutions=usb_camera_resolutions,
        usbCameraResolution=settings.usb_camera_resolution,
        usbCameraFrameRates=usb_camera_frame_rates,
        usbCameraFrameRate=settings.usb_camera_frame_rate,
        cameraType=Camera.camera_type(settings.camera_source)
    )


#
# Change Camera
#
@app.route('/change_camera', methods=['POST'])
def change_camera():
    """Change the selected camera."""
    settings.selected_camera = request.form.get('selectedCamera')
    settings.camera_change = True
    settings.set_camera_source()
    app.logger.info("Camera source is: %s", settings.camera_source)
    app.logger.info("%s %s %s %s",
                    settings.selected_camera,
                    settings.camera_resolution,
                    settings.camera_compression,
                    settings.fps_value)
    return redirect(url_for('cameras'))


#
# Refresh USB Cameras
#
@app.route('/refresh_usb_cameras', methods=['GET'])
def refresh_usb_cameras():
    """Refresh list of USB cameras.."""
    usb_camera_info_str = json.dumps(
        settings.usb_camera_info.refresh(),
        indent=4
    )
    settings.usb_cameras = settings.usb_camera_info.get_devices_list()
    settings.populate_attached_cameras()
    return render_template("refusbcam.html",
                           list=usb_camera_info_str)


#
# Add RTSP Camera
#
@app.route('/add_rtsp_camera', methods=['GET', 'POST'])
async def add_rtsp_camera():
    """Render the add rtsp camera page."""
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        app.logger.info(name)
        app.logger.info(url)
        settings.add_rtsp_camera(name, url)
        return redirect(url_for('cameras'))

    return render_template("addcam.html",
                           name="",
                           url="")


#
# Change Classifier
#
@app.route('/change_classifier', methods=['POST'])
def change_classifier():
    """Change the selected classifier."""
    settings.selected_classifier = request.form.get('selectedClassifier')
    return redirect(url_for('cameras'))


#
# Change USB CameraPixel Format
#
@app.route('/change_pixel_format', methods=['POST'])
def change_pixel_format():
    """Change the selected camera's attributes."""
    settings.usb_camera_pixel_format = request.form.get('pixelFormat')
    app.logger.info(
        "USB Camera Pixel Format is: %s",
        settings.usb_camera_pixel_format
    )
    return redirect(url_for('cameras'))


#
# Change USB Camera Resolution
#
@app.route('/change_usb_camera_resolution', methods=['POST'])
def change_usb_camera_resolution():
    """Change the selected camera's attributes."""
    settings.usb_camera_resolution = request.form.get('usbCameraResolution')
    app.logger.info(
        "USB Camera Resolution is: %s",
        settings.usb_camera_resolution
    )
    return redirect(url_for('cameras'))


#
# Change USB Camera Frame Rates
#
@app.route('/change_usb_camera_frame_rate', methods=['POST'])
def change_usb_camera_frame_rate():
    """Change the selected camera's attributes."""
    settings.usb_camera_frame_rate = request.form.get('usbCameraFrameRate')
    app.logger.info(
        "USB Camera Frame Rate is: %s",
        settings.usb_camera_frame_rate
    )
    return redirect(url_for('cameras'))


#
# Change Camera Attributes
#
@app.route('/change_camera_attributes', methods=['POST'])
def change_camera_attributes():
    """Change the selected camera's attributes."""
    settings.camera_resolution = request.form.get('cameraResolution')
    settings.camera_compression = request.form.get('cameraCompression')
    settings.fps_value = request.form.get('fpsValue')
    settings.camera_change = True
    settings.set_camera_source()
    app.logger.info("Camera source is: %s", settings.camera_source)
    app.logger.info(
        "%s %s %s %s",
        settings.selected_camera,
        settings.camera_resolution,
        settings.camera_compression,
        settings.fps_value
    )
    return redirect(url_for('cameras'))


#
# Capture Image
#
@app.route('/capture_image')
def capture_image():
    """Capture an image to a file and display."""
    settings.camera.write_frame()
    image = os.path.join(app.config['UPLOAD_FOLDER'], "frame.jpg")
    return render_template("capture_image.html",
                           image=image)


#
# Video Feed
#
@app.route('/video_feed')
def video_feed():
    """Handle the video feed."""
    return Response(
        gen(settings.camera),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


###########################
#
# Removable Media
#
###########################
@app.route('/removable_media')
def removable_media():
    """Render the removable_media page."""
    path = "/media"
    return render_template("removable_media.html",
                           tree=make_tree(path))


###########################
#
# GPIOs Page
#
###########################
@app.route('/gpios')
def gpios():
    """Render the GPIOs page."""
    try:
        fd = os.open("/dev/ttyUSB0", os.O_RDWR)
    except Exception:
        fd = None
    state1 = "???"
    state2 = "???"
    if fd:
        os.system("stty -F /dev/ttyUSB0 9600 ignbrk -brkint -imaxbel -opost -onlcr -isig -icanon -iexten -echo -echoe -echok -echoctl -echoke noflsh -ixon -crtscts")
        os.write(fd, b'\xff\x01\x03')
        sleep(0.1)
        status1 = os.read(fd, 3)
        if status1[2] == 1:
            state1 = "ON"
        elif status1[2] == 0:
            state1 = "OFF"
        else:
            state1 = "!!!"

        os.write(fd, b'\xff\x02\x03')
        sleep(0.1)
        status2 = os.read(fd, 3)

        if status2[2] == 1:
            state2 = "ON"
        elif status2[2] == 0:
            state2 = "OFF"
        else:
            state2 = "!!!"
        os.close(fd)

    if fd:
        warning = ""
    else:
        warning = ("Warning: This device ("
                   + settings.env['OPTRA_DEVICE_MODEL']
                   + ") does not have ttyUSB hardware.")
    return render_template("gpios.html",
                           warning=warning,
                           state1=state1,
                           state2=state2)

def ttyusb_write(s):
    try:
        fd = os.open("/dev/ttyUSB0", os.O_RDWR)
    except Exception:
        fd = None
    if fd:
        os.write(fd, s)
        os.close(fd)


@app.route('/poweron1')
def poweron1():
    ttyusb_write(b'\xff\x01\x01')
    return redirect(url_for('gpios'))

@app.route('/poweroff1')
def poweroff1():
    ttyusb_write(b'\xff\x01\x00')
    return redirect(url_for('gpios'))

@app.route('/poweron2')
def poweron2():
    ttyusb_write(b'\xff\x02\x01')
    return redirect(url_for('gpios'))

@app.route('/poweroff2')
def poweroff2():
    ttyusb_write(b'\xff\x02\x00')
    return redirect(url_for('gpios'))

###########################
#
# System Page
#
###########################
@app.route('/system')
def system():
    """Render the System page."""
    with subprocess.Popen("top -bcn1 -w133",
                          shell=True,
                          text=True,
                          bufsize=-1,
                          stdout=subprocess.PIPE).stdout as get_top:
        top = get_top.read()
    return render_template("system.html",
                           top=top)


###########################
#
# About Page
#
###########################
@app.route('/about')
def about():
    """Render the About page."""
    return render_template("about.html",
                           version=__version__)


###########################
#
# Main
#
###########################
if __name__ == '__main__':

    # Eliminate insecure reqests warnings
    requests.packages.urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )

    # Setup logging
    dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s]'
                          + ' %(levelname)s'
                          + 'in %(module)s:'
                          + ' %(message)s',
            }
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        }
    })
    app.logger = create_logger(app)

    # Initialize settings
    settings = Settings()

    # Get Module Twin
    settings.twin = asyncio.run(get_twin())

    # Populate attached cameras from the twin
    settings.populate_attached_cameras()

    # Set directory for captured images
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'capture')

    # Log the environment variables and the module twin
    app.logger.info("Environment Variables: \n%s", settings.env_vars)
    app.logger.info("Twin: \n%s", json.dumps(settings.twin, indent=4))

    # Development server
    # app.run(host='0.0.0.0', port=7000, debug=True, use_reloader=False)

    # Production server
    from waitress import serve
    serve(app, listen='0.0.0.0:7000')
