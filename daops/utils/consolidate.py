import collections
import glob
import os
import xarray as xr

from daops.utils.core import _wrap_sequence
from roocs_utils.project_utils import get_project_base_dir, get_project_name

from daops import logging

LOGGER = logging.getLogger(__file__)


def _consolidate_dset(dset):
    if dset.startswith('https'):
        raise Exception('This format is not supported yet')
    elif os.path.isfile(dset) or dset.endswith('.nc'):
        return dset
    elif os.path.isdir(dset):
        return os.path.join(dset, '*.nc')
    elif dset.count('.') > 6:
        project = get_project_name(dset)
        base_dir = get_project_base_dir(project)
        return base_dir.rstrip("/") + "/" + dset.replace(".", "/") + "/*.nc"
    else:
        raise Exception(f'The format of {dset} is not known.')


def consolidate(collection, **kwargs):
    collection = _wrap_sequence(collection.tuple)

    filtered_refs = collections.OrderedDict()

    for dset in collection:
        consolidated = _consolidate_dset(dset)

        if "time" in kwargs:
            time = kwargs["time"].asdict()

            file_paths = glob.glob(consolidated)
            LOGGER.info(f"Testing {len(file_paths)} files in time range: ...")
            files_in_range = []

            ds = xr.open_mfdataset(file_paths, use_cftime=True)

            if time['start_time'] is None:
                time['start_time'] = ds.time.values.min().strftime("%Y")
            if time['end_time'] is None:
                time['end_time'] = ds.time.values.max().strftime("%Y")

            times = [int(time['start_time'].split('-')[0]), int(time['end_time'].split('-')[0]) + 1]
            required_years = set(range(*[_ for _ in times]))

            for i, fpath in enumerate(file_paths):

                LOGGER.info(f"File {i}: {fpath}")
                ds = xr.open_dataset(fpath)

                found_years = set([int(_) for _ in ds.time.dt.year])

                if required_years.intersection(found_years):
                    files_in_range.append(fpath)

            LOGGER.info(f"Kept {len(files_in_range)} files")
            consolidated = files_in_range[:]
            if len(files_in_range) == 0:
                raise Exception(f"No files found in given time range for {dset}")

        filtered_refs[dset] = consolidated

    return filtered_refs
