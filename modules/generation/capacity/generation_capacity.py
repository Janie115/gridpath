#!/usr/bin/env python

import os
from pyomo.environ import *


def add_model_components(m):
    m.GENERATORS = Set()

    m.capacity = Param(m.GENERATORS, within=NonNegativeReals)
    m.variable_cost = Param(m.GENERATORS, within=NonNegativeReals)


def load_model_data(m, data_portal, inputs_directory):
    data_portal.load(filename=os.path.join(inputs_directory, "generators.tab"),
                     index=m.GENERATORS,
                     select=("GENERATORS", "capacity", "variable_cost"),
                     param=(m.capacity, m.variable_cost)
                     )


def view_loaded_data(instance):
    print "Viewing data"
    for g in instance.GENERATORS:
        print(g, instance.capacity[g])