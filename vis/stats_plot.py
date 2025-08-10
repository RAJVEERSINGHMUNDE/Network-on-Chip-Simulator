import yaml
import numpy as np
import matplotlib.pyplot as plt

import sys
sys.path.append('..')
from noc.simulator import Simulator

def run_single_experiment(config: dict) -> float:
    simulator = Simulator(config=config)
    simulator.run(num_cycles=config['simulation_cycles'])
    tracker = simulator.tracker
    avg_latency = tracker.calculate_average_latency()
    
    rate = config['injection_rate']
    print(f"  Injection Rate: {rate:.3f} to Avg Latency: {avg_latency:.2f} cycles")
    
    return avg_latency

def main():
    with open('../config.yaml', 'r') as f:
        base_config = yaml.safe_load(f)
    
    traffic_pattern = base_config.get('traffic_pattern', 'uniform_random')
    print(f"Starting Experiment Sweep for '{traffic_pattern}' pattern")

    injection_rates = np.arange(0.01, 0.16, 0.01)
    
    latencies = []
    
    for rate in injection_rates:
        current_config = base_config.copy()
        current_config['injection_rate'] = rate
        
        latency = run_single_experiment(current_config)
        latencies.append(latency)

    plt.figure(figsize=(10, 6))
    plt.plot(injection_rates, latencies, marker='o', linestyle='-')
    
    plt.title(f'Network Performance under "{traffic_pattern}" Load')
    plt.xlabel('Injection Rate (packets/node/cycle)')
    plt.ylabel('Average Packet Latency (cycles)')
    plt.grid(True)
    plt.xticks(injection_rates)

    output_filename = f'latency_vs_injection_rate_{traffic_pattern}.png'
    plt.savefig(output_filename)
    print(f"\nPlot saved to {output_filename}")
    
    plt.show()


if __name__ == "__main__":
    main()