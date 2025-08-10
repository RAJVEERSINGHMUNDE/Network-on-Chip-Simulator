import yaml
from noc.simulator import Simulator


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    num_gpus = config['num_gpus']
    num_cycles = config['simulation_cycles']
    pattern = config['traffic_pattern']

    print("AI GPU Grid NoC Simulator")
    print(f"Configuration: {num_gpus} GPUs, Pattern: {pattern}, "
          f"Cycles: {num_cycles}")

    simulator = Simulator(config=config)

    simulator.run(num_cycles=num_cycles)
    
    print("\n Simulation Metrics Summary")
    tracker = simulator.tracker
    
    total_packets_sent = sum(node.packets_sent for node in simulator.nodes)
    total_packets_received = len(tracker.packet_latencies)
    avg_latency = tracker.calculate_average_latency()
    throughput = tracker.calculate_throughput(num_cycles, num_gpus)

    print(f"Total Packets Sent:     {total_packets_sent}")
    print(f"Total Packets Received: {total_packets_received}")
    print(f"Average Packet Latency: {avg_latency:.2f} cycles")
    print(f"Network Throughput:     {throughput:.4f} packets/cycle")


if __name__ == "__main__":
    main()