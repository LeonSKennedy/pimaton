from time import time, sleep

import yaml
import datetime
import logging

from PimatonCam import PimatonCam
from PimatonImage import PimatonImage
from PimatonPrint import PimatonPrint
from PimatonInput import PimatonInput, PimatonInputKeyboard
from PimatonExceptions import PimatonExceptions, PimatonCamExceptions, PimatonPrintExceptions

logging.basicConfig()
logger = logging.getLogger("Pimaton")


class Pimaton:
    """
    This Class is the main Pimaton class that manage the whole application.
    """

    def __init__(self, config_file=None):
        logger.info('*** Configuring Pimaton ***')
        self.set_config(config_file)

        # Init classes now so it checks the config early.
        self.pimatoncam = PimatonCam(self.config['picamera'])
        self.pimatonimage = PimatonImage(self.config['image'])
        self.pimatoninput = self.init_input(self.config['input'])

        if self.config['print']['enabled'] is True:
            logger.info('**** Pimaton is configured to print images.')
            self.pimatonprint = PimatonPrint(self.config['print'])
        else:
            logger.info('**** Pimaton is configured to NOT print image.')
            self.pimatonprint = None

    def run(self):
        """
        Class method that run the main loop of the application.
        """

        while True:
            # TODO v0.0.3 : Manage button to start taking picture.
            unique_key = str(int(time()))

            if self.pimatoninput.is_triggered() is False:
                continue

            logger.info(
                '*** Pimaton trigger has been pressed, starting taking pictures!')

            try:
                taken_pictures = self.pimatoncam.take_pictures(unique_key)
            except PimatonCamExceptions as e:
                logger.error('An error occured when taking pictures: %s' % e)
                raise PimatonExceptions("An error occured when taking picture")

            if len(
                    taken_pictures) != self.config['picamera']['number_of_pictures_to_take']:
                logger.error("The number of taken pictures is incorrect")
                raise PimatonExceptions(
                    'The number of taken pictures isnt right.')

            filename = self.config['image']['print_pic']['generated_prefix_name'] + '_' + \
                unique_key + '_' + datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + ".jpg"

            try:
                logger.info('Starting image generation')

                self.pimatonimage.render_image_to_print(
                    self.__get_fullpath_thumbnails_list(taken_pictures),
                    filename,
                    self.config['image'])
                to_print = self.config['image']['print_pic']['output_dir'] + \
                    '/' + filename

            except PimatonExceptions as e:
                logger.error('PimatonImageExceptions: %s' % e)
                raise PimatonExceptions(
                    'Couldnt generate the picture to print')

            # TODO v0.0.3 : Manage print.
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

            logger.debug('Sleeping %s second' %
                         self.config['pimaton']['time_between_loop'])
            sleep(self.config['pimaton']['time_between_loop'])

    def set_config(self, config_file=None):
        """
        Class method to set the configuration of the application
        """
        if config_file is None:
            config_file = './assets/default_config.yaml'
            logger.debug(
                'No given config, loading default one %s' %
                config_file)
        else:
            logger.debug('No template given, loading default one')

        # Overriding all config, so be sure when not using default one :).
        self.config = self.load_config(config_file)
        logger.debug('self config = %s' % self.config)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            data = yaml.load(f)

        logger.debug("Loaded configuration: %s" % data)
        return data

    def __get_fullpath_thumbnails_list(self, taken_pictures):
        fpp = []
        for pic in taken_pictures:
            fpp.append(self.config['picamera']['photo_directory'] + '/' + pic)

        return fpp

    def init_input(self, config):
        if self.config['input']['type'] == 'keyboard':
            pimatoninput = PimatonInputKeyboard()

        elif self.config['input']['type'] == 'GPIO':
            # TODO v0.0.2
            pimatoninput = PimatonInputGPIO()
        else:
            raise PimatonExceptions(
                'Not recognized input type % s' %
                self.config['input']['type'])

        return pimatoninput


class PimatonExceptions:
    pass
