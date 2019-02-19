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

import os, math

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
    def __init__(self, name, base_name, rotated):
        self.name = name
        self.base_name = base_name
        self.rotated = rotated
        self.lat_0=None
        self.lon_0=None
        lat1=None
        lat2=None
        proj='lcc'
        datum='WGS84'
        self.llon = None
        self.rlon = None
        self.ulat = None
        self.llat = None
        self.column_count = None
        htm_name = base_name + '.htm'
        if not os.path.exists (htm_name):
            htm_name = base_name + '_tif.htm'
        with open(htm_name, 'r') as htm:
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
                    self.lon_0 = float(line[n:e])
                if 'Latitude_of_Projection_Origin' in line:
                    i = line.index('Projection_Origin')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    self.lat_0 = float(line[n:e])
                if 'Column_Count' in line:
                    i = line.index('Column_Count')
                    n = line.index('>', i) + 1
                    e = line.index('<', n)
                    self.column_count = int(line[n:e])
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

        wfname = base_name + '.tfw'
        if not os.path.exists (wfname):
            wfname = base_name + '.tfwx'
        with open(wfname, 'r') as wf:
            constants = wf.readlines()
            wf.close()
            self.A,self.D, self.B,self.E, self.C,self.F = [float(c) for c in constants]

        self.divisor = (self.E*self.A) - (self.B*self.D)
        self.xconst = self.B*self.F - self.C*self.E
        self.yconst = self.D*self.C - self.A*self.F
        self.center_lat = (self.ulat + self.llat) / 2.0
        self.center_lon = (self.llon + self.rlon) / 2.0
        self.p = Proj(proj=proj, lat_0=self.lat_0, lon_0=self.lon_0, units='meters',
                      datum=datum, lat_1=lat1, lat_2=lat2)

        cx,cy = self.proj (self.center_lon, self.center_lat)
        ux,uy = self.proj (self.center_lon, self.ulat)
        dx = ux-cx
        dy = uy-cy
        self.north_angle = math.atan2(dy, dx) + math.pi # 180 degree flip because positive y is down

        pxmp0 = QPixmap(base_name + '00.png')
        self.tile_width = pxmp0.width()
        self.tile_height = pxmp0.height()

    def is_valid(self):
        return not (self.llon is None or self.rlon is None or
                    self.ulat is None or self.llat is None)

    def proj(self, lon,lat):
        x1,y1 = self.p(lon,lat)
        x = (self.E*x1 - self.B*y1 + self.xconst) / self.divisor
        y = ((self.A*y1 - self.D*x1 + self.yconst) / self.divisor)
        if self.rotated:
            temp = x
            x = y
            y = self.column_count - temp - 1
        return (x,y)

    def get_tile_coord(self, lon, lat):
        x,y = self.proj(lon,lat)
        x /= self.tile_width
        y /= self.tile_height
        x = int(x)
        y = int(y)
        return x,y

    def get_tile_pixmap_pos (self, lon, lat, just_check=False):
        x,y = self.get_tile_coord(lon, lat)
        if x < 0:
            log.debug ("%g,%g is out of longitude bounds: %g,%g", lon, lat, x,y)
            return (x,y,None)
        elif y < 0:
            log.debug ("%g,%g is out of latitude bounds: %g,%g", lon, lat, x,y)
            return (x,y,None)
        return self.get_tile_pixmap(x,y, just_check)

    def get_tile_pixmap (self, x,y, just_check=False):
        fname = self.base_name + str(x) + str(y) + '.png'
        if not os.path.exists (fname):
            log.debug ("No tile %s", fname)
            return (x,y,None)
        if just_check:
            return (x,y,True)
        else:
            return (x,y,QPixmap(fname))

    def compute_tile_bounds(self, lon, lat, width, height, zoom_width, zoom_height):
        imcenterx = width/2
        imcentery = height/2
        cx,cy = self.get_tile_coord(lon, lat)
        begin_xindex = cx - int(imcenterx / zoom_width)
        begin_yindex = cy - int(imcentery / zoom_height)
        log.debug ("begin_xindex = %d-int(round(%g/%g))(%d) = %d",
                cx, imcenterx, zoom_width, int(imcenterx / zoom_width), begin_xindex)
        log.debug ("begin_yindex = %d-int(round(%g/%g))(%d) = %d",
                cy, imcentery, zoom_height, int(imcentery / zoom_height), begin_yindex)
        out_of_bounds = False
        if begin_xindex < 0:
            begin_xindex = 0
            out_of_bounds = True
        if begin_yindex < 0:
            begin_yindex = 0
            out_of_bounds = True
        end_xindex = begin_xindex + int(width / zoom_width)+1
        end_yindex = begin_yindex + int(height / zoom_height)+1
        log.debug ("end_*index = %d,%d", end_xindex,end_yindex)
        fname = self.base_name + str(end_xindex) + str(end_yindex) + '.png'
        if not os.path.exists (fname):
            out_of_bounds = True
        return begin_xindex,begin_yindex, end_xindex,end_yindex, out_of_bounds

    def construct_pixmap(self, lon, lat, width, height, zoom):
        ret = QPixmap(width, height)
        ret.fill (QColor(Qt.black))
        cx,cy,ci = self.get_tile_pixmap_pos (lon, lat)
        if ci is None:
            raise RuntimeError ("longitude %g, latitude %g is not contained in map %s (tile %d,%d)"%(
                                    lon,lat,self.name,cx,cy))

        zoom_width = self.tile_width * zoom
        zoom_height = self.tile_height * zoom
        begin_xindex,begin_yindex,end_xindex,end_yindex,oob = self.compute_tile_bounds (lon, lat,
                        width, height, zoom_width, zoom_height)

        painter = QPainter(ret)
        tile_place_x = 0
        log.debug ("const_pmp: zoom w,h = %g,%g", zoom_width, zoom_height)
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
                    painter.drawPixmap(QPoint(int(round(tile_place_x)),int(round(tile_place_y))), tp)
                    log.debug ("const_pmp: tile %d,%d drawn at %d,%d", i,j,
                                int(round(tile_place_x)),int(round(tile_place_y)))
                tile_place_y += zoom_height
            tile_place_x += zoom_width

        corner_x = begin_xindex * zoom_width
        corner_y = begin_yindex * zoom_height
        xzoom,yzoom = self.get_zoom_pos(lon,lat,zoom)
        return ret,corner_x,corner_y,xzoom,yzoom

    def compute_ul_corner(self, lon, lat, width, height, zoom):
        zoom_width = self.tile_width * zoom
        zoom_height = self.tile_height * zoom
        begin_xindex,begin_yindex,end_xindex,end_yindex,oob = self.compute_tile_bounds (lon, lat,
                        width, height, zoom_width, zoom_height)
        corner_x = begin_xindex * zoom_width
        corner_y = begin_yindex * zoom_height
        return corner_x, corner_y, oob

    def check_boundaries (self, lon, lat, width, height, zoom):
        cx,cy,ci = self.get_tile_pixmap_pos (lon, lat, just_check=True)
        if ci is None or ci is False:
            return False, True
        zoom_width = self.tile_width * zoom
        zoom_height = self.tile_height * zoom
        begin_xindex,begin_yindex,end_xindex,end_yindex,boundary_spill = \
                    self.compute_tile_bounds (lon, lat,
                        width, height, zoom_width, zoom_height)
        return True,boundary_spill

    def get_zoom_pos(self, lon, lat, zoom):
        chart_x,chart_y = self.proj(lon,lat)
        xzoom = chart_x * zoom
        yzoom = chart_y * zoom
        return xzoom,yzoom


def load_chart(name, chtype, directory=None):
    if name in charts[chtype]:
        rotated = False
        base_name = charts[chtype][name][0]
        if len(charts[chtype][name]) > 1 and bool(charts[chtype][name][1]):
            rotated = True
        if directory is not None:
            base_name = os.path.join (directory, chtype, name, base_name)
        else:
            base_name = os.path.join (chtype, name, base_name)
        ret = AvChart (name, base_name, rotated)
        return ret
    else:
        log.error ("chart %s not found", name)
        return None

def find_chart (chart_type, lon, lat, directory):
    ch = list(charts[chart_type].keys())[0]
    tried = set()
    while True:
        in_bounds = False
        chart = load_chart(ch, chart_type, directory)
        if chart is not None and chart.is_valid():
            in_bounds = True
            tried.add (ch)
            if lon < chart.llon:
                in_bounds = False
                newch = charts[chart_type][ch][4]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
            if lon > chart.rlon:
                in_bounds = False
                newch = charts[chart_type][ch][3]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
            if lat > chart.ulat:
                in_bounds = False
                newch = charts[chart_type][ch][1]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
            if lat < chart.llat:
                in_bounds = False
                newch = charts[chart_type][ch][2]
                if newch is not None and (newch not in tried):
                    ch = newch
                    continue
        if in_bounds:
            return chart
        else:
            # No chart found
            return None

def find_charts (chart_type, lon, lat, directory, width, height, zoom):
    ret = list()
    for ch,chinfo in charts[chart_type].items():
        chart = load_chart(ch, chart_type, directory)
        if chart is not None and chart.is_valid():
            in_bounds = True
            if lon < chart.llon:
                in_bounds = False
            if lon > chart.rlon:
                in_bounds = False
            if lat > chart.ulat:
                in_bounds = False
            if lat < chart.llat:
                in_bounds = False
            if in_bounds:
                valid,boundary_spill = chart.check_boundaries(lon, lat,
                                width, height, zoom)
                if valid:
                    ret.append(chart)
    return ret
