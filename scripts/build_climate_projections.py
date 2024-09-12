# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Creates a dataset corresponding to the projected climate in a requested year.

Relevant Settings
-----------------

.. code:: yaml

    projection:
        climate_scenario:
        base_year:
        future_year:
        years_window:
        gcm_selection:

Inputs
------

- ``cutouts/cutout.nc``: confer :ref:`cutout`, a cutout file produced by altile
- ``data/cmip6_avr.nc``: confer :ref:`cmip6`, a global-scale dataset of the global climate
CMIP6 projections aggregated into IPCC Global Climate Atlas

Outputs
-------

- ``cutouts/proj-{cutout}.nc"``: confer :ref:`proj`, a cutout modified to account for future
climate conditions

Description
-----------

The rule :mod:`build_climate_projections` creates a cutout file which corresponds to
a requested year in the future. The parameter projections is calculated combining data
for cutout.nc which is assumed to be representative data sample for the past climate and
an ensemble of CMIP6 global climate models to account for the future climate.

A morphing approach is implemented meaning that the projection value x_future is calculated
data for a representative period base_year in the past x_past using a combination
of shift dx and stretch a:

x_future = x_past + dx + a(x_past - <x_past>|month),

where
x_future and x_past have the highest temporal resolution,
<x_past>|month is the monthly average for a considered month.

A value of the stretch is calculated using projections for minimal and maximal values
of the climate parameter.

The procedure is applied for each month to account for seasonality. Snapshots settings
are used to define for which months to be used in calculating a climate projection.

Methodology notes
-----------------
Originally the morphing approach originates from buildings physics, and is still in active
use for detailed simulation of heat transfer in buildings. See, for example:

J.B. Dias, G.C. da Graça, P.M.M. Soares (2020) Comparison of methodologies for
generation of future  building thermal energy simulation. Energy and Buildings,
vol. 206, 109556, https://doi.org/10.1016/j.enbuild.2019.109556.

J. Pulkkinen, J.-N. Louis (2021) Near- and medium-term hourly morphed mean and
extreme future temperature datasets for Jyväskylä, Finland, for building thermal
energy demand simulations. Data in Brief, vol. 37, 107209,
https://doi.org/10.1016/j.dib.2021.107209.
"""


import datetime as dt
import os

import atlite
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from _helpers import configure_logging, create_logger
from shapely.geometry import LineString as Line
from shapely.geometry import Point

logger = create_logger(__name__)


def crop_cmip6(cmip6_xr, cutout_xr):
    """
    Crop the global-scale CMIP6 dataset to match the cutout extend.

    Parameters
    ----------
    cmip6_xr: xarray
        CMIP6 climate projections loaded as xarray
    cutout_xr : xarray of a cutout dataset
        Cutout dataset loaded as xarray

    Returns
    -------
    cmip6_region: xarray
        Clipped according to an area of interest
    """

    # spartial margin needed to avoid data losses during further interpolation
    d_pad = 1

    cmip6_region = cmip6_xr.sel(
        lat=slice(
            min(cutout_xr.coords["y"].values) - d_pad,
            max(cutout_xr.coords["y"].values) + d_pad,
        ),
        lon=slice(
            min(cutout_xr.coords["x"].values) - d_pad,
            max(cutout_xr.coords["x"].values) + d_pad,
        ),
    )
    return cmip6_region


def interpolate_cmip6_to_cutout_grid(cmip6_xr, cutout_xr):
    """
    Interpolate CMIP6 dataset to the cutout grid.

    Parameters
    ----------
    cmip6_xr: xarray
        CMIP6 climate projections loaded as xarray
    cutout_xr : xarray of a cutout dataset
        Cutout dataset loaded as xarray

    Returns
    -------
    cmip6_interp: xarray
        Interpolated to the grid identical to the cutout one
    """
    newlon = np.arange(
        round(np.min(cutout_xr.coords["x"].values), 1),
        round(np.max(cutout_xr.coords["x"].values) + cutout_xr.attrs["dx"], 1),
        cutout_xr.attrs["dx"],
    )
    newlat = np.arange(
        round(np.min(cutout_xr.coords["y"].values), 1),
        round(np.max(cutout_xr.coords["y"].values) + cutout_xr.attrs["dy"], 1),
        cutout_xr.attrs["dy"],
    )
    cmip6_interp = cmip6_xr.interp(time=cmip6_xr.time, lat=newlat, lon=newlon)

    return cmip6_interp


def prepare_cmip6(
    cmip6_fl,
    cutout_xr,
    months,
    base_year,
    predict_year,
    years_window,
):
    """
    Prepare the CMIP6 for calculation projections for the area of interest.

    Parameters
    ----------
    cmip6_xr: xarray
        CMIP6 climate projections loaded as xarray
    cutout_xr : xarray of a cutout dataset
        Cutout dataset loaded as xarray
    months: list
        A list of month numbers to be considered further projection
    base_year: integer
        The first year of an earlier period in the future
    predict_year: integer
        The first year of a later period in the future
    years_window: integer
        Width of the considered time period

    Returns
    -------
    cmip6_interp: xarray
        Now clipped to the region and interpolated to match with the cutour grid
    """
    cmip6_xr = xr.open_dataset(cmip6_fl)

    # All the requested data from the projection period should present in the CMIP6 datasets
    year_month_df = pd.DataFrame(
        {
            "year": cmip6_xr.time.dt.year.to_series(),
            "month": cmip6_xr.time.dt.month.to_series(),
        }
    )
    cmip6_in_base = year_month_df.apply(
        lambda row: (row["year"] >= (base_year))
        & (row["year"] < (base_year + years_window))
        & (row["month"] in months),
        axis=1,
    )
    cmip6_in_future = year_month_df.apply(
        lambda row: (row["year"] <= (predict_year))
        & (row["year"] > (predict_year - years_window))
        & (row["month"] in months),
        axis=1,
    )

    if sum(cmip6_in_base) == 0:
        raise Exception(
            f"No data to build a projection are available in the provided CMIP6 data "
            f"for the base year {base_year}-{base_year + years_window - 1}.\n\r"
        )
    if sum(cmip6_in_future) == 0:
        raise Exception(
            f"No data to build a projection are available in the provided CMIP6 data "
            f"for the base year {predict_year}-{predict_year - years_window + 1}.\n\r"
        )

    if sum(cmip6_in_base) < (len(months) * years_window):
        logger.warning(
            f"The requested projection period is not fully covered by the provided CMIP6 data. "
            f"The requested base period is {base_year}-{base_year + years_window - 1}\n\r"
        )
    if sum(cmip6_in_future) < (len(months) * years_window):
        logger.warning(
            f"The requested projection period is not fully covered by the provided CMIP6 data. "
            f"The requested base period is {predict_year}-{predict_year - years_window + 1}\n\r"
        )

    cmip6_cropped_xr = crop_cmip6(cmip6_xr, cutout_xr)
    cmip6_interp = interpolate_cmip6_to_cutout_grid(
        cmip6_xr=cmip6_cropped_xr, cutout_xr=cutout_xr
    )
    return cmip6_interp


def subset_by_time(cmip6_xr, month, year, years_window):
    """
    Filter CMIP6 dataset according to the requested year and the processed
    month.

    Parameters
    ----------
    cmip6_xr: xarray
        CMIP6 climate projections loaded as xarray
    month: integer
        A month value to be considered further for the morphing procedure
    year: integer
        The first year of the requested period in the future
    years_window: integer
        A width of the considered time period

    Returns
    -------
    cmip6_in_period: xarray
        Sub-setted for a month and a years range of interest

    Example
    -------
    month=3, year=2050, years_window=30
    filters CMIP6 cmip6_xr dataset to calculate projection for March at 2050-2079
    """

    cmip6_in_period = cmip6_xr.where(
        (
            (cmip6_xr["time.month"] == month)
            & (cmip6_xr["time.year"] >= year - years_window)
            & (cmip6_xr["time.year"] < year + years_window - 1)
        ),
        drop=True,
    )
    return cmip6_in_period


# TODO add functionality to customise CMIP6 ensemble
def calculate_proj_of_average(
    cmip6_xr, month, base_year, predict_year, years_window, cmip6_param_name="t"
):
    """
    Calculate a change in a monthly average value for a climate parameter for
    the requested year periods and the processed month (a single value for each
    grid cell)

    Parameters
    ----------
    cmip6_xr: xarray
        CMIP6 climate projections loaded as xarray
    month: float
        A month value to be considered further for the morphing procedure
    base_year: integer
        The first year of an earlier period in the future
    predict_year: integer
        The first year of a later period in the future
    years_window: integer
        Width of the considered time period
    cmip6_param_name: string
        A name of CMIP6 parameter of interest

    Outputs
    -------
    dt_interp: xarray of the changes in the monthly averages for each grid cell
        Contains a single value for each grid cell.

    Example
    -------
    month=3, base_year=2020, base_year=2070, years_window=30
    calculates a multimodel change in the monthly average for
    March in 2020-2049 as compared with 2070-2099
    """

    cmip6_interp_base_year = subset_by_time(
        cmip6_xr, month, year=base_year, years_window=years_window
    )
    cmip6_interp_predict_year = subset_by_time(
        cmip6_xr, month=month, year=predict_year, years_window=years_window
    )
    dt_interp = cmip6_interp_predict_year[cmip6_param_name].mean("member").mean(
        "time"
    ) - cmip6_interp_base_year[cmip6_param_name].mean("member").mean("time")
    return dt_interp


def build_projection_for_month(
    cutout_xr, dt_xr, month, a, t_mean_month, cutout_param_name="temperature"
):
    """
    Calculate the projection for the cutout data applying the morphing approach
    using a dataset dt_xr for the changes in monthly aggregates for the
    processed month.

    Parameters
    ----------
    cutout_xr: xarray
        Cutout dataset loaded as xarray
    dt_xr: xarray
        Dataset of the changes in the monthly averages for each grid cell
    month: float
        A month value to be considered further for the morphing procedure
    cutout_param_name: string
        A name of a cutout parameter for which a projection is being calculated

    Output
    -------
    cutout_xr: xarray of the projected changes for each grid cell for a processed month
        Contains a time series for each grid cell.
    """

    k_time = cutout_xr.time.dt.month.isin(month)

    # stretch calculations
    if a & t_mean_month:
        dt_xr = dt_xr + a * (cutout_xr[cutout_param_name][k_time, :, :] - t_mean_month)

    for i in range(0, len(cutout_xr.y)):
        for j in range(0, len(cutout_xr.x)):
            cutout_xr[cutout_param_name][k_time, i, j] = np.add(
                cutout_xr[cutout_param_name][k_time, i, j],
                # spreading dt_xr which is of monthly resolution across the whole time dimension of a cutout
                # which is normally of hourly resolution
                np.array([dt_xr[i, j].item()] * k_time.sum().item()),
            )

    return cutout_xr


def build_cutout_future(
    cutout_xr,
    cmip6_xr,
    months,
    base_year,
    predict_year,
    years_window,
    cutout_param_name="temperature",
    add_stretch=False,
    cmip6_nn_xr=False,
    cmip6_xx_xr=False,
):
    """
    Calculate the projection for the cutout data applying the morphing approach
    for each month in the months.

    Parameters
    ----------
    cutout_xr: xarray
        Cutout dataset loaded as xarray
    cmip6_xr: xarray
        CMIP6 climate projections loaded as xarray
    months: list
        Months values to be used as a definition of a season to be considered
        for building projection time series
    base_year: integer
        The first year of an earlier period in the future
    predict_year: integer
        The first year of a later period in the future
    years_window: integer
        Width of the considered time period
    cutout_param_name: string
        A name of the variable to be read from the cutout
    add_stretch: boolean
        Add a stretch transformation to a shift when calculating a projection
    cmip6_nn_xr: xarray
        CMIP6 projection for the minimum of the climate parameter
    cmip6_xx_xr: xarray
        CMIP6 projection for the maximum of the climate parameter

    Output
    -------
    cutout_xr: xarray
        Dataset on the projected changes for each grid cell for a processed month
        Contains a time series for each grid cell.
    """
    for k_month in [months]:
        dt_k = calculate_proj_of_average(
            cmip6_xr=cmip6_xr,
            month=k_month,
            base_year=base_year,
            predict_year=predict_year,
            years_window=years_window,
        )

        a = False
        t_mean_month = False

        if add_stretch:
            # TODO Check cmip6_nn_xr and cmip6_xx_xr are not empty
            dt_nn_k = calculate_proj_of_average(
                cmip6_xr=cmip6_nn_xr,
                month=k_month,
                base_year=base_year,
                predict_year=predict_year,
                years_window=years_window,
            )
            dt_xx_k = calculate_proj_of_average(
                cmip6_xr=cmip6_xx_xr,
                month=k_month,
                base_year=base_year,
                predict_year=predict_year,
                years_window=years_window,
            )
            ddt_nx = dt_xx_k - dt_nn_k
            k_time = cutout_xr.time.dt.month.isin(k_month)
            t_mean_month = cutout_xr[cutout_param_name][k_time, :, :].mean()

            a = ddt_nx / t_mean_month

        build_projection_for_month(
            cutout_xr,
            dt_k,
            k_month,
            a=a,
            t_mean_month=t_mean_month,
            cutout_param_name=cutout_param_name,
        )

    cutout_xr = cutout_xr.where(cutout_xr.time.dt.month.isin(months), drop=True)

    return cutout_xr


def plot_cmpi6(cmip6_xr, param_name="t", fl_name="results/test_cmip6.png"):
    fig = plt.figure()
    cmip6_xr[param_name].mean("time").mean("member").plot()
    fig.savefig(fl_name, dpi=700)


def plot_cutout(
    cutout_xr, param_name="temperature", cmap="OrRd", fl_name="results/test_present.png"
):
    fig = plt.figure()
    if param_name == "temperature":
        (cutout_xr[param_name] - 273.15).mean("time").plot(cmap=cmap)
    else:
        (cutout_xr[param_name]).mean("time").plot(cmap=cmap)
    fig.savefig(fl_name, dpi=700)


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        snakemake = mock_snakemake(
            "build_climate_projections",
            climate_scenario="ssp2-2.6",
            base_year=2020,
            future_year=2050,
            years_window=5,
            cutout="africa-2013-era5",
        )
    configure_logging(snakemake)

    climate_scenario = snakemake.params.climate_scenario
    base_year = snakemake.params.base_year
    future_year = snakemake.params.future_year
    years_window = snakemake.params.years_window
    cmip6_nn_fl = snakemake.params.cmip6_nn_fl
    cmip6_xx_fl = snakemake.params.cmip6_xx_fl

    cutout = snakemake.input.cutout
    cmip6 = snakemake.input.cmip6_avr

    snapshots = pd.date_range(freq="h", **snakemake.params.snapshots)
    season_in_focus = snapshots.month.unique().to_list()

    cutout_xr = xr.open_dataset(cutout)

    cmip6_region_interp = prepare_cmip6(
        cmip6_fl=cmip6,
        cutout_xr=cutout_xr,
        months=season_in_focus,
        base_year=base_year,
        predict_year=future_year,
        years_window=years_window,
    )

    if cmip6_nn_fl:
        cmip6_nn_region_interp = prepare_cmip6(
            cmip6_fl=cmip6_nn_fl, cutout_xr=cutout_xr
        )

    if cmip6_xx_fl:
        cmip6_xx_region_interp = prepare_cmip6(
            cmip6_fl=cmip6_xx_fl, cutout_xr=cutout_xr
        )

    # -----------------------------------------------------------------
    #       to be replaced after debug
    # -----------------------------------------------------------------
    # graphical test of interpolation
    plot_cmpi6(cmip6_region_interp, fl_name="results/test_cmip6.png")
    plot_cmpi6(
        cmip6_nn_region_interp, param_name="tnn", fl_name="results/test_cmip6_nn.png"
    )
    plot_cmpi6(
        cmip6_xx_region_interp, param_name="txx", fl_name="results/test_cmip6_xx.png"
    )

    plot_cutout(cutout_xr, fl_name="results/test_present.png")

    # -----------------------------------------------------------------

    cutout_future = build_cutout_future(
        cutout_xr=cutout_xr,
        cmip6_xr=cmip6_region_interp,
        months=season_in_focus,
        base_year=base_year,
        predict_year=future_year,
        years_window=years_window,
    )

    cutout_future.to_netcdf(snakemake.output[0])

    # -----------------------------------------------------------------
    #       to be replaced after debug
    # -----------------------------------------------------------------
    # graphical test of projection
    plot_cutout(cutout_future, fl_name="results/test_cmip6_project_shift.png")

    cutout_future2 = build_cutout_future(
        cutout_xr=cutout_xr,
        cmip6_xr=cmip6_region_interp,
        months=season_in_focus,
        base_year=base_year,
        predict_year=future_year,
        years_window=years_window,
        cutout_param_name="temperature",
        cmip6_nn_xr=cmip6_nn_fl,
        cmip6_xx_xr=cmip6_xx_fl,
    )

    # -----------------------------------------------------------------
    #       to be replaced after debug
    # -----------------------------------------------------------------
    # graphical test of projection
    plot_cutout(cutout_future2, fl_name="results/test_cmip6_project_full.png")
