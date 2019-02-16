#!/usr/bin/env python3

#  Copyright (c) 2019 Garrett Herschleb
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import sys

import logging
import logging.config
import argparse
try:
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    PYQT = 5
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    PYQT = 4
import yaml

import fix
import pyavmap
import pyavmap.avchart_proj as proj
import hmi
from hmi import Menu

class Main(QMainWindow):
    keyPress = pyqtSignal(QEvent)
    keyRelease = pyqtSignal(QEvent)
    def keyPressEvent(self, event):
        self.keyPress.emit(event)
    def keyReleaseEvent(self, event):
        self.keyRelease.emit(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    parser = argparse.ArgumentParser(description='pyAvMap')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Run in verbose mode')
    parser.add_argument('--config-file', default='config/main.yaml', type=argparse.FileType('r'),
                        help='Alternate configuration file')

    args = parser.parse_args()

    # if we passed in a configuration file on the command line...
    config = yaml.load(args.config_file)

    if 'logging' in config:
        logging.config.dictConfig(config['logging'])
    else:
        logging.basicConfig()

    log = logging.getLogger()
    if args.verbose:
        log.setLevel(logging.INFO)
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting pyAvMap")

    log.debug("PyQT Version = %d" % PYQT)

    fix.initialize(config)

    if 'sectional_charts' in config:
        proj.configure_charts (proj.CT_SECTIONAL, config['sectional_charts'])

    if 'ifr_charts' in config:
        proj.configure_charts (proj.CT_IFR, config['ifr_charts'])

    main_window = Main()
    screenWidth = int(config["main"]["screenWidth"])
    screenHeight = int(config["main"]["screenHeight"])
    main_window.resize(screenWidth, screenHeight)
    avmap = pyavmap.AvMap (config, main_window)
    avmap.resize(screenWidth, screenHeight)
    hmi.initialize(config)
    hmi.keys.initialize(main_window, config["keybindings"])
    if 'menu' in config:
        menu = Menu(main_window, config["menu"])
        menu.start()
        menu.register_map(avmap)

    main_window.show()
    # Main program loop
    result = app.exec_()

    # Clean up and get out
    fix.stop()
    log.info("PyAvMap Exiting Normally")
    sys.exit(result)
