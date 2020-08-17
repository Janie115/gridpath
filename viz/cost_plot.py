#!/usr/bin/env python
# Copyright 2017 Blue Marble Analytics LLC. All rights reserved.

"""
Make plot of costs by period for a certain scenario/zone/stage
"""

from argparse import ArgumentParser
from bokeh.embed import json_item

import pandas as pd
import sys

# GridPath modules
from db.common_functions import connect_to_database
from gridpath.auxiliary.auxiliary import get_scenario_id_and_name
from viz.common_functions import create_stacked_bar_plot, show_plot, \
    get_parent_parser, get_unit, process_stacked_plot_data


def create_parser():
    """

    :return:
    """
    parser = ArgumentParser(add_help=True, parents=[get_parent_parser()])
    parser.add_argument("--scenario_id", help="The scenario ID. Required if "
                                              "no --scenario is specified.")
    parser.add_argument("--scenario", help="The scenario name. Required if "
                                           "no --scenario_id is specified.")
    parser.add_argument("--load_zone", required=True, type=str,
                        help="The name of the load zone. Required.")
    parser.add_argument("--stage", default=1, type=int,
                        help="The stage ID. Defaults to 1.")

    return parser


def parse_arguments(arguments):
    """

    :return:
    """
    parser = create_parser()
    parsed_arguments = parser.parse_args(args=arguments)

    return parsed_arguments


def get_plotting_data(conn, scenario_id, load_zone, stage, **kwargs):
    """
    Get costs results by period and component for a given
    scenario/load_zone/stage.

    **kwargs needed, so that an error isn't thrown when calling this
    function with extra arguments from the UI.

    :param conn:
    :param scenario_id:
    :param load_zone:
    :param stage:
    :return:
    """

    # TODO: move this into a view that keeps all scenarios and periods
    #   and then select from it? (but full table takes 19s to load, whereas
    #   a slice is much faster!) Perhaps we can move each cost by scen/period
    #   into a view, but that won't make things faster, just shorter queries?
    # TODO: will this work when there are no capacity cost (left join would
    #   start with empty capacity table
    # TODO: what hurdle rates should we include? load_zone_to, load_zone_from
    #   or both?
    # TODO: add new transmisison costs?

    # Note: fuel cost and variable O&M cost are actually cost *rates* in $/hr
    #  and should be multiplied by the timepoint duration to get the actual
    #  cost.

    # System costs by scenario and period -- by source and total
    # Spinup/lookahead timepoints are ignored by adding the resp. column tag
    # through inner joins and adding a conditional to ignore those timepoints
    sql = """SELECT period,
        capacity_cost/1000000 as Capacity,
        fuel_cost/1000000 as Fuel,
        variable_om_cost/1000000 as Variable_OM,
        startup_cost/1000000 as Startups,
        shutdown_cost/1000000 as Shutdowns,
        hurdle_cost/1000000 as Hurdle_Rates

        FROM
        
        (SELECT scenario_id, period, sum(capacity_cost) AS capacity_cost
        FROM  results_project_costs_capacity
        WHERE scenario_id = ?
        AND stage_id = ?
        AND load_zone = ?
        GROUP BY scenario_id, period) AS cap_costs

        LEFT JOIN

        (SELECT scenario_id, period, 
        sum(fuel_cost * timepoint_weight * number_of_hours_in_timepoint) 
        AS fuel_cost,
        sum(variable_om_cost * timepoint_weight * number_of_hours_in_timepoint) 
        AS variable_om_cost,
        sum(startup_cost * timepoint_weight) AS startup_cost,
        sum(shutdown_cost * timepoint_weight) AS shutdown_cost
        FROM results_project_costs_operations
        
        -- add temporal scenario id so we can join timepoints table
        INNER JOIN
        
        (SELECT temporal_scenario_id, scenario_id FROM scenarios)
        USING (scenario_id)
        
        -- filter out spinup_or_lookahead timepoints
        INNER JOIN
        
        (SELECT temporal_scenario_id, stage_id, subproblem_id, timepoint, 
        spinup_or_lookahead
        FROM inputs_temporal)
        USING (temporal_scenario_id, stage_id, subproblem_id, timepoint)
        
        WHERE scenario_id = ?
        AND stage_id = ?
        AND load_zone = ?
        AND spinup_or_lookahead is NULL
        
        GROUP BY scenario_id, period) AS operational_costs
        USING (scenario_id, period)

        LEFT JOIN

        (SELECT scenario_id, period, 
        sum((hurdle_cost_positive_direction + hurdle_cost_negative_direction) * 
        timepoint_weight * number_of_hours_in_timepoint) AS hurdle_cost
        FROM
        results_transmission_hurdle_costs
        
        -- add temporal scenario id so we can join timepoints table
        INNER JOIN
        
        (SELECT temporal_scenario_id, scenario_id FROM scenarios)
        USING (scenario_id)
        
        -- filter out spinup_or_lookahead timepoints
        INNER JOIN
        
        (SELECT temporal_scenario_id, stage_id, subproblem_id, timepoint, 
        spinup_or_lookahead
        FROM inputs_temporal)
        USING (temporal_scenario_id, stage_id, subproblem_id, timepoint)
        
        WHERE scenario_id = ?
        AND stage_id = ?
        AND load_zone_to = ?
        AND spinup_or_lookahead is NULL
        
        GROUP BY scenario_id, period) AS hurdle_costs
        USING (scenario_id, period)
        ;"""

    df = pd.read_sql(
        sql,
        con=conn,
        params=(scenario_id, stage, load_zone,
                scenario_id, stage, load_zone,
                scenario_id, stage, load_zone)
    )

    # Melt dataframe from wide format to long
    # (create_stacked_bar_plot requires un-pivoted dataframe)
    df = pd.melt(
        df,
        id_vars=['period'],
        value_vars=['Capacity', 'Fuel', 'Variable_OM',
                    'Startups', 'Shutdowns', 'Hurdle_Rates'],
        var_name='Cost Component',
        value_name='Cost'
    )

    return df


def main(args=None):
    """
    Parse the arguments, get the data in a df, and create the plot

    :return: if requested, return the plot as JSON object
    """
    if args is None:
        args = sys.argv[1:]
    parsed_args = parse_arguments(arguments=args)

    conn = connect_to_database(db_path=parsed_args.database)
    c = conn.cursor()

    scenario_id, scenario = get_scenario_id_and_name(
        scenario_id_arg=parsed_args.scenario_id,
        scenario_name_arg=parsed_args.scenario,
        c=c,
        script="cost_plot"
    )

    cost_unit = "million " + get_unit(c, "cost")

    plot_title = "{}Total Cost by Period - {} - Stage {}".format(
        "{} - ".format(scenario)
        if parsed_args.scenario_name_in_title else "",
        parsed_args.load_zone, parsed_args.stage)
    plot_name = "CostPlot-{}-{}".format(
        parsed_args.load_zone, parsed_args.stage)

    df = get_plotting_data(
        conn=conn,
        scenario_id=scenario_id,
        load_zone=parsed_args.load_zone,
        stage=parsed_args.stage
    )

    source, x_col_reordered = process_stacked_plot_data(
        df=df,
        y_col="Cost",
        x_col=["period"],
        category_col="Cost Component"
    )

    # Multi-level index in CDS will be joined into one column with "_" separator
    x_col_cds = "_".join(x_col_reordered)
    x_col_label = ", ".join([x.capitalize() for x in x_col_reordered])
    plot = create_stacked_bar_plot(
        source=source,
        x_col=x_col_cds,
        x_label=x_col_label,
        y_label="Cost ({})".format(cost_unit),
        category_label="Cost Component",
        title=plot_title,
        ylimit=parsed_args.ylimit
    )

    # Show plot in HTML browser file if requested
    if parsed_args.show:
        show_plot(plot=plot,
                  plot_name=plot_name,
                  plot_write_directory=parsed_args.plot_write_directory,
                  scenario=scenario)

    # Return plot in json format if requested
    if parsed_args.return_json:
        return json_item(plot, plot_name)


if __name__ == "__main__":
    main()
