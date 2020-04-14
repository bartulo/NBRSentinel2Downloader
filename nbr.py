#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Descarga de imagenes Sentinel-2
Script para descargar imagenes del satélite Sentinel-2
usando las credenciales de sci-hub y un fichero geojson para determinar la localiazción
'''

import sys
import argparse
import numpy as np
from osgeo import gdal
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date, timedelta
import requests
import inquirer

def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('geojson', metavar='file', type=str, help='un fichero geojson que describa la zona de busqueda')
    parser.add_argument('--days', help='número de días desde la fecha actual a partir de la que realizar la busqueda', default=10)
    return parser.parse_args(args)

def download(url, filename, api_s):
    with open(filename, 'wb') as f:
        response = api_s.get(url, stream=True)
        total = response.headers.get('content-length')

        if total is None:
            f.write(response.content)
        else:
            downloaded = 0
            total = int(total)
            print('Downloading %s' % filename)
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                downloaded += len(data)
                f.write(data)
                done = int(50*downloaded/total)
                sys.stdout.write('\r[{}{}]'.format('█' * done, '.' * (50-done)))
                sys.stdout.flush()
    sys.stdout.write('\n')

def generate_nbr():
    dim = b8.shape
    factor = b8.shape[0] / b12.shape[0]

    b8 = b8.astype('int32')
    b12_ = np.repeat(np.repeat(b12, factor, axis = 0), factor, axis=1)
    b12 = b12_.astype('int32')
    nbr = (b8 - b12) / (b8 + b12)
    nbr = nbr.astype('float32')

    driver = gdal.GetDriverByName('GTiff')
    dst = driver.Create('prueba.tiff', xsize = dim[0], ysize = dim[1], bands = 1, eType = gdal.GDT_Float32)

    dst.SetGeoTransform(banda8.GetGeoTransform())
    dst.SetProjection(banda8.GetProjection())

    dst.GetRasterBand(1).WriteArray(nbr)
    dst = None

def main(options):
    api = SentinelAPI('bartulo', 'ventanuco')
    footprint = geojson_to_wkt(read_geojson(options.geojson))
    products = api.query( footprint, 
                          date = ( date.today() - timedelta(options.days), date.today() + timedelta(1)),
                          producttype = 'S2MSI2A',
                          platformname = 'Sentinel-2')

    data = api.to_geojson(products)['features']

    question_name = 'capa'
    questions = [
            inquirer.List(
                question_name,
                message = 'Imagenes disponibles',
                choices = ["Id: %s - Fecha: %s - Cobertura de nubes:%.4s%%" % (i, data[i]['properties']['beginposition'], data[i]['properties']['cloudcoverpercentage']) for i in range(len(data))],
                ),
            ]

    answers = inquirer.prompt(questions)
    index = int(answers[question_name].split('-')[0].split(':')[1].replace(' ', ''))
    baseURL = data[index]['properties']['link_alternative']
    filename = data[index]['properties']['filename']
                
    api_session = requests.Session()
    api_session.auth = ('bartulo', 'ventanuco')
    granules = api_session.get("%s/Nodes('%s')/Nodes('GRANULE')/Nodes?$format=json" % (baseURL, filename)).json()
    granules_id = granules['d']['results'][0]['Id']
    print("%s/Nodes('%s')/Nodes('GRANULE')/Nodes?$format=json" % (baseURL, filename))

    bands_10m = api_session.get("%s/Nodes('%s')/Nodes('GRANULE')/Nodes('%s')/Nodes('IMG_DATA')/Nodes('R10m')/Nodes?$format=json" % (baseURL, filename, granules_id)).json()
    band8 = bands_10m['d']['results'][4]['__metadata']['media_src']
    bandColor = bands_10m['d']['results'][5]['__metadata']['media_src']

    bands_20m = api_session.get("%s/Nodes('%s')/Nodes('GRANULE')/Nodes('%s')/Nodes('IMG_DATA')/Nodes('R20m')/Nodes?$format=json" % (baseURL, filename, granules_id)).json()
    band12 = bands_20m['d']['results'][8]['__metadata']['media_src']
    print("%s/Nodes('%s')/Nodes('GRANULE')/Nodes('%s')/Nodes('IMG_DATA')/Nodes('R20m')/Nodes?$format=json" % (baseURL, filename, granules_id))

#    download(band12, 'banda12.jp2', api_session)
#    download(band8, 'banda8.jp2', api_session)
#    download(bandColor, 'color.jp2', api_session)

    banda8 = gdal.Open('banda8.jp2')
    banda12 = gdal.Open('banda12.jp2')

    b8 = banda8.ReadAsArray()
    b12 = banda12.ReadAsArray()

if __name__ == "__main__":
    options = parse_args()
    print(options)
    main(options)
