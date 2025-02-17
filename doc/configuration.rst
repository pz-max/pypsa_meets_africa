.. SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
..
.. SPDX-License-Identifier: CC-BY-4.0

.. _config:

##########################################
Configuration
##########################################

PyPSA-Earth imports the configuration options originally developed in `PyPSA-Eur <https://pypsa-eur.readthedocs.io/en/latest/index.html>`_ and here reported and adapted.
The options here described are collected in a ``config.yaml`` file located in the root directory.
Users should copy the provided default configuration (``config.default.yaml``) and amend
their own modifications and assumptions in the user-specific configuration file (``config.yaml``);
confer installation instructions at :ref:`installation`.

.. note::
  Credits to PyPSA-Eur developers for the initial drafting of the configuration documentation here reported

.. _toplevel_cf:

Top-level configuration
=======================

.. literalinclude:: ../configs/config.main.yaml
   :language: yaml
   :start-at: version:
   :end-at:  build_cutout:


.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/toplevel.csv

.. _run:

``run``
=======

It is common conduct to analyse energy system optimisation models for **multiple scenarios** for a variety of reasons,
e.g. assessing their sensitivity towards changing the temporal and/or geographical resolution or investigating how
investment changes as more ambitious greenhouse-gas emission reduction targets are applied.

The ``run`` section is used for running and storing scenarios with different configurations which are not covered by :ref:`wildcards`. It determines the path at which resources, networks and results are stored. Therefore the user can run different configurations within the same directory. If a run with a non-empty name should use cutouts shared across runs, set ``shared_cutouts`` to `true`.

.. literalinclude:: ../configs/config.main.yaml
   :language: yaml
   :start-at: run:
   :end-at: allow_scenario_failure:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/run.csv

.. _scenario:

``scenario``
============

The ``scenario`` section is an extraordinary section of the config file
that is strongly connected to the :ref:`wildcards` and is designed to
facilitate running multiple scenarios through a single command

.. code:: bash

    snakemake -j 1 solve_all_networks

For each wildcard, a **list of values** is provided. The rule ``solve_all_networks`` will trigger the rules for creating ``results/networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc`` for **all combinations** of the provided wildcard values as defined by Python's `itertools.product(...) <https://docs.python.org/2/library/itertools.html#itertools.product>`_ function that snakemake's `expand(...) function <https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#targets>`_ uses.

An exemplary dependency graph (starting from the simplification rules) then looks like this:

.. image:: img/scenarios.png

.. literalinclude:: ../configs/config.main.yaml
   :language: yaml
   :start-at: scenario:
   :end-at: snapshots:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/scenario.csv

.. _snapshots_cf:

``snapshots``
=============

Specifies the temporal range for the historical weather data, which is used to build the energy system model. It uses arguments to `pandas.date_range <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.date_range.html>`_. The date range must be in the past (before 2022). A well-tested year is 2013.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: snapshots:
   :end-at: inclusive:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/snapshots.csv

.. _crs_cf:

``crs``
===============

Defines the coordinate reference systems (crs).

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: crs:
   :end-at: area_crs:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/crs.csv


.. _augmented_line_connection_cf:

``augmented_line_connection``
=============================

If enabled, it increases the connectivity of the network. It makes the network graph `k-edge-connected <https://en.wikipedia.org/wiki/K-edge-connected_graph>`_, i.e.,
if fewer than k edges are removed, the network graph stays connected. It uses the `k-edge-augmentation <https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.connectivity.edge_augmentation.k_edge_augmentation.html#networkx.algorithms.connectivity.edge_augmentation.k_edge_augmentation>`_
algorithm from the `NetworkX <https://networkx.org/documentation/stable/index.html>`_ Python package.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: augmented_line_connection:
   :end-at: min_DC_length:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/augmented_line_connection.csv

.. _cluster_options_cf:

``cluster_options``
=============================

Specifies the options to simplify and cluster the network. This is done in two stages, first using the rule ``simplify_network`` and then using the rule ``cluster_network``. For more details on this process, see the `PyPSA-Earth paper <https://www.sciencedirect.com/science/article/pii/S0306261923004609>`_, section 3.7.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: cluster_options:
   :end-at: efficiency:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/cluster_options.csv

.. _build_shape_options_cf:

``build_shape_options``
=============================

Specifies the options to build the shapes in which the region of interest (``countries``) is divided.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: build_shape_options:
   :end-at: contended_flag:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/build_shape_options.csv

.. _subregion_cf:

``subregion``
=============================

If enabled, this option allows a region of interest (``countries``) to be redefined into subregions,
which can be activated at various stages of the workflow. Currently, it is only used in the ``simplify_network`` rule.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: subregion:
   :end-at: path_custom_shapes:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/subregion.csv

The names of subregions are arbitrary. Its sizes are determined by how many GADM IDs that are included in the list.
A single country can be divided into multiple subregions, and a single subregion can include GADM IDs from multiple countries.
If the same GADM ID appears in different subregions, the first subregion listed will take precedence over that region.
The remaining GADM IDs that are not listed will be merged back to form the remaining parts of their respective countries.
For example, consider the Central District of Botswana, which has a GADM ID of ``BW.3``. To separate this district from the rest of the country, you can select:

.. literalinclude:: ../test/config.landlock.yaml
   :language: yaml
   :start-at: subregion:
   :end-at: Central:

There are several formats for GADM IDs depending on the version, so before using this feature, please review the ``resources/shapes/gadm_shape.geojson`` file which can be created using the command:

.. code:: bash

    snakemake -j 1 build_shapes

.. note::
   The rule ``build_shapes`` currently use `Version 4.1  <https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/>`_ for their GADM data. This may change in the future.

.. _clean_osm_data_options_cf:

``clean_osm_data_options``
=============================

Specifies the options to clean the `OpenStreetMap <https://wiki.osmfoundation.org/wiki/Main_Page>`_ (OSM) data.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: clean_osm_data_options:
   :end-at: generator_name_method:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/clean_osm_data_options.csv

.. _build_osm_network_cf:

``build_osm_network``
=============================

Specifies the options to build the `OpenStreetMap <https://wiki.osmfoundation.org/wiki/Main_Page>`_ (OSM) network.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: build_osm_network:
   :end-at: force_ac:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/build_osm_network.csv

.. _base_network_cf:

``base_network``
=============================

Specifies the minimum voltage magnitude in the base network and the offshore substations.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: base_network:
   :end-at: min_voltage_rebase_voltage:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/base_network.csv

.. _load_options_cf:

``load_options``
=============================

Specifies the options to estimate future electricity demand (load). Different years might be considered for weather and the socioeconomic pathway (GDP and population growth), to enhance modelling capabilities.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: load_options:
   :end-at: scale:

.. csv-table::
   :header-rows: 1
   :widths: 25,10,22,27
   :file: configtables/load_options.csv

.. warning::
    The snapshots date range (``snapshots\start`` - ``snapshots\end``) must be in the ``weather_year``.

.. _electricity_cf:

``electricity``
===============

Specifies the options for the rule ``add_electricity``. This includes options across several features, including but not limited to: voltage levels, electricity carriers available, renewable capacity estimation, CO2 emission limits, operational reserve, storage parameters. See the table below for more details.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: electricity:
   :end-at: PV:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/electricity.csv

.. warning::
    Carriers in ``conventional_carriers`` must not also be in ``extendable_carriers``.

.. _lines_cf:

``lines``
=============

Specifies electricity line parameters.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-after: PV:
   :end-at: under_construction:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/lines.csv

.. _links_cf:

``links``
=============

Specifies Link parameters. Links are a fundamental component of `PyPSA <https://pypsa.readthedocs.io/en/latest/components.html>`_ .

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: links:
   :end-before: transformers:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/links.csv

.. _transformers_cf:

``transformers``
================

Specifies transformers parameters and types.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: transformers:
   :end-before: atlite:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/transformers.csv

.. _atlite_cf:

``atlite``
==========

Define and specify the ``atlite.Cutout`` used for calculating renewable potentials and time-series. All options except for ``features`` are directly used as `cutout parameters <https://atlite.readthedocs.io/en/latest/ref_api.html#cutout>`_.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: atlite:
   :end-before: renewable:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/atlite.csv

.. _renewable_cf:

``renewable``
=============

Specifies the options to obtain renewable potentials in every cutout. These are divided in five different renewable technologies: onshore wind (``onwind``), offshore wind with AC connection (``offwind-ac``), offshore wind with DC connection (``offwind-dc``), solar (``solar``), and hydropower (``hydro``).

``onwind``
----------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: renewable:
   :end-before:   offwind-ac:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/onwind.csv

``offwind-ac``
--------------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at:   offwind-ac:
   :end-before:   offwind-dc:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/offwind-ac.csv

``offwind-dc``
---------------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at:   offwind-dc:
   :end-before:   solar:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/offwind-dc.csv

``solar``
---------------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at:   solar:
   :end-before:   hydro:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/solar.csv

``hydro``
---------------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at:   hydro:
   :end-at: multiplier:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/hydro.csv

``csp``
---------------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at:   csp:
   :end-at: csp_model:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/csp.csv

.. _costs_cf:

``costs``
=============

Specifies the cost assumptions of the technologies considered. Cost information is obtained from the config file and the file ``data/costs.csv``, which can also be modified manually.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-after: Costs Configuration
   :end-at: CCGT: 0.58

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/costs.csv

.. note::
   To change cost assumptions in more detail (i.e. other than ``marginal_cost``), consider modifying cost assumptions directly in ``data/costs.csv`` as this is not yet supported through the config file.
   You can also build multiple different cost databases. Make a renamed copy of ``data/costs.csv`` (e.g. ``data/costs-optimistic.csv``) and set the variable ``COSTS=data/costs-optimistic.csv`` in the ``Snakefile``.

.. note::
   The ``marginal costs`` or in this context ``variable costs`` of operating the assets is important for realistic operational model outputs.
   It can define the curtailment order of renewable generators, the dispatch order of generators, and the dispatch of storage units.
   If not approapriate set, the model might output unrealistic results. Learn more about this in
   `Parzen et al. 2023 <https://www.sciencedirect.com/science/article/pii/S2589004222020028>`_ and in
   `Kittel et al. 2022 <https://www.sciencedirect.com/science/article/pii/S2589004222002723>`_.


.. _monte_cf:

``monte_carlo``
===============

Specifies the options for Monte Carlo sampling.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: monte_carlo:
   :end-before:   solving:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/monte-carlo.csv

.. _solving_cf:

``solving``
=============

Specify linear power flow formulation and optimization solver settings.

``options``
-----------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: solving:
   :end-before:   solver:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/solving-options.csv

``solver``
----------

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at:   solver:
   :end-before: plotting:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/solving-solver.csv

.. _plotting_cf:

``plotting``
=============

Specifies plotting options.

.. literalinclude:: ../config.default.yaml
   :language: yaml
   :start-at: plotting:

.. csv-table::
   :header-rows: 1
   :widths: 25,7,22,30
   :file: configtables/plotting.csv
