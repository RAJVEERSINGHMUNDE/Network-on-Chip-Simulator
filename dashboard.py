# dashboard.py

import dash
from dash import dcc, html, Input, Output, State
import yaml
import numpy as np
import io
import base64
import random
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from noc.simulator import Simulator

def create_plot(x_data, y_data, config, title_extra, xlabel):
    plt.figure(figsize=(10, 6))
    plt.plot(x_data, y_data, marker='o', linestyle='-')
    arch = config.get('architecture', 'monolithic').replace('_', ' ').title()
    plt.title(f'Network Performance: {arch} under {title_extra}')
    plt.xlabel(xlabel)
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    data = base64.b64encode(buf.getbuffer()).decode("utf8")
    return f"data:image/png;base64,{data}"

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("AI GPU Grid - NoC Simulator Dashboard"),
    
    html.Div([
        html.H3("Simulation Configuration"),
        
        html.Label("Architecture:"),
        dcc.RadioItems(
            id='architecture-radio',
            options=[
                {'label': 'Monolithic Electrical', 'value': 'monolithic'},
                {'label': 'Hybrid Electrical', 'value': 'hybrid_electrical'},
            ],
            value='monolithic',
            labelStyle={'display': 'inline-block', 'margin-right': '20px'}
        ),
        html.Hr(),

        html.Div(id='primary-topo-div', children=[
            html.Label("Primary Topology:"),
            dcc.Dropdown(
                id='primary-topology-dropdown',
                options=[
                    {'label': '2D Mesh', 'value': 'mesh'},
                    {'label': '2D Torus', 'value': 'torus'},
                ], value='mesh'
            )
        ]),

        html.Div(id='secondary-topo-div', style={'display': 'none'}, children=[
            html.Label("Secondary Topology (for collectives):"),
            dcc.Dropdown(
                id='secondary-topology-dropdown',
                options=[{'label': 'Fat-Tree', 'value': 'fat_tree'}],
                value='fat_tree'
            )
        ]),

        html.Label("Traffic Pattern:"),
        dcc.Dropdown(id='traffic-pattern-dropdown', options=[
            {'label': 'Uniform Random', 'value': 'uniform_random'},
            {'label': 'Transpose', 'value': 'transpose'},
            {'label': 'Hotspot', 'value': 'hotspot'},
            {'label': 'All-Reduce Workload', 'value': 'all_reduce'},
        ], value='uniform_random'),

        html.Div(id='all-reduce-options', style={'display': 'none'}, children=[
            html.H4("All-Reduce Workload Settings"),
            html.Label("Packet Size (Flits per chunk):"),
            dcc.Input(id='ar-chunk-size-input', type='number', value=4, min=1),
            html.P("Experiment sweeps over the total number of data chunks."),
        ]),

        html.Label("Routing Algorithm:"),
        dcc.Dropdown(id='routing-algo-dropdown', options=[
            {'label': 'Deterministic (XY or Up/Down)', 'value': 'deterministic'},
            {'label': 'Adaptive', 'value': 'adaptive'}
        ], value='adaptive'),
        
        html.Label("Number of Virtual Channels:"),
        dcc.Input(id='num-vcs-input', type='number', value=4, min=1, step=1),
        
        # This input will now be controlled by a callback
        html.Div(id='sim-cycles-div', children=[
             html.Label("Simulation Cycles:"),
             dcc.Input(id='sim-cycles-input', type='number', value=3000, min=100, step=100),
        ]),
        html.Hr(),

        html.Button('Run Experiment Sweep', id='run-button', n_clicks=0),
        
    ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
    
    html.Div([
        html.H3("Results"),
        dcc.Loading(id="loading-spinner", type="circle", children=[
            html.Div(id='results-summary'),
            html.Img(id='results-graph', style={'width': '100%'})
        ])
    ], style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
])

@app.callback(
    Output('secondary-topo-div', 'style'),
    Input('architecture-radio', 'value')
)
def toggle_secondary_topo_options(architecture):
    if architecture == 'hybrid_electrical':
        return {'display': 'block'}
    return {'display': 'none'}

@app.callback(
    Output('all-reduce-options', 'style'),
    Input('traffic-pattern-dropdown', 'value')
)
def toggle_workload_options(traffic_pattern):
    if traffic_pattern == 'all_reduce':
        return {'display': 'block'}
    return {'display': 'none'}

# --- NEW CALLBACK TO HIDE SIMULATION CYCLES INPUT ---
@app.callback(
    Output('sim-cycles-div', 'style'),
    Input('traffic-pattern-dropdown', 'value')
)
def toggle_sim_cycles_visibility(traffic_pattern):
    """Hides the simulation cycles input if a workload is selected."""
    if traffic_pattern == 'all_reduce':
        # Hide the input because the simulation will run until the workload is complete
        return {'display': 'none'}
    # Show the input for all other traffic patterns
    return {'display': 'block'}


@app.callback(
    [Output('results-summary', 'children'), Output('results-graph', 'src')],
    Input('run-button', 'n_clicks'),
    [State('architecture-radio', 'value'),
     State('primary-topology-dropdown', 'value'),
     State('secondary-topology-dropdown', 'value'),
     State('traffic-pattern-dropdown', 'value'),
     State('routing-algo-dropdown', 'value'),
     State('num-vcs-input', 'value'),
     State('sim-cycles-input', 'value'),
     State('ar-chunk-size-input', 'value')]
)
def run_simulation_sweep(n_clicks, arch, p_topo, s_topo, pattern, routing, vcs, cycles, ar_chunk):
    if n_clicks == 0:
        return "Click 'Run Experiment Sweep' to start.", ""

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['architecture'] = arch
    config['topology'] = p_topo
    if arch == 'hybrid_electrical':
        if 'hybrid_electrical_config' not in config: config['hybrid_electrical_config'] = {}
        config['hybrid_electrical_config']['secondary_topology'] = s_topo
    
    config.update({
        'traffic_pattern': pattern, 'routing_algo': routing,
        'num_virtual_channels': vcs, 'simulation_cycles': cycles
    })
    
    seed = config.get('random_seed', None)
    if seed:
        random.seed(seed)
        print(f"--- Running experiment with Random Seed: {seed} ---")

    latencies = []
    
    if pattern == 'all_reduce':
        sweep_values = np.arange(4, 33, 4)
        xlabel = "Number of Data Chunks per Node for All-Reduce"
        title_extra = '"All-Reduce" Workload'
        for num_chunks in sweep_values:
            sim_config = config.copy()
            if 'workload' not in sim_config: sim_config['workload'] = {}
            sim_config['workload']['all_reduce_data_size'] = int(num_chunks)
            sim_config['workload']['all_reduce_chunk_size_flits'] = ar_chunk
            latencies.append(run_single_sim(sim_config))
    else:
        sweep_values = np.arange(0.01, 0.16, 0.02)
        xlabel = "Injection Rate (packets/node/cycle)"
        title_extra = f'"{pattern}" Load on {p_topo.capitalize()}'
        for rate in sweep_values:
            sim_config = config.copy()
            sim_config['injection_rate'] = rate
            latencies.append(run_single_sim(sim_config))

    summary_text = f"Experiment Complete. Architecture: {arch.replace('_', ' ').title()}."
    graph_src = create_plot(sweep_values, latencies, config, title_extra, xlabel)
    
    return summary_text, graph_src

def run_single_sim(sim_config: dict) -> float:
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            simulator = Simulator(config=sim_config)
            # The simulator's run method now handles whether to use num_cycles or not
            simulator.run(num_cycles=sim_config['simulation_cycles'])
            avg_latency = simulator.tracker.calculate_average_latency()
            if w:
                for warning_message in w:
                    print(f"Warning: {warning_message.message}")
            return avg_latency
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
        return 0.0

if __name__ == '__main__':
    app.run(debug=True)