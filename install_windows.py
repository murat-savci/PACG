# Because windows has no 'make' tool. We select to run a python script to install Polymer and auxdata. This file is a python transfer of makefile.
# Author: feng qiao
import os
import wget
import shutil
import hashlib


def main():
    cmd = 'python setup.py build_ext --inplace'
    os.system(cmd)


def auxdata_all():
    auxdata_common()
    # auxdata_meris()
    # auxdata_olci()
    # auxdata_modisa()
    # auxdata_seawifs()
    # auxdata_viirs()
    # auxdata_msi()
    auxdata_oli()


def auxdata_oli():
    # base url for auxiliary data download
    URL = 'http://download.hygeos.com/POLYMER/auxdata'
    auxdata = 'auxdata'
    oli = 'oli'
    auxdata_oli_dict = {'Ball_BA_RSR.v1.2.xlsx': {'path': oli,
                                                  'MD5': '3bd7911f9544917130d1feb45f0ef31e'}}
    os.makedirs(os.path.join(auxdata, oli), exist_ok=True)
    for name, dict in auxdata_oli_dict.items():
        url = '{}/{}/{}'.format(URL, dict['path'], name)
        file = os.path.join(auxdata, dict['path'], name)
        if os.path.exists(file):
            # Cheack MD5
            with open(file, 'rb') as f:
                MD5_cheack = dict['MD5'] == hashlib.md5(f.read()).hexdigest()
            if not MD5_cheack:
                print('\nDownloading {} from {}.'.format(name, url))
                wget.download(url, out=file)
        else:
            print('\nDownloading {} from {}.'.format(name, url))
            wget.download(url, out=file)

def auxdata_common():
    auxdata = 'auxdata'
    common = 'common'
    generic = 'generic'

    # base url for auxiliary data download
    URL = 'http://download.hygeos.com/POLYMER/auxdata'
    os.makedirs(os.path.join(auxdata, common), exist_ok=True)
    os.makedirs(os.path.join(auxdata, generic), exist_ok=True)
    auxdata_common_dict = {
        'LUT.hdf': {'path': generic, 'MD5': '4cfc8b2ab76b1b2b2ea85611940ae6e2'},
        'no2_climatology.hdf': {'path': common, 'MD5': 'b88aadd272734634b756922ad5b6f439'},
        'trop_f_no2_200m.hdf': {'path': common, 'MD5': '10350ad3441c9e76346f6429985f3c71'},
        'morel_fq.dat': {'path':  common, 'MD5': '7f3ba3b9ff13b9f135c53256d02a8b1b'},
        'AboveRrs_gCoef_w0.dat': {'path': common, 'MD5': '44d9d702654ed7a35ba0a481a66be604'},
        'AboveRrs_gCoef_w10.dat': {'path': common, 'MD5': '5f1eea393b1fda6d25f54ad34f93c450'},
        'AboveRrs_gCoef_w5.dat': {'path': common, 'MD5': 'f86841556820841ed0d623a69cbc9984'},
        'aph_bricaud_1995.txt': {'path': common, 'MD5': '6ae4d62a28140e7221ad615ef4a59e8f'},
        'aph_bricaud_1998.txt': {'path': common, 'MD5': 'c998374a93b993123d6f85e9f627787d'},
        'morel_buiteveld_bsw.txt': {'path': common, 'MD5': '7f178e809c8b8d4f379a26df7d258640'},
        'palmer74.dat': {'path': common, 'MD5': 'a7896ee2b35e09cacbeb96be69883026'},
        'pope97.dat': {'path': common, 'MD5': 'ba868100590c3248e14892c32b18955d'},
        'raman_westberry13.txt': {'path': common, 'MD5': '0dda3b7d9e2062abbb24f55f86ededf5'},
        'astarmin_average_2015_SLSTR.txt': {'path': common, 'MD5': 'c340ec49f1ad3214a4ee84a19652b7ac'},
        'astarmin_average.txt': {'path': common, 'MD5': '56cd52dfaf2dab55b67398ac9adcbded'},
        'Matsuoka11_aphy_Table1_JGR.csv': {'path': common, 'MD5': '862c49b5dd19c9b09e451891ef11ce50'},
        'k_oz.csv': {'path': common, 'MD5': 'dfe0ca3e6f37d7525675e50f6f0352fc'},
        'SOLAR_SPECTRUM_WMO_86': {'path': common, 'MD5': '9290372ca2a4cab5ddd9eaed9b9942c1'}
    }
    for name, dict in auxdata_common_dict.items():
        url = '{}/{}/{}'.format(URL, dict['path'], name)
        file = os.path.join(auxdata, dict['path'], name)
        if os.path.exists(file):
            # Cheack MD5
            with open(file, 'rb') as f:
                MD5_cheack = dict['MD5'] == hashlib.md5(f.read()).hexdigest()
            if not MD5_cheack:
                print('\nDownloading {} from {}.'.format(name, url))
                wget.download(url, out=file)
        else:
            print('\nDownloading {} from {}.'.format(name, url))
            wget.download(url, out=file)


def ancillary():
    os.makedirs(os.path.join('ANCILLARY', 'METEO'), exist_ok=True)


def all():
    auxdata_all()
    main()
    ancillary()


def clean():
    if os.path.exists('build'):
        shutil.rmtree('build')
    for f in os.listdir('polymer'):
        if f.endswith('.pyd') or f.endswith('.so'):
            os.remove(os.path.join('polymer', f))


def rebuild():
    clean()
    all()


if __name__ == '__main__':

    # main()
    rebuild()
