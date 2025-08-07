# ai_gpu_grid_sim/metrics/tracker.py

class MetricsTracker:
    """
    A dedicated class to track and calculate simulation performance metrics.
    """
    def __init__(self):
        # A dictionary to store the creation time of each packet
        self.packet_creation_times: dict[int, int] = {}
        
        # A list to store the individual latency for each packet that is successfully received
        self.packet_latencies: list[int] = []

    def record_packet_creation(self, packet_id: int, creation_time: int):
        """Called by a Node when it creates a new packet."""
        self.packet_creation_times[packet_id] = creation_time

    def record_packet_receipt(self, packet_id: int, receipt_time: int):
        """Called by a Node when it receives the TAIL flit of a packet."""
        if packet_id in self.packet_creation_times:
            creation_time = self.packet_creation_times[packet_id]
            latency = receipt_time - creation_time
            self.packet_latencies.append(latency)
            # Remove from tracking to save memory
            del self.packet_creation_times[packet_id]

    def calculate_average_latency(self) -> float:
        """Calculates the average latency of all received packets."""
        if not self.packet_latencies:
            return 0.0
        return sum(self.packet_latencies) / len(self.packet_latencies)
    
    def calculate_throughput(self, num_cycles: int, num_nodes: int) -> float:
        """
        Calculates the average network throughput in flits/cycle/node.
        Assumes 1 flit = 1 word of data.
        """
        total_flits_received = sum(self.packet_latencies) # A proxy for flits
        if num_cycles == 0 or num_nodes == 0:
            return 0.0
        # A simple throughput metric
        return len(self.packet_latencies) / num_cycles