import ee

ee.Authenticate()
ee.Initialize(project='s2cloudles')

"""
|Parameter | Type | Description |
| :-- | :-- | :-- |
| `AOI` | `ee.Geometry` | Area of interest |
| `START_DATE` | string | Image collection start date (inclusive) |
| `END_DATE` | string | Image collection end date (exclusive) |
| `CLOUD_FILTER` | integer | Maximum image cloud cover percent allowed in image collection |
| `CLD_PRB_THRESH` | integer | Cloud probability (%); values greater than are considered cloud |
| `NIR_DRK_THRESH` | float | Near-infrared reflectance; values less than are considered potential cloud shadow |
| `CLD_PRJ_DIST` | float | Maximum distance (km) to search for cloud shadows from cloud edges |
| `BUFFER` | integer | Distance (m) to dilate the edge of cloud-identified objects |
"""

AOI = ee.Geometry.Rectangle(-147.5, 64.5, -146.5, 65.5)
START_DATE = '2020-06-01'
END_DATE = '2020-06-02'
CLOUD_FILTER = 60
CLD_PRB_THRESH = 50
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 1
BUFFER = 50