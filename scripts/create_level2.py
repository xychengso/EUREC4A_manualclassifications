"""
Script to convert level 1 data
to level 2 data

This level2 dataset includes:
   - masks for each classification

The output is an array with the dimensions
    classification_ids x image_x x image_y x 4
"""

# Path to zooniverse files
clas_fn = '../zooniverse_raw/sugar-flower-fish-or-gravel-classifications.csv'
subj_fn = '../zooniverse_raw/sugar-flower-fish-or-gravel-subjects.csv'

# Level1 filename
level1_file = '../processed_data/EUREC4A_ManualClassifications_l1.nc'

# Level2 filename
level2_file = '../processed_data/EUREC4A_ManualClassifications_MergedClassifications.zarr'

# Define subject sets of interest
subjs_of_interest = [81160, 81382, 80697, 80696]

import sys
# Path to pycloud folder (https://github.com/raspstephan/sugar-flower-fish-or-gravel/tree/master/pyclouds)
sys.path.append("/Users/haukeschulz/Documents/PhD/Work/Own/AI_CloudClassification/CloudClassificationDay/cloud-classification/")

sys.path.append("../helpers/")

import os
import subprocess
import time
import tqdm
import numpy as np
import pandas as pd
import datetime as dt
import logging
import dask.array as da
import xarray as xr
import zarr
from pyclouds import *
import general_helpers as g
from helpers import *

g.setup_logging('INFO')

try:
    git_module_version = subprocess.check_output(["git", "describe", "--dirty"]).strip().decode("utf-8")
except:
    git_module_version = "--"

logging.info('Open Level1 file')
ds_l1 = xr.open_dataset(level1_file)
df_l1 = ds_l1.to_dataframe()

nb_classifications = len(np.unique(df_l1.classification_id))
nb_lats = 1500
nb_lons = 2200
nb_patterns = 4

boxes_arr = np.empty(len(df_l1.groupby('classification_id')),dtype=object)
for c, (clas_id, clas_df) in enumerate(df_l1.groupby('classification_id')):
    boxes = clas_df.loc[:,['x','y','width','height','tool_label']].values
    boxes_arr[c] = boxes

# Create file and calculate common boxes
logging.info('Level2 data creation started')
store = zarr.DirectoryStore(level2_file)
root_grp = zarr.group(store, overwrite=True)
mask = root_grp.create_dataset('mask', shape=(nb_classifications, nb_lons, nb_lats, nb_patterns),
                               chunks=(1, nb_lons, nb_lats, nb_patterns),
                               dtype=bool, compressor=zarr.Zlib(level=1))
clas_ids = root_grp.create_dataset('classification_id', shape=(nb_classifications), chunks=(1),
                        dtype=int, compressor=zarr.Zlib(level=1))
lats = root_grp.create_dataset('latitude', shape=(nb_lats), chunks=(nb_lats),
                        dtype=float, compressor=zarr.Zlib(level=1))
lons = root_grp.create_dataset('longitude', shape=(nb_lons), chunks=(nb_lons),
                        dtype=float, compressor=zarr.Zlib(level=1))
patterns = root_grp.create_dataset('pattern', shape=(nb_patterns), chunks=(nb_patterns),
                        dtype=str, compressor=zarr.Zlib(level=1))


# z_arr = zarr.convenience.open(level2_file, mode='a',
#               shape=(len(np.unique(df_l1.classification_id)), 2200, 1500, 4),
#               chunks=(1, 2200, 1500, 4), dtype=bool)

for b, box in enumerate(tqdm.tqdm(boxes_arr)):
    mask[b,:,:,:] = most_common_boxes(box,return_all_pattern=True,imag_dim=(nb_lons,nb_lats))
    
clas_ids[:] = np.unique(df_l1.classification_id)
lons[:] = np.linspace(-62,-40,nb_lons)
lats[:] = np.linspace(20,5,nb_lats)
patterns[:] = ['Sugar', 'Flowers', 'Fish', 'Gravel']

# Add attributes to file
# Variable attributes
mask.attrs['_ARRAY_DIMENSIONS'] = ('classification_id', 'longitude', 'latitude', 'pattern')
mask.attrs['description'] = 'classification mask for every single pattern and classification_id'
lons.attrs['_ARRAY_DIMENSIONS'] = ('longitude')
lons.attrs['standard_name'] = 'longitude'
lons.attrs['units'] = 'degree_east'
lats.attrs['_ARRAY_DIMENSIONS'] = ('latitude')
lats.attrs['standard_name'] = 'latitude'
lats.attrs['units'] = 'degree_north'
clas_ids.attrs['_ARRAY_DIMENSIONS'] = ('classification_id')
clas_ids.attrs['description'] = 'classification id (basically each sighting of an image has a unique id)'
patterns.attrs['_ARRAY_DIMENSIONS'] = ('pattern')

# Global attributes
root_grp.attrs['title'] = 'EUREC4A: manual meso-scale cloud pattern classifications'
root_grp.attrs['description'] = 'Level-2: classification masks'
root_grp.attrs['author'] = 'Hauke Schulz (hauke.schulz@mpimet.mpg.de)'
root_grp.attrs['institute'] = 'Max Planck Institut für Meteorologie, Germany'
root_grp.attrs['created_on'] = dt.datetime.now().strftime('%Y-%m-%d %H:%M UTC')
root_grp.attrs['created_with'] = os.path.basename(__file__) + " with its last modification on " + time.ctime(
            os.path.getmtime(os.path.realpath(__file__)))
root_grp.attrs['version'] = git_module_version
root_grp.attrs['python_version'] = "{}".format(sys.version)

logging.info('Level2 data creation completed')
