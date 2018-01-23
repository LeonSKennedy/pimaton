from picamera import PiCamera
from time import sleep, strftime
import datetime
import logging

from PimatonExceptions import PimatonCamExceptions

logging.basicConfig()
logger = logging.getLogger("Pimaton")


class PimatonCam:
    """
    Class that handles the PiCamera for the Pimaton app
    """

    def __init__(self, config):
        logger.debug('Instanciating PimatonCam with config %s' % config)
        self.picamera = PiCamera()
        self.config_picamera(config)
        self.config = config

    def take_pictures(self, unique_key):
        """
        This function takes picture via the pi camera
        """
        logger.debug("Starting taking_pictures")

        taken_pictures = []
        self.picamera.start_preview()
        sleep(self.config['time_before_first_picture'])

        for i in range(self.config['number_of_pictures_to_take']):
            filename = self.config['picture_prefix_name'] + "_" + unique_key + \
                '_' + datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + ".jpg"
            taken_pictures.append(filename)

            sleep(self.config['time_between_pictures'])
            logger.debug('Taking picture %s' % i)
            self.capture(filename)
            logger.debug("Photo (" + filename + ") saved: " + filename)

        self.picamera.stop_preview()

        logger.debug("The following pictures were taken %s" % taken_pictures)
        return taken_pictures

    def capture(self, filename):
        logger.debug("Capturing picture %s in %s" %
                     (filename, self.config['photo_directory']))
        try:
            self.picamera.capture(
                self.config['photo_directory'] + '/' + filename)
        except Exception as e:
            raise PimatonCamExceptions(
                'An error occured capturing the picture: %s' % e)

    def config_picamera(self, config):
        logger.debug('Configuring Pi Camera')

        try:
            self.picamera.resolution = (
                config['settings']['resolution']['width'],
                config['settings']['resolution']['height'])
            self.picamera.framerate = config['settings']['framerate']
            self.picamera.sharpness = config['settings']['sharpness']
            self.picamera.contrast = config['settings']['contrast']
            self.picamera.brightness = config['settings']['brightness']
            self.picamera.saturation = config['settings']['saturation']
            self.picamera.iso = config['settings']['iso']
            self.picamera.video_stabilization = config['settings']['video_stabilization']
            self.picamera.exposure_compensation = config['settings']['exposure_compensation']
            self.picamera.exposure_mode = config['settings']['exposure_mode']
            self.picamera.meter_mode = config['settings']['meter_mode']
            self.picamera.awb_mode = config['settings']['awb_mode']
            self.picamera.rotation = config['settings']['rotation']
            self.picamera.hflip = config['settings']['hflip']
            self.picamera.vflip = config['settings']['vflip']
        except Exception as e:
            raise PimatonCamExceptions('Couldnt config picamera: %s' % e)
