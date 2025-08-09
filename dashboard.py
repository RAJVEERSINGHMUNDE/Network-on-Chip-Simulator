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

# We now need the Simulator and potentially the workload classes
from noc.simulator import Simulator

def create_plot(x_data, y_data, config, title_extra, xlabel):
    """Generates a base64-encoded plot with dynamic labels."""
    plt.figure(figsize=(10, 6))
    plt.plot(x_data, y_data, marker='o', linestyle='-')
    
    topology = config.get('topology', 'N/A')
    
    plt.title(f'Network Performance: {topology.capitalize()} under {title_extra}')
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
    
    # --- Configuration Panel ---
    html.Div([
        html.H3("Simulation Configuration"),
        
        html.Label("Topology:"),
        dcc.Dropdown(
            id='topology-dropdown',
            options=[
                {'label': '2D Mesh', 'value': 'mesh'},
                {'label': '2D Torus', 'value': 'torus'},
                {'label': 'Fat-Tree', 'value': 'fat_tree'},
                {'label': 'Flattened Butterfly (Not Implemented)', 'value': 'flattened_butterfly', 'disabled': True}
            ],
            value='mesh'
        ),
        
        html.Label("Traffic Pattern:"),
        dcc.Dropdown(
            id='traffic-pattern-dropdown',
            options=[
                {'label': 'Uniform Random', 'value': 'uniform_random'},
                {'label': 'Transpose', 'value': 'transpose'},
                {'label': 'Hotspot', 'value': 'hotspot'},
                {'label': 'All-Reduce Workload', 'value': 'all_reduce'},
            ],
            value='uniform_random'
        ),

        html.Label("Routing Algorithm (Mesh/Torus/Fat-Tree):"),
        dcc.Dropdown(
            id='routing-algo-dropdown',
            options=[
                {'label': 'Deterministic (XY or Up/Down)', 'value': 'deterministic'},
                {'label': 'Adaptive', 'value': 'adaptive'}
            ],
            value='adaptive'
        ),
        
        html.Label("Number of Virtual Channels:"),
        dcc.Input(id='num-vcs-input', type='number', value=4, min=1, step=1),
        
        html.Label("Simulation Cycles:"),
        dcc.Input(id='sim-cycles-input', type='number', value=2000, min=100, step=100),
        html.Hr(),

        # --- Dynamic Options based on Traffic Pattern ---
        # Options for All-Reduce Workload
        html.Div(id='all-reduce-options', style={'display': 'none'}, children=[
            html.H4("All-Reduce Workload Settings"),
            html.Label("Packet Size (Number of Flits per chunk):"),
            dcc.Input(id='ar-chunk-size-input', type='number', value=4, min=1),
            html.P("The experiment will sweep over the total number of data chunks."),
        ]),

        html.Button('Run Experiment Sweep', id='run-button', n_clicks=0),
        
    ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
    
    # --- Results Panel ---
    html.Div([
        html.H3("Results"),
        dcc.Loading(
            id="loading-spinner", type="circle",
            children=[
                html.Div(id='results-summary'),
                html.Img(id='results-graph', style={'width': '100%'})
            ]
        )
    ], style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
])

@app.callback(
    Output('all-reduce-options', 'style'),
    Input('traffic-pattern-dropdown', 'value')
)
def toggle_workload_options(traffic_pattern):
    """Shows or hides the All-Reduce options based on the selected traffic pattern."""
    if traffic_pattern == 'all_reduce':
        return {'display': 'block'}
    else:
        return {'display': 'none'}

@app.callback(
    [Output('results-summary', 'children'), Output('results-graph', 'src')],
    Input('run-button', 'n_clicks'),
    [State('topology-dropdown', 'value'), State('traffic-pattern-dropdown', 'value'),
     State('routing-algo-dropdown', 'value'), State('num-vcs-input', 'value'),
     State('sim-cycles-input', 'value'),
     # Add state for new All-Reduce inputs
     State('ar-chunk-size-input', 'value')]
)
def run_simulation_sweep(n_clicks, topology, traffic_pattern, routing_algo, num_vcs, sim_cycles, ar_chunk_size):
    if n_clicks == 0:
        return "Click 'Run Experiment Sweep' to start.", ""

    # Load base config and update with UI values
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    config.update({
        'topology': topology, 'traffic_pattern': traffic_pattern,
        'routing_algo': routing_algo, 'num_virtual_channels': num_vcs,
        'simulation_cycles': sim_cycles
    })
    
    # Set seed for reproducibility
    seed = config.get('random_seed', None)
    if seed:
        random.seed(seed)
        print(f"--- Running experiment with Random Seed: {seed} ---")

    latencies = []
    
    # --- Logic to select the correct sweep experiment ---
    if traffic_pattern == 'all_reduce':
        # For All-Reduce, sweep over the number of chunks to see how latency scales with data size
        sweep_values = np.arange(4, 33, 4) # Sweep from 4 to 32 chunks
        xlabel = "Number of Data Chunks per Node for All-Reduce"
        title_extra = '"All-Reduce" Workload'

        for num_chunks in sweep_values:
            sim_config = config.copy()
            sim_config['workload'] = {
                'all_reduce_data_size': int(num_chunks),
                'all_reduce_chunk_size_flits': ar_chunk_size
            }
            avg_latency = run_single_sim(sim_config)
            latencies.append(avg_latency)

    else: # For synthetic patterns, sweep over injection rate
        sweep_values = np.arange(0.01, 0.16, 0.02)
        xlabel = "Injection Rate (packets/node/cycle)"
        title_extra = f'"{traffic_pattern}" Load'

        for rate in sweep_values:
            sim_config = config.copy()
            sim_config['injection_rate'] = rate
            avg_latency = run_single_sim(sim_config)
            latencies.append(avg_latency)

    summary_text = f"Experiment Complete. Topology: {topology.capitalize()}, Pattern: {traffic_pattern}, Routing: {routing_algo}, VCs: {num_vcs}."
    graph_src = create_plot(sweep_values, latencies, config, title_extra, xlabel)
    
    return summary_text, graph_src

def run_single_sim(sim_config: dict) -> float:
    """Helper function to instantiate and run a single simulator instance."""
    try:
        # Use a warnings context to catch and print potential issues
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            simulator = Simulator(config=sim_config)
            simulator.run(num_cycles=sim_config['simulation_cycles'])
            avg_latency = simulator.tracker.calculate_average_latency()
            
            if w:
                for warning_message in w:
                    print(f"Warning: {warning_message.message}")
            return avg_latency
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
        return 0.0 # Return 0 latency on error

if __name__ == '__main__':
    app.run(debug=True)