======================================
MakerPlane Aviation Moving Map Package
======================================

Copyright (c) 2018-2019 MakerPlane

pyAvMap is an open source moving map package for aviation.

Installation
------------

Begin by cloning the Git repository

::

    git clone git@github.com:makerplane/pyAvMap.git

or

::

    git clone https://github.com/makerplane/pyAvMap.git


If you'd like to install the program permanently to your system or into a virtualenv you
can issue the command...

::

  sudo pip3 install .

from the root directory of the source repository.  **Caution** This feature is still
in development and may not work consistently.

Requirements
------------
Download chart(s) from FAA website.  https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/

Unzip them into pyAvMap/charts/Sectional/<ChartName>   # Should include *.tif and *.htm
cd pyAvMap/charts/Sectional/<ChartName>
pyAvMap/make_tiles/make_tiles.py <base_file_name> # e.g. "Albuquerque SEC 101"
rm pyAvMap/charts/Sectional/<ChartName>/*.tif             # after the tiles are created, you don't need the humongo tiff anymore

The above example is for sectional charts. Other directory names for other chart types are:
1. IFR
1. Jet
1. Terminal

Configure what charts you have in pyAvMap/config/main.yaml:

Example:
sectional_charts:
    Albuquerque:
        - 'Albuquerque SEC 101'
        - 9881
        - 5990
        - Denver
        - El Paso
        - Dallas-Ft Worth
        - Phoenix
    Seattle:
        - 'Seattle SEC 96'
        - 9669
        - 6165
        - null
        - 'Klamath Falls'
        - 'Great Falls'
        - null

The chart key names should match the <ChartName> where you unzipped the file

The list definitions are as follows:
Filename base
column pixel of center of the chart, as identified in the html file
row pixel of center of chart, as identified in the html file
Chart keyname that is north of this chart
"   "   south "   "
   "   east   "    "
   "   west   "      "
