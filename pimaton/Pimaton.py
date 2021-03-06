from time import time, sleep
import os

import yaml
import datetime
import logging
import subprocess
import socket

from PimatonCam import PimatonCam
from PimatonImage import PimatonImage
from PimatonPrint import PimatonPrint
from PimatonExceptions import PimatonExceptions, PimatonCamExceptions, PimatonPrintExceptions, PimatonSyncExceptions

logging.basicConfig()
logger = logging.getLogger("Pimaton")

try:
    import RPi.GPIO as GPIO
except BaseException:
    logger.debug('Couldn\'t load RPi.GPIO library')


class Pimaton:
    """
    This Class is the main Pimaton class that manage the whole application.
    """

    def __init__(self, config_file=None, single_loop=False):
        logger.info('*** Configuring Pimaton ***')
        self.set_config(config_file)

        # Init classes now so it checks the config early.
        if self.is_flash_enabled() is True:
            logger.debug('Flash option is enabled.')
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for led in self.config['GPIO']['leds']:
                logger.debug('Enable Flash on GPIO %s' % led)
                GPIO.setup(led, GPIO.OUT)
        self.pimatoncam = PimatonCam(self.config['picamera'])
        self.pimatonimage = PimatonImage(self.config['image'])

        if self.config['print']['enabled'] is True:
            logger.info('**** Pimaton is configured to print images.')
            self.pimatonprint = PimatonPrint(self.config['print'])
        else:
            logger.info('**** Pimaton is configured to NOT print image.')
            self.pimatonprint = None

        self.single_loop = True if single_loop is True else False

    def get_unique_key(cls):
        return str(int(time()))

    def take_pictures(self, unique_key):
        logger.info('*** Pimaton *** Starting taking pictures')

        # In case the uuid is in the directory path, we need to create it on
        # the fly.
        self.check_directory(
            self.config['picamera']['photo_directory'].replace(
                '%%uuid%%', unique_key))

        try:
            self.toggle_flash(True)
            taken_pictures = self.pimatoncam.take_pictures(unique_key)
            self.toggle_flash(False)
        except PimatonCamExceptions as e:
            logger.error('An error occured when taking pictures: %s' % e)
            raise PimatonExceptions("An error occured when taking picture")

        if len(
                taken_pictures) != self.config['picamera']['number_of_pictures_to_take']:
            logger.error("The number of taken pictures is incorrect")
            raise PimatonExceptions(
                'The number of taken pictures isnt right.')

        logger.debug('Pimaton - Take Pictures %s' % taken_pictures)
        return taken_pictures

    def get_filename(self, unique_key):
        filename = self.config['image']['print_pic']['generated_prefix_name'].replace(
            '%%hostname%%', socket.gethostname()) + '_' + unique_key + \
            '_' + datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + \
            '.' + self.config['image']['print_pic']['image_format']

        logger.debug('Generated filename for final image: %s' % filename)
        return filename

    def generate_picture(self, taken_pictures, filename, qrcode, unique_key):
        logger.info('*** Pimaton *** Starting image generation')

        # In case the uuid is in the directory path, we need to create it on
        # the fly.
        self.check_directory(
            self.config['image']['print_pic']['output_dir'].replace(
                '%%uuid%%', unique_key))

        try:
            self.pimatonimage.render_image_to_print(
                self.__get_fullpath_thumbnails_list(
                    taken_pictures,
                    unique_key),
                filename,
                self.config['image'],
                qrcode,
                unique_key)
            to_print = self.config['image']['print_pic']['output_dir'].replace(
                '%%uuid%%', unique_key) + '/' + filename
            return to_print

        except PimatonExceptions as e:
            logger.error('PimatonImageExceptions: %s' % e)
            raise PimatonExceptions(
                'Couldnt generate the picture to print')

    def get_qrcode(self, unique_key):
        if self.config['image']['print_pic']['qr_code_enabled'] is not True:
            return False

        import qrcode
        link = self.config['image']['print_pic']['qr_code_session_link'].replace(
            '%%uuid%%', unique_key)
        logger.debug(link)
        qr = qrcode.QRCode(
            version=self.config['image']['print_pic']['qr_code_size'],
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4)
        qr.add_data(link)
        qr.make(fit=True)

        return qr.make_image()

    def print_picture(self, to_print):
        logger.info('*** Pimaton *** Starting printing image')
        if self.config['print']['enabled'] is True \
                and isinstance(self.pimatonprint, PimatonPrint):
            try:
                self.pimatonprint.print_file(to_print)
            except PimatonPrintExceptions as e:
                logger.debug(
                    'An error occured when trying to print the image: %s' %
                    e)
                raise
        else:
            logger.debug('Print is disable, skipping')

    def sync_pictures(self):
        logger.info('*** Pimaton *** Starting uploading image')
        with open(os.devnull, 'w') as FNULL:
            try:
                subprocess.call(["rsync",
                                 "-azP",
                                 self.config['sync']['source'],
                                 self.config['sync']['destination']],
                                stdout=FNULL)
            except Exception as e:
                raise PimatonSyncExceptions('Couldnt sync pictures: %s' % e)

    def wait_before_next_iteration(self):
        logger.debug(
            'Sleeping %s second' %
            self.config['pimaton']['time_between_loop'])
        sleep(self.config['pimaton']['time_between_loop'])

    def set_config(self, config_file=None):
        """
        Class method to set the configuration of the application
        """
        if config_file is None:
            config_file = os.path.dirname(
                os.path.realpath(__file__)) + '/assets/default_config.yaml'
            logger.debug(
                'No given config, loading default one %s' %
                config_file)
        else:
            logger.debug('Loading configuration file: %s' % config_file)

        # Overriding all config, so be sure when not using default one :).
        self.config = self.load_config(config_file)
        logger.debug('self config = %s' % self.config)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            data = yaml.load(f)

        logger.debug("Loaded configuration: %s" % data)
        return data

    def __get_fullpath_thumbnails_list(self, taken_pictures, unique_key):
        fpp = []
        for pic in taken_pictures:
            fpp.append(
                self.config['picamera']['photo_directory'].replace(
                    '%%uuid%%', unique_key) + '/' + pic)

        logger.debug('full path pictures %s' % fpp)
        return fpp

    def get_ui_mode(self):
        return self.config['pimaton']['ui_mode']

    def is_print_enabled(self):
        return self.config['print']['enabled']

    def is_sync_enabled(self):
        return self.config['sync']['enabled']

    def generate_template(self):
        self.pimatonimage.generate_template_file(self.config['image'])

    def is_single_loop(self):
        return self.single_loop

    def is_qr_code_enabled(self):
        return self.config['pimaton']['qr_code_link_to_site']

    def check_directory(self, directory):
        logger.debug('Checking if %s exists' % directory)
        if not os.path.exists(directory):
            logger.debug(
                'Directory %s does not exist, creating it.' %
                directory)
            try:
                os.makedirs(directory)
            except OSError as e:
                raise PimatonExceptions(
                    'Couldn\'t create directory %s, error: %s' %
                    (directory, e))

    def is_flash_enabled(self):
        if 'flash_enabled' in self.config['picamera'] and self.config['picamera'][
                'flash_enabled'] is True and 'GPIO' in self.config and 'leds' in self.config['GPIO']:
            return True

    def toggle_flash(self, toggle=False):
        if self.is_flash_enabled() is True:
            action = GPIO.HIGH if toggle is True else GPIO.LOW
            for led in self.config['GPIO']['leds']:
                GPIO.output(led, action)
