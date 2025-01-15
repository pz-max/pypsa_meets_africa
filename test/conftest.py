# -*- coding: utf-8 -*-
import pandas as pd
import pypsa
import pytest


@pytest.fixture
def network():
    n = pypsa.Network()
    n.set_snapshots(pd.date_range("2022-01-01", periods=24, freq="H"))
    n.add("Bus", "bus1")
    n.add(
        "Link",
        "battery discharger",
        bus0="bus1",
        bus1="bus1",
        p_nom_extendable=True,
        efficiency=0.9,
    )
    n.add("Link", "battery charger", bus0="bus1", bus1="bus1", p_nom_extendable=True)

    # Add links
    n.add(
        "Link",
        "urban central CHP electric",
        bus0="bus0",
        bus1="bus1",
        p_nom_extendable=True,
        efficiency=0.9,
        p_nom_ratio=1.0,
    )
    n.add(
        "Link",
        "urban central CHP heat",
        bus0="bus1",
        bus1="bus0",
        p_nom_extendable=True,
        efficiency=0.9,
    )

    n.optimize.create_model()

    return n
