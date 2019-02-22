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

import math
import logging
import time
import threading
import os
from glob import glob

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import pyavmap.avchart_proj as proj

log = logging.getLogger(__name__)

class AvMap(QGraphicsView):
    icon_poly_points = [
        QPointF (0,0)
       ,QPointF (5,5)
       ,QPointF (20,5)

       ,QPointF (30,25)
       ,QPointF (40,25)
       ,QPointF (35,5)

       ,QPointF (50,5)
       ,QPointF (55,10)
       ,QPointF (65,10)
       ,QPointF (60,0)
       ,QPointF (65,-10)
       ,QPointF (55,-10)
       ,QPointF (50,-5)

       ,QPointF (35,-5)
       ,QPointF (40,-25)
       ,QPointF (30,-25)

       ,QPointF (20,-5)
       ,QPointF (5,-5)
    ]
    icon_center = QPointF(25,0)
    scene_size_multiplier=4
    def __init__(self, config, parent=None):
        super(AvMap, self).__init__(parent)
        self.config = config

        self.setStyleSheet("border: 0px")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.NoFocus)
        self.fontSize = 30
        self._lat = 0
        self._lon = 0
        self._track_direction = 0

        self.chart_type = proj.CT_SECTIONAL if 'chart_type' not in self.config else self.config ['chart_type']

        self.zoom = 1.0 if 'zoom' not in self.config else self.config['zoom']
        self.xoff = 0 if 'xoff' not in self.config else self.config['xoff']
        self.yoff = 0 if 'yoff' not in self.config else self.config['yoff']
        self.pxmap_update_period = 1.0 if 'pxmap_update_period' not in self.config \
                                       else self.config['pxmap_update_period']
        self.icon_opacity = .8 if 'icon_opacity' not in self.config else self.config['icon_opacity']
        self.icon_scale = 1.0 if 'icon_scale' not in self.config else self.config['icon_scale']
        self.icon_fill = Qt.white if 'icon_fill' not in self.config \
                            else self.config['icon_fill']
        self.icon_outline = Qt.black if 'icon_outline' not in self.config \
                            else self.config['icon_outline']
        self.show_path = False if 'show_path' not in self.config else self.config['show_path']
        self.path_color = Qt.green if 'path_color' not in self.config else self.config['path_color']
        self.path_history = list()
        self.last_path_time = 0
        self.max_path_len = 1000 if 'path_length' not in self.config else self.config['path_length']
        self.north_is_up = True if 'north_is_up' not in self.config else self.config['north_is_up']
        self.extended_track_length = 100 if 'extended_track_length' not in self.config \
                                    else self.config['extended_track_length']
        self.el_color = Qt.yellow if 'el_color' not in self.config else self.config['el_color']
        self.last_rotation_val = 0.0
        self.chart = None
        self.map_pixmap = None
        self.new_map_pixmap = None
        self.map_pixmap_lon = None
        self.map_pixmap_lat = None
        self.pmi = None
        # Data from pixmap construction
        # The offset of the upper left corner of the constructed pixmap in over-all chart x-y coordinates,
        # adjusted for zoom level
        self.corner_x = None
        self.corner_y = None
        # The position of the given lat,lon in the over-all chart x-y coordinates,
        # adjusted for zoom level
        self.xzoom = None
        self.yzoom = None
        self.chart_image_time = 0
        self.pxmap_update_pending = False
        self.pxmap_update = None
        self.pxmap_lock = threading.RLock()

    def resizeEvent(self, event):
        log.debug("resizeEvent")
        #Setup the scene that we use for the background of the AI
        self.pxmpHeight = self.height() * self.scene_size_multiplier
        self.pxmpWidth = self.width() * self.scene_size_multiplier
        self.scene = QGraphicsScene(0, 0, self.pxmpWidth+self.width(), self.pxmpHeight+self.height())
        self.setScene(self.scene)
        self.init_chart()

    def find_best_chart(self):
        cd = None if 'charts_dir' not in self.config else self.config['charts_dir']
        candidates = proj.find_charts (self.chart_type, self._lon, self._lat, cd,
                    self.pxmpWidth, self.pxmpHeight, self.zoom)
        if len(candidates) == 0:
            return None
        best_chart = candidates[0]
        if len(candidates) > 1:
            best_dir = abs(Heading (((self._lon,self._lat), (candidates[0].center_lat, candidates[0].center_lon))) -
                            self._track_direction)
            if best_dir > 180:
                best_dir -= 180
            for ch in candidates[1:]:
                d = abs(Heading (((self._lon,self._lat), (ch.center_lat, ch.center_lon))) - self._track_direction)
                if d > 180:
                    d = abs(d-360)
                if d < best_dir:
                    best_dir = d
                    best_chart = ch
        return best_chart

    def init_chart(self):
        log.debug("init_chart")
        self.chart = self.find_best_chart()
        if self.chart is None:
            log.error ("No chart found for %g,%g", self._lon, self._lat)
            return
        self.map_pixmap_lon = self._lon
        self.map_pixmap_lat = self._lat
        try:
            self.map_pixmap,self.corner_x,self.corner_y,self.xzoom,self.yzoom = \
                        self.chart.construct_pixmap(self._lon, self._lat,
                        self.pxmpWidth, self.pxmpHeight, self.zoom)
            self.chart_image_time = time.time()
            good = True
        except RuntimeError:
            good = False
            log.error ("Chart set failure: %s %g,%g", self.chart.name, self._lon, self._lat)
        if good:
            if self.pmi is None:
                self.pmi = self.scene.addPixmap (self.map_pixmap)
                self.pmi.setOffset(self.width()/2,self.height()/2)
            else:
                self.pmi.setPixmap (self.map_pixmap)
            self.redraw()

    def redraw(self):
        self.resetTransform()
        self.pxmap_lock.acquire()
        if self.pxmap_update_pending and (self.new_map_pixmap is not None):
            self.map_pixmap = self.new_map_pixmap
            self.pmi.setPixmap (self.map_pixmap)
            self.new_map_pixmap = None
            self.pxmap_update_pending = False
        cx = self.xzoom-self.corner_x + self.width()/2
        cy = self.yzoom-self.corner_y + self.height()/2
        self.pxmap_lock.release()
        log.log (2, "redraw center on %g,%g - %g,%g - %d,%d = %g,%g", self.xzoom, self.yzoom,
                        self.corner_x, self.corner_y,
                        self.width()/2, self.height()/2,
                        cx,cy)
        if cy < self.height()/2:
            log.error ("Image spill to the top")
        if self.scene.height()-cy < self.height()/2:
            log.error ("Image spill to the bottom")
        if cx < self.width()/2:
            log.error ("Image spill to the left")
        if self.scene.width()-cx < self.width()/2:
            log.error ("Image spill to the right")
        if (not self.north_is_up) and (self.chart is not None):    # Track is up
            cna = self.chart.north_angle * 180 / math.pi
            rotate_angle = -self._track_direction - (cna - 90)
            if rotate_angle != self.last_rotation_val:
                increment_angle = rotate_angle - self.last_rotation_val
                self.rotate(increment_angle)
                self.last_rotation_angle = rotate_angle
            if self.yoff != 0 or self.xoff != 0:
                rotate_angle *= math.pi / 180
                cosa = math.cos(rotate_angle)
                sina = math.sin(rotate_angle)
                yoff = (self.yoff*cosa - self.xoff*sina)
                xoff = (self.xoff*cosa + self.yoff*sina)
                cy -= yoff
                cx -= xoff
        else:
            cx -= self.xoff
            cy -= self.yoff
        self.centerOn(cx, cy)

    def setLat(self, val):
        if val != self._lat and self.isVisible():
            self._lat = val
            if self.chart is None or self.map_pixmap is None:
                self.init_chart()
            else:
                self.xzoom,self.yzoom = self.chart.get_zoom_pos (self._lon, self._lat, self.zoom)
                self.redraw()
                self.check_pxmap_update()
                self.record_track()

    def setLon(self, val):
        if val != self._lon and self.isVisible():
            self._lon = val
            if self.chart is None or self.map_pixmap is None:
                self.init_chart()
            else:
                self.xzoom,self.yzoom = self.chart.get_zoom_pos (self._lon, self._lat, self.zoom)
                self.redraw()
                self.check_pxmap_update()
                self.record_track()

    def record_track(self):
        add = False
        now = time.time()
        if len(self.path_history) > 0:
            dist = Distance (((self._lon,self._lat), self.path_history[-1]))
            if dist > 10 and now - self.last_path_time > 1:
                add = True
        else:
            add = True
        if add:
            self.path_history.append ((self._lon,self._lat))
            self.last_path_time = now
            if len(self.path_history) > self.max_path_len:
                del self.path_history[0]

    def incZoom(self, diff):
        log.debug("incZoom")
        if diff != 0 and self.isVisible():
            newzoom = self.zoom + diff
            if newzoom <= .2:
                newzoom = .2
            if newzoom > 2:
                newzoom = 2
            if self.zoom != newzoom:
                self.zoom = newzoom
                if self.chart is None or self.map_pixmap is None:
                    self.init_chart()
                else:
                    self.map_pixmap_lon = self._lon
                    self.map_pixmap_lat = self._lat
                    try:
                        self.map_pixmap,self.corner_x,self.corner_y,self.xzoom,self.yzoom = \
                                    self.chart.construct_pixmap(self._lon, self._lat,
                                    self.pxmpWidth, self.pxmpHeight, self.zoom)
                        self.chart_image_time = time.time()
                        good = True
                    except RuntimeError:
                        good = False
                        log.error ("Chart set failure: %s %g,%g", chart_name, self._lon, self._lat)
                    if good:
                        self.pmi.setPixmap (self.map_pixmap)
                        self.redraw()

    def setTrack(self, val):
        if val != self._track_direction and self.isVisible():
            self._track_direction = val

    def set_chart_type(self, ct):
        self.chart_type = ct
        self.init_chart()

    def set_north_up(self, nu):
        self.north_is_up = nu

# We use the paintEvent to draw on the viewport the parts that aren't moving.
    def paintEvent(self, event):
        super(AvMap, self).paintEvent(event)
        w = self.width()
        h = self.height()
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing)

        p.setPen(QColor(self.icon_outline))
        p.setBrush(QColor(self.icon_fill))
        p.setOpacity (self.icon_opacity)
        ix = self.icon_center.x()*self.icon_scale
        iy = self.icon_center.y()*self.icon_scale
        if (self.chart is not None) and self.north_is_up:
            angle = self._track_direction * math.pi/180
            angle += self.chart.north_angle
        else:
            angle = math.pi/2
        cosa = math.cos(angle)
        sina = math.sin(angle)
        offset_x = self.width()/2 + self.xoff - (ix*cosa - iy*sina)
        offset_y = self.height()/2 + self.yoff - (iy*cosa + ix*sina)
        pp = [QPointF ((p.x()*cosa - p.y()*sina)*self.icon_scale + offset_x,
                       (p.y()*cosa + p.x()*sina)*self.icon_scale + offset_y)
              for p in self.icon_poly_points]
        p.drawPolygon(QPolygonF(pp))

        if self.north_is_up and self.show_path and len(self.path_history) >= 2:
            p.setPen(QColor(self.path_color))
            p.setOpacity(1.0)
            cx = self.xzoom-self.corner_x-self.xoff     # Where in the pixmap is the center of the display
            cy = self.yzoom-self.corner_y-self.yoff
            cx -= self.width()/2                        # Where in the pixmap is the ul corner of display
            cy -= self.height()/2
            last_coord_x,last_coord_y = self.screen_coord (self.path_history[0][0], self.path_history[0][1], cx, cy)
            for i in range(1,len(self.path_history)):
                icoord_x,icoord_y = self.screen_coord (self.path_history[i][0], self.path_history[i][1], cx,cy)
                p.drawLine(QPointF(last_coord_x,last_coord_y), QPointF(icoord_x,icoord_y))
                log.debug("path_history %.1f,%.1f -> %.1f,%.1f", last_coord_x, last_coord_y, icoord_x, icoord_y)
                last_coord_x = icoord_x
                last_coord_y = icoord_y
        if self.north_is_up and self.extended_track_length > 0:
            ix = 0
            iy = -self.extended_track_length
            ext_dx = (ix*cosa - iy*sina)
            ext_dy = (iy*cosa + ix*sina)
            pen = QPen(QColor(self.el_color))
            pen.setStyle(Qt.DotLine)
            p.setPen(pen)
            bx = self.width()/2 + self.xoff
            by = self.height()/2 + self.yoff
            ex = bx + ext_dy
            ey = by - ext_dx
            p.drawLine (QPointF(bx,by), QPointF(ex,ey))

    def screen_coord(self, lon, lat, cx, cy):
            coord_x,coord_y = self.chart.proj (lon,lat)
            coord_x *= self.zoom
            coord_y *= self.zoom
            coord_x -= self.corner_x                    # Where is the track in the pixmap
            coord_y -= self.corner_y
            coord_x -= cx
            coord_y -= cy
            return coord_x,coord_y

    def update_chart_pixmap(self, chart):
        try:
            map_pixmap,corner_x,corner_y,xzoom,yzoom = \
                    chart.construct_pixmap(self._lon, self._lat,
                    self.pxmpWidth, self.pxmpHeight, self.zoom)
            good = True
        except RuntimeError:
            good = False
            self.pxmap_update_pending = False
            log.error ("update pixmap set failure: %s %g,%g", chart.name, self._lon, self._lat)
        if good:
            self.pxmap_lock.acquire()
            self.new_map_pixmap,self.corner_x,self.corner_y,self.xzoom,self.yzoom = \
                map_pixmap,corner_x,corner_y,xzoom,yzoom
            self.chart = chart
            self.pxmap_lock.release()
            self.chart_image_time = time.time()

    def check_pxmap_update(self):
        if (self.chart is not None) and (not self.pxmap_update_pending):
            if time.time() - self.chart_image_time > self.pxmap_update_period:
                cx,cy,oob = self.chart.compute_ul_corner(self._lon, self._lat,
                            self.pxmpWidth, self.pxmpHeight, self.zoom)
                chart = self.chart
                if oob:     # out of bounds
                    chart = self.find_best_chart()
                    if chart is None or chart.name == self.chart.name:
                        log.debug ("Out of bounds, but no better chart available")
                        chart = self.chart
                    else:
                        log.debug ("Out of bounds. change chart to %s"%chart.name)
                self.chart_image_time = time.time()
                if cx != self.corner_x or cy != self.corner_y or chart != self.chart:
                    self.pxmap_update_pending = True
                    th = threading.Thread (target=self.update_chart_pixmap, args=(chart,))
                    th.start()

def get_polar_deltas(course):
    lng1,lat1 = course[0]
    lng2,lat2 = course[1]
    dlng = lng2 - lng1
    dlat = lat2 - lat1
    return (dlng,dlat)

def GetRelLng(lat1):
    return math.cos(lat1)

def adjusted_polar_deltas(course, rel_lng=0):
    dlng,dlat = get_polar_deltas(course)

    # Determine how far is a longitude increment relative to latitude at this latitude
    if rel_lng == 0:
        lat1 = course[0][1] * math.pi / 180.0
        relative_lng_length = GetRelLng(lat1)
    else:
        relative_lng_length = rel_lng
    dlng *= relative_lng_length
    return dlng,dlat

METERS_PER_NM = 1852
# Computes distance in meters between 2 long/lat points
def Distance(course, rel_lng=0):
    dlng,dlat = adjusted_polar_deltas(course, rel_lng)
    # Multiply by 60 to convert from degrees to nautical miles.
    distance = math.sqrt(dlng * dlng + dlat * dlat) * 60.0
    return distance * METERS_PER_NM

def Heading(course, rel_lng=0):
    dlng,dlat = adjusted_polar_deltas(course, rel_lng)
    heading = math.atan2(dlng, dlat) * 180 / math.pi
    return heading

def configure_charts (directory):
    chart_types = glob(os.path.join (directory, '*'))
    chart_types = [os.path.basename(ct) for ct in chart_types]
    log.debug ("Found chart types: %s", str(chart_types))
    for ct in chart_types:
        proj.charts[ct] = dict()
        chart_names = glob(os.path.join (directory, ct, '*'))
        chart_names = [os.path.basename(cn) for cn in chart_names]
        log.debug ("Found chart in %s: %s", ct, str(chart_names))
        for cn in chart_names:
            base_name = glob(os.path.join (directory, ct, cn, '*.tfw'))
            if len(base_name) == 0:
                base_name = glob(os.path.join (directory, ct, cn, '*.tfwx'))
            if len(base_name) == 0:
                log.error ("Invalid chart found: %s", os.path.join (directory, ct, cn))
                continue
            base = os.path.basename(base_name[0])
            base = os.path.splitext(base)[0]
            proj.charts[ct][cn] = [base]
            if os.path.exists (os.path.join (directory, ct, cn, 'rotated')):
                proj.charts[ct][cn].append(True)
            log.debug ("chart %s of type %s is defined: %s", cn, ct, str(proj.charts[ct][cn]))

def chart_types():
    return (list(proj.charts.keys()))
