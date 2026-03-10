from preprocessing import AOI, START_DATE, END_DATE
from preprocessing import add_cld_shdw_mask, add_spectral_indices, apply_cld_shdw_mask, get_s2_sr_cld_col

import ee
import folium

def add_ee_layer(self, ee_image_object, vis_params, name, show=True, opacity=1, min_zoom=0):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        show=show,
        opacity=opacity,
        min_zoom=min_zoom,
        overlay=True,
        control=True
        ).add_to(self)

folium.Map.add_ee_layer = add_ee_layer


def display_cloud_layers(col):
    img = col.mosaic()

    # Subset layers and prepare them for display.
    clouds = img.select('clouds').selfMask()
    shadows = img.select('shadows').selfMask()
    dark_pixels = img.select('dark_pixels').selfMask()
    probability = img.select('probability')
    cloudmask = img.select('cloudmask').selfMask()
    cloud_transform = img.select('cloud_transform')

    center = AOI.centroid(10).coordinates().reverse().getInfo()
    m = folium.Map(location=center, zoom_start=12)

    m.add_ee_layer(img,
                   {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 2500, 'gamma': 1.1},
                   'S2 image', True, 1, 9)
    m.add_ee_layer(probability,
                   {'min': 0, 'max': 100},
                   'probability (cloud)', False, 1, 9)
    m.add_ee_layer(clouds,
                   {'palette': 'e056fd'},
                   'clouds', False, 1, 9)
    m.add_ee_layer(cloud_transform,
                   {'min': 0, 'max': 1, 'palette': ['white', 'black']},
                   'cloud_transform', False, 1, 9)
    m.add_ee_layer(dark_pixels,
                   {'palette': 'orange'},
                   'dark_pixels', False, 1, 9)
    m.add_ee_layer(shadows, {'palette': 'yellow'},
                   'shadows', False, 1, 9)
    m.add_ee_layer(cloudmask, {'palette': 'orange'},
                   'cloudmask', True, 0.5, 9)

    m.add_child(folium.LayerControl())
    m.save("s2-cloud-layers.html")


if __name__ == "__main__":
    s2_sr_cld_col_eval = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)
    s2_sr_cld_col_eval_disp = s2_sr_cld_col_eval.map(add_cld_shdw_mask)
    display_cloud_layers(s2_sr_cld_col_eval_disp)

    s2_sr_cld_col = get_s2_sr_cld_col(ee.Geometry.Rectangle(-150, 60, -140, 65), '2020-06-01', '2020-09-01')

    s2_sr_median = (s2_sr_cld_col.map(add_cld_shdw_mask)
                    .map(apply_cld_shdw_mask)
                    .map(add_spectral_indices)
                    .median().clip(AOI))

    center = AOI.centroid(10).coordinates().reverse().getInfo()
    m = folium.Map(location=center, zoom_start=12)

    m.add_ee_layer(s2_sr_median,
                   {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 2500, 'gamma': 1.1},
                   'S2 cloud-free mosaic', True, 1, 9)
    m.add_ee_layer(s2_sr_median.select("NDVI"),
                   {'min': -1, "max": 1, "palette": ["blue", "white", "green"]},
                   "NDVI vegetation index", False)

    stats = s2_sr_median.select('NDVI').reduceRegion(
        reducer = ee.Reducer.mean(),
        geometry = AOI,
        scale = 10,
        maxPixels = 1_0000_0000_00
    )

    print("Mean NDVI in AOI:", stats.getInfo())

    m.add_child(folium.LayerControl())

    m.save("s2_cloud_free_mosaic.html")


    # ee does computatios on cloud, so the GeoTIFF export must go to a cloud destination first

    export_task = ee.batch.Export.image.toDrive(
        image = s2_sr_median,
        description = "sentinel2_cloudfree_composite",
        folder = "earthengine",
        fileNamePrefix = "s2_cloudfree",
        region = AOI,
        scale = 10,
        maxPixels = 1_0000_0000_0000_0,
    )

    export_task.start()
    print("Export started. GeoTIFF will be available in Google Drive.")
