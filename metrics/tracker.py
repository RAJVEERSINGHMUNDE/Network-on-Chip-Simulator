class MetricsTracker:
    def __init__(self):
        self.packet_creation_times: dict[int, int] = {}
        self.packet_latencies: list[int] = []

    def record_packet_creation(self, packet_id: int, creation_time: int): 
        self.packet_creation_times[packet_id] = creation_time

    def record_packet_receipt(self, packet_id: int, receipt_time: int):
        if packet_id in self.packet_creation_times:
            creation_time = self.packet_creation_times[packet_id]
            latency = receipt_time - creation_time
            self.packet_latencies.append(latency)
            del self.packet_creation_times[packet_id]

    def calculate_average_latency(self) -> float:
        if not self.packet_latencies:
            return 0.0
        return sum(self.packet_latencies) / len(self.packet_latencies)
    
    def calculate_throughput(self, num_cycles: int, num_nodes: int) -> float:
        total_flits_received = sum(self.packet_latencies) # A proxy for flits
        if num_cycles == 0 or num_nodes == 0:
            return 0.0
        return len(self.packet_latencies) / num_cycles