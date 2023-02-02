# Copyright 2016-2023 Blue Marble Analytics LLC.
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
Capacity transfers between PRM zones.

Note that the capacity transfer variable is not at the transmission line level -- it
is defined at the "capacity transfer link" level, with the transmission line topology
used to limit total transfers on each link.

"""

import csv
import os.path
from pyomo.environ import (
    Set,
    Param,
    Var,
    Constraint,
    NonNegativeReals,
    Expression,
    value,
)

from db.common_functions import spin_on_database_lock
from gridpath.auxiliary.dynamic_components import prm_balance_provision_components


def add_model_components(m, d, scenario_directory, subproblem, stage):
    """
    The following Pyomo model components are defined in this module:

    +-------------------------------------------------------------------------+
    | Sets                                                                    |
    +=========================================================================+
    | | :code:`PRM_TX_LINES`                                                  |
    |                                                                         |
    | The set of PRM-relevant transmission lines.                             |
    +-------------------------------------------------------------------------+

    |

    +-------------------------------------------------------------------------+
    | Required Input Params                                                   |
    +=========================================================================+
    | | :code:`prm_zone_from`                                                 |
    | | *Defined over*: :code:`PRM_TX_LINES`                                  |
    | | *Within*: :code:`PRM_ZONES`                                           |
    |                                                                         |
    | The transmission line's starting PRM zone.                              |
    +-------------------------------------------------------------------------+
    | | :code:`prm_zone_to`                                                  |
    | | *Defined over*: :code:`TX_LINES`                                      |
    | | *Within*: :code:`PRM_ZONES`                                           |
    |                                                                         |
    | The transmission line's ending PRM zone.                                |
    +-------------------------------------------------------------------------+
    """
    # Exogenous param limits
    m.min_transfer_energyunit = Param(
        m.PRM_ZONES_CAPACITY_TRANSFER_ZONES,
        m.PERIODS,
        within=NonNegativeReals,
        default=0,
    )
    m.max_transfer_energyunit = Param(
        m.PRM_ZONES_CAPACITY_TRANSFER_ZONES,
        m.PERIODS,
        within=NonNegativeReals,
        default=float("inf"),
    )

    # Endogenous limits based on transmission links
    m.PRM_TX_LINES = Set(within=m.TX_LINES)

    m.prm_zone_from = Param(m.PRM_TX_LINES, within=m.PRM_ZONES)
    m.prm_zone_to = Param(m.PRM_TX_LINES, within=m.PRM_ZONES)

    # Transfers between pairs of zones in each period
    m.Transfer_Capacity_Contribution = Var(
        m.PRM_ZONES_CAPACITY_TRANSFER_ZONES,
        m.PERIODS,
        within=NonNegativeReals,
        initialize=0,
    )

    # Constraint based on the params

    # Constrain based on the available transmission
    # TODO: add limits on transfers; will need to move to own module that is only
    #  included if transmission reliability is included
    def transfer_limits_constraint_rule(mod, prm_z_from, prm_z_to, prd):
        # Sum of max capacity of lines with prm_zone_to == z plus
        # Negative sum of min capacity of lines with prm_zone_from == z
        return mod.Transfer_Capacity_Contribution[prm_z_from, prm_z_to, prd] <= sum(
            mod.Tx_Max_Capacity_MW[tx, op]
            for (tx, op) in mod.TX_OPR_PRDS
            if op == prd
            and mod.prm_zone_from[tx] == prm_z_from
            and mod.prm_zone_to[tx] == prm_z_to
        ) + -sum(
            mod.Tx_Min_Capacity_MW[tx, op]
            for (tx, op) in mod.TX_OPR_PRDS
            if op == prd
            and mod.prm_zone_from[tx] == prm_z_to
            and mod.prm_zone_to[tx] == prm_z_from
        )

    m.Capacity_Transfer_Limits_Constraint = Constraint(
        m.PRM_ZONES_CAPACITY_TRANSFER_ZONES,
        m.PERIODS,
        rule=transfer_limits_constraint_rule,
    )

    # Get the total transfers for each zone
    def total_transfers_from_init(mod, z, prd):
        return -sum(
            mod.Transfer_Capacity_Contribution[z, t_z, prd]
            for (zone, t_z) in mod.PRM_ZONES_CAPACITY_TRANSFER_ZONES
            if zone == z
        )

    m.Total_Transfers_from_PRM_Zone = Expression(
        m.PRM_ZONES, m.PERIODS, initialize=total_transfers_from_init
    )

    def total_transfers_to_init(mod, t_z, prd):
        return sum(
            mod.Transfer_Capacity_Contribution[z, t_z, prd]
            for (z, to_zone) in mod.PRM_ZONES_CAPACITY_TRANSFER_ZONES
            if to_zone == t_z
        )

    m.Total_Transfers_to_PRM_Zone = Expression(
        m.PRM_ZONES, m.PERIODS, initialize=total_transfers_to_init
    )

    # Add to balance constraint
    getattr(d, prm_balance_provision_components).append("Total_Transfers_from_PRM_Zone")
    getattr(d, prm_balance_provision_components).append("Total_Transfers_to_PRM_Zone")


# Input-Output
###############################################################################


def load_model_data(m, d, data_portal, scenario_directory, subproblem, stage):
    """

    :param m:
    :param d:
    :param data_portal:
    :param scenario_directory:
    :param stage:
    :param stage:
    :return:
    """
    limits_tab_file = os.path.join(
                scenario_directory,
                str(subproblem),
                str(stage),
                "inputs",
                "prm_capacity_transfer_limits.tab",
            )
    if os.path.exists(limits_tab_file):
        data_portal.load(
            filename=limits_tab_file,
            index=m.PRM_TX_LINES,
            param=(
                m.min_transfer_energyunit,
                m.max_transfer_energyunit,
            ),
        )

    data_portal.load(
        filename=os.path.join(
            scenario_directory,
            subproblem,
            stage,
            "inputs",
            "prm_transmission_lines.tab",
        ),
        index=m.PRM_TX_LINES,
        param=(
            m.prm_zone_from,
            m.prm_zone_to,
        ),
    )


# Database
###############################################################################


def get_inputs_from_database(scenario_id, subscenarios, subproblem, stage, conn):
    """
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """
    subproblem = 1 if subproblem == "" else subproblem
    stage = 1 if stage == "" else stage

    c1 = conn.cursor()
    limits = c1.execute(
        f"""
        SELECT prm_zone, prm_capacity_transfer_zone, period, 
        min_transfer_energyunit, max_transfer_energyunit
        FROM inputs_transmission_prm_capacity_transfer_limits
        WHERE prm_capacity_transfer_limits_scenario_id = 
        {subscenarios.PRM_CAPACITY_TRANSFER_LIMITS_SCENARIO_ID}
        ;
        """
    )

    c2 = conn.cursor()
    transmission_lines = c2.execute(
        """SELECT transmission_line, prm_zone_from, prm_zone_to
        FROM inputs_transmission_portfolios
        LEFT OUTER JOIN
            (SELECT transmission_line, prm_zone_from, prm_zone_to
            FROM inputs_transmission_prm_zones
            WHERE transmission_prm_zone_scenario_id = {prm_z}) as tx_prm_zones
        USING (transmission_line)
        WHERE transmission_portfolio_scenario_id = {portfolio};""".format(
            prm_z=subscenarios.TRANSMISSION_PRM_ZONE_SCENARIO_ID,
            portfolio=subscenarios.TRANSMISSION_PORTFOLIO_SCENARIO_ID,
        )
    )

    # TODO: allow Tx lines with no PRM zones from and to specified, that are only
    #  used for say, reliability capacity exchanges; they would need a different
    #  operational type (no power transfer); the decisions also won't be made at the
    #  transmission line level, but the capacity will limit the aggregate transfer
    #  between PRM zones, so there won't be flow variables

    return limits, transmission_lines


def write_model_inputs(
    scenario_directory, scenario_id, subscenarios, subproblem, stage, conn
):
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

    limits, transmission_lines = get_inputs_from_database(
        scenario_id, subscenarios, subproblem, stage, conn
    )

    limits = limits.fetchall()
    if limits:
        with open(
            os.path.join(
                scenario_directory,
                str(subproblem),
                str(stage),
                "inputs",
                "prm_capacity_transfer_limits.tab",
            ),
            "w",
            newline="",
        ) as limits_tab_file:
            writer = csv.writer(limits_tab_file, delimiter="\t", lineterminator="\n")

            # Write header
            writer.writerow(
                [
                    "prm_zone",
                    "prm_capacity_transfer_zone",
                    "period",
                    "min_transfer_energyunit",
                    "max_transfer_energyunit",
                ]
            )

            for row in limits:
                replace_nulls = ["." if i is None else i for i in row]
                writer.writerow(replace_nulls)

    with open(
        os.path.join(
            scenario_directory,
            str(subproblem),
            str(stage),
            "inputs",
            "prm_transmission_lines.tab",
        ),
        "w",
        newline="",
    ) as transmission_lines_tab_file:
        writer = csv.writer(
            transmission_lines_tab_file, delimiter="\t", lineterminator="\n"
        )

        # Write header
        writer.writerow(
            [
                "transmission_line",
                "prm_zone_from",
                "prm_zone_to",
            ]
        )

        for row in transmission_lines:
            replace_nulls = ["." if i is None else i for i in row]
            writer.writerow(replace_nulls)


def export_results(scenario_directory, subproblem, stage, m, d):
    """

    :param scenario_directory:
    :param subproblem:
    :param stage:
    :param m:
    :param d:
    :return:
    """
    with open(
        os.path.join(
            scenario_directory,
            str(subproblem),
            str(stage),
            "results",
            "capacity_contribution_transfers.csv",
        ),
        "w",
        newline="",
    ) as results_file:
        writer = csv.writer(results_file)
        writer.writerow(
            [
                "prm_zone",
                "period",
                "capacity_contribution_transferred_from_mw",
                "capacity_contribution_transferred_to_mw",
            ]
        )
        for (z, p) in m.PRM_ZONE_PERIODS_WITH_REQUIREMENT:
            writer.writerow(
                [
                    z,
                    p,
                    value(m.Total_Transfers_from_PRM_Zone[z, p]),
                    value(m.Total_Transfers_to_PRM_Zone[z, p]),
                ]
            )


def import_results_into_database(
    scenario_id, subproblem, stage, c, db, results_directory, quiet
):
    """

    :param scenario_id:
    :param c:
    :param db:
    :param results_directory:
    :param quiet:
    :return:
    """
    if not quiet:
        print("system prm capacity contribution transfers")
    # PRM contributions transferred from the PRM zone
    # Prior results should have already been cleared by
    # system.prm.aggregate_project_simple_prm_contribution,
    # then elcc_simple_mw imported
    # Update results_system_prm with NULL for surface contribution just in
    # case (instead of clearing prior results)
    nullify_sql = """
        UPDATE results_system_prm
        SET capacity_contribution_transferred_from_mw = NULL, 
        capacity_contribution_transferred_from_mw = NULL
        WHERE scenario_id = ?
        AND subproblem_id = ?
        AND stage_id = ?;
        """
    spin_on_database_lock(
        conn=db,
        cursor=c,
        sql=nullify_sql,
        data=(scenario_id, subproblem, stage),
        many=False,
    )

    results = []
    with open(
        os.path.join(results_directory, "capacity_contribution_transfers.csv"),
        "r",
    ) as surface_file:
        reader = csv.reader(surface_file)

        next(reader)  # skip header
        for row in reader:
            prm_zone = row[0]
            period = row[1]
            transfers_from = row[2]
            transfers_to = row[3]

            results.append(
                (
                    transfers_from,
                    transfers_to,
                    scenario_id,
                    prm_zone,
                    period,
                    subproblem,
                    stage,
                )
            )

    update_sql = """
        UPDATE results_system_prm
        SET capacity_contribution_transferred_from_mw = ?, 
        capacity_contribution_transferred_to_mw = ?
        WHERE scenario_id = ?
        AND prm_zone = ?
        AND period = ?
        AND subproblem_id = ?
        AND stage_id = ?
        """
    spin_on_database_lock(conn=db, cursor=c, sql=update_sql, data=results)