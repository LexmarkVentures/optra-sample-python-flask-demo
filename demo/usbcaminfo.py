"""Module usbcam
"""
import subprocess
import json
import logging


# pylint: disable=too-many-instance-attributes
class UsbCameraInfo():
    """Class to extract USB Camera information using v4l2-ctl."""

    # pylint: disable=no-member
    def __init__(self):
        self.init_usb_camera_info()

    @staticmethod
    def exec_cmd_return_output(command):
        """Execute a command and return the output."""
        lines = []
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        ) as cmdpipe:
            stdout, stderr = cmdpipe.communicate()
            status = cmdpipe.wait()
            lines = stdout.splitlines()
            if status:
                err_msg = stderr.splitlines()
                err = f"Command '{command}' failed: rc={status} {err_msg}"
                logging.error(err)
        return lines

    def refresh(self):
        """Refresh the USB camera info."""
        self.init_usb_camera_info()
        return self.usb_camera_info

    def get_all(self):
        """Return all of the USB Camera Info."""
        return self.usb_camera_info

    def get_devices_list(self):
        """Return the list of usb camera devices."""
        devices_list = []
        info = self.usb_camera_info
        if info:
            for cam in info:
                devices_list.append(cam["Device"])
        return devices_list

    def get_format_list(self, device):
        """Return the list of formats for a device."""
        pixel_format_list = []
        info = self.usb_camera_info
        if info:
            for cam in info:
                if cam["Device"] == device:
                    for fmt in cam["Formats"]:
                        pixel_format_list.append(fmt["Format"])
        return pixel_format_list

    def get_resolution_list(self, device, pixel_format):
        """Return the list of resolutions for a device/format."""
        resolution_list = []
        info = self.usb_camera_info
        # pylint: disable=too-many-nested-blocks
        if info:
            for cam in info:
                if cam["Device"] == device:
                    for fmt in cam["Formats"]:
                        if fmt["Format"] == pixel_format:
                            for res in fmt["Resolutions"]:
                                resolution_list.append(res["Resolution"])
        return resolution_list

    def get_fps_list(self, device, pixel_format, resolution):
        """Return list of frame rates for device/format/resolution."""
        fps_list = []
        info = self.usb_camera_info
        # pylint: disable=too-many-nested-blocks
        if info:
            for cam in info:
                if cam["Device"] == device:
                    for fmt in cam["Formats"]:
                        if fmt["Format"] == pixel_format:
                            for res in fmt["Resolutions"]:
                                if res["Resolution"] == resolution:
                                    if res["FrameRates"]:
                                        for fps in res["FrameRates"]:
                                            if fps not in fps_list:
                                                fps_list.append(fps)
        return fps_list

    @staticmethod
    def width_from_resolution(resolution):
        """Return the width from the resolution."""
        return resolution.split("x")[0]

    @staticmethod
    def height_from_resolution(resolution):
        """Return the height from the resolution."""
        return resolution.split("x")[1]

    @staticmethod
    def fractional_frame_rate(frame_rate):
        """Return the frame rate as a fraction."""
        numerator, denominator = float(frame_rate).as_integer_ratio()
        return str(numerator) + "/" + str(denominator)

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    def init_usb_camera_info(self):
        """Gets the USB Camera info from v4l2-ctl.

        Example:

        [
            {
                "Device": "/dev/video3",
                "Name": "UVC Camera (0603:8612) (usb-3610000.xhci-2.1)",
                "Formats": [
                    {
                        "Format": "MJPG",
                        "Resolutions": [
                            {
                                "Width": "1920",
                                "Height": "1080",
                                "FrameRates": [
                                    "60.000",
                                    "30.000"
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        """

        self.usb_camera_info = []

        cmd = "v4l2-ctl --list-devices"
        lines = UsbCameraInfo.exec_cmd_return_output(cmd)

        prev_line = ""
        for line in lines:
            if line.strip()[0:10] == "/dev/video":
                self.usb_camera_info.append(
                    {
                        "Device": line.strip(),
                        "Name": prev_line
                    }
                )
            else:
                prev_line = line[:-1]

        # pylint: disable=too-many-nested-blocks
        for cam in self.usb_camera_info:
            # Get number following "/dev/video"
            index = cam["Device"].split("video", 1)[1]

            cmd = f"v4l2-ctl -d{index} --list-formats"
            lines = UsbCameraInfo.exec_cmd_return_output(cmd)

            cam["Formats"] = []

            for line in lines:
                if "Pixel Format" in line:
                    parsed_line = line.strip().split("'")
                    if len(parsed_line) < 2 or parsed_line[1] == "":
                        logging.info("Bad Pixel Format line")
                        # Pixel Format line not valid, so continue
                        continue
                    pixel_format = parsed_line[1]
                    pixel_format_index = len(cam["Formats"])
                    fmts = cam["Formats"]
                    fmts.append(
                        {
                            "Format": pixel_format,
                            "Resolutions": []
                        }
                    )

                    cmd = (
                        f"v4l2-ctl -d{index} --list-framesizes={pixel_format}"
                    )
                    lines2 = UsbCameraInfo.exec_cmd_return_output(cmd)

                    for line2 in lines2:
                        if "Size" in line2:
                            resolution = line2.strip().split(" ")[2]
                            width = resolution.split("x")[0]
                            height = resolution.split("x")[1]
                            resolution_index = (
                                len(
                                    cam["Formats"]
                                    [pixel_format_index]
                                    ["Resolutions"]
                                )
                            )
                            res = fmts[pixel_format_index]["Resolutions"]
                            res.append(
                                    {
                                        "Resolution": width+"x"+height,
                                        "FrameRates": []
                                    }
                            )

                            cmd = (
                                f"v4l2-ctl -d{index} --list-frameintervals="
                                + f"width={width},"
                                + f"height={height},"
                                + f"pixelformat={pixel_format}"
                            )
                            lines3 = UsbCameraInfo.exec_cmd_return_output(cmd)

                            for line3 in lines3:
                                if "Interval" in line3:
                                    frame_rate = (
                                        line3.strip().split(" ")[3][1:]
                                    )
                                    frame_rates = (
                                        res[resolution_index]["FrameRates"]
                                    )
                                    frame_rates.append(frame_rate)

        # Remove devices that do not have Formats
        for cam in self.usb_camera_info:
            if not cam["Formats"]:
                logging.info(
                    "Removing device with no formats: %s",
                    json.dumps(cam, indent=4)
                )
                self.usb_camera_info.remove(cam)


if __name__ == '__main__':
    print(json.dumps(UsbCameraInfo().get_all(), indent=4))
