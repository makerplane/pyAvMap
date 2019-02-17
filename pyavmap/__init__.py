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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import fix

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

        self.chart_type = proj.CT_SECTIONAL if 'chart_type' not in self.config else self.config ['chart_type']

        lat = fix.db.get_item("LAT", True)
        self._lat = lat.value
        lon = fix.db.get_item("LONG", True)
        self._lon = lon.value
        track = fix.db.get_item("TRACK", True)
        self._track = track.value
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
        self.show_track = False if 'show_track' not in self.config else self.config['show_track']
        self.track_color = Qt.green if 'track_color' not in self.config else self.config['track_color']
        self.track = list()
        self.last_track_time = 0
        self.max_track_len = 1000 if 'track_length' not in self.config else self.config['track_length']
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
        lat.valueChanged[float].connect(self.setLat)
        lon.valueChanged[float].connect(self.setLon)
        track.valueChanged[float].connect(self.setTrack)
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

    def find_best_chart(self):
        cd = None if 'charts_dir' not in self.config else self.config['charts_dir']
        candidates = proj.find_charts (self.chart_type, self._lon, self._lat, cd,
                    self.pxmpWidth, self.pxmpHeight, self.zoom)
        if len(candidates) == 0:
            return None
        best_chart = candidates[0]
        if len(candidates) > 1:
            best_dir = abs(Heading (((self._lon,self._lat), (candidates[0].center_lat, candidates[0].center_lon))) -
                            self._track)
            if best_dir > 180:
                best_dir -= 180
            for ch in candidates[1:]:
                d = abs(Heading (((self._lon,self._lat), (ch.center_lat, ch.center_lon))) - self._track)
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
        cx = self.xzoom-self.corner_x-self.xoff + self.width()/2
        cy = self.yzoom-self.corner_y-self.yoff + self.height()/2
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
        self.centerOn(cx, cy)
        self.pxmap_lock.release()
        #self.rotate()

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
        if len(self.track) > 0:
            dist = Distance (((self._lon,self._lat), self.track[-1]))
            if dist > 10 and now - self.last_track_time > 1:
                add = True
        else:
            add = True
        if add:
            self.track.append ((self._lon,self._lat))
            self.last_track_time = now
            if len(self.track) > self.max_track_len:
                del self.track[0]

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
        if val != self._track and self.isVisible():
            self._track = val

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
        angle = self._track * math.pi/180
        if self.chart is not None:
            angle += self.chart.north_angle
        else:
            angle += math.pi/2
        cosa = math.cos(angle)
        sina = math.sin(angle)
        ix = self.icon_center.x()*self.icon_scale
        iy = self.icon_center.y()*self.icon_scale
        offset_x = self.width()/2 + self.xoff - (ix*cosa - iy*sina)
        offset_y = self.height()/2 + self.yoff - (iy*cosa + ix*sina)
        pp = [QPointF ((p.x()*cosa - p.y()*sina)*self.icon_scale + offset_x,
                       (p.y()*cosa + p.x()*sina)*self.icon_scale + offset_y)
              for p in self.icon_poly_points]
        p.drawPolygon(QPolygonF(pp))

        if self.show_track and len(self.track) >= 2:
            p.setPen(QColor(self.track_color))
            p.setOpacity(1.0)
            cx = self.xzoom-self.corner_x-self.xoff     # Where in the pixmap is the center of the display
            cy = self.yzoom-self.corner_y-self.yoff
            cx -= self.width()/2                        # Where in the pixmap is the ul corner of display
            cy -= self.height()/2
            last_coord_x,last_coord_y = self.screen_coord (self.track[0][0], self.track[0][1], cx, cy)
            for i in range(1,len(self.track)):
                icoord_x,icoord_y = self.screen_coord (self.track[i][0], self.track[i][1], cx,cy)
                p.drawLine(QPointF(last_coord_x,last_coord_y), QPointF(icoord_x,icoord_y))
                log.debug("track %.1f,%.1f -> %.1f,%.1f", last_coord_x, last_coord_y, icoord_x, icoord_y)
                last_coord_x = icoord_x
                last_coord_y = icoord_y

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
