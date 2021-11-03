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
This operational type describes transmission lines whose flows are simulated
using a linear transport model, i.e. transmission flow is constrained to be
less than or equal to the line capacity. Line capacity can be defined for
both transmission flow directions. The user can define losses as a fraction
of line flow.

"""

import csv
import os
import pandas as pd
from pyomo.environ import Set, Param, Var, Constraint, NonNegativeReals, \
    Reals, PercentFraction


def add_model_components(
        m, d, scenario_directory, subproblem, stage
):
    """
    The following Pyomo model components are defined in this module:

    +-------------------------------------------------------------------------+
    | Sets                                                                    |
    +=========================================================================+
    | | :code:`TX_SIMPLE`                                                     |
    |                                                                         |
    | The set of transmission lines of the :code:`tx_simple` operational      |
    | type.                                                                   |
    +-------------------------------------------------------------------------+
    | | :code:`TX_SIMPLE_OPR_TMPS`                                            |
    |                                                                         |
    | Two-dimensional set with transmission lines of the :code:`tx_simple`    |
    | operational type and their operational timepoints.                      |
    +-------------------------------------------------------------------------+

    +-------------------------------------------------------------------------+
    | Params                                                                  |
    +=========================================================================+
    | | :code:`tx_simple_loss_factor`                                         |
    | | *Defined over*: :code:`TX_SIMPLE`                                     |
    | | *Within*: :code:`PercentFraction`                                     |
    | | *Default*: :code:`0`                                                  |
    |                                                                         |
    | The fraction of power that is lost when transmitted over this line.     |
    +-------------------------------------------------------------------------+


    |

    +-------------------------------------------------------------------------+
    | Variables                                                               |
    +=========================================================================+
    | | :code:`TxSimple_Transmit_Power_MW`                                    |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    | | *Within*: :code:`Reals`                                               |
    |                                                                         |
    | The transmission line's power flow in each timepoint in which the line  |
    | is operational. Negative power means the power flow goes in the         |
    | opposite direction of the line's defined direction.                     |
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Losses_LZ_From_MW`                                    |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    | | *Within*: :code:`NonNegativeReals`                                    |
    |                                                                         |
    | Losses on the transmission line in each timepoint, which we'll account  |
    | for in the "from" origin load zone's load balance, i.e. losses incurred |
    | when power is flowing to the "from" zone.                               |
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Losses_LZ_To_MW`                                      |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    | | *Within*: :code:`NonNegativeReals`                                    |
    |                                                                         |
    | Losses on the transmission line in each timepoint, which we'll account  |
    | for in the "to" origin load zone's load balance, i.e. losses incurred   |
    | when power is flowing to the "to" zone.                                 |
    +-------------------------------------------------------------------------+

    |

    +-------------------------------------------------------------------------+
    | Constraints                                                             |
    +=========================================================================+
    | | :code:`TxSimple_Min_Transmit_Constraint`                              |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    |                                                                         |
    | Transmitted power should exceed the transmission line's minimum power   |
    | flow for in every operational timepoint.                                |
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Max_Transmit_Constraint`                              |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    |                                                                         |
    | Transmitted power cannot exceed the transmission line's maximum power   |
    | flow in every operational timepoint.                                    |
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Losses_LZ_From_Constraint`                            |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    |                                                                         |
    | Losses to be accounted for in the "from" load zone's load balance are 0 |
    | when power flow on the line is positive (power flowing from the "from"  |
    | to the "to" load zone) and must be greater than or equal to  the flow   |
    | times the loss factor otherwise (power flowing to the "from" load zone).|
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Losses_LZ_To_Constraint`                              |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    |                                                                         |
    | Losses to be accounted for in the "to" load zone's load balance are 0   |
    | when power flow on the line is negative (power flowing from the "to"    |
    | to the "from" load zone) and must be greater than or equal to the flow  |
    | times the loss factor otherwise (power flowing to the "to" load zone).  |
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Max_Losses_From_Constraint`                           |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    |                                                                         |
    | Losses cannot exceed the maximum transmission flow capacity times the   |
    | loss factor in each operational timepoint. Provides upper bound on      |
    | losses.                                                                 |
    +-------------------------------------------------------------------------+
    | | :code:`TxSimple_Max_Losses_To_Constraint`                             |
    | | *Defined over*: :code:`TX_SIMPLE_OPR_TMPS`                            |
    |                                                                         |
    | Losses cannot exceed the maximum transmission flow capacity times the   |
    | loss factor in each operational timepoint. Provides upper bound on      |
    | losses.                                                                 |
    +-------------------------------------------------------------------------+

    """

    # Sets
    ###########################################################################

    m.TX_SIMPLE = Set(
        within=m.TX_LINES,
        initialize=lambda mod: list(
            set(l for l in mod.TX_LINES
                if mod.tx_operational_type[l] == "tx_simple")
        )
    )

    m.TX_SIMPLE_OPR_TMPS = Set(
        dimen=2, within=m.TX_OPR_TMPS,
        initialize=lambda mod: list(
            set((l, tmp) for (l, tmp) in mod.TX_OPR_TMPS
                if l in mod.TX_SIMPLE)
        )
    )

    m.TX_SIMPLE_BLN_TYPE_HRZS_W_MIN_CONSTRAINT = Set(
        dimen=3, within=m.TX_SIMPLE * m.BLN_TYPE_HRZS
    )

    # Params
    ###########################################################################
    m.tx_simple_loss_factor = Param(
        m.TX_SIMPLE, within=PercentFraction, default=0
    )

    # Optional Params
    ###########################################################################

    m.tx_simple_min_transmit_power_mw = Param(
        m.TX_SIMPLE_BLN_TYPE_HRZS_W_MIN_CONSTRAINT,
        within=Reals, default=0
    )

    # Variables
    ###########################################################################

    m.TxSimple_Transmit_Power_MW = Var(
        m.TX_SIMPLE_OPR_TMPS,
        within=Reals
    )

    m.TxSimple_Losses_LZ_From_MW = Var(
        m.TX_SIMPLE_OPR_TMPS,
        within=NonNegativeReals
    )

    m.TxSimple_Losses_LZ_To_MW = Var(
        m.TX_SIMPLE_OPR_TMPS,
        within=NonNegativeReals
    )

    # Constraints
    ###########################################################################

    m.TxSimple_Min_Transmit_Constraint = Constraint(
        m.TX_SIMPLE_OPR_TMPS,
        rule=min_transmit_rule
    )

    m.TxSimple_Max_Transmit_Constraint = Constraint(
        m.TX_SIMPLE_OPR_TMPS,
        rule=max_transmit_rule
    )

    m.TxSimple_Losses_LZ_From_Constraint = Constraint(
        m.TX_SIMPLE_OPR_TMPS,
        rule=losses_lz_from_rule
    )

    m.TxSimple_Losses_LZ_To_Constraint = Constraint(
        m.TX_SIMPLE_OPR_TMPS,
        rule=losses_lz_to_rule
    )

    m.TxSimple_Max_Losses_From_Constraint = Constraint(
        m.TX_SIMPLE_OPR_TMPS,
        rule=max_losses_from_rule
    )

    m.TxSimple_Max_Losses_To_Constraint = Constraint(
        m.TX_SIMPLE_OPR_TMPS,
        rule=max_losses_to_rule
    )

    m.TxSimple_Min_Transmit_Power_Constraint = Constraint(
        m.TX_SIMPLE_BLN_TYPE_HRZS_W_MIN_CONSTRAINT,
        rule=min_transmit_power_rule
    )

# Constraint Formulation Rules
###############################################################################

# TODO: should these move to operations.py since all transmission op_types
#  have this constraint?
def min_transmit_rule(mod, l, tmp):
    """
    **Constraint Name**: TxSimple_Min_Transmit_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS

    Transmitted power should exceed the minimum transmission flow capacity in
    each operational timepoint.
    """
    return mod.TxSimple_Transmit_Power_MW[l, tmp] \
        >= mod.Tx_Min_Capacity_MW[l, mod.period[tmp]] \
        * mod.Tx_Availability_Derate[l, tmp]


def max_transmit_rule(mod, l, tmp):
    """
    **Constraint Name**: TxSimple_Max_Transmit_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS

    Transmitted power cannot exceed the maximum transmission flow capacity in
    each operational timepoint.
    """
    return mod.TxSimple_Transmit_Power_MW[l, tmp] \
        <= mod.Tx_Max_Capacity_MW[l, mod.period[tmp]] \
        * mod.Tx_Availability_Derate[l, tmp]


def losses_lz_from_rule(mod, l, tmp):
    """
    **Constraint Name**: TxSimple_Losses_LZ_From_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS

    Losses for the 'from' load zone of this transmission line (non-negative
    variable) must be greater than or equal to the negative of the flow times
    the loss factor. When the flow on the line is negative, power is flowing
    to the 'from', so losses are positive. When the flow on the line is
    positive (i.e. power flowing from the 'from' load zone), losses can be set
    to zero.
    If the tx_simple_loss_factor is 0, losses are set to 0.
    WARNING: since we have a greater than or equal constraint here, whenever
    tx_simple_loss_factor is not 0, the model can incur line losses that are
    not actually real.
    """
    if mod.tx_simple_loss_factor[l] == 0:
        return mod.TxSimple_Losses_LZ_From_MW[l, tmp] == 0
    else:
        return mod.TxSimple_Losses_LZ_From_MW[l, tmp] >= \
            - mod.TxSimple_Transmit_Power_MW[l, tmp] * \
            mod.tx_simple_loss_factor[l]


def losses_lz_to_rule(mod, l, tmp):
    """
    **Constraint Name**: TxSimple_Losses_LZ_To_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS

    Losses for the 'to' load zone of this transmission line (non-negative
    variable) must be greater than or equal to the flow times the loss
    factor. When the flow on the line is positive, power is flowing to the
    'to' LZ, so losses are positive. When the flow on the line is negative
    (i.e. power flowing from the 'to' load zone), losses can be set to zero.
    If the tx_simple_loss_factor is 0, losses are set to 0.
    WARNING: since we have a greater than or equal constraint here, whenever
    tx_simple_loss_factor is not 0, the model can incur line losses that are
    not actually real.
    """
    if mod.tx_simple_loss_factor[l] == 0:
        return mod.TxSimple_Losses_LZ_To_MW[l, tmp] == 0
    else:
        return mod.TxSimple_Losses_LZ_To_MW[l, tmp] >= \
            mod.TxSimple_Transmit_Power_MW[l, tmp] * \
            mod.tx_simple_loss_factor[l]


def max_losses_from_rule(mod, l, tmp):
    """
    **Constraint Name**: TxSimple_Max_Losses_From_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS

    Losses cannot exceed the maximum transmission flow capacity times the
    loss factor in each operational timepoint. Provides upper bound on losses.
    """
    if mod.tx_simple_loss_factor[l] == 0:
        return mod.TxSimple_Losses_LZ_From_MW[l, tmp] == 0
    else:
        return mod.TxSimple_Losses_LZ_From_MW[l, tmp] \
            <= mod.Tx_Max_Capacity_MW[l, mod.period[tmp]] \
            * mod.Tx_Availability_Derate[l, tmp] \
            * mod.tx_simple_loss_factor[l]


def max_losses_to_rule(mod, l, tmp):
    """
    **Constraint Name**: TxSimple_Max_Losses_To_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS

    Losses cannot exceed the maximum transmission flow capacity times the
    loss factor in each operational timepoint. Provides upper bound on losses.
    """
    if mod.tx_simple_loss_factor[l] == 0:
        return mod.TxSimple_Losses_LZ_To_MW[l, tmp] == 0
    else:
        return mod.TxSimple_Losses_LZ_To_MW[l, tmp] \
            <= mod.Tx_Max_Capacity_MW[l, mod.period[tmp]] \
            * mod.Tx_Availability_Derate[l, tmp] \
            * mod.tx_simple_loss_factor[l]


def min_transmit_power_rule(mod, l, bt, h):
    """
    **Constraint Name**: TxSimple_Min_Transmit_Power_Constraint
    **Enforced Over**: TX_SIMPLE_OPR_TMPS_W_MIN_CONSTRAINT

    Transmitted power should exceed the defined minimum transmission power in
    each operational timepoint.
    """
    var = mod.tx_simple_min_transmit_power_mw[l, bt, h]
    if var == 0:
        return Constraint.Skip
    elif var > 0:
        for tmp in mod.TMPS_BY_BLN_TYPE_HRZ[bt, h]:
            return mod.TxSimple_Transmit_Power_MW[l, tmp] >= var
    else:
        for tmp in mod.TMPS_BY_BLN_TYPE_HRZ[bt, h]:
            return mod.TxSimple_Transmit_Power_MW[l, tmp] <= var


# Transmission Operational Type Methods
###############################################################################

def transmit_power_rule(mod, line, tmp):
    """
    The power flow on this transmission line before accounting for losses.
    """
    return mod.TxSimple_Transmit_Power_MW[line, tmp]


def transmit_power_losses_lz_from_rule(mod, line, tmp):
    """
    Transmission losses that we'll account for in the origin 
    load zone (load_zone_from) of this transmission line. These are zero
    when the flow is positive (power flowing from the origin load zone) and
    can be more than 0 when the flow is negative (power flowing to the
    origin load zone).
    """
    return mod.TxSimple_Losses_LZ_From_MW[line, tmp]


def transmit_power_losses_lz_to_rule(mod, line, tmp):
    """
    Transmission losses that we'll account for in the destination
    load zone (load_zone_to) of this transmission line. These are zero
    when the flow is negative (power flowing from the destination load zone)
    and can be more than 0 when the flow is positive (power flowing to the
    destination load zone).
    """
    return mod.TxSimple_Losses_LZ_To_MW[line, tmp]


# Input-Output
###############################################################################

def load_model_data(m, d, data_portal, scenario_directory,
                              subproblem, stage):
    """

    :param m:
    :param data_portal:
    :param scenario_directory:
    :param subproblem:
    :param stage:
    :return:
    """

    # Get the simple transport model lines
    df = pd.read_csv(
        os.path.join(scenario_directory, str(subproblem), str(stage), "inputs",
                     "transmission_lines.tab"),
        sep="\t",
        usecols=["transmission_line", "tx_operational_type",
                 "tx_simple_loss_factor"]
    )
    df = df[df["tx_operational_type"] == "tx_simple"]

    # Dict of loss factor by tx_simple line based on raw data
    loss_factor_raw = dict(zip(
        df["transmission_line"],
        df["tx_simple_loss_factor"]
    ))

    # Convert loss factors to float and remove any missing data (will
    # default to 0 in the model)
    loss_factor = {
        line: float(loss_factor_raw[line])
        for line in loss_factor_raw
        if loss_factor_raw[line] != "."
    }

    # Load data
    data_portal.data()["tx_simple_loss_factor"] = loss_factor

    # Min transmit power
    transmission_horizons_with_min = list()
    min_transmit_power_mw = dict()

    header = pd.read_csv(
        os.path.join(scenario_directory, str(subproblem), str(stage), "inputs",
                     "transmission_min_transmit_power.tab"),
        sep="\t", header=None, nrows=1
    ).values[0]

    optional_columns = ["min_transmit_power_mw"]
    used_columns = [c for c in optional_columns if c in header]

    df = pd.read_csv(
        os.path.join(scenario_directory, str(subproblem), str(stage), "inputs",
                     "transmission_min_transmit_power.tab"),
        sep="\t", usecols=["transmission_line", "balancing_type_horizon", "horizon"] + used_columns
    )

    # min_transmit_power_mw is optional,
    # so TX_SIMPLE_BLN_TYPE_HRZS_W_MIN_CONSTRAINT
    # and min_transmit_power_mw simply won't be initialized if
    # min_transmit_power_mw does not exist in the input file
    if "min_transmit_power_mw" in df.columns:
        for row in zip(df["transmission_line"],
                       df["balancing_type_horizon"],
                       df["horizon"],
                       df["min_transmit_power_mw"]):
            if row[3] != ".":
                transmission_horizons_with_min.append((row[0], row[1], row[2]))
                min_transmit_power_mw[(row[0], row[1], row[2])] = float(row[3])
            else:
                pass
    else:
        pass

    # Load min transmit power data
    if not transmission_horizons_with_min:
        pass  # if the list is empty, don't initialize the set
    else:
        data_portal.data()["TX_SIMPLE_BLN_TYPE_HRZS_W_MIN_CONSTRAINT"] = \
            {None: transmission_horizons_with_min}

    data_portal.data()["tx_simple_min_transmit_power_mw"] = \
        min_transmit_power_mw


def get_model_inputs_from_database(scenario_id, subscenarios, subproblem, stage, conn):
    """
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """
    subproblem = 1 if subproblem == "" else subproblem
    stage = 1 if stage == "" else stage

    c = conn.cursor()
    tx_min_transmit_power = c.execute(
        """SELECT transmission_line, balancing_type_horizon, horizon, min_transmit_power_mw
        FROM inputs_transmission_min_transmit_power
        JOIN
        (SELECT balancing_type_horizon, horizon
        FROM inputs_temporal_horizons
        WHERE temporal_scenario_id = {}) as relevant_horizons
        USING (balancing_type_horizon, horizon)        
        JOIN
        (SELECT transmission_line
        FROM inputs_transmission_portfolios
        WHERE transmission_portfolio_scenario_id = {}) as relevant_tx
        USING (transmission_line)
        WHERE transmission_min_transmit_power_scenario_id = {}
        AND subproblem_id = {}
        AND stage_ID = {}
        """.format(
            subscenarios.TEMPORAL_SCENARIO_ID,
            subscenarios.TRANSMISSION_PORTFOLIO_SCENARIO_ID,
            subscenarios.TRANSMISSION_MIN_TRANSMIT_POWER_SCENARIO_ID,
            subproblem,
            stage
        )
    )

    return tx_min_transmit_power


def write_model_inputs(scenario_directory, scenario_id, subscenarios, subproblem, stage, conn):
    """
    Get inputs from database and write out the model input
    transmission_lines.tab file.
    :param scenario_directory: string, the scenario directory
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """

    tx_min_transmit_power = get_model_inputs_from_database(
        scenario_id, subscenarios, subproblem, stage, conn)

    with open(os.path.join(scenario_directory, str(subproblem), str(stage), "inputs",
                           "transmission_min_transmit_power.tab"),
              "w", newline="") as tx_min_transmit_power_tab_file:
        writer = csv.writer(tx_min_transmit_power_tab_file, delimiter="\t", lineterminator="\n")

        # TODO: remove all_caps for TRANSMISSION_LINES and make columns
        #  same as database
        # Write header
        writer.writerow(
            ["transmission_line", "balancing_type_horizon", "horizon", "min_transmit_power_mw"]
        )

        for row in tx_min_transmit_power:
            replace_nulls = ["." if i is None else i for i in row]
            writer.writerow(replace_nulls)
