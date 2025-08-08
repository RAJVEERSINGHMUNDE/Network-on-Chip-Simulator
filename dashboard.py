# dashboard.py (Corrected for Matplotlib Backend)

import dash
from dash import dcc, html, Input, Output, State
import yaml
import numpy as np
import io
import base64

# --- THIS IS THE FIX ---
# Set the backend for Matplotlib to a non-interactive one.
# This must be done BEFORE importing matplotlib.pyplot.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# Import the simulator from the parent directory
from noc.simulator import Simulator

# --- Matplotlib Plotting Function ---
def create_plot(x_data, y_data, config):
    """Generates a matplotlib plot and returns it as a base64 encoded string."""
    plt.figure(figsize=(10, 6))
    plt.plot(x_data, y_data, marker='o', linestyle='-')
    
    traffic_pattern = config.get('traffic_pattern', 'N/A')
    topology = config.get('topology', 'N/A')
    plt.title(f'Network Performance: {topology.capitalize()} under "{traffic_pattern}" Load')
    plt.xlabel('Injection Rate (packets/node/cycle)')
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close() # Close the plot to free up memory
    data = base64.b64encode(buf.getbuffer()).decode("utf8")
    return f"data:image/png;base64,{data}"

# --- Dash App Initialization ---
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("AI GPU Grid - NoC Simulator Dashboard"),
    
    html.Div([ # Control Panel
        html.H3("Simulation Configuration"),
        
        html.Label("Topology:"),
        dcc.Dropdown(
            id='topology-dropdown',
            options=[
                {'label': '2D Mesh', 'value': 'mesh'},
                {'label': '2D Torus', 'value': 'torus'},
                {'label': 'Fat-Tree (Not Implemented)', 'value': 'fat_tree', 'disabled': True},
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
                {'label': 'Hotspot', 'value': 'hotspot'}
            ],
            value='transpose'
        ),
        
        html.Label("Routing Algorithm:"),
        dcc.Dropdown(
            id='routing-algo-dropdown',
            options=[
                {'label': 'XY', 'value': 'XY'},
                {'label': 'Adaptive', 'value': 'adaptive'}
            ],
            value='adaptive'
        ),

        html.Label("Number of Virtual Channels:"),
        dcc.Input(id='num-vcs-input', type='number', value=4, min=1, step=1),
        
        html.Label("Simulation Cycles:"),
        dcc.Input(id='sim-cycles-input', type='number', value=1000, min=100, step=100),

        html.Hr(),
        html.Button('Run Experiment Sweep', id='run-button', n_clicks=0),

    ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
    
    html.Div([ # Results Panel
        html.H3("Results"),
        dcc.Loading(
            id="loading-spinner",
            type="circle",
            children=[
                html.Div(id='results-summary'),
                html.Img(id='results-graph', style={'width': '100%'})
            ]
        )
    ], style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'})
])

@app.callback(
    [Output('results-summary', 'children'),
     Output('results-graph', 'src')],
    [Input('run-button', 'n_clicks')],
    [State('topology-dropdown', 'value'),
     State('traffic-pattern-dropdown', 'value'),
     State('routing-algo-dropdown', 'value'),
     State('num-vcs-input', 'value'),
     State('sim-cycles-input', 'value')]
)
def run_simulation_sweep(n_clicks, topology, traffic_pattern, routing_algo, num_vcs, sim_cycles):
    if n_clicks == 0:
        return "Click 'Run Experiment Sweep' to start.", ""

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    config['topology'] = topology
    config['traffic_pattern'] = traffic_pattern
    config['routing_algo'] = routing_algo
    config['num_virtual_channels'] = num_vcs
    config['simulation_cycles'] = sim_cycles

    injection_rates = np.arange(0.01, 0.16, 0.02)
    latencies = []
    
    for rate in injection_rates:
        sim_config = config.copy()
        sim_config['injection_rate'] = rate
        
        simulator = Simulator(config=sim_config)
        simulator.run(num_cycles=sim_config['simulation_cycles'])
        
        avg_latency = simulator.tracker.calculate_average_latency()
        latencies.append(avg_latency)

    summary_text = f"Experiment Complete. Topology: {topology.capitalize()}, Pattern: {traffic_pattern}, Routing: {routing_algo}, VCs: {num_vcs}."
    graph_src = create_plot(injection_rates, latencies, config)

    return summary_text, graph_src

if __name__ == '__main__':
    app.run(debug=True)