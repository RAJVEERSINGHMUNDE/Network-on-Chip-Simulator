# noc/node.py
import collections
import random
import warnings
from .packet import Packet, PacketType, Flit, FlitType
from metrics.tracker import MetricsTracker

class Node:
    def __init__(self, node_id: int, coords: tuple, config: dict, tracker: MetricsTracker):
        self.node_id = node_id
        self.coords = coords
        self.config = config
        self.tracker = tracker
        self.num_nodes = config['num_gpus']
        self.grid_width = int(self.num_nodes**0.5) if coords else None
        self.injection_rate = config['injection_rate']
        self.traffic_pattern = config.get('traffic_pattern', 'uniform_random')
        self.hotspot_nodes = config.get('hotspot_nodes', [])
        self.hotspot_rate = config.get('hotspot_rate', 0.0)
        self.injection_queue: collections.deque[Flit] = collections.deque()
        self.reassembly_buffer: dict[int, list[Flit]] = collections.defaultdict(list)
        self.packets_sent = 0
        self.packets_received = 0

        self.secondary_traffic_patterns = []
        if config.get('architecture') == 'hybrid_electrical':
            self.secondary_traffic_patterns = config['hybrid_electrical_config']['secondary_traffic']

    def _packetize(self, packet: Packet, vc_id: int) -> list[Flit]:
        flits = []
        payload = packet.data_payload
        
        use_secondary = self.traffic_pattern in self.secondary_traffic_patterns
        
        common_args = {
            'packet_id': packet.packet_id, 'vc_id': vc_id,
            'src_address': packet.src_address, 'dest_address': packet.dest_address,
            'use_secondary_network': use_secondary
        }

        if not payload: # Handle empty payload case
            payload = [0] 

        flits.append(Flit(flit_type=FlitType.HEAD, payload=payload[0], **common_args))
        for data_item in payload[1:-1]:
            flits.append(Flit(flit_type=FlitType.BODY, payload=data_item, **common_args))
        if len(payload) > 1:
            flits.append(Flit(flit_type=FlitType.TAIL, payload=payload[-1], **common_args))
        return flits

    def _get_destination(self) -> int:
        if self.traffic_pattern == "transpose":
            if self.coords is None:
                warnings.warn(f"Node {self.node_id}: 'transpose' pattern is only valid for grid topologies.to uniform_random.")
            else:
                dest_y, dest_x = self.coords
                dest_id = dest_y * self.grid_width + dest_x
                if dest_id != self.node_id:
                    return dest_id
        if self.traffic_pattern == "hotspot" and self.hotspot_nodes and random.random() < self.hotspot_rate:
            if self.node_id not in self.hotspot_nodes:
                return random.choice(self.hotspot_nodes)
        dest_id = self.node_id
        while dest_id == self.node_id:
            dest_id = random.randint(0, self.num_nodes - 1)
        return dest_id
    
    def inject_workload_packet(self, dest_id: int, packet_size_flits: int, current_cycle: int, transaction_id: int):
        if packet_size_flits <= 0: return
        dummy_payload = list(range(packet_size_flits))
        new_packet = Packet(
            packet_type=PacketType.WRITE,
            src_address=self.node_id, dest_address=dest_id,
            transaction_id=transaction_id, data_payload=dummy_payload,
            creation_time=current_cycle
        )
        self.tracker.record_packet_creation(new_packet.packet_id, new_packet.creation_time)
        vc_id = random.randint(0, self.config['num_virtual_channels'] - 1)
        flits = self._packetize(new_packet, vc_id)
        self.injection_queue.extend(flits)
        self.packets_sent += 1

    def _generate_traffic(self, current_cycle: int):
        if random.random() < self.injection_rate:
            dest_id = self._get_destination()
            new_packet = Packet(
                packet_type=PacketType.WRITE, src_address=self.node_id, dest_address=dest_id,
                transaction_id=random.randint(0, 65535),
                data_payload=[random.randint(0, 2**32-1) for _ in range(random.randint(1, 8))],
                creation_time=current_cycle
            )
            self.tracker.record_packet_creation(new_packet.packet_id, new_packet.creation_time)
            vc_id = random.randint(0, self.config['num_virtual_channels'] - 1)
            flits = self._packetize(new_packet, vc_id)
            self.injection_queue.extend(flits)
            self.packets_sent += 1

    def receive_flit(self, flit: Flit, current_cycle: int) -> dict | None:
        if flit.flit_type == FlitType.TAIL:
            self.packets_received += 1
            self.tracker.record_packet_receipt(flit.packet_id, current_cycle)
            return {"packet_id": flit.packet_id, "src_address": flit.src_address, "dest_address": flit.dest_address}
        return None

    def process_cycle(self, current_cycle: int):
        self._generate_traffic(current_cycle)