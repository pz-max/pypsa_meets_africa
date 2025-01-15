# -*- coding: utf-8 -*-
import sys

import pypsa
import pytest

sys.path.append("./scripts")
from test.conftest import network

import _helpers
from solve_network import add_battery_constraints, add_chp_constraints


def test_add_battery_constraints(network):

    # Apply the function
    add_battery_constraints(network)

    constraints = network.model.constraints["Link-charger_ratio"]
    assert constraints is not None

    # Check that the constraints were added
    assert "Link-charger_ratio" in network.model.constraints

    # Check the constraint expression
    lhs = network.model.constraints["Link-charger_ratio"][0].lhs

    assert lhs.equals(
        network.model["Link-p_nom"].loc["battery charger"]
        - 0.9 * network.model["Link-p_nom"].loc["battery discharger"]
    )


def test_chp_constraints(network):

    # Apply the function
    add_chp_constraints(network)

    constraints = network.model.constraints["Link-CHP_ratio"]
    assert constraints is not None

    # Check that the constraints were added
    assert "Link-CHP_ratio" in network.model.constraints

    # Check the constraint expression
    lhs = network.model.constraints["Link-CHP_ratio"][0].lhs

    assert lhs.equals(
        network.model["Link-p_nom"].loc["urban central CHP heat"]
        - 0.9 * network.model["Link-p_nom"].loc["urban central CHP electric"]
    )
