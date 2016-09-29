#!/usr/bin/env python

"""
Describes the relationships among timepoints in the optimization
"""

import os.path

from pyomo.environ import Set, Param, NonNegativeReals, NonNegativeIntegers


def add_model_components(m, d, scenario_directory, horizon, stage):
    """

    :param m:
    :param d:
    :param scenario_directory:
    :param horizon:
    :param stage:
    :return:
    """
    m.PERIODS = Set(within=NonNegativeIntegers, ordered=True)
    m.discount_factor = Param(m.PERIODS, within=NonNegativeReals)
    m.number_years_represented = Param(m.PERIODS, within=NonNegativeReals)

    m.period = Param(m.TIMEPOINTS, within=m.PERIODS)

    m.TIMEPOINTS_IN_PERIOD = \
        Set(m.PERIODS,
            initialize=lambda mod, p:
            set(tmp for tmp in mod.TIMEPOINTS if mod.period[tmp] == p))


def load_model_data(m, d, data_portal, scenario_directory, horizon, stage):
    """
    """
    data_portal.load(filename=os.path.join(scenario_directory,
                                           "inputs", "periods.tab"),
                     select=("PERIODS", "discount_factor",
                             "number_years_represented"),
                     index=m.PERIODS,
                     param=(m.discount_factor, m.number_years_represented)
                     )

    data_portal.load(filename=os.path.join(scenario_directory, horizon, stage,
                                           "inputs", "timepoints.tab"),
                     select=("TIMEPOINTS","period"),
                     index=m.TIMEPOINTS,
                     param=m.period
                     )