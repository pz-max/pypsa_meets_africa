# -*- coding: utf-8 -*-
# Copyright 2019-2020 Fabian Hofmann (FIAS)
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.5894972.svg
   :target: https://doi.org/10.5281/zenodo.5894972

The data bundles contains common GIS datasets like EEZ shapes, Copernicus Landcover, Hydrobasins
and also electricity specific summary statistics like historic per country yearly totals of hydro generation,
GDP and POP on NUTS3 levels and per-country load time-series.

This rule downloads the data bundle from `zenodo <https://doi.org/10.5281/zenodo.5894972>`_
or `google drive <https://drive.google.com/drive/u/1/folders/1dkW1wKBWvSY4i-XEuQFFBj242p0VdUlM>`_
and extracts it in the ``data``, ``resources`` and ``cutouts`` sub-directory.
Bundle data are then deleted once downloaded and unzipped.

The :ref:`tutorial` uses a smaller `data bundle <https://zenodo.org/record/3517921/files/pypsa-eur-tutorial-data-bundle.tar.xz>`_
than required for the full model (around 500 MB)

The required bundles are downloaded automatically according to the list names, in agreement to
the data bundles specified in the bundle configuration file, typically located in the ``config`` folder.
Each data bundle entry has the following structure:

.. code:: yaml

  bundle_name:  # name of the bundle
    countries: [country code, region code or country list]  # list of countries represented in the databundle
    [tutorial: true/false]  # (optional, default false) whether the bundle is a tutorial or not
    category: common/resources/data/cutouts  # category of data contained in the bundle:
    destination: "."  # folder where to unzip the files with respect to the repository root (\"\" or \".\")
    urls:  # list of urls by source, e.g. zenodo or google
      zenodo: {zenodo url}  # key to download data from zenodo
      gdrive: {google url}  # key to download data from google drive
      protectedplanet: {url}  # key to download data from protected planet; the url can contain {month:s} and {year:d} to let the workflow specify the current month and year
      direct: {url}  # key to download data directly from a url; if unzip option is enabled data are unzipped
      post:  # key to download data using an url post request; if unzip option is enabled data are unzipped
        url: {url}
        [post arguments]
    [unzip: true/false]  # (optional, default false) used in direct download technique to automatically unzip files
    output: [...]  # list of outputs of the databundle
    [disable_by_opt:]  # option to disable outputs from the bundle; it contains a dictionary of options, each one with
                       # each one with its output. When "all" is specified, the entire bundle is not executed
      [{option}: [outputs,...,/all]]  # list of options and the outputs to remove, or "all" corresponding to ignore everything

Depending on the country list that is asked to perform, all needed databundles are downloaded
according to the following rules:

- The databundle shall adhere to the tutorial configuration: when
  the tutorial configuration is running, only the databundles having tutorial flag true
  shall be downloaded
- For every data category, the most suitable bundles are downloaded by order of
  number of countries matched: for every bundles matching the category,
  the algorithm sorts the bundles by the number of countries that are matched and starts
  downloading them starting from those matching more countries till all countries are matched
  or no more bundles are available
- For every bundle to download, it is given priority to the first bundle source,
  as listed in the ``urls`` option of each bundle configuration; when a source fails,
  the following source is used and so on

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.3517921.svg
    :target: https://doi.org/10.5281/zenodo.3517921

**Relevant Settings**

.. code:: yaml

    tutorial:  # configuration stating whether the tutorial is needed


.. seealso::
    Documentation of the configuration file ``config.yaml`` at
    :ref:`toplevel_cf`

**Outputs**

- ``data``: input data unzipped into the data folder
- ``resources``: input data unzipped into the resources folder
- ``cutouts``: input data unzipped into the cutouts folder

"""
import datetime as dt
import os
import re
from zipfile import ZipFile

import geopandas as gpd
import googledrivedownloader as gdd
import pandas as pd
import yaml
from _helpers import (
    BASE_DIR,
    configure_logging,
    create_country_list,
    create_logger,
    progress_retrieve,
)
from tqdm import tqdm

logger = create_logger(__name__)


def load_databundle_config(config):
    "Load databundle configurations from path file or dictionary"

    if type(config) is str:
        with open(config) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)["databundles"]
    elif type(config) is not dict:
        logger.error("Impossible to load the databundle configuration")

    # parse the "countries" list specified in the file before processing
    for bundle_name in config:
        config[bundle_name]["countries"] = create_country_list(
            config[bundle_name]["countries"], iso_coding=False
        )

    return config


def download_and_unzip_zenodo(config, rootpath, hot_run=True, disable_progress=False):
    """
    download_and_unzip_zenodo(config, rootpath, dest_path, hot_run=True,
    disable_progress=False)

    Function to download and unzip the data from zenodo

    Inputs
    ------
    config : Dict
        Configuration data for the category to download
    rootpath : str
        Absolute path of the repository
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    resource = config["category"]
    file_path = os.path.join(rootpath, "tempfile.zip")
    destination = os.path.join(BASE_DIR, config["destination"])
    url = config["urls"]["zenodo"]

    if hot_run:
        try:
            logger.info(f"Downloading resource '{resource}' from cloud '{url}'")
            progress_retrieve(url, file_path, disable_progress=disable_progress)
            logger.info(f"Extracting resources")
            with ZipFile(file_path, "r") as zipObj:
                # Extract all the contents of zip file in current directory
                zipObj.extractall(path=destination)
            os.remove(file_path)
            logger.info(f"Downloaded resource '{resource}' from cloud '{url}'.")
        except:
            logger.warning(f"Failed download resource '{resource}' from cloud '{url}'.")
            return False

    return True


def download_and_unzip_gdrive(config, rootpath, hot_run=True, disable_progress=False):
    """
    download_and_unzip_gdrive(config, rootpath, dest_path, hot_run=True,
    disable_progress=False)

    Function to download and unzip the data from google drive

    Inputs
    ------
    config : Dict
        Configuration data for the category to download
    rootpath : str
        Absolute path of the repository
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    resource = config["category"]
    file_path = os.path.join(rootpath, "tempfile.zip")
    destination = os.path.join(BASE_DIR, config["destination"])
    url = config["urls"]["gdrive"]

    # retrieve file_id from path
    # cut the part before the ending \view
    partition_view = re.split(r"/view|\\view", str(url), 1)
    if len(partition_view) < 2:
        logger.error(
            f'Resource {resource} cannot be downloaded: "\\view" not found in url {url}'
        )
        return False

    # split url to get the file_id
    code_split = re.split(r"\\|/", partition_view[0])

    if len(code_split) < 2:
        logger.error(
            f'Resource {resource} cannot be downloaded: character "\\" not found in {partition_view[0]}'
        )
        return False

    # get file id
    file_id = code_split[-1]

    # if hot run enabled
    if hot_run:
        # remove file
        if os.path.exists(file_path):
            os.remove(file_path)
        # download file from google drive
        gdd.download_file_from_google_drive(
            file_id=file_id,
            dest_path=file_path,
            showsize=not disable_progress,
            unzip=False,
        )
        with ZipFile(file_path, "r") as zipObj:
            # Extract all the contents of zip file in current directory
            zipObj.extractall(path=destination)

        logger.info(f"Download resource '{resource}' from cloud '{url}'.")

        return True
    else:
        logger.error(f"Host {host} not implemented")
        return False


def download_and_unzip_protectedplanet(
    config, rootpath, attempts=3, hot_run=True, disable_progress=False
):
    """
    download_and_unzip_protectedplanet(config, rootpath, dest_path,
    hot_run=True, disable_progress=False)

    Function to download and unzip the data by category from protectedplanet

    Inputs
    ------
    config : Dict
        Configuration data for the category to download
    rootpath : str
        Absolute path of the repository
    attempts : int (default 3)
        Number of attempts to download the data by month.
        The download is attempted for the current and previous months according to the number of attempts
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    resource = config["category"]
    file_path = os.path.join(rootpath, "tempfile_wpda.zip")
    destination = os.path.join(BASE_DIR, config["destination"])
    url = config["urls"]["protectedplanet"]

    def get_first_day_of_month(date):
        return date.replace(day=1)

    def get_first_day_of_previous_month(date):
        return get_first_day_of_month(date - dt.timedelta(days=1))

    # starting from the next month to check the current and the previous after
    current_first_day = get_first_day_of_month(
        dt.datetime.today() + dt.timedelta(days=31)
    )

    if hot_run:
        if os.path.exists(file_path):
            os.remove(file_path)

        downloaded = False

        for i in range(attempts + 1):
            # customize url to current month
            month_MMM = current_first_day.strftime("%b")
            year_YYYY = current_first_day.year
            url_iter = url.format(month=month_MMM, year=year_YYYY)

            resource_iter = resource + " - " + month_MMM + " " + str(year_YYYY)

            try:
                logger.info(
                    f"Downloading resource '{resource_iter}' from cloud '{url_iter}'."
                )
                progress_retrieve(
                    url_iter, file_path, disable_progress=disable_progress
                )

                zip_obj = ZipFile(file_path, "r")

                # list of zip files, which contains the shape files
                zip_files = [
                    fname for fname in zip_obj.namelist() if fname.endswith(".zip")
                ]

                # if empty, the download failed
                if not zip_files:
                    raise Exception(
                        "Corrupted zip file downloaded from protectedplanet"
                    )

                # extract the nested zip files
                for fzip in zip_files:
                    # final path of the file
                    try:
                        inner_zipname = os.path.join(destination, fzip)

                        zip_obj.extract(fzip, path=destination)

                        dest_nested = os.path.join(destination, fzip.split(".")[0])

                        with ZipFile(inner_zipname, "r") as nested_zip:
                            nested_zip.extractall(path=dest_nested)

                        # remove inner zip file
                        os.remove(inner_zipname)

                        logger.info(f"{resource} - Successfully unzipped file '{fzip}'")
                    except:
                        logger.warning(
                            f"Exception while unzipping file '{fzip}' for {resource_iter}: skipped file"
                        )

                # close and remove outer zip file
                zip_obj.close()
                os.remove(file_path)

                logger.info(
                    f"Downloaded resource '{resource_iter}' from cloud '{url_iter}'."
                )

                downloaded = True
                break
            except:
                logger.warning(
                    f"Failed download resource '{resource_iter}' from cloud '{url_iter}'."
                )
                current_first_day = get_first_day_of_previous_month(current_first_day)

    if not downloaded:
        logger.warning(
            f"All attempts ({attempts}) to download resource '{resource}' from protected planet failed."
        )

    return downloaded


def download_and_unpack(
    url,
    file_path,
    resource,
    destination,
    headers=None,
    hot_run=True,
    unzip=True,
    disable_progress=False,
):
    """
    download_and_unpack( url, file_path, resource, destination, headers=None,
    hot_run=True, unzip=True, disable_progress=False)

    A helper function to encapsulate retrieval and unzip

    Inputs
    ------
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    if hot_run:
        if os.path.exists(file_path):
            os.remove(file_path)

        try:
            logger.info(f"Downloading resource '{resource}' from cloud '{url}'.")
            progress_retrieve(
                url, file_path, headers=headers, disable_progress=disable_progress
            )

            # if the file is a zipfile and unzip is enabled
            # then unzip it and remove the original file
            if unzip:
                with ZipFile(file_path, "r") as zipfile:
                    zipfile.extractall(destination)

                os.remove(file_path)
            logger.info(f"Downloaded resource '{resource}' from cloud '{url}'.")
            return True
        except:
            logger.warning(f"Failed download resource '{resource}' from cloud '{url}'.")
            return False


def download_and_unzip_direct(config, rootpath, hot_run=True, disable_progress=False):
    """
    download_and_unzip_direct(config, rootpath, dest_path, hot_run=True,
    disable_progress=False)

    Function to download the data by category from a direct url with no processing.
    If in the configuration file the unzip is specified True, then the downloaded data is unzipped.

    Inputs
    ------
    config : Dict
        Configuration data for the category to download
    rootpath : str
        Absolute path of the repository
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    resource = config["category"]
    destination = os.path.join(BASE_DIR, config["destination"])
    url = config["urls"]["direct"]

    file_path = os.path.join(destination, os.path.basename(url))

    unzip = config.get("unzip", False)

    download_and_unpack(
        url=url,
        file_path=file_path,
        resource=resource,
        hot_run=hot_run,
        unzip=unzip,
        disable_progress=disable_progress,
    )


def download_and_unzip_hydrobasins(
    config, rootpath, hot_run=True, disable_progress=False
):
    """
    download_and_unzip_basins(config, rootpath, dest_path, hot_run=True,
    disable_progress=False)

    Function to download and unzip the data for hydrobasins from HydroBASINS database
    available via https://www.hydrosheds.org/products/hydrobasins

    We are using data from the HydroSHEDS version 1 database
    which is © World Wildlife Fund, Inc. (2006-2022) and has been used herein under license.
    WWF has not evaluated our data pipeline and therefore gives no warranty regarding its
    accuracy, completeness, currency or suitability for any particular purpose.
    Portions of the HydroSHEDS v1 database incorporate data which are the intellectual property
    rights of © USGS (2006-2008), NASA (2000-2005), ESRI (1992-1998), CIAT (2004-2006),
    UNEP-WCMC (1993), WWF (2004), Commonwealth of Australia (2007), and Her Royal Majesty
    and the British Crown and are used under license. The HydroSHEDS v1 database and
    more information are available at https://www.hydrosheds.org.

    Inputs
    ------
    config : Dict
        Configuration data for the category to download
    rootpath : str
        Absolute path of the repository
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    resource = config["category"]
    destination = os.path.join(BASE_DIR, config["destination"])
    url_templ = config["urls"]["hydrobasins"]["base_url"]
    suffix_list = config["urls"]["hydrobasins"]["suffixes"]

    level_code = snakemake.config["renewable"]["hydro"]["hydrobasins_level"]
    level_code = "{:02d}".format(int(level_code))

    all_downloaded = True

    for rg in suffix_list:
        url = url_templ + "hybas_" + rg + "_lev" + level_code + "_v1c.zip"
        file_path = os.path.join(destination, os.path.basename(url))

        all_downloaded &= download_and_unpack(
            url=url,
            file_path=file_path,
            resource=resource,
            destination=destination,
            headers={"User-agent": "Mozilla/5.0"},
            hot_run=hot_run,
            unzip=True,
            disable_progress=disable_progress,
        )

    return all_downloaded


def download_and_unzip_post(config, rootpath, hot_run=True, disable_progress=False):
    """
    download_and_unzip_post(config, rootpath, dest_path, hot_run=True,
    disable_progress=False)

    Function to download the data by category from a post request.

    Inputs
    ------
    config : Dict
        Configuration data for the category to download
    rootpath : str
        Absolute path of the repository
    hot_run : Bool (default True)
        When true the data are downloaded
        When false, the workflow is run without downloading and unzipping
    disable_progress : Bool (default False)
        When true the progress bar to download data is disabled

    Outputs
    -------
    True when download is successful, False otherwise
    """
    resource = config["category"]
    destination = os.path.join(BASE_DIR, config["destination"])

    # load data for post method
    postdata = config["urls"]["post"]
    # remove url feature
    url = postdata.pop("url")

    file_path = os.path.join(destination, os.path.basename(url))

    if hot_run:
        if os.path.exists(file_path):
            os.remove(file_path)

        # try:
        logger.info(f"Downloading resource '{resource}' from cloud '{url}'.")

        progress_retrieve(
            url,
            file_path,
            data=postdata,
            disable_progress=disable_progress,
        )

        # if the file is a zipfile and unzip is enabled
        # then unzip it and remove the original file
        if config.get("unzip", False):
            with ZipFile(file_path, "r") as zipfile:
                zipfile.extractall(destination)

            os.remove(file_path)
        logger.info(f"Downloaded resource '{resource}' from cloud '{url}'.")
        # except:
        #     logger.warning(f"Failed download resource '{resource}' from cloud '{url}'.")
        #     return False

    return True


def _check_disabled_by_opt(config_bundle, config_enable):
    """
    Checks if the configbundle has conflicts with the enable configuration.

    Returns
    -------
    disabled : Bool
        True when the bundle is completely disabled
    """

    disabled_outs = []

    if "disable_by_opt" in config_bundle:
        disabled_config = config_bundle["disable_by_opt"]
        disabled_objs = [
            disabled_outputs
            for optname, disabled_outputs in disabled_config.items()
            if config_enable.get(optname, False)
        ]

        # merge all the lists unique elements
        all_disabled = []
        for tot_outs in disabled_objs:
            for out in tot_outs:
                if out not in all_disabled:
                    all_disabled.append(out)

        if "all" in all_disabled:
            disabled_outs = ["all"]
        elif "output" in config_enable:
            disabled_outs = list(set(all_disabled))

    return disabled_outs


def get_best_bundles_by_category(
    country_list, category, config_bundles, tutorial, config_enable
):
    """
    get_best_bundles_by_category(country_list, category, config_bundles,
    tutorial)

    Function to get the best bundles that download the data for selected countries,
    given category and tutorial characteristics.

    The selected bundles shall adhere to the following criteria:
    - The bundles' tutorial parameter shall match the tutorial argument
    - The bundles' category shall match the category of data to download
    - When multiple bundles are identified for the same set of users,
    the bundles matching more countries are first selected and more bundles
    are added until all countries are matched or no more bundles are available

    Inputs
    ------
    country_list : list
        List of country codes for the countries to download
    category : str
        Category of the data to download
    config_bundles : Dict
        Dictionary of configurations for all available bundles
    tutorial : Bool
        Whether data for tutorial shall be downloaded
    config_enable : dict
        Dictionary of the enabled/disabled scripts

    Outputs
    -------
    returned_bundles : list
        List of bundles to download
    """
    # dictionary with the number of match by configuration for tutorial/non-tutorial configurations
    df_matches = pd.DataFrame(columns=["bundle_name", "bundle_size", "n_matched"])

    for bname, bvalue in config_bundles.items():
        if (
            bvalue["category"] == category
            and bvalue.get("tutorial", False) == tutorial
            and _check_disabled_by_opt(bvalue, config_enable) != ["all"]
        ):
            df_matches.loc[bname] = [
                bname,
                len(bvalue["countries"]),
                bvalue["n_matched"],
            ]

    df_matches["neg_bundle_size"] = -df_matches["bundle_size"]
    df_matches.sort_values(
        by=["n_matched", "neg_bundle_size"], inplace=True, ascending=False
    )

    returned_bundles = []

    if not df_matches.empty:
        current_matched_countries = []
        remaining_countries = set(country_list)

        for bname in df_matches.index:
            cbundle_list = set(config_bundles[bname]["countries"])

            # list of countries in the bundle that are not yet matched
            intersect = cbundle_list.intersection(remaining_countries)

            if intersect:
                current_matched_countries.extend(intersect)
                remaining_countries = remaining_countries.difference(intersect)

                returned_bundles.append(bname)

    return returned_bundles


def get_best_bundles(countries, config_bundles, tutorial, config_enable):
    """
    get_best_bundles(countries, category, config_bundles, tutorial)

    Function to get the best bundles that download the data for selected countries,
    given tutorial characteristics.

    First, the categories of data to download are identified in agreement to
    the bundles that match the list of countries and tutorial configuration.

    Then, the bundles to be downloaded shall adhere to the following criteria:
    - The bundles' tutorial parameter shall match the tutorial argument
    - The bundles' category shall match the category of data to download
    - When multiple bundles are identified for the same set of users,
      the bundles matching more countries are first selected and more bundles
      are added until all countries are matched or no more bundles are available

    Inputs
    ------
    countries : list
        List of country codes for the countries to download
    config_bundles : Dict
        Dictionary of configurations for all available bundles
    tutorial : Bool
        Whether data for tutorial shall be downloaded
    config_enable : dict
        Dictionary of the enabled/disabled scripts

    Outputs
    -------
    returned_bundles : list
        List of bundles to download
    """

    # categories of data to download
    categories = list(
        set([config_bundles[conf]["category"] for conf in config_bundles])
    )

    # identify matched countries for every bundle
    for bname in config_bundles:
        config_bundles[bname]["matched_countries"] = [
            c for c in config_bundles[bname]["countries"] if c in countries
        ]
        n_matched = len(config_bundles[bname]["matched_countries"])
        config_bundles[bname]["n_matched"] = n_matched

    # bundles to download
    bundles_to_download = []

    for cat in categories:
        selection_bundles = get_best_bundles_by_category(
            countries, cat, config_bundles, tutorial, config_enable
        )

        # check if non-empty dictionary
        if selection_bundles:
            bundles_to_download.extend(selection_bundles)

            if len(selection_bundles) > 1:
                logger.warning(
                    f"Multiple bundle data for category {cat}: "
                    + ", ".join(selection_bundles)
                )

    return bundles_to_download


def datafiles_retrivedatabundle(config):
    """
    Function to get the output files from the bundles, given the target
    countries, tutorial settings, etc.
    """

    tutorial = config["tutorial"]
    countries = config["countries"]
    config_enable = config["enable"]

    config_bundles = load_databundle_config(config["databundles"])

    bundles_to_download = get_best_bundles(
        countries, config_bundles, tutorial, config_enable
    )

    listoutputs = list(
        set(
            [
                inneroutput
                for bundlename in bundles_to_download
                for inneroutput in config["databundles"][bundlename]["output"]
                if "*" not in inneroutput
                or inneroutput.endswith("/")  # exclude directories
            ]
        )
    )

    return listoutputs


def merge_hydrobasins_shape(config_hydrobasin, hydrobasins_level):
    basins_path = os.path.join(BASE_DIR, config_hydrobasin["destination"])
    output_fl = os.path.join(BASE_DIR, config_hydrobasin["output"][0])

    files_to_merge = [
        "hybas_{0:s}_lev{1:02d}_v1c.shp".format(suffix, hydrobasins_level)
        for suffix in config_hydrobasin["urls"]["hydrobasins"]["suffixes"]
    ]
    gpdf_list = [None] * len(files_to_merge)
    logger.info("Merging hydrobasins files into: " + output_fl)
    for i, f_name in tqdm(enumerate(files_to_merge)):
        gpdf_list[i] = gpd.read_file(os.path.join(basins_path, f_name))
    fl_merged = gpd.GeoDataFrame(pd.concat(gpdf_list)).drop_duplicates(
        subset="HYBAS_ID", ignore_index=True
    )
    fl_merged.to_file(output_fl, driver="ESRI Shapefile")


if __name__ == "__main__":
    if "snakemake" not in globals():

        from _helpers import mock_snakemake

        snakemake = mock_snakemake("retrieve_databundle_light")

    # TODO Make logging compatible with progressbar (see PR #102, PyPSA-Eur)
    configure_logging(snakemake)

    rootpath = "."
    tutorial = snakemake.params.tutorial
    countries = snakemake.params.countries
    logger.info(f"Retrieving data for {len(countries)} countries.")

    # load enable configuration
    config_enable = snakemake.config["enable"]
    # load databundle configuration
    config_bundles = load_databundle_config(snakemake.config["databundles"])
    disable_progress = not config_enable["progress_bar"]

    bundles_to_download = get_best_bundles(
        countries, config_bundles, tutorial, config_enable
    )

    logger.warning(
        "DISCLAIMER LICENSES: the use of PyPSA-Earth is conditioned \n \
        to the acceptance of its multiple licenses.\n \
        The use of the code automatically implies that you accept all the licenses.\n \
        See our documentation for more information. \n \
        Link: https://pypsa-earth.readthedocs.io/en/latest/introduction.html#licence"
    )

    logger.info("Bundles to be downloaded:\n\t" + "\n\t".join(bundles_to_download))

    # initialize downloaded and missing bundles
    downloaded_bundles = []

    # download the selected bundles
    for b_name in bundles_to_download:
        host_list = config_bundles[b_name]["urls"]

        downloaded_bundle = False

        # loop all hosts until data is successfully downloaded
        for host in host_list:
            logger.info(f"Downloading bundle {b_name} - Host {host}")

            try:
                download_and_unzip = globals()[f"download_and_unzip_{host}"]
                if download_and_unzip(
                    config_bundles[b_name], rootpath, disable_progress=disable_progress
                ):
                    downloaded_bundle = True
            except Exception:
                logger.warning(f"Error in downloading bundle {b_name} - host {host}")

            if downloaded_bundle:
                downloaded_bundles.append(b_name)
                break

        if not downloaded_bundle:
            logger.error(f"Bundle {b_name} cannot be downloaded")

    hydrobasin_bundles = [
        b_name for b_name in bundles_to_download if "hydrobasins" in b_name
    ]
    if len(hydrobasin_bundles) > 0:
        logger.info("Merging regional hydrobasins files into a global shapefile")
        hydrobasins_level = snakemake.params["hydrobasins_level"]
        merge_hydrobasins_shape(
            config_bundles[hydrobasin_bundles[0]], hydrobasins_level
        )

    # log the downloaded and missing bundles
    logger.info(
        "Bundle successfully loaded and unzipped:\n\t" + "\n\t".join(downloaded_bundles)
    )

    missing_bundles = set(bundles_to_download) - set(downloaded_bundles)
    if missing_bundles:
        logger.warning(
            "The following bundles could not be downloaded:\n\t"
            + "\n\t".join(list(missing_bundles))
        )
