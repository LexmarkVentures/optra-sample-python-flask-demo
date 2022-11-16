"""Module camera
"""
import os
import logging
import threading
import time
import cv2


# pylint: disable=too-many-instance-attributes
class Camera():
    """Camera class to capture frames using OpenCV
    """

    # pylint: disable=no-member
    def __init__(self):
        self.source = None
        self.cap = None
        self.queue = []
        self.starting = True
        self.resize_factor = 1
        self.cap_thread = None
        self.time_to_stop = threading.Event()
        self.cascade = None
        self.queue_size = 10
        self.seconds_to_wait_for_frame = 0.5

        # Load the test pattern frame for times when a captured frame
        # is not available
        self.test_pattern_frame = cv2.imread("test_pattern.jpg")
        self.frame = self.test_pattern_frame

        # Load the test pattern frame as a jpeg for use if jpeg
        # conversion fails
        with open("test_pattern.jpg", "rb") as file:
            self.test_pattern_jpeg = file.read()

    def __del__(self):
        # Stop the capture thread if it is running
        self.stop()

    # pylint: disable=too-many-arguments
    def start(
        self,
        source,
        pixel_format,
        resolution,
        frame_rate,
        cascade_classifier=None,
        resize_factor=1.0
    ):
        """Start the capture on a source."""

        # Make sure capture thread is stopped
        self.stop()

        # Check for a selected cascade classifier
        if cascade_classifier is None or cascade_classifier == "none":
            self.cascade = None
        else:
            self.cascade = cv2.CascadeClassifier(
                f"{cv2.data.haarcascades}{cascade_classifier}"
            )
            self.resize_factor = resize_factor

        # Open the capture source
        logging.info("Opening camera %s", source)
        self.cap = cv2.VideoCapture(source)

        # If failed to open, return
        if not self.cap.isOpened():
            logging.info("Failed to open camera %s", source)
            return

        # If Camera is USB, then set the properties
        #   FOURCC is the pixel format, usually MJPG or YUYV
        #   WIDTH is the resolution width
        #   HEIGHT is the resolution height
        #   FPS is the frame rate
        #
        # RTSP cameras must use the URL to set properties
        if Camera.is_usb_cam(source):
            self.cap.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*pixel_format)
            )
            self.cap.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                float(resolution.split('x')[0])
            )
            self.cap.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                float(resolution.split('x')[1])
            )
            self.cap.set(
                cv2.CAP_PROP_FPS,
                float(frame_rate)
            )

        self.cap_thread = threading.Thread(
            target=Camera.capture_thread,
            args=(self, )
        )

        # Clear the stop event
        self.time_to_stop.clear()

        # Start thread that capatures the frames
        self.cap_thread.start()

    def stop(self):
        """Stop the capture thread and wait for it to die."""
        if self.cap_thread and self.cap_thread.is_alive():
            logging.info("Stopping capture_thread()")
            # set the stop event
            self.time_to_stop.set()
            # wait for thread to finish
            self.cap_thread.join()
            logging.info("capture_thread() stopped")

    def capture_thread(self):
        """Thread that captures frames from the source"""

        logging.info("Starting capture_thread()")

        # Run until time to stop
        while not self.time_to_stop.is_set():
            success, self.frame = self.cap.read()
            if not success:
                logging.info("Read failed in thread")
                self.frame = self.test_pattern_frame

            if len(self.queue) < self.queue_size:
                self.queue.append(self.frame)

            # Give the main thread a chance to run
            time.sleep(0)

        logging.info("Releasing camera")
        self.cap.release()
        self.frame = None
        self.source = None
        self.queue = []
        logging.info("Ending capture_thread()")

    def write_frame(self):
        """Write a captured frame to a file."""

        if self.frame is None:
            logging.info("Capture set to test pattern")
            frame = self.test_pattern_frame
        else:
            frame = self.frame

        cv2.imwrite("/demo/static/capture/frame.jpg", frame)

    # pylint: disable=no-member
    # pylint: disable=invalid-name
    def get_frame(self):
        """Get a frame from the source.

        Optionally, do a classification on the frame.
        """

        # Wait a short time for a frame
        end = time.time() + self.seconds_to_wait_for_frame
        while (not self.queue and time.time() < end):
            time.sleep(0.05)

        # If there is no frame from the source, just return the test pattern
        if not self.queue:
            frame = self.test_pattern_frame
        else:
            frame = self.queue.pop(0)

        # Do classifer if selected
        if self.cascade:

            try:
                # Resize the frame based on resize_factor
                frame = cv2.resize(
                    frame,
                    None,
                    fx=self.resize_factor,
                    fy=self.resize_factor,
                    interpolation=cv2.INTER_AREA
                )

                # Create a gray scale version of the frame
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Find the object and return the rectangles
                rects = self.cascade.detectMultiScale(gray, 1.3, 5)

                # Draw the rectangles on the frame
                for (x, y, w, h) in rects:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # If we get an exception, just continue on to display the frame
            # pylint: disable=broad-except
            except Exception as error:
                logging.error(error)

        # Convert and return the frame
        success, jpeg = cv2.imencode('.jpg', frame)
        if not success:
            logging.info("cv2.imencode() failed")
            jpeg = self.test_pattern_jpeg
        return jpeg.tobytes()

    @staticmethod
    def is_usb_cam(source):
        """Return True if camera is USB."""
        return (
            len(source) > 9
            and source[0:10] == "/dev/video"
        )

    @staticmethod
    def is_rtsp_cam(source):
        """Return True if camera is RTSP."""
        return (
            len(source) > 3
            and source[0:4] == "rtsp"
        )

    @staticmethod
    def camera_type(source):
        """Return camera Type."""
        if Camera.is_usb_cam(source):
            return "USB"
        if Camera.is_rtsp_cam(source):
            return "RTSP"
        return "Other"

    @staticmethod
    def available_classifiers():
        """Returns the available Haar Cascade Classifiers."""
        classifiers = []
        for file in os.listdir(cv2.data.haarcascades):
            if file.endswith(".xml"):
                classifiers.append(file)
        return classifiers
