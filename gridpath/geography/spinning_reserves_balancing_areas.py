#!/usr/bin/env python
# Copyright 2017 Blue Marble Analytics LLC. All rights reserved.

import csv
import os.path
from pyomo.environ import Set


def add_model_components(m, d):
    """

    :param m:
    :param d:
    :return:
    """
    m.SPINNING_RESERVES_ZONES = Set()


def load_model_data(m, d, data_portal, scenario_directory, horizon, stage):
    """

    :param m:
    :param d:
    :param data_portal:
    :param scenario_directory:
    :param horizon:
    :param stage:
    :return:
    """
    data_portal.load(
        filename=os.path.join(scenario_directory, "inputs",
                              "spinning_reserves_balancing_areas.tab"),
        select=("balancing_area",),
        index=m.SPINNING_RESERVES_ZONES,
        param=()
    )


def get_inputs_from_database(subscenarios, c, inputs_directory):
    """

    :param subscenarios
    :param c:
    :param inputs_directory:
    :return:
    """
    # spinning_reserves_balancing_areas.tab
    with open(os.path.join(inputs_directory,
                           "spinning_reserves_balancing_areas.tab"),
              "w") as \
            lf_up_bas_tab_file:
        writer = csv.writer(lf_up_bas_tab_file, delimiter="\t")

        # Write header
        writer.writerow(["balancing_area",
                         "violation_penalty_per_mw",
                         "reserve_to_energy_adjustment"])

        lf_up_bas = c.execute(
            """SELECT lf_reserves_up_ba, 
            violation_penalty_per_mw, reserve_to_energy_adjustment
               FROM inputs_geography_lf_reserves_up_bas
               WHERE lf_reserves_up_ba_scenario_id = {};""".format(
                subscenarios.SPINNING_RESERVES_BA_SCENARIO_ID
            )
        ).fetchall()

        for row in lf_up_bas:
            replace_nulls = ["." if i is None else i for i in row]
            writer.writerow(replace_nulls)