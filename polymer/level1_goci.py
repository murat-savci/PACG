import os
import numpy as np
import h5py
import time
import calendar
import datetime
from collections import OrderedDict
from polymer.ancillary import Ancillary_NASA
from polymer.block import Block
from pysolar.solar import get_altitude, get_azimuth
from polymer.common import L2FLAGS
from polymer.goci_utils import goci_sensor_azimuth,goci_sensor_zenith,goci_slots,goci_slots_time
from polymer.utils import raiseflag


class Level1_GOCI():
    """
    GOCI Level reader
    """

    def __init__(self, filename, blocksize=100, sline=0, eline=-1, scol=0, ecol=-1, ancillary=None):
        self.sensor = 'GOCI'
        self.band = np.array([412, 443, 490, 555, 660, 680, 745, 865])
        self.central_wavelength = {412:412,443:443,490:490,555:555,660:660,680:680,745:745,865:865}
        self.tauray = np.array([0.31667194, 0.23525281, 0.15534917, 0.09366972,
                                0.04625096, 0.04092455, 0.02828797, 0.01555036])

        self.F0 = [1732.31, 1890.70, 1964.90, 1833.35, 1519.61,
                   1474.92, 1277.85, 954.43]  # [W/m^2/um]
        self.filename = filename
        with h5py.File(self.filename) as f:
            band1 = f['HDFEOS']['GRIDS']['Image Data']['Data Fields']['Band 1 Image Pixel Values'][()]
            starttime = f['HDFEOS/POINTS/Ephemeris'].attrs['Scene Start time'].decode(
                'utf-8')
            centertime = f['HDFEOS/POINTS/Ephemeris'].attrs['Scene center time'].decode(
                'utf-8')
   
        # use datetime.datetime model to read start\center\end time as localtime
        self.starttimedate = datetime.datetime.strptime(
            starttime, '%d-%b-%Y %H:%M:%S.%f') 
        # convert localtime to utc time
        self.starttimedate=self.starttimedate.replace(tzinfo=datetime.timezone.utc)
        self.centertimedate = datetime.datetime.strptime(
            centertime, '%d-%b-%Y %H:%M:%S.%f')
        self.totalheight, self.totalwidth = band1.shape
        self.blocksize = blocksize
        self.sline = sline
        self.scol = scol
        self.landmask = './auxdata/goci/COMS_GOCI_L2AUX_GA_20000101000000.he5'

        if ancillary is None:
            self.ancillary = Ancillary_NASA()
        else:
            self.ancillary = ancillary

        if eline < 0:
            self.eline = self.totalheight
        else:
            self.eline = eline
        self.height = self.eline-self.sline

        if ecol < 0:
            self.ecol = self.totalwidth
        else:
            self.ecol = ecol
        self.width = self.ecol-self.scol

        self.shape = (self.height, self.width)
        print('Initializing GOCI product of size', self.shape)

        self.init_ancillary()
        self.init_lonlat()
        self.init_slot()
        self.init_geometry()
        self.read_l1b()
        self.init_landmask()
        

    def init_lonlat(self):
        with h5py.File('./auxdata/goci/COMS_GOCI_L2P_GA_20110524031644.LAT.he5') as f:
            self.latitude = f['HDFEOS']['GRIDS']['Image Data']['Data Fields']['Latitude Image Pixel Values'][(
            )][self.sline:self.eline,self.scol:self.ecol]
        with h5py.File('./auxdata/goci/COMS_GOCI_L2P_GA_20110524031644.LON.he5') as f:
            self.longitude = f['HDFEOS']['GRIDS']['Image Data']['Data Fields']['Longitude Image Pixel Values'][(
            )][self.sline:self.eline,self.scol:self.ecol]

    def init_ancillary(self):
        # use GOCI center slot time for ancillary
        self.ozone = self.ancillary.get('ozone', self.centertimedate)
        self.wind_speed = self.ancillary.get('wind_speed', self.centertimedate)
        self.surf_press = self.ancillary.get('surf_press', self.centertimedate)

        self.ancillary_files = OrderedDict()
        self.ancillary_files.update(self.ozone.filename)
        self.ancillary_files.update(self.wind_speed.filename)
        self.ancillary_files.update(self.surf_press.filename)

    def init_slot(self):
        print('Generating GOCI slot data...')
        with h5py.File(self.filename) as f:
            nav_data = f['HDFEOS/POINTS/Navigation for GOCI/Data/Navigation for GOCI']
            self.goci_slot = goci_slots(nav_data, self.sline, self.eline, self.scol, self.ecol, 7)
            self.goci_slot_relat_time = goci_slots_time(nav_data)
        print('Finished generating GOCI slot data.')

    def read_l1b(self):
        nband = len(self.band)
        self.Ltoa_data = np.zeros([self.height, self.width, nband])
        with h5py.File(self.filename) as f:
            scale = f['HDFEOS/POINTS/Radiometric Calibration for GOCI'].attrs['Table for DN to Radiance conversion']
            for i in np.arange(nband):
                self.Ltoa_data[:, :, i] = f['HDFEOS/GRIDS/Image Data/Data Fields/Band '+str(
                    i+1)+' Image Pixel Values'][()][self.sline:self.eline,self.scol:self.ecol]*scale[i]

    def init_geometry(self):
        # sza
        self.sza = np.full((self.height, self.width), -999.0,dtype=np.float32)
        # saa
        self.saa = np.full((self.height, self.width), -999.0,dtype=np.float32)
        # vza
        self.vza = np.full((self.height, self.width), -999.0,dtype=np.float32)
        # vaa
        self.vaa = np.full((self.height, self.width), -999.0,dtype=np.float32)

        nslot = 16
        for i in np.arange(nslot):
            realtime = self.starttimedate.timestamp() + round(self.goci_slot_relat_time[i])
            date = datetime.datetime.fromtimestamp(
                realtime, tz=datetime.timezone.utc)
            self.sza[self.goci_slot == i+1] = 90 - \
                get_altitude(self.latitude[self.goci_slot == i+1],
                             self.longitude[self.goci_slot == i+1], date)
            self.saa[self.goci_slot == i + 1] = get_azimuth(
                self.latitude[self.goci_slot == i+1], self.longitude[self.goci_slot == i+1], date)

            self.vza[self.goci_slot == i+1] = goci_sensor_zenith(
                self.latitude[self.goci_slot == i+1], self.longitude[self.goci_slot == i+1])
            self.vaa[self.goci_slot == i+1] = goci_sensor_azimuth(
                self.latitude[self.goci_slot == i + 1], self.longitude[self.goci_slot == i + 1], 128.2)

        relaz = self.vaa - 180.0 - self.saa
        relaz[relaz > 180.] = 360.-relaz[relaz > 180.]
        relaz[relaz < -180.] = 360.+relaz[relaz < -180.]
        self.relaz = relaz


    def init_landmask(self):
        with h5py.File(self.landmask) as f:
            # ocean is 0, land is 2
            self.landmask_data = f['HDFEOS']['GRIDS']['Image Data']['Data Fields']['Land Image Pixel Values'][(
            )][self.sline:self.eline,self.scol:self.ecol]

    def read_block(self, size, offset, bands):
        (ysize, xsize) = size
        nbands = len(bands)

        block = Block(offset=offset, size=size, bands=bands)
        SY = slice(offset[0], offset[0]+ysize)
        SX = slice(offset[1], offset[1]+xsize)

        # read latitude/longitude
        block.latitude = self.latitude[SY, SX]
        block.longitude = self.longitude[SY, SX]

        # ancillary data
        block.ozone = np.zeros(size, dtype='float32')
        block.ozone[:] = self.ozone[block.latitude, block.longitude]
        block.wind_speed = np.zeros(size, dtype='float32')
        block.wind_speed[:] = self.wind_speed[block.latitude, block.longitude]
        block.surf_press = np.zeros(size, dtype='float32')
        block.surf_press[:] = self.surf_press[block.latitude, block.longitude]
        
        # read TOA
        block.Ltoa = np.full((ysize, xsize,nbands),np.nan) 
        for iband, band in enumerate(bands):
            block.Ltoa[:,:,iband] =self.Ltoa_data[SY, SX, iband]
            

        # read geometry
        block.sza = self.sza[SY, SX]
        block.saa = self.saa[SY, SX]
        block.vza = self.vza[SY, SX]
        block.vaa = self.vaa[SY, SX]

        # read bitmask
        block.bitmask = np.zeros(size, dtype='uint16')
        raiseflag(block.bitmask, L2FLAGS['LAND'], self.landmask_data[SY, SX])

        for i in np.arange(nbands):
            if i == 0:
                l1_invalid = self.Ltoa_data[:, :, i][SY, SX]
            else:
                l1_invalid = l1_invalid*self.Ltoa_data[:, :, i][SY, SX]
        l1_invalid[l1_invalid <= 0] = 1
        l1_invalid[l1_invalid > 0] = 0

        raiseflag(block.bitmask, L2FLAGS['L1_INVALID'], l1_invalid)

        # solar irradiance (seasonally corrected)
        block.F0 = np.full((ysize, xsize, nbands), np.nan)
        for iband, band in enumerate(bands):
            block.F0[:,:,iband] = self.F0[iband]
        
        block.altitude = np.zeros(size, dtype='float32')

        # solar irradiance (seasonally corrected)
        block.jday = self.centertimedate.timetuple().tm_yday
        block.month = self.centertimedate.timetuple().tm_mon

        # detector wavelength
        block.wavelen = np.zeros((ysize, xsize, nbands), dtype='float32') + np.NaN
        block.cwavelen = np.zeros(nbands, dtype='float32') + np.NaN
        for iband, band in enumerate(bands):
            block.wavelen[:,:,iband] = self.central_wavelength[band]
            block.cwavelen[iband] = self.central_wavelength[band]

        return block

    def blocks(self, bands_read):
        nblocks = int(np.ceil(float(self.height)/self.blocksize))
        for iblock in range(nblocks):
            # determine block size
            xsize = self.width
            if iblock == nblocks-1:
                ysize = self.height-(nblocks-1)*self.blocksize
            else:
                ysize = self.blocksize
            size = (ysize, xsize)

            # determine the block offset
            xoffset = 0
            yoffset = iblock*self.blocksize
            offset = (yoffset, xoffset)

            yield self.read_block(size, offset, bands_read)

    def attributes(self, datefmt):
        attr = OrderedDict()
        attr['datetime'] = self.centertimedate
        return attr

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
