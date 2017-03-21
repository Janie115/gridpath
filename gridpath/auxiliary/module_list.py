#!/usr/bin/env python
# Copyright 2017 Blue Marble Analytics LLC. All rights reserved.

from importlib import import_module
import os.path
import pandas as pd
import sys


def all_modules_list():
    # If all optional modules are selected, this would be the list
    all_modules = [
        "temporal.operations.timepoints",
        "temporal.operations.horizons",
        "temporal.investment.periods",
        "geography.load_zones",
        "geography.load_following_up_balancing_areas",
        "geography.load_following_down_balancing_areas",
        "geography.regulation_up_balancing_areas",
        "geography.regulation_down_balancing_areas",
        "geography.rps_zones",
        "geography.carbon_cap_zones",
        "system.load_balance.static_load_requirement",
        "system.policy.rps.rps_requirement",
        "system.policy.carbon_cap.carbon_cap",
        'project',
        "project.capacity.capacity",
        "project.capacity.costs",
        "project.fuels",
        "project.operations",
        "project.operations.reserves.lf_reserves_up",
        "project.operations.reserves.lf_reserves_down",
        "project.operations.reserves.regulation_up",
        "project.operations.reserves.regulation_down",
        "project.operations.operational_types",
        "project.operations.aggregate_power",
        "project.operations.fix_commitment",
        "project.operations.aggregate_costs",
        "project.operations.aggregate_recs",
        "project.operations.aggregate_carbon_emissions",
        "project.operations.fuel_burn",
        "transmission",
        "transmission.capacity.capacity",
        "transmission.operations.operations",
        "transmission.operations.aggregate_costs",
        "transmission.operations.simultaneous_flow_limits",
        "transmission.operations.aggregate_carbon_emissions",
        "system.load_balance.load_balance",
        "system.load_balance.costs",
        "system.reserves.lf_reserves_up",
        "system.reserves.regulation_up",
        "system.reserves.lf_reserves_down",
        "system.reserves.regulation_down",
        "system.policy.rps.rps_balance",
        "system.policy.carbon_cap.carbon_balance",
        "objective.min_total_cost"
    ]
    return all_modules


def optional_modules_list():
    # Names of groups of optional modules
    optional_modules = {
        "fuels":
            ["project.fuels", "project.operations.fuel_burn"],
        "multi_stage":
            ["project.operations.fix_commitment"],
        "transmission":
            ["transmission",
             "transmission.capacity.capacity",
             "transmission.operations.operations"],
        "transmission_hurdle_rates":
             ["transmission.operations.aggregate_costs"],
        "lf_reserves_up":
            ["geography.load_following_up_balancing_areas",
             "project.operations.reserves.lf_reserves_up",
             "system.reserves.lf_reserves_up"],
        "lf_reserves_down":
            ["geography.load_following_down_balancing_areas",
             "project.operations.reserves.lf_reserves_down",
             "system.reserves.lf_reserves_down"],
        "regulation_up":
            ["geography.regulation_up_balancing_areas",
             "project.operations.reserves.regulation_up",
             "system.reserves.regulation_up"],
        "regulation_down":
            ["geography.regulation_down_balancing_areas",
             "project.operations.reserves.regulation_down",
             "system.reserves.regulation_down"],
        "rps":
            ["geography.rps_zones",
             "system.policy.rps.rps_requirement",
             "project.operations.aggregate_recs",
             "system.policy.rps.rps_balance"],
        "carbon_cap":
            ["geography.carbon_cap_zones",
             "system.policy.carbon_cap.carbon_cap",
             "project.operations.aggregate_carbon_emissions",
             "system.policy.carbon_cap.carbon_balance"]
    }
    return optional_modules


def cross_modules_list():
    # Some modules depend on more than one supermodule
    # Currently, these are: track_carbon_imports and simultaneous_flow_limits
    cross_modules = {
        ("transmission", "carbon_cap", "track_carbon_imports"):
            ["transmission.operations.aggregate_carbon_emissions"],
        ("transmission", "simultaneous_flow_limits"):
            ["transmission.operations.simultaneous_flow_limits"]
    }
    return cross_modules


def get_modules(scenario_directory):
    """
    Modules needed for scenario
    :param scenario_directory:
    :return:
    """
    modules_file = os.path.join(scenario_directory, "modules.csv")
    try:
        requested_modules = pd.read_csv(modules_file)["modules"].tolist()
    except IOError:
        print("ERROR! Modules file {} not found".format(modules_file))
        sys.exit(1)

    # Remove any modules not requested by user
    modules_to_use = all_modules_list()

    optional_modules = optional_modules_list()
    for supermodule in optional_modules.keys():
        if supermodule in requested_modules:
            pass
        else:
            for m in optional_modules[supermodule]:
                modules_to_use.remove(m)

    # Some modules depend on more than one supermodule
    # We have to check if all supermodules that the module depends on are
    # specified before removing it
    cross_modules = cross_modules_list()
    for supermodule_group in cross_modules.keys():
        if all(supermodule in requested_modules
               for supermodule in supermodule_group ):
            pass
        else:
            for m in cross_modules[supermodule_group]:
                modules_to_use.remove(m)

    return modules_to_use


def load_modules(modules_to_use):
    """
    Load modules, keep track of which modules have been imported
    :param modules_to_use:
    :return:
    """
    loaded_modules = list()
    for m in modules_to_use:
        try:
            imported_module = import_module("."+m, package='gridpath')
            loaded_modules.append(imported_module)
        except ImportError:
            print("ERROR! Module " + str(m) + " not found.")
            sys.exit(1)

    return loaded_modules