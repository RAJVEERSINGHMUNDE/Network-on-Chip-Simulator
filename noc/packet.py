# ai_gpu_grid_sim/noc/packet.py

from dataclasses import dataclass, field
from enum import Enum, auto
import itertools

# A unique ID generator for packets to make tracking easier
packet_id_counter = itertools.count()

class PacketType(Enum):
    """
    Enumeration for the type of packet, based on the design specification.
    """
    READ = auto()
    WRITE = auto()
    RESPONSE = auto()
    # SNOOP is included as a potential future type as per the spec 
    SNOOP = auto()

class FlitType(Enum):
    """
    Enumeration for the type of flit, required for wormhole switching.
    """
    HEAD = auto()
    BODY = auto()
    TAIL = auto()

@dataclass
class Packet:
    """
    Represents a full data packet before it is broken into flits.
    The fields are derived from the project's design specification.
    """
    # --- Fields from Design Specification  ---
    packet_type: PacketType
    src_address: int  # Source GPU/Node ID
    dest_address: int # Destination GPU/Node ID
    transaction_id: int
    data_payload: list[int]

    # --- Fields for Simulation & Metrics ---
    packet_id: int = field(default_factory=lambda: next(packet_id_counter))
    creation_time: int = -1 # Will be set by the simulator at injection time

    def __post_init__(self):
        # Payload size can be derived from the data payload itself.
        self.payload_size = len(self.data_payload)

@dataclass
class Flit:
    """
    Represents a single Flow Control unit (flit) that travels the NoC.
    A Packet is broken down into one or more flits.
    """
    flit_type: FlitType
    payload: int # The actual data chunk for this flit
    packet_id: int
    vc_id: int
    # Routing information is carried by the flit.
    # In a simple model, all flits carry this for stateless routers.
    # In a more complex router, only the HEAD flit might carry it.
    src_address: int
    dest_address: int

    def __repr__(self):
        return (f"Flit(Type: {self.flit_type.name}, Pkt_ID: {self.packet_id}, "
                f"VC: {self.vc_id}, Src: {self.src_address}, Dst: {self.dest_address})")