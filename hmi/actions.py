#  Copyright (c) 2018 Phil Birkelbach; 2019 Garrett Herschleb
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
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *

except:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *

import hmi.functions

class ActionClass(QWidget):
    activateMenuItem    = pyqtSignal(object)
    setMenuFocus        = pyqtSignal(object)
    evalExpression      = pyqtSignal(object)

    def __init__(self):
        super(ActionClass, self).__init__()
        self.signalMap = {"activate menu item":self.activateMenuItem
                         ,"set menu focus":self.setMenuFocus
                         }


    def trigger(self, action, argument=""):
        a = self.signalMap[action.lower()]
        if isinstance(a, pyqtBoundSignal):
            a.emit(argument)
        else: # It's not a signal so assume it's a function
            a(argument)


    def findAction(self, action):
        a = action.lower()
        if a in self.signalMap:
            return self.signalMap[a]
        else:
            return None
