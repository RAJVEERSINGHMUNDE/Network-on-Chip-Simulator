# ai_gpu_grid_sim/noc/packet.py

from dataclasses import dataclass, field
from enum import Enum, auto
import itertools

# A unique ID generator for packets to make tracking easier
packet_id_counter = itertools.count()

class PacketType(Enum):
    READ = auto()
    WRITE = auto()
    RESPONSE = auto()
    SNOOP = auto()

class FlitType(Enum):
    HEAD = auto()
    BODY = auto()
    TAIL = auto()

@dataclass
class Packet:
    packet_type: PacketType
    src_address: int
    dest_address: int
    transaction_id: int
    data_payload: list[int]
    packet_id: int = field(default_factory=lambda: next(packet_id_counter))
    creation_time: int = -1

    def __post_init__(self):
        self.payload_size = len(self.data_payload)

@dataclass
class Flit:
    flit_type: FlitType
    payload: int
    packet_id: int
    vc_id: int
    src_address: int
    dest_address: int
    # --- UPDATED: Generic flag for hybrid routing ---
    use_secondary_network: bool = False

    def __repr__(self):
        # Updated representation to show which network the flit is for
        network_marker = " (Sec)" if self.use_secondary_network else " (Pri)"
        return (f"Flit(Type: {self.flit_type.name}, Pkt_ID: {self.packet_id}, "
                f"VC: {self.vc_id}, Dst: {self.dest_address}){network_marker}")