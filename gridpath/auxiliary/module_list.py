# Copyright 2016-2020 Blue Marble Analytics LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains:

1) the list of all GridPath modules;
2) the modules included in each optional feature;
3) the 'cross-feature' modules;
4) the method for determining the user-requested features for the scenarios;
5) the method for loading modules.
"""

from __future__ import print_function

from builtins import str
from importlib import import_module
import os.path
import pandas as pd
import sys
import traceback

from gridpath.auxiliary.auxiliary import check_for_integer_subdirectories


def all_modules_list():
    """
    :return: list of all GridPath modules in order they are loaded

    This is the list of all GridPath modules in the order they would be
    loaded if all optional features were selected.
    """
    all_modules = [
        "temporal.operations.timepoints",
        "temporal.operations.horizons",
        "temporal.investment.periods",
        "geography.load_zones",
        "geography.load_following_up_balancing_areas",
        "geography.load_following_down_balancing_areas",
        "geography.regulation_up_balancing_areas",
        "geography.regulation_down_balancing_areas",
        "geography.frequency_response_balancing_areas",
        "geography.spinning_reserves_balancing_areas",
        "geography.energy_target_zones",
        "geography.carbon_cap_zones",
        "geography.carbon_tax_zones",
        "geography.prm_zones",
        "geography.local_capacity_zones",
        "geography.markets",
        "system.load_balance.static_load_requirement",
        "system.reserves.requirement.lf_reserves_up",
        "system.reserves.requirement.lf_reserves_down",
        "system.reserves.requirement.regulation_up",
        "system.reserves.requirement.regulation_down",
        "system.reserves.requirement.frequency_response",
        "system.reserves.requirement.spinning_reserves",
        "system.policy.energy_targets.period_energy_target",
        "system.policy.energy_targets.horizon_energy_target",
        "system.policy.carbon_cap.carbon_cap",
        "system.policy.carbon_tax.carbon_tax",
        "system.reliability.prm.prm_requirement",
        "system.reliability.local_capacity.local_capacity_requirement",
        "system.markets.prices",
        "project",
        "project.capacity",
        "project.capacity.capacity_types",
        "project.capacity.capacity",
        "project.capacity.capacity_groups",
        "project.capacity.costs",
        "project.availability.availability",
        "project.fuels",
        "project.operations",
        "project.operations.reserves.lf_reserves_up",
        "project.operations.reserves.lf_reserves_down",
        "project.operations.reserves.regulation_up",
        "project.operations.reserves.regulation_down",
        "project.operations.reserves.frequency_response",
        "project.operations.reserves.spinning_reserves",
        "project.operations.operational_types",
        "project.operations.reserves.op_type_dependent.lf_reserves_up",
        "project.operations.reserves.op_type_dependent.lf_reserves_down",
        "project.operations.reserves.op_type_dependent.regulation_up",
        "project.operations.reserves.op_type_dependent.regulation_down",
        "project.operations.reserves.op_type_dependent.frequency_response",
        "project.operations.reserves.op_type_dependent.spinning_reserves",
        "project.operations.power",
        "project.operations.fix_commitment",
        "project.operations.fuel_burn",
        "project.operations.costs",
        "project.operations.tuning_costs",
        "project.operations.energy_target_contributions",
        "project.operations.carbon_emissions",
        "project.operations.carbon_cap",
        "project.operations.carbon_tax",
        "project.reliability.prm",
        "project.reliability.prm.prm_types",
        "project.reliability.prm.prm_simple",
        "project.reliability.prm.elcc_surface",
        "project.reliability.prm.group_costs",
        "project.reliability.local_capacity",
        "project.reliability.local_capacity.local_capacity_contribution",
        "transmission",
        "transmission.capacity.capacity_types",
        "transmission.capacity.capacity",
        "transmission.operations.operational_types",
        "transmission.operations.operations",
        "transmission.operations.hurdle_costs",
        "transmission.operations.simultaneous_flow_limits",
        "transmission.operations.carbon_emissions",
        "system.load_balance.aggregate_project_power",
        "system.load_balance.aggregate_transmission_power",
        "transmission.operations.export_penalty_costs",
        "system.load_balance.market_participation",
        "system.load_balance.load_balance",
        "system.reserves.aggregation.lf_reserves_up",
        "system.reserves.aggregation.regulation_up",
        "system.reserves.aggregation.lf_reserves_down",
        "system.reserves.aggregation.regulation_down",
        "system.reserves.aggregation.frequency_response",
        "system.reserves.aggregation.spinning_reserves",
        "system.reserves.balance.lf_reserves_up",
        "system.reserves.balance.regulation_up",
        "system.reserves.balance.lf_reserves_down",
        "system.reserves.balance.regulation_down",
        "system.reserves.balance.frequency_response",
        "system.reserves.balance.spinning_reserves",
        "system.policy.energy_targets"
        ".aggregate_period_energy_target_contributions",
        "system.policy.energy_targets"
        ".aggregate_horizon_energy_target_contributions",
        "system.policy.energy_targets.period_energy_target_balance",
        "system.policy.energy_targets.horizon_energy_target_balance",
        "system.policy.carbon_cap.aggregate_project_carbon_emissions",
        "system.policy.carbon_cap.aggregate_transmission_carbon_emissions",
        "system.policy.carbon_cap.carbon_balance",
        "system.policy.carbon_tax.aggregate_project_carbon_emissions",
        "system.policy.carbon_tax.carbon_tax_costs",
        "system.reliability.prm.aggregate_project_simple_prm_contribution",
        "system.reliability.prm.elcc_surface",
        "system.reliability.prm.prm_balance",
        "system.reliability.local_capacity"
        ".aggregate_local_capacity_contribution",
        "system.reliability.local_capacity.local_capacity_balance",
        "system.markets.volume",
        "objective.project.aggregate_capacity_costs",
        "objective.project.aggregate_prm_group_costs",
        "objective.project.aggregate_operational_costs",
        "objective.project.aggregate_operational_tuning_costs",
        "objective.transmission.aggregate_capacity_costs",
        "objective.transmission.aggregate_hurdle_costs",
        "objective.transmission.aggregate_export_penalty_costs",
        "objective.transmission.carbon_imports_tuning_costs",
        "objective.system.aggregate_load_balance_penalties",
        "objective.system.reserve_violation_penalties.lf_reserves_up",
        "objective.system.reserve_violation_penalties.lf_reserves_down",
        "objective.system.reserve_violation_penalties.regulation_up",
        "objective.system.reserve_violation_penalties.regulation_down",
        "objective.system.reserve_violation_penalties.frequency_response",
        "objective.system.reserve_violation_penalties.spinning_reserves",
        "objective.system.policy"
        ".aggregate_period_energy_target_violation_penalties",
        "objective.system.policy"
        ".aggregate_horizon_energy_target_violation_penalties",
        "objective.system.policy.aggregate_carbon_cap_violation_penalties",
        "objective.system.policy.aggregate_carbon_tax_costs",
        "objective.system.reliability.prm.dynamic_elcc_tuning_penalties",
        "objective.system.reliability.prm.aggregate_prm_violation_penalties",
        "objective.system.reliability.local_capacity"
        ".aggregate_local_capacity_violation_penalties",
        "objective.system.aggregate_market_revenue_and_costs",
        "objective.max_npv"
    ]
    return all_modules


def optional_modules_list():
    """
    :return: dictionary with the optional feature names as keys and a list
        of the modules included in each feature as values

    These are all of GridPath's optional modules grouped by features (features
    as the dictionary keys). Each of these modules belongs to only one feature.
    """
    optional_modules = {
        "transmission":
            ["transmission",
             "transmission.capacity.capacity_types",
             "transmission.capacity.capacity",
             "transmission.operations.operational_types",
             "transmission.operations.operations",
             "system.load_balance.aggregate_transmission_power",
             "transmission.operations.export_penalty_costs",
             "objective.transmission.aggregate_capacity_costs",
             "objective.transmission.aggregate_export_penalty_costs"],
        "lf_reserves_up":
            ["geography.load_following_up_balancing_areas",
             "system.reserves.requirement.lf_reserves_up",
             "project.operations.reserves.lf_reserves_up",
             "project.operations.reserves.op_type_dependent.lf_reserves_up",
             "system.reserves.aggregation.lf_reserves_up",
             "system.reserves.balance.lf_reserves_up",
             "objective.system.reserve_violation_penalties.lf_reserves_up"],
        "lf_reserves_down":
            ["geography.load_following_down_balancing_areas",
             "system.reserves.requirement.lf_reserves_down",
             "project.operations.reserves.lf_reserves_down",
             "project.operations.reserves.op_type_dependent.lf_reserves_down",
             "system.reserves.aggregation.lf_reserves_down",
             "system.reserves.balance.lf_reserves_down",
             "objective.system.reserve_violation_penalties.lf_reserves_down"],
        "regulation_up":
            ["geography.regulation_up_balancing_areas",
             "system.reserves.requirement.regulation_up",
             "project.operations.reserves.regulation_up",
             "project.operations.reserves.op_type_dependent.regulation_up",
             "system.reserves.aggregation.regulation_up",
             "system.reserves.balance.regulation_up",
             "objective.system.reserve_violation_penalties.regulation_up"],
        "regulation_down":
            ["geography.regulation_down_balancing_areas",
             "system.reserves.requirement.regulation_down",
             "project.operations.reserves.regulation_down",
             "system.reserves.aggregation.regulation_down",
             "project.operations.reserves.op_type_dependent.regulation_down",
             "system.reserves.balance.regulation_down",
             "objective.system.reserve_violation_penalties.regulation_down"],
        "frequency_response":
            ["geography.frequency_response_balancing_areas",
             "system.reserves.requirement.frequency_response",
             "project.operations.reserves.frequency_response",
             "project.operations.reserves.op_type_dependent."
             "frequency_response",
             "system.reserves.aggregation.frequency_response",
             "system.reserves.balance.frequency_response",
             "objective.system.reserve_violation_penalties.frequency_response"
             ],
        "spinning_reserves":
            ["geography.spinning_reserves_balancing_areas",
             "system.reserves.requirement.spinning_reserves",
             "project.operations.reserves.spinning_reserves",
             "project.operations.reserves.op_type_dependent.spinning_reserves",
             "system.reserves.aggregation.spinning_reserves",
             "system.reserves.balance.spinning_reserves",
             "objective.system.reserve_violation_penalties.spinning_reserves"],
        "period_energy_target":
            ["system.policy.energy_targets.period_energy_target",
             "system.policy.energy_targets"
             ".aggregate_period_energy_target_contributions",
             "system.policy.energy_targets.period_energy_target_balance",
             "objective.system.policy"
             ".aggregate_period_energy_target_violation_penalties"],
        "horizon_energy_target":
            ["system.policy.energy_targets.horizon_energy_target",
             "system.policy.energy_targets"
             ".aggregate_horizon_energy_target_contributions",
             "system.policy.energy_targets.horizon_energy_target_balance",
             "objective.system.policy"
             ".aggregate_horizon_energy_target_violation_penalties"],
        "carbon_cap":
            ["geography.carbon_cap_zones",
             "system.policy.carbon_cap.carbon_cap",
             "project.operations.carbon_cap",
             "system.policy.carbon_cap.aggregate_project_carbon_emissions",
             "system.policy.carbon_cap.carbon_balance",
             "objective.system.policy.aggregate_carbon_cap_violation_penalties"
             ],
        "carbon_tax":
            ["geography.carbon_tax_zones",
             "system.policy.carbon_tax.carbon_tax",
             "project.operations.carbon_tax",
             "system.policy.carbon_tax.aggregate_project_carbon_emissions",
             "system.policy.carbon_tax.carbon_tax_costs",
             "objective.system.policy.aggregate_carbon_tax_costs"
            ],
        "prm":
            ["geography.prm_zones",
             "system.reliability.prm.prm_requirement",
             "project.reliability.prm",
             "project.reliability.prm.prm_types",
             "project.reliability.prm.prm_simple",
             "project.reliability.prm.group_costs",
             "system.reliability.prm."
             "aggregate_project_simple_prm_contribution",
             "system.reliability.prm.prm_balance",
             "objective.project."
             "aggregate_prm_group_costs",
             "objective.system.reliability.prm."
             "aggregate_prm_violation_penalties"
             ],
        "local_capacity": [
            "geography.local_capacity_zones",
             "system.reliability.local_capacity.local_capacity_requirement",
             "project.reliability.local_capacity",
             "project.reliability.local_capacity.local_capacity_contribution",
             "system.reliability.local_capacity"
             ".aggregate_local_capacity_contribution",
             "system.reliability.local_capacity.local_capacity_balance",
             "objective.system.reliability.local_capacity"
             ".aggregate_local_capacity_violation_penalties",
            ],
        "markets": [
            "geography.markets",
            "system.markets.prices",
            "system.load_balance.market_participation",
            "system.markets.volume",
            "objective.system.aggregate_market_revenue_and_costs"
            ],
        "tuning": [
            "project.operations.tuning_costs",
            "objective.project.aggregate_operational_tuning_costs"
            ]
    }
    return optional_modules


def cross_feature_modules_list():
    """
    :return: dictionary with a tuple of features as keys and a list of
        modules to be included if all those features are selected as values

    Some modules depend on more than one feature, i.e. they are included
    only if multiple features are selected. These relationships are
    described in the 'cross_modules' dictionary here.
    """
    cross_modules = {
        ("transmission", "transmission_hurdle_rates"):
            ["transmission.operations.hurdle_costs",
             "objective.transmission.aggregate_hurdle_costs"],
        ("transmission", "carbon_cap", "track_carbon_imports"):
            ["system.policy.carbon_cap"
             ".aggregate_transmission_carbon_emissions",
             "transmission.operations.carbon_emissions"],
        ("transmission", "carbon_cap", "track_carbon_imports", "tuning"):
            ["objective.transmission.carbon_imports_tuning_costs"],
        ("transmission", "simultaneous_flow_limits"):
            ["transmission.operations.simultaneous_flow_limits"],
        ("prm", "elcc_surface"):
            ["project.reliability.prm.elcc_surface",
             "system.reliability.prm.elcc_surface"],
        ("prm", "elcc_surface", "tuning"):
            ["objective.system.reliability.prm.dynamic_elcc_tuning_penalties"]
    }
    return cross_modules


def feature_shared_modules_list():
    """
    :return: dictionary with a tuple of features as keys and a list of
        modules to be included if either of those features is selected as
        values
    """
    shared_modules = {
        ("period_energy_target", "horizon_energy_target"):
            ["geography.energy_target_zones",
             "project.operations.energy_target_contributions"],
    }

    return shared_modules


def determine_modules(
    features=None, scenario_directory=None, multi_stage=None,
):
    """
    :param features: List of requested features. Optional input; if
        not specified, function will try to load 'features.csv' file to
        determine the requested features.
    :param scenario_directory: the scenario directory, where we will look
        for the list of requested features. Optional input; if not specified,
        function will look for the 'features' input parameter
    :param multi_stage: Boolean. Optional input that determines whether the
        fix_commitment module is used (yes if True, no if False); if not
        specified, this function will check the scenario_directory to
        determine whether there are stage subdirectories (if there are not,
        the fix_commitment module is removed).
    :return: the list of modules -- a subset of all GridPath modules -- needed
        for a scenario. These are the module names, not the actual modules.

    This method determines which modules are needed for a scenario based on
    the features specified for the scenario. The features can be either
    directly specified as a list or by providing the directory where a
    'features.csv' file lists the requested features.

    We start with the list of all GridPath modules from *all_modules_list()*
    as the list of modules to use in the scenario. We then iterate over all
    optional features, which we get from the keys of the
    *optional_modules_list()* method above; if the feature is in the list of
    user-requested features, we do nothing; if it is not, we remove all of the
    feature's modules from the list of modules to use. Similarly, for the cross
    feature modules, which we get from the *cross_feature_module_list()* method,
    we check if all features they depend on are included and, if not, remove
    those modules from the list of modules to use.
    """
    if (scenario_directory is None) and (features is None):
        raise IOError("""Need to specify either 'scenario_directory', the
                      directory where 'features.csv' is saved, or 'features',
                      the list of requested features""")
    elif features is not None:
        requested_features = features
    elif scenario_directory is not None:
        features_file = os.path.join(scenario_directory, "features.csv")
        try:
            requested_features = pd.read_csv(features_file)["features"].tolist()
        except IOError:
            print("ERROR! Features file {} not found in {}.".format(
                features_file, scenario_directory
            ))
            sys.exit(1)

    # Remove any modules not requested by user
    # Start with the list of all modules
    modules_to_use = all_modules_list()

    # If we haven't explicitly specified whether this is a multi-stages
    # scenario, check the scenario directory to determine whether we have
    # multiple stages and remove the fix_commitment module from the
    # modules_to_use list if not
    # Also remove the fix_commitment if the multi_stage argument is False
    if multi_stage is None:
        subproblems = check_for_integer_subdirectories(scenario_directory)
        # Check if we have subproblems
        if subproblems:
            # If so, check if there are stages in the subproblem
            for subproblem in subproblems:
                stages = check_for_integer_subdirectories(
                    os.path.join(scenario_directory, subproblem)
                )
                # If we find stages in any subproblem, break out of the loop
                # and keep the fix_commitment module
                if stages:
                    break
            else:
                modules_to_use.remove("project.operations.fix_commitment")
        # If we make it here, we didn't find subproblems so we'll remove the
        # fix_commitment module
        else:
            modules_to_use.remove("project.operations.fix_commitment")
    # If multi_stages has been specified explicitly, decide whether to
    # remove the fix_commitment module based on the value specified
    elif multi_stage is False:
        modules_to_use.remove("project.operations.fix_commitment")
    else:
        pass

    # Remove modules associated with features that are not requested
    optional_modules = optional_modules_list()
    for feature in list(optional_modules.keys()):
        if feature in requested_features:
            pass
        else:
            for m in optional_modules[feature]:
                modules_to_use.remove(m)

    # Remove shared modules if none of the features sharing those modules is
    # requested
    shared_modules = feature_shared_modules_list()
    for feature_group in shared_modules.keys():
        if any(feature in requested_features for feature in feature_group):
            pass
        else:
            for m in shared_modules[feature_group]:
                modules_to_use.remove(m)
            
    # Some modules depend on more than one feature
    # We have to check if all features that the module depends on are
    # specified before removing it
    cross_feature_modules = cross_feature_modules_list()
    for feature_group in list(cross_feature_modules.keys()):
        if all(feature in requested_features
               for feature in feature_group):
            pass
        else:
            for m in cross_feature_modules[feature_group]:
                modules_to_use.remove(m)

    return modules_to_use


def load_modules(modules_to_use):
    """
    :param modules_to_use: a list of the names of the modules to use
    :return: list of imported modules (Python <class 'module'> objects)

    Load the requested modules and return them as a list of Python module
    objects.
    """
    loaded_modules = list()
    for m in modules_to_use:
        try:
            imported_module = import_module("."+m, package='gridpath')
            loaded_modules.append(imported_module)
        except ImportError:
            print("ERROR! Unable to import module " + str(m) + ".")
            traceback.print_exc()
            sys.exit(1)

    return loaded_modules
