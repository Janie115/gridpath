#!/usr/bin/env python

"""
Operations of must-run generators. Can't provide reserves.
"""

from pyomo.environ import Var

from ..auxiliary import make_gen_tmp_var_df


def add_module_specific_components(m):
    """
    Add a continuous commit variable to represent the fraction of fleet
    capacity that is on.
    :param m:
    :return:
    """

    m.Commit_Continuous = Var(m.DISPATCHABLE_CONTINUOUS_COMMIT_GENERATORS,
                              m.TIMEPOINTS,
                              bounds=(0, 1)
                              )


def power_provision_rule(mod, g, tmp):
    """
    Power provision from dispatchable generators is an endogenous variable.
    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    return mod.Provide_Power_MW[g, tmp]


def commitment_rule(mod, g, tmp):
    return mod.Commit_Continuous[g, tmp]


def max_power_rule(mod, g, tmp):
    """
    Power plus upward services cannot exceed capacity.
    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    return mod.Provide_Power_MW[g, tmp] + \
        mod.Headroom_Provision_MW[g, tmp] \
        <= mod.Capacity_MW[g, mod.period[tmp]] * mod.Commit_Continuous[g, tmp]


def min_power_rule(mod, g, tmp):
    """
    Power minus downward services cannot be below a minimum stable level.
    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    return mod.Provide_Power_MW[g, tmp] - \
        mod.Footroom_Provision_MW[g, tmp] \
        >= mod.Commit_Continuous[g, tmp] * mod.Capacity_MW[g, mod.period[tmp]] \
        * mod.min_stable_level_fraction[g]


# TODO: figure out how this should work with fleets (unit size here or in data)
def fuel_use_rule(mod, g, tmp):
    """
    Fuel use in terms of an IO curve with an incremental heat rate above
    the minimum stable level, i.e. a minimum MMBtu input to have the generator
    on plus incremental fuel use for each MWh above the minimum stable level of
    the generator.
    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    return mod.Commit_Continuous[g, tmp] \
        * mod.minimum_input_mmbtu_per_hr[g] \
        + (mod.Provide_Power_MW[g, tmp] -
           (mod.Commit_Continuous[g, tmp] * mod.Capacity_MW[g, mod.period[tmp]]
            * mod.min_stable_level_fraction[g])
           ) * mod.inc_heat_rate_mmbtu_per_mwh[g]


# TODO: startup/shutdown cost per unit won't work without additional info
# about unit size vs total fleet size if modeling a fleet with this module
def startup_rule(mod, g, tmp):
    """
    Will be positive when there are more generators committed in the current
    timepoint that there were in the previous timepoint.
    If horizon is circular, the last timepoint of the horizon is the
    previous_timepoint for the first timepoint if the horizon;
    if the horizon is linear, no previous_timepoint is defined for the first
    timepoint of the horizon, so return 'None' here
    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    if tmp == mod.first_horizon_timepoint[mod.horizon[tmp]] \
            and mod.boundary[mod.horizon[tmp]] == "linear":
        return None
    else:
        return mod.Commit_Continuous[g, tmp] \
            - mod.Commit_Continuous[g, mod.previous_timepoint[tmp]]


def shutdown_rule(mod, g, tmp):
    """
    Will be positive when there were more generators committed in the previous
    timepoint that there are in the current timepoint.
    If horizon is circular, the last timepoint of the horizon is the
    previous_timepoint for the first timepoint if the horizon;
    if the horizon is linear, no previous_timepoint is defined for the first
    timepoint of the horizon, so return 'None' here
    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    if tmp == mod.first_horizon_timepoint[mod.horizon[tmp]] \
            and mod.boundary[mod.horizon[tmp]] == "linear":
        return None
    else:
        return mod.Commit_Continuous[g, mod.previous_timepoint[tmp]] \
            - mod.Commit_Continuous[g, tmp]


def fix_commitment(mod, g, tmp):
    """

    :param mod:
    :param g:
    :param tmp:
    :return:
    """
    mod.Commit_Continuous[g, tmp] = mod.fixed_commitment[g, tmp].value
    mod.Commit_Continuous[g, tmp].fixed = True


def export_module_specific_results(mod):
    """
    Export commitment decisions.
    :param mod:
    :return:
    """

    continuous_commit_df = \
        make_gen_tmp_var_df(
            mod,
            "DISPATCHABLE_CONTINUOUS_COMMIT_GENERATOR_OPERATIONAL_TIMEPOINTS",
            "Commit_Continuous",
            "commit_continuous")

    mod.module_specific_df.append(continuous_commit_df)
