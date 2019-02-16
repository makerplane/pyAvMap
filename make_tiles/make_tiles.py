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

import sys, os
from PIL import Image

Image.MAX_IMAGE_PIXELS=225000000
print ("Reading Image...")
i=Image.open(sys.argv[1] + '.tif')
if len(sys.argv) > 2:
    rotate = bool(sys.argv[2])
else:
    rotate = False
ncuts = 10
cut_width = int(round(float(i.width) / float(ncuts)))
cut_height = int(round(float(i.height) / float(ncuts)))
xoff = 0
for x in range(ncuts):
    yoff = 0
    for y in range(ncuts):
        print ("Cropping tile %dx%d..."%(x,y))
        ci = i.crop((xoff,yoff,xoff+cut_width,yoff+cut_height))
        if rotate:
            ci = ci.transpose (Image.ROTATE_90)
            ci.save(sys.argv[1] + str(y) + str(ncuts-x-1) + ".png")
        else:
            ci.save(sys.argv[1] + str(x) + str(y) + ".png")
        yoff += cut_height
    xoff += cut_width
