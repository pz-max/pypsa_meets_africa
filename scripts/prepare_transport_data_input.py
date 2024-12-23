# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import os
import shutil
from pathlib import Path

import country_converter as coco
import numpy as np
import pandas as pd
from _helpers import BASE_DIR

logger = logging.getLogger(__name__)


def _add_iso2_code_per_country_and_clean_data(df):
    """
    Converts 'Country' names to ISO2 codes in a new 'country' column.
    Cleans DataFrame by removing rows with invalid 'country' values.
    """

    cc = coco.CountryConverter()
    df["country"] = cc.pandas_convert(
        series=pd.Series(df["Country"]), to="ISO2", not_found="not found"
    )

    df = df[df.country != "not found"]

    # Drop region names where country column contains list of countries
    df = df[df.country.apply(lambda x: isinstance(x, str))]

    df = df.drop_duplicates(subset=["country"])

    return df


def download_number_of_vehicles():
    """
    Downloads and returns the number of registered vehicles
    as tabular data from WHO and Wikipedia.

    The csv data from the WHO website is imported
    from 'https://apps.who.int/gho/data/node.main.A995'.
    A few countries are missing in the WHO list (e.g. South Africa, Algeria).
    Therefore, the number of vehicles per country table from Wikipedia
    is also imported for completion (prio 2):
    'https://en.wikipedia.org/wiki/List_of_countries_and_territories_by_motor_vehicles_per_capita'.
    """

    def _download_vehicles_data_from_gho():
        url = "https://apps.who.int/gho/athena/data/GHO/RS_194?filter=COUNTRY:*&ead=&x-sideaxis=COUNTRY;YEAR;DATASOURCE&x-topaxis=GHO&profile=crosstable&format=csv"
        storage_options = {"User-Agent": "Mozilla/5.0"}
        df = pd.read_csv(url, storage_options=storage_options, encoding="utf8")

        df.rename(
            columns={
                "Countries, territories and areas": "Country",
                "Number of registered vehicles": "number cars",
            },
            inplace=True,
        )

        df["number cars"] = df["number cars"].str.replace(" ", "").replace("", np.nan)

        df = df.dropna(subset=["number cars"])

        return df[["Country", "number cars"]]

    def _download_vehicles_data_from_wiki():
        url = "https://en.wikipedia.org/wiki/List_of_countries_and_territories_by_motor_vehicles_per_capita"
        df = pd.read_html(url)[0]

        df.rename(
            columns={"Location": "Country", "Vehicles": "number cars"}, inplace=True
        )

        return df[["Country", "number cars"]]

    try:
        nbr_vehicles = pd.concat(
            [_download_vehicles_data_from_gho(), _download_vehicles_data_from_wiki()],
            ignore_index=True,
        )
    except Exception as e:
        logger.warning(
            "Failed to read the file:",
            e,
            "\nReturning an empty df and falling back on the hard-coded data.",
        )
        return pd.DataFrame()

    nbr_vehicles["number cars"] = nbr_vehicles["number cars"].astype(int)

    nbr_vehicles = _add_iso2_code_per_country_and_clean_data(nbr_vehicles)

    # Drops duplicates and keeps WHO-GHO data in case of duplicates
    nbr_vehicles = nbr_vehicles.drop_duplicates(subset=["country"], keep="first")

    return nbr_vehicles


def download_CO2_emissions():
    """
    Downloads the CO2_emissions from vehicles as .csv File.

    The dataset is downloaded from the following link: https://data.worldbank.org/indicator/EN.CO2.TRAN.ZS?view=map
    It is until the year 2014. # TODO: Maybe search for more recent years.
    """

    url = (
        "https://api.worldbank.org/v2/en/indicator/EN.CO2.TRAN.ZS?downloadformat=excel"
    )

    # Read the 'Data' sheet directly from the Excel file at the provided URL
    try:
        CO2_emissions = pd.read_excel(url, sheet_name="Data", skiprows=[0, 1, 2])
        print("File read successfully.")
    except Exception as e:
        print("Failed to read the file:", e)
        return pd.DataFrame()

    CO2_emissions = CO2_emissions[
        ["Country Name", "Country Code", "Indicator Name", "2014"]
    ]

    # Calculate efficiency based on CO2 emissions from transport (% of total fuel combustion)
    CO2_emissions["average fuel efficiency"] = (100 - CO2_emissions["2014"]) / 100

    CO2_emissions = CO2_emissions.dropna(subset=["average fuel efficiency"])

    CO2_emissions = CO2_emissions.rename(columns={"Country Name": "Country"})

    CO2_emissions = _add_iso2_code_per_country_and_clean_data(CO2_emissions)

    CO2_emissions["average fuel efficiency"] = CO2_emissions[
        "average fuel efficiency"
    ].astype(float)

    CO2_emissions.loc[:, "average fuel efficiency"] = CO2_emissions[
        "average fuel efficiency"
    ].round(3)

    return CO2_emissions[["country", "average fuel efficiency"]]


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake("prepare_transport_data_input")

    # configure_logging(snakemake)

    # run = snakemake.config.get("run", {})
    # RDIR = run["name"] + "/" if run.get("name") else ""
    # store_path_data = Path.joinpath(Path().cwd(), "data")
    # country_list = country_list_to_geofk(snakemake.config["countries"])'

    # Downloaded and prepare vehicles data:
    vehicles_df = download_number_of_vehicles().copy()

    # Downloaded and prepare CO2_emissions data:
    CO2_emissions_df = download_CO2_emissions().copy()

    if vehicles_df.empty or CO2_emissions_df.empty:
        # In case one of the urls is not working, we can use the hard-coded data
        src = BASE_DIR + "/data/temp_hard_coded/transport_data.csv"
        dest = snakemake.output.transport_data_input
        shutil.copy(src, dest)
    else:
        # Join the DataFrames by the 'country' column
        merged_df = pd.merge(vehicles_df, CO2_emissions_df, on="country")
        merged_df = merged_df[["country", "number cars", "average fuel efficiency"]]

        # Save the merged DataFrame to a CSV file
        merged_df.to_csv(
            snakemake.output.transport_data_input,
            sep=",",
            encoding="utf-8",
            header="true",
            index=False,
        )
