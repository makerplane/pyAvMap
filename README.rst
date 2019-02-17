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
::
  Unzip them into pyAvMap/charts/Sectional/<ChartName>   # Should include *.tif and *.htm and *.tfw(x)
  cd pyAvMap/charts/Sectional/<ChartName>
  pyAvMap/make_tiles/make_tiles.py <base_file_name> # e.g. "Albuquerque SEC 101"
  rm pyAvMap/charts/Sectional/<ChartName>/*.tif             # after the tiles are created, you don't need the humongo tiff anymore

The above example is for sectional charts. Other directory names for other chart types are:
  1. IFR
  1. Jet
  1. Terminal

Some IFR charts are laid out so that North is approximately in the width direction rather
than the height direction. L-01 and L-02 are examples of this. In this case, add a second
argument of "1" (the number without quotes) to the make_tiles.py command line,
and that will rotate the chart so it's oriented correctly.

Dependencies
------------
The pyAvTools repo should be cloned adjacent to pyAvMap. You should use makerplane/pyAvTools.
