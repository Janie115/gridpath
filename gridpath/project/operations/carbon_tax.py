# Copyright 2021 (c) Crown Copyright, GC.
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

"""

import csv
import os.path
from pyomo.environ import Param, Set, NonNegativeReals, Expression, value

from gridpath.auxiliary.auxiliary import cursor_to_df, subset_init_by_param_value
from gridpath.auxiliary.db_interface import (
    update_prj_zone_column,
    determine_table_subset_by_start_and_column,
)
from gridpath.auxiliary.validations import write_validation_to_database, validate_idxs


def add_model_components(m, d, scenario_directory, subproblem, stage):
    """
    The following Pyomo model components are defined in this module:

    +-------------------------------------------------------------------------+
    | Sets                                                                    |
    +=========================================================================+
    | | :code:`CARBON_TAX_PRJS`                                               |
    | | *Within*: :code:`PROJECTS`                                            |
    |                                                                         |
    | Two set of carbonaceous projects we need to track for the carbon tax.   |
    +-------------------------------------------------------------------------+

    |

    +-------------------------------------------------------------------------+
    | Required Input Params                                                   |
    +=========================================================================+
    | | :code:`carbon_tax_zone`                                               |
    | | *Defined over*: :code:`CARBON_TAX_PRJS`                               |
    | | *Within*: :code:`CARBON_TAX_ZONES`                                    |
    |                                                                         |
    | This param describes the carbon tax zone for each carbon tax project.   |
    +-------------------------------------------------------------------------+
    | | :code:`carbon_tax_allowance`                                          |
    | | *Defined over*: :code:`CARBON_TAX_PRJS`, `CARBON_TAX_PRJ_OPR_PRDS`    |
    | | *Within*: :code:`NonNegativeReals`                                    |
    |                                                                         |
    | This param describes the carbon tax allowance for each carbon tax       |
    | project.                                                                |
    +-------------------------------------------------------------------------+

    |

    +-------------------------------------------------------------------------+
    | Derived Sets                                                            |
    +=========================================================================+
    | | :code:`CARBON_TAX_PRJS_BY_CARBON_TAX_ZONE`                            |
    | | *Defined over*: :code:`CARBON_TAX_ZONES`                              |
    | | *Within*: :code:`CARBON_TAX_PRJS`                                     |
    |                                                                         |
    | Indexed set that describes the list of carbonaceous projects for each   |
    | carbon tax zone.                                                        |
    +-------------------------------------------------------------------------+
    | | :code:`CARBON_TAX_PRJ_OPR_TMPS`                                       |
    | | *Within*: :code:`PRJ_OPR_TMPS`                                        |
    |                                                                         |
    | Two-dimensional set that defines all project-timepoint combinations     |
    | when a carbon tax project can be operational.                           |
    +-------------------------------------------------------------------------+
    | | :code:`CARBON_TAX_PRJ_OPR_PRDS`                                       |
    | | *Within*: :code:`PRJ_OPR_PRDS`                                        |
    |                                                                         |
    | Two-dimensional set that defines all project-period combinations        |
    | when a carbon tax project can be operational.                           |
    +-------------------------------------------------------------------------+

    """

    # Sets
    ###########################################################################

    m.CARBON_TAX_PRJS = Set(within=m.PROJECTS)

    m.CARBON_TAX_PRJ_OPR_TMPS = Set(
        within=m.PRJ_OPR_TMPS,
        initialize=lambda mod: [
            (p, tmp) for (p, tmp) in mod.PRJ_OPR_TMPS if p in mod.CARBON_TAX_PRJS
        ],
    )

    m.CARBON_TAX_PRJ_FUEL_GROUP_OPR_TMPS = Set(
        dimen=3,
        initialize=lambda mod: set(
            (g, fg, tmp)
            for (g, tmp) in mod.CARBON_TAX_PRJ_OPR_TMPS
            for _g, fg, f in mod.FUEL_PRJ_FUELS_FUEL_GROUP
            if g == _g
        ),
    )

    m.CARBON_TAX_PRJ_OPR_PRDS = Set(
        within=m.PRJ_OPR_PRDS,
        initialize=lambda mod: [
            (p, tmp) for (p, tmp) in mod.PRJ_OPR_PRDS if p in mod.CARBON_TAX_PRJS
        ],
    )

    # Input Params
    ###########################################################################

    m.carbon_tax_zone = Param(m.CARBON_TAX_PRJS, within=m.CARBON_TAX_ZONES)

    m.carbon_tax_allowance = Param(
        m.CARBON_TAX_PRJS, m.FUEL_GROUPS, m.PERIODS,  within=NonNegativeReals, default=0
    )

    # Derived Sets
    ###########################################################################

    m.CARBON_TAX_PRJS_BY_CARBON_TAX_ZONE = Set(
        m.CARBON_TAX_ZONES,
        within=m.CARBON_TAX_PRJS,
        initialize=lambda mod, co2_z: subset_init_by_param_value(
            mod, "CARBON_TAX_PRJS", "carbon_tax_zone", co2_z
        ),
    )

    # Expressions
    ###########################################################################

    def carbon_tax_allowance_rule(mod, prj, fg, tmp):
        """
        Allowance from each project. Multiply by the timepoint duration,
        timepoint weight and power to get the total emissions allowance.
        """

        return (
            mod.Power_Provision_MW[prj, tmp]
            * mod.carbon_tax_allowance[prj, fg, mod.period[tmp]]
            * mod.Opr_Fuel_Burn_by_Fuel_Group_MMBtu[prj, fg, tmp]
            / mod.Opr_Fuel_Burn_by_Project_MMBtu[prj, tmp]
        )

    m.Project_Carbon_Tax_Allowance = Expression(
        m.CARBON_TAX_PRJ_FUEL_GROUP_OPR_TMPS, rule=carbon_tax_allowance_rule
    )


# Input-Output
###############################################################################


def load_model_data(m, d, data_portal, scenario_directory, subproblem, stage):
    """

    :param m:
    :param d:
    :param data_portal:
    :param scenario_directory:
    :param subproblem:
    :param stage:
    :return:
    """
    data_portal.load(
        filename=os.path.join(
            scenario_directory, str(subproblem), str(stage), "inputs", "projects.tab"
        ),
        select=("project", "carbon_tax_zone"),
        param=(m.carbon_tax_zone,),
    )

    data_portal.data()["CARBON_TAX_PRJS"] = {
        None: list(data_portal.data()["carbon_tax_zone"].keys())
    }

    data_portal.load(
        filename=os.path.join(
            scenario_directory,
            str(subproblem),
            str(stage),
            "inputs",
            "project_carbon_tax_allowance.tab",
        ),
        select=("project", "fuel_group", "period", "carbon_tax_allowance_tco2_per_mwh"),
        param=m.carbon_tax_allowance,
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
    project_zones = c1.execute(
        """SELECT project, carbon_tax_zone
        FROM
        -- Get projects from portfolio only
        (SELECT project
            FROM inputs_project_portfolios
            WHERE project_portfolio_scenario_id = {}
        ) as prj_tbl
        LEFT OUTER JOIN 
        -- Get carbon tax zones for those projects
        (SELECT project, carbon_tax_zone
            FROM inputs_project_carbon_tax_zones
            WHERE project_carbon_tax_zone_scenario_id = {}
        ) as prj_ct_zone_tbl
        USING (project)
        -- Filter out projects whose carbon tax zone is not one included in 
        -- our carbon_tax_zone_scenario_id
        WHERE carbon_tax_zone in (
                SELECT carbon_tax_zone
                    FROM inputs_geography_carbon_tax_zones
                    WHERE carbon_tax_zone_scenario_id = {}
        );
        """.format(
            subscenarios.PROJECT_PORTFOLIO_SCENARIO_ID,
            subscenarios.PROJECT_CARBON_TAX_ZONE_SCENARIO_ID,
            subscenarios.CARBON_TAX_ZONE_SCENARIO_ID,
        )
    )

    c2 = conn.cursor()
    project_carbon_tax_allowance = c2.execute(
        """SELECT project, period, fuel_group,
        carbon_tax_allowance_tco2_per_mwh
        FROM
        -- Get projects from portfolio only
        (SELECT project
            FROM inputs_project_portfolios
            WHERE project_portfolio_scenario_id = {}
        ) as prj_tbl
        CROSS JOIN
            (SELECT period
            FROM inputs_temporal_periods
            WHERE temporal_scenario_id = {}) as relevant_periods 
        LEFT OUTER JOIN
        -- Get carbon tax allowance for those projects
            (SELECT project, period, fuel_group,
            carbon_tax_allowance_tco2_per_mwh
            FROM inputs_project_carbon_tax_allowance
            WHERE project_carbon_tax_allowance_scenario_id = {}) as prj_ct_allowance_tbl
        USING (project, period)
        WHERE project in (
                SELECT project
                    FROM inputs_project_carbon_tax_zones
                    WHERE project_carbon_tax_zone_scenario_id = {}
        );
        """.format(
            subscenarios.PROJECT_PORTFOLIO_SCENARIO_ID,
            subscenarios.TEMPORAL_SCENARIO_ID,
            subscenarios.PROJECT_CARBON_TAX_ALLOWANCE_SCENARIO_ID,
            subscenarios.CARBON_TAX_ZONE_SCENARIO_ID,
        )
    )

    return project_zones, project_carbon_tax_allowance


def write_model_inputs(
    scenario_directory, scenario_id, subscenarios, subproblem, stage, conn
):
    """
    Get inputs from database and write out the model input
    projects.tab (to be precise, amend it) and project_carbon_tax_allowance.tab files.
    :param scenario_directory: string, the scenario directory
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """
    project_zones, project_carbon_tax_allowance = get_inputs_from_database(
        scenario_id, subscenarios, subproblem, stage, conn
    )

    # projects.tab
    # Make a dict for easy access
    prj_zone_dict = dict()
    for (prj, zone) in project_zones:
        prj_zone_dict[str(prj)] = "." if zone is None else str(zone)

    with open(
        os.path.join(
            scenario_directory, str(subproblem), str(stage), "inputs", "projects.tab"
        ),
        "r",
    ) as projects_file_in:
        reader = csv.reader(projects_file_in, delimiter="\t", lineterminator="\n")

        new_rows = list()

        # Append column header
        header = next(reader)
        header.append("carbon_tax_zone")
        new_rows.append(header)

        # Append correct values
        for row in reader:
            # If project specified, check if BA specified or not
            if row[0] in list(prj_zone_dict.keys()):
                row.append(prj_zone_dict[row[0]])
                new_rows.append(row)
            # If project not specified, specify no BA
            else:
                row.append(".")
                new_rows.append(row)

    with open(
        os.path.join(
            scenario_directory, str(subproblem), str(stage), "inputs", "projects.tab"
        ),
        "w",
        newline="",
    ) as projects_file_out:
        writer = csv.writer(projects_file_out, delimiter="\t", lineterminator="\n")
        writer.writerows(new_rows)

    # project_carbon_tax_allowance.tab
    ct_allowance_df = cursor_to_df(project_carbon_tax_allowance)
    if not ct_allowance_df.empty:
        ct_allowance_df = ct_allowance_df.fillna(".")
        fpath = os.path.join(
            scenario_directory,
            str(subproblem),
            str(stage),
            "inputs",
            "project_carbon_tax_allowance.tab",
        )
        ct_allowance_df.to_csv(fpath, index=False, sep="\t")


def process_results(db, c, scenario_id, subscenarios, quiet):
    """

    :param db:
    :param c:
    :param subscenarios:
    :param quiet:
    :return:
    """
    if not quiet:
        print("update carbon tax zones")

    tables_to_update = determine_table_subset_by_start_and_column(
        conn=db, tbl_start="results_project_", cols=["carbon_tax_zone"]
    )

    for tbl in tables_to_update:
        update_prj_zone_column(
            conn=db,
            scenario_id=scenario_id,
            subscenarios=subscenarios,
            subscenario="project_carbon_tax_zone_scenario_id",
            subsc_tbl="inputs_project_carbon_tax_zones",
            prj_tbl=tbl,
            col="carbon_tax_zone",
        )


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
            "carbon_tax_allowance_by_project.csv",
        ),
        "w",
        newline="",
    ) as carbon_tax_allowance_results_file:
        writer = csv.writer(carbon_tax_allowance_results_file)
        writer.writerow(
            [
                "project",
                "period",
                "horizon",
                "timepoint",
                "timepoint_weight",
                "number_of_hours_in_timepoint",
                "carbon_tax_zone",
                "technology",
                "carbon_tax_allowance_tons",
            ]
        )
        for (p, tmp) in m.CARBON_TAX_PRJ_OPR_TMPS:
            writer.writerow(
                [
                    p,
                    m.period[tmp],
                    m.horizon[tmp, m.balancing_type_project[p]],
                    tmp,
                    m.tmp_weight[tmp],
                    m.hrs_in_tmp[tmp],
                    m.carbon_tax_zone[p],
                    m.technology[p],
                    value(m.Project_Carbon_Tax_Allowance[p, tmp]),
                ]
            )


# Validation
###############################################################################


def validate_inputs(scenario_id, subscenarios, subproblem, stage, conn):
    """
    Get inputs from database and validate the inputs
    :param subscenarios: SubScenarios object with all subscenario info
    :param subproblem:
    :param stage:
    :param conn: database connection
    :return:
    """

    project_zones, project_carbon_tax_allowance = get_inputs_from_database(
        scenario_id, subscenarios, subproblem, stage, conn
    )

    # Convert input data into pandas DataFrame
    df = cursor_to_df(project_zones)
    zones_w_project = df["carbon_tax_zone"].unique()

    # Get the required carbon tax zones
    # TODO: make this into a function similar to get_projects()?
    #  could eventually centralize all these db query functions in one place
    c = conn.cursor()
    zones = c.execute(
        """SELECT carbon_tax_zone FROM inputs_geography_carbon_tax_zones
        WHERE carbon_tax_zone_scenario_id = {}
        """.format(
            subscenarios.CARBON_TAX_ZONE_SCENARIO_ID
        )
    )
    zones = [z[0] for z in zones]  # convert to list

    # Check that each carbon tax zone has at least one project assigned to it
    write_validation_to_database(
        conn=conn,
        scenario_id=scenario_id,
        subproblem_id=subproblem,
        stage_id=stage,
        gridpath_module=__name__,
        db_table="inputs_project_carbon_tax_zones",
        severity="High",
        errors=validate_idxs(
            actual_idxs=zones_w_project,
            req_idxs=zones,
            idx_label="carbon_tax_zone",
            msg="Each carbon tax zone needs at least 1 " "project assigned to it.",
        ),
    )

    # TODO: need validation that projects with carbon tax zones also have fuels
