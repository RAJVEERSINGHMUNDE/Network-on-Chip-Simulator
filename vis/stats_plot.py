# ai_gpu_grid_sim/vis/stats_plot.py

import yaml
import numpy as np
import matplotlib.pyplot as plt

# Import the simulator from the parent directory
import sys
sys.path.append('..')
from noc.simulator import Simulator

def run_single_experiment(config: dict) -> float:
    """Runs one simulation with a given config and returns the average latency."""
    simulator = Simulator(config=config)
    simulator.run(num_cycles=config['simulation_cycles'])
    tracker = simulator.tracker
    avg_latency = tracker.calculate_average_latency()
    
    # Print progress for the user
    rate = config['injection_rate']
    print(f"  Injection Rate: {rate:.3f} -> Avg Latency: {avg_latency:.2f} cycles")
    
    return avg_latency

def main():
    """
    Main function to run a sweep of experiments and plot the results.
    """
    # Load the base configuration
    with open('../config.yaml', 'r') as f:
        base_config = yaml.safe_load(f)
    
    traffic_pattern = base_config.get('traffic_pattern', 'uniform_random')
    print(f"--- Starting Experiment Sweep for '{traffic_pattern}' pattern ---")

    # Define the range of injection rates to test
    injection_rates = np.arange(0.01, 0.16, 0.01) # Test from 0.01 to 0.15
    
    latencies = []
    
    # Run the experiment for each injection rate
    for rate in injection_rates:
        # Create a copy of the config and update the injection rate
        current_config = base_config.copy()
        current_config['injection_rate'] = rate
        
        latency = run_single_experiment(current_config)
        latencies.append(latency)

    # --- Plotting the results ---
    plt.figure(figsize=(10, 6))
    plt.plot(injection_rates, latencies, marker='o', linestyle='-')
    
    plt.title(f'Network Performance under "{traffic_pattern}" Load')
    plt.xlabel('Injection Rate (packets/node/cycle)')
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    plt.xticks(injection_rates)
    
    # Save the plot to a file
    output_filename = f'latency_vs_injection_rate_{traffic_pattern}.png'
    plt.savefig(output_filename)
    print(f"\nPlot saved to {output_filename}")
    
    plt.show()


if __name__ == "__main__":
    main()