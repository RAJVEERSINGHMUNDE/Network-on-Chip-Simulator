# ai_gpu_grid_sim/noc/node.py (Corrected for VCs)

import collections
import random
import warnings
from .packet import Packet, PacketType, Flit, FlitType
from metrics.tracker import MetricsTracker

class Node:
    """
    Represents a single GPU node attached to a router. It generates, injects,
    receives, and consumes packets.
    """
    def __init__(self, node_id: int, coords: tuple[int, int], config: dict, tracker: MetricsTracker):
        """
        Initializes the Node.

        Args:
            node_id: The unique address of this node (0 to num_gpus-1).
            coords: The (x, y) coordinates of this node in the grid.
            config: The global configuration dictionary.
            tracker: The central metrics tracker instance.
        """
        self.node_id = node_id
        self.coords = coords
        self.config = config
        self.tracker = tracker

        self.num_nodes = config['num_gpus']
        self.grid_width = int(self.num_nodes**0.5)
        self.injection_rate = config['injection_rate']
        self.traffic_pattern = config.get('traffic_pattern', 'uniform_random')
        self.hotspot_nodes = config.get('hotspot_nodes', [])
        self.hotspot_rate = config.get('hotspot_rate', 0.0)

        self.injection_queue: collections.deque[Flit] = collections.deque()
        self.reassembly_buffer: dict[int, list[Flit]] = collections.defaultdict(list)
        self.packets_sent = 0
        self.packets_received = 0

    def _packetize(self, packet: Packet, vc_id: int) -> list[Flit]:
        """
        Breaks a Packet into a list of Flits, assigning them all to the given vc_id.
        """
        flits = []
        payload = packet.data_payload
        
        flits.append(Flit(
            flit_type=FlitType.HEAD, payload=payload[0], packet_id=packet.packet_id,
            vc_id=vc_id, src_address=packet.src_address, dest_address=packet.dest_address
        ))

        for data_item in payload[1:-1]:
            flits.append(Flit(
                flit_type=FlitType.BODY, payload=data_item, packet_id=packet.packet_id,
                vc_id=vc_id, src_address=packet.src_address, dest_address=packet.dest_address
            ))

        if len(payload) > 1:
            flits.append(Flit(
                flit_type=FlitType.TAIL, payload=payload[-1], packet_id=packet.packet_id,
                vc_id=vc_id, src_address=packet.src_address, dest_address=packet.dest_address
            ))

        return flits

    def _get_destination(self) -> int:
        """Selects a destination node based on the configured traffic pattern."""
        
        # --- FIX: Check for topology/pattern compatibility ---
        if self.traffic_pattern == "transpose":
            if self.coords is None:
                warnings.warn(f"Node {self.node_id}: 'transpose' pattern is only valid for grid topologies. Falling back to uniform_random.")
                # Fall through to uniform random logic
            else:
                # Destination is (y, x)
                dest_y, dest_x = self.coords
                dest_id = dest_y * self.grid_width + dest_x
                # Avoid sending to self if it's a diagonal node in a square grid
                if dest_id == self.node_id:
                    pass # Fall through to uniform random
                else:
                    return dest_id

        if self.traffic_pattern == "hotspot" and self.hotspot_nodes and random.random() < self.hotspot_rate:
            if self.node_id not in self.hotspot_nodes:
                return random.choice(self.hotspot_nodes)

        # --- Uniform Random Pattern (Default/Fallback) ---
        dest_id = self.node_id
        while dest_id == self.node_id:
            dest_id = random.randint(0, self.num_nodes - 1)
        return dest_id

    def _generate_traffic(self, current_cycle: int):
        """Generates a new packet and assigns it to a random virtual channel."""
        if random.random() < self.injection_rate:
            dest_id = self._get_destination()

            new_packet = Packet(
                packet_type=PacketType.WRITE, src_address=self.node_id, dest_address=dest_id,
                transaction_id=random.randint(0, 65535),
                data_payload=[random.randint(0, 2**32-1) for _ in range(random.randint(1, 8))],
                creation_time=current_cycle
            )
            
            self.tracker.record_packet_creation(new_packet.packet_id, new_packet.creation_time)

            # Assign all flits of this packet to a single, random VC
            vc_id = random.randint(0, self.config['num_virtual_channels'] - 1)
            flits = self._packetize(new_packet, vc_id)
            self.injection_queue.extend(flits)
            self.packets_sent += 1

    def receive_flit(self, flit: Flit, current_cycle: int):
        """Processes a flit received from the router's LOCAL port."""
        self.reassembly_buffer[flit.packet_id].append(flit)
        if flit.flit_type == FlitType.TAIL:
            self.packets_received += 1
            self.tracker.record_packet_receipt(flit.packet_id, current_cycle)
            del self.reassembly_buffer[flit.packet_id]

    def process_cycle(self, current_cycle: int):
        """Generates traffic for the current cycle."""
        self._generate_traffic(current_cycle)