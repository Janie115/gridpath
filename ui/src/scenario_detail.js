'use strict';

const { ipcRenderer, remote }= require('electron');
const Database = require('better-sqlite3');
const path = require('path');

// Listen for a scenario name
ipcRenderer.send('Scenario-Detail-Window-Requests-Scenario-Name');
ipcRenderer.on(
    'Main-Relays-Scenario-Name',
    (event, scenarioName) => {
        console.log('Scenario Detail Window received message');
        console.log(scenarioName);

        // Create the HTML for the scenario name
        document.getElementById('scenarioName').innerHTML =
            scenarioName;

        // Create the scenario detail HTML
        createScenarioDetailTable(scenarioName);
        document.getElementById('scenarioDetailTable').innerHTML =
            createScenarioDetailTable(scenarioName);

        // TODO: create button to run scenario here, not in html file?

        // If runScenarioButton is clicked, send scenario name to main process
        const runScenarioButton =
            document.getElementById('runScenarioButton');

        runScenarioButton.addEventListener(
            'click',
            (event) => {
                console.log(`User requests to run scenario ${scenarioName}`);
                ipcRenderer.send(
                    'User-Requests-to-Run-Scenario', scenarioName
                );
            }
        );
    }
);

// Create the html for the scenario detail table
const createScenarioDetailTable = (scenario) => {
    const scenarioParamsDict = getScenarioDetails(scenario);
    console.log(scenarioParamsDict);
    let scenarioDetailTable = '<table style="width:100%">';
    Object.keys(scenarioParamsDict).forEach(
        (key) => {
            scenarioDetailTable += '<tr>';
            scenarioDetailTable += `<td>${key}</td>`;
            scenarioDetailTable += `<td>${scenarioParamsDict[key]}</td>`;
            scenarioDetailTable += '</tr>';
        }
    );
    scenarioDetailTable += '</table>';
    console.log(scenarioDetailTable);
    return scenarioDetailTable
};


const getScenarioDetails = (scenario) => {
    const io_file = path.join(__dirname, '../db/io.db');
    const io = new Database (io_file, {fileMustExist: true});
    const scenarioDetails = {};
    scenarioDetails.scenario_name = scenario;


    const getIDs =
        io.prepare(
            `SELECT project_portfolio_scenario_id,
            project_operational_chars_scenario_id, load_scenario_id, 
            fuel_price_scenario_id
            FROM scenarios WHERE scenario_name = ?`
        ).get(scenario);

    scenarioDetails.project_portfolio_scenario_id =
        getIDs.project_portfolio_scenario_id;
    scenarioDetails.project_operational_chars_scenario_id =
        getIDs.project_operational_chars_scenario_id;
    scenarioDetails.load_scenario_id = getIDs.load_scenario_id;
    scenarioDetails.fuel_price_scenario_id = getIDs.fuel_price_scenario_id;

    console.log(scenarioDetails);
    io.close();
    return scenarioDetails
};



