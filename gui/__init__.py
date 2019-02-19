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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import logging
log = logging.getLogger(__name__)
import sys, os

if "pyAvTools" not in ''.join(sys.path):
    neighbor_tools = os.path.join ('..', 'pyAvTools')
    if os.path.isdir (neighbor_tools):
        sys.path.append (neighbor_tools)
    elif 'TOOLS_PATH' in os.environ:
        sys.path.append (os.environ['TOOLS_PATH'])

try:
    import pyavui
except:
    print ("You need to have pyAvTools installed, or in an adjacent directory to pyAvMap.")
    print ("Or set the environment variable 'TOOLS_PATH' to point to the location of pyAvTools.")
    sys.exit(-1)

class ChartTypeSel(pyavui.AVUI):
    def __init__(self, enc_key, enc_sel_key, chart_types, callback, parent=None, config=None):
        super(ChartTypeSel,self).__init__ (enc_key, enc_sel_key, parent)
        self.chart_types = chart_types
        self.callback = callback

    def resizeEvent(self, event):
        title = "Chart Type"
        self.ctsel_widget = pyavui.SelectMenuWidget(title, self.chart_types, self.change_chart_type,
                pyavui.SelectMenuWidget.MENU_ACTION_TYPE_FUNCTION, self.width(), self.height())
        super(ChartTypeSel,self).resizeEvent (event)
        super(ChartTypeSel,self).set_widgets ([self.ctsel_widget])

    def change_chart_type(self, i, ct_string):
        self.callback (ct_string)
