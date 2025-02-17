# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# -*- coding: utf-8 -*-
"""
Set of helper functions to deal with human-redable outputs.
"""

import logging

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# definitions of output blocks ------------------------------------------------
# model_keys = [
#   "version", "tutorial", "foresight", "countries",
#   "scenario", "snapshots", "enable", "run",
#   "clean_osm_data_options", "build_osm_network", "base_network",
#   "build_shape_options",
#   "electricity", "lines", "links", "transformers",
#   "load_options", "demand_data",
#   "augmented_line_connection",
#   "cluster_options",
#   "atlite", "renewable", "solar_thermal",
#   "policy_config", "fossil_reserves",
#   "sector", "export", "industry"
#   "custom_data", "existing_capacities", "costs",
#   "monte_carlo", "solving",
#   "plotting", "crs",
# ]

major_run_keys = [
    "version",
    "tutorial",
    "foresight",
    "countries",
    "enable",
    "run",
]
major_model_keys = [
    "scenario",
    "snapshots",
]
grid_model_keys = [
    "clean_osm_data_options",
    "build_osm_network",
    "base_network",
]
electrycity_model_keys = ["electricity"]

# visual settings -------------------------------------------------------------
style = """<style type='text/css'>
html {
  font-family: Georgia;
}
r {
  color: #ff0000;
  background-color: coral;
}
g {
  color: #00ff00;
  background-color: coral;
}
b {
  color: #0000ff;
  background-color: grey;
}
blue_bg {
  color: #36454F;
  background-color: #A7C8FF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
mint_bg {
  color: #36454F;
  background-color: #B7E5D5;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
coral_bg {
  color: #36454F;
  background-color: #FF9E9E;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
lavend_bg {
  color: #36454F;
  background-color: #D8ADEF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
gold_bg {
  color: #36454F;
  background-color: #F9C6A1;
  width: 100%;
  background-size: contain;
  display:inline-block;
}

blue_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #A7C8FF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
mint_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #B7E5D5;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
coral_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #FF9E9E;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
lavend_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #D8ADEF;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
gold_hd {
  font-weight: bold;
  color: #36454F;
  background-color: #F9C6A1;
  width: 100%;
  background-size: contain;
  display:inline-block;
}
</style>"""


def make_license_text(html=False):
    # Avoid confusing REUSE as in https://reuse.software/faq/#exclude-lines
    # REUSE-IgnoreStart
    license_str_list = [
        "# SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors",
        "# SPDX-License-Identifier: AGPL-3.0-or-later ",
    ]
    # REUSE-IgnoreEnd
    if html:
        license_str = "<br />".join(license_str_list)
    else:
        license_str = "\n\r".join(license_str_list)
    return license_str


def write_html(style, fl, type, str_):
    fl.write("<%(type)s>%(str)s</%(type)s>" % {"type": type, "str": str_})


def write_dict_key(
    header, dict, style_text, style_header, style_def=style, fl_name="out.html"
):

    # define styles to be used in htmls generated below
    coral_bg = "coral_bg"
    mint_bg = "mint_bg"
    blue_bg = "blue_bg"

    content_str = yaml.dump(dict)

    clean_str = (
        content_str.replace("\t", "     ")
        .replace("\n", "<br />")
        .replace("\r", "<br />")
    )
    # clean_str = content_str.replace("\n", ", ")#.replace("\r", "<br />")

    # f = open(fl_name, "w")
    f = open(fl_name, "a")

    f.write("<html>")
    f.write(style)

    write_html(
        style=style_def,
        fl=f,
        type=style_text,
        str_="------------------------------------------ <br />",
    )
    write_html(style=style_def, fl=f, type=style_header, str_=header + "<br />")
    write_html(
        style=style_def,
        fl=f,
        type=style_text,
        str_="------------------------------------------ <br />",
    )
    write_html(style=style_def, fl=f, type=style_text, str_=clean_str)

    write_html(style=style_def, fl=f, type=mint_bg, str_="<br />")
    # write_html(
    #     style=style_def,
    #     fl=f,
    #     type=style_text,
    #     str_="------------------------------------------ <br /><br />",
    # )

    f.write("</html>")


def get_vals(test_dict, key_list):
    df = pd.json_normalize(test_dict, sep=" ")
    d_flat = df.to_dict(orient="records")[0]

    res = [(key, value) for key, value in d_flat.items() if key_list in key.lower()]

    return res


def parse_config(config, fl_name=None, style_def=style):
    """
    Outputs a config summary to highlight points which require attention
    from a modeler

    Currently, the following checks are implemented:
    1. List all the year-related parameters used in a simulation
    """

    # TODO Add a check for the cutouts used

    # 1. Outline all the years used in a simulation
    # The config contains
    res = dict(get_vals(config, "year"))

    str_list = [None] * len(res)
    k = 0
    for i, j in res.items():
        str_list[k] = str(i) + ": " + str(j)
        k += 1

    html_content_string = "<br />".join(str_list) + "<br />"

    # define styles to be used in htmls generated below
    coral_bg = "coral_bg"
    mint_bg = "mint_bg"
    blue_bg = "blue_bg"

    f = open("config_check.html", "w")

    f.write("<html>")
    f.write(style)
    write_html(
        style=mint_bg,
        fl=f,
        type=mint_bg,
        str_="------------------------------------------ <br />",
    )
    f.write(make_license_text(html=True))
    write_html(
        style=mint_bg,
        fl=f,
        type=mint_bg,
        str_="------------------------------------------ <br />",
    )
    write_html(
        style=mint_bg,
        fl=f,
        type=mint_bg,
        str_="The current configuration contains the following year definitions:<br />",
    )
    write_html(
        style=mint_bg,
        fl=f,
        type=mint_bg,
        str_=html_content_string,
    )
    write_html(
        style=mint_bg,
        fl=f,
        type=mint_bg,
        str_="------------------------------------------ <br />",
    )
