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

import os

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from pyproj import Proj

import logging
log = logging.getLogger(__name__)

CT_SECTIONAL = 'Sectional'
CT_IFR = 'IFR'
CT_JET = 'Jet'
CT_TAC = 'Terminal'

charts = dict()

class AvChart:
    def __init__(self, name, base_name, xoff, yoff):
        self.name = name
        self.base_name = base_name
        self.xoff=xoff
        self.yoff=yoff
        lat_0=None
        lon_0=None
        lat1=None
        lat2=None
        proj='lcc'
        datum='WGS84'
        self.xscale=0
        self.yscale=0
        self.llon = None
        self.rlon = None
        self.ulat = None
        self.llat = None
        with open(base_name + '.htm', 'r') as htm:
            while True:
                line = htm.readline()
                if line is None or len(line) == 0:
                    htm.close()
                    break
                if 'Map_Projection_Name' in line:
                    if not 'Lambert' in line:
                        raise RuntimeError("Unrecognized map projection")
                if 'Standard_Parallel' in line:
                    i = line.index('Standard_Parallel')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    p = float(line[n:e])
                    if lat1 is not None:
                        lat2 = p
                        log.debug ("%s: lat2 = %g"%(base_name, lat2))
                    else:
                        lat1 = p
                        log.debug ("%s: lat1 = %g"%(base_name, lat1))
                if 'Longitude_of_Central_Meridian' in line:
                    i = line.index('Central_Meridian')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    lon_0 = float(line[n:e])
                if 'Latitude_of_Projection_Origin' in line:
                    i = line.index('Projection_Origin')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    lat_0 = float(line[n:e])
                if 'Abscissa_Resolution' in line:
                    i = line.index('Resolution')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    self.yscale = float(line[n:e])
                if 'Ordinate_Resolution' in line:
                    i = line.index('Resolution')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    self.xscale = float(line[n:e])
                if '_Bounding_Coordinate' in line:
                    i = line.index('Coordinate')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    coord = float(line[n:e])
                    if 'West' in line:
                        self.llon = coord
                        log.debug ("West boundary of %s is %g"%(self.name, coord))
                    elif 'East' in line:
                        self.rlon = coord
                        log.debug ("East boundary of %s is %g"%(self.name, coord))
                    elif 'North' in line:
                        self.ulat = coord
                        log.debug ("North boundary of %s is %g"%(self.name, coord))
                    elif 'South' in line:
                        self.llat = coord
                        log.debug ("South boundary of %s is %g"%(self.name, coord))
                    else:
                        raise RuntimeError ("%s: Unknown bounding coordinate type: %s"%(base_name, line))

        self.p = Proj(proj=proj, lat_0=lat_0, lon_0=lon_0, units='meters',
                      datum=datum, lat_1=lat1, lat_2=lat2)

        pxmp0 = QPixmap(base_name + '00.png')
        self.tile_width = pxmp0.width()
        self.tile_height = pxmp0.height()

    def proj(self, lon,lat):
        x,y = self.p(lon,lat)
        x /= self.xscale
        y /= self.yscale
        x += self.xoff
        y = self.yoff - y
        return (x,y)

    def get_tile_coord(self, lon, lat, xoff, yoff):
        x,y = self.proj(lon,lat)
        x /= self.tile_width
        y /= self.tile_height
        x = int(round(x))
        y = int(round(y))
        x += xoff
        y += yoff
        return x,y

    def get_tile_pixmap_pos (self, lon, lat, xoff, yoff):
        x,y = self.get_tile_coord(lon, lat, xoff, yoff)
        if x < 0:
            return (x,y,None)
        elif y < 0:
            return (x,y,None)
        return self.get_tile_pixmap(x,y)

    def get_tile_pixmap (self, x,y):
        fname = self.base_name + str(x) + str(y) + '.png'
        if not os.path.exists (fname):
            log.debug ("No tile %s", fname)
            return (x,y,None)
        return (x,y,QPixmap(fname))

    def compute_upper_left_position(self, lon, lat, width, height, zoom_width, zoom_height, xoff, yoff):
        imcenterx = int(round(width/2)) + xoff
        imcentery = int(round(height/2)) + yoff
        cx,cy = self.get_tile_coord(lon, lat, xoff, yoff)
        begin_xindex = cx - int(round(imcenterx / zoom_width))
        begin_yindex = cy - int(round(imcentery / zoom_height))
        out_of_bounds = False
        if begin_xindex < 0:
            begin_xindex = 0
            out_of_bounds = True
        if begin_yindex < 0:
            begin_yindex = 0
            out_of_bounds = True
        return begin_xindex,begin_yindex, out_of_bounds

    def construct_pixmap(self, lon, lat, width, height, xoff, yoff, zoom):
        ret = QPixmap(width, height)
        ret.fill (QColor(Qt.black))
        cx,cy,ci = self.get_tile_pixmap_pos (lon, lat, 0,0)
        if ci is None:
            raise RuntimeError ("longitude %g, latitude %g is not contained in map %s (tile %d,%d)"%(
                                    lon,lat,self.name,cx,cy))

        zoom_width = int(round(self.tile_width * zoom))
        zoom_height = int(round(self.tile_height * zoom))
        begin_xindex,begin_yindex,oob = self.compute_upper_left_position (lon, lat,
                        width, height, zoom_width, zoom_height, xoff, yoff)
        end_xindex = begin_xindex + int(width / zoom_width)+1
        end_yindex = begin_yindex + int(height / zoom_height)+1

        painter = QPainter(ret)
        tile_place_x = 0
        for i in range(begin_xindex,end_xindex):
            if tile_place_x > width:
                break
            tile_place_y = 0
            for j in range(begin_yindex,end_yindex):
                if tile_place_y > height:
                    break
                tx,ty,tp = self.get_tile_pixmap(i,j)
                if tp is not None:
                    tp = tp.scaled (int(round(tp.width()*zoom)), int(round(tp.height()*zoom)),
                                    transformMode=Qt.SmoothTransformation)
                    painter.drawPixmap(QPoint(tile_place_x,tile_place_y), tp)
                tile_place_y += zoom_height
            tile_place_x += zoom_width

        corner_x = begin_xindex * zoom_width
        corner_y = begin_yindex * zoom_height
        xzoom,yzoom = self.get_zoom_pos(lon,lat,zoom)
        return ret,corner_x,corner_y,xzoom,yzoom

    def compute_ul_corner(self, lon, lat, width, height, xoff, yoff, zoom):
        zoom_width = int(round(self.tile_width * zoom))
        zoom_height = int(round(self.tile_height * zoom))
        begin_xindex,begin_yindex,oob = self.compute_upper_left_position (lon, lat,
                        width, height, zoom_width, zoom_height, xoff, yoff)
        corner_x = begin_xindex * zoom_width
        corner_y = begin_yindex * zoom_height
        return corner_x, corner_y, oob

    def get_zoom_pos(self, lon, lat, zoom):
        chart_x,chart_y = self.proj(lon,lat)
        xzoom = int(round(chart_x * zoom))
        yzoom = int(round(chart_y * zoom))
        return xzoom,yzoom


def load_chart(name, chtype, directory=None):
    if name in charts[chtype]:
        base_name, xoff, yoff = charts[chtype][name][:3]
        if directory is not None:
            base_name = os.path.join (directory, chtype, name, base_name)
        else:
            base_name = os.path.join (chtype, name, base_name)
        ret = AvChart (name, base_name, xoff, yoff)
        return ret
    else:
        log.error ("chart %s not found", name)
        return None

def find_chart (chart_type, lon, lat, directory):
    ch = list(charts[chart_type].keys())[0]
    tried = set()
    while True:
        in_bounds = True
        chart = load_chart(ch, chart_type, directory)
        if chart is not None:
            tried.add (ch)
            if lon < chart.llon:
                in_bounds = False
                newch = charts[chart_type][ch][6]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
            if lon > chart.rlon:
                in_bounds = False
                newch = charts[chart_type][ch][5]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
            if lat > chart.ulat:
                in_bounds = False
                newch = charts[chart_type][ch][3]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
            if lat < chart.llat:
                in_bounds = False
                newch = charts[chart_type][ch][4]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
        if in_bounds:
            return chart
        else:
            # No chart found
            return None

def configure_charts (chtype, d):
    charts[chtype] = d
