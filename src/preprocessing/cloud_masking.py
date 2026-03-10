from .config import BUFFER, CLD_PRB_THRESH, CLD_PRJ_DIST, CLOUD_FILTER, NIR_DRK_THRESH

import ee


def get_s2_sr_cld_col(aoi, start_date, end_date) -> ee.ImageCollection:
    """
    [Sentinel-2 surface reflectance](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR) and
    [Sentinel-2 cloud probability](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_CLOUD_PROBABILITY)
    are two different image collections. Each collection must be filtered similarly (e.g., by date and bounds) and then
    the two filtered collections must be joined.

    Define a function to filter the SR and s2cloudless collections according to area of interest and date parameters,
    then join them on the `system:index` property. The result is a copy of the SR collection where each image has a
    new `'s2cloudless'` property whose value is the corresponding s2cloudless image.

    :return: Combined image collection of both SR and s2cloudless
    """

    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))


def add_cloud_bands(img):
    """
    :return: Adds two additional bands(cloud-probability and whether the probability is greater than threshold or not)
            to the given image.
    """
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')
    return img.addBands(ee.Image([cld_prb, is_cloud]))

def add_shadow_bands(img):
    """
    Adds dark pixels, cloud projection, and identified shadows as bands to an S2 SR image input.
    Note that the image input needs to be the result of the above `add_cloud_bands` function because it relies on
    knowing which pixels are considered cloudy (`'clouds'` band).
    """
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    shadows = cld_proj.multiply(dark_pixels).rename('shadows')
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

def add_cld_shdw_mask(img):
    """
    Assembles all of the cloud and cloud shadow components and produce the final mask.
    """
    img_cloud = add_cloud_bands(img)
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    return img_cloud_shadow.addBands(is_cld_shdw)

def apply_cld_shdw_mask(img):
    """
    Apply the cloud mask to each image in the collection.
    """
    not_cld_shdw = img.select('cloudmask').Not()
    return img.select('B.*').updateMask(not_cld_shdw)

def add_spectral_indices(img):
    """
    Adds common multispectral indices used in remote sensing.
    NDVI  – vegetation health
    NDWI  – water detection
    NBR   – burn severity indicator
    """
    ndvi = img.normalizedDifference(['B8','B4']).rename('NDVI')
    ndwi = img.normalizedDifference(['B3','B8']).rename('NDWI')
    nbr  = img.normalizedDifference(['B8','B12']).rename('NBR')

    return img.addBands([ndvi, ndwi, nbr])
