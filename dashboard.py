# dashboard.py

import dash
from dash import dcc, html, Input, Output, State
import yaml
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

from noc.simulator import Simulator

# --- Matplotlib Plotting Function ---
def create_plot(x_data, y_data, config):
    """Generates a matplotlib plot and returns it as a base64 encoded string."""
    plt.figure(figsize=(10, 6))
    plt.plot(x_data, y_data, marker='o', linestyle='-')
    
    traffic_pattern = config.get('traffic_pattern', 'N/A')
    plt.title(f'Network Performance under "{traffic_pattern}" Load')
    plt.xlabel('Injection Rate (packets/node/cycle)')
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    
    # Save plot to a bytes buffer and encode it
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
    [State('traffic-pattern-dropdown', 'value'),
     State('routing-algo-dropdown', 'value'),
     State('num-vcs-input', 'value'),
     State('sim-cycles-input', 'value')]
)
def run_simulation_sweep(n_clicks, traffic_pattern, routing_algo, num_vcs, sim_cycles):
    if n_clicks == 0:
        return "Click 'Run Experiment Sweep' to start.", ""

    # Load base config and override with UI values
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    config['traffic_pattern'] = traffic_pattern
    config['routing_algo'] = routing_algo
    config['num_virtual_channels'] = num_vcs
    config['simulation_cycles'] = sim_cycles

    # Define the experiment sweep
    injection_rates = np.arange(0.01, 0.16, 0.02)
    latencies = []
    
    for rate in injection_rates:
        sim_config = config.copy()
        sim_config['injection_rate'] = rate
        
        simulator = Simulator(config=sim_config)
        simulator.run(num_cycles=sim_config['simulation_cycles'])
        
        avg_latency = simulator.tracker.calculate_average_latency()
        latencies.append(avg_latency)

    # Prepare results
    summary_text = f"Experiment Complete. Pattern: {traffic_pattern}, Routing: {routing_algo}, VCs: {num_vcs}."
    graph_src = create_plot(injection_rates, latencies, config)

    return summary_text, graph_src

if __name__ == '__main__':
    app.run(debug=True)