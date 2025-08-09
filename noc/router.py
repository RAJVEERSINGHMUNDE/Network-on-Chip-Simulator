# ai_gpu_grid_sim/noc/router.py (Corrected)

import collections
import random
from enum import IntEnum

from .packet import Flit

class Network:
    pass

class Port(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    LOCAL = 4

class Router:
    def __init__(self, router_id: any, num_ports: int, num_vcs: int, network: 'Network', config: dict):
        self.router_id = router_id
        self.num_ports = num_ports
        self.num_vcs = num_vcs
        self.network = network
        self.config = config
        self.buffer_depth = config.get('router_buffer_size', 8)

        # Buffers are now indexed by integer port numbers
        self.input_buffers: dict[int, list[collections.deque]] = {
            port: [collections.deque() for _ in range(num_vcs)]
            for port in range(self.num_ports)
        }
        self.vc_arbiter_state: dict[int, int] = {p: 0 for p in range(self.num_ports)}
        self.buffer_depth = config.get('router_buffer_size', 8)

    def _get_dest_coords(self, flit: Flit) -> tuple[int, int]:
        dest_id = flit.dest_address
        # This assumes a grid layout for destination coordinates
        if self.network.grid_width is None:
            # For non-grid topologies, this needs a different logic
            # This is a placeholder and might need to be adapted for Fat-Tree
            return (0,0) 
        dest_y = dest_id // self.network.grid_width
        dest_x = dest_id % self.network.grid_width
        return (dest_x, dest_y)

    def _get_buffer_fullness(self, port: int) -> float:
        if port not in self.network.connections[self]:
            return 1.0
        
        dest_router, dest_in_port = self.network.connections[self][port]
        total_used = sum(len(vc) for vc in dest_router.input_buffers[dest_in_port])
        total_capacity = self.num_vcs * self.buffer_depth
        return total_used / total_capacity if total_capacity > 0 else 1.0

    def _compute_route_adaptive(self, flit: Flit) -> int:
        dest_x, dest_y = self._get_dest_coords(flit)
        
        # This logic is for grid topologies.
        # It needs to be adapted for non-grid like Fat-Tree.
        if self.router_id.__class__ is not tuple: # Hacky check for non-grid router
            print(f"Warning: Adaptive routing for {self.router_id} not implemented.")
            return 1 # Default port

        if (dest_x, dest_y) == self.router_id:
            return Port.LOCAL.value

        possible_ports = []
        if dest_x > self.router_id[0]: possible_ports.append(Port.EAST.value)
        if dest_x < self.router_id[0]: possible_ports.append(Port.WEST.value)
        if dest_y > self.router_id[1]: possible_ports.append(Port.SOUTH.value)
        if dest_y < self.router_id[1]: possible_ports.append(Port.NORTH.value)

        if not possible_ports:
             return Port.LOCAL.value

        best_port = min(possible_ports, key=lambda p: self._get_buffer_fullness(p))
        return best_port
    
    def _compute_route_xy(self, flit: Flit) -> int:
        """XY routing for grid topologies."""
        dest_x, dest_y = self._get_dest_coords(flit)

        if self.router_id.__class__ is not tuple: # Hacky check for non-grid router
            print(f"Warning: XY routing for {self.router_id} not implemented.")
            return 1 # Default port

        if dest_x != self.router_id[0]:
            return Port.EAST.value if dest_x > self.router_id[0] else Port.WEST.value
        elif dest_y != self.router_id[1]:
            return Port.SOUTH.value if dest_y > self.router_id[1] else Port.NORTH.value
        else:
            return Port.LOCAL.value

    def process_cycle(self) -> dict[int, Flit]:
        routing_requests: dict[int, list[tuple[Flit, int, int]]] = collections.defaultdict(list)

        # 1. Route computation for the head of each VC
        for in_port, vcs in self.input_buffers.items():
            for vc_id, buffer in enumerate(vcs):
                if buffer:
                    head_flit = buffer[0]
                    
                    # Placeholder for topology-specific routing
                    if self.config['routing_algo'] == 'adaptive':
                        out_port = self._compute_route_adaptive(head_flit)
                    else: # Default to XY
                        out_port = self._compute_route_xy(head_flit)
                    routing_requests[out_port].append((head_flit, in_port, vc_id))

        # 2. VC Arbitration: Select one winner for each output port
        forwarded_flits: dict[int, Flit] = {}
        for out_port, requests in routing_requests.items():
            if not requests: continue
            
            # Simple round-robin arbitration
            start_index = self.vc_arbiter_state.get(out_port, 0)
            num_requests = len(requests)
            
            for i in range(num_requests):
                winner_index = (start_index + i) % num_requests
                _flit, in_port, vc_id = requests[winner_index]
                
                # Check if destination buffer has space (simplified)
                # A more realistic model would check credits
                if out_port in self.network.connections.get(self, {}):
                    dest_router, dest_in_port = self.network.connections[self][out_port]
                    if len(dest_router.input_buffers[dest_in_port][vc_id]) >= self.buffer_depth:
                        continue # Skip if destination buffer is full

                self.vc_arbiter_state[out_port] = (winner_index + 1) % num_requests
                winning_flit = self.input_buffers[in_port][vc_id].popleft()
                forwarded_flits[out_port] = winning_flit
                break # Only one flit per output port per cycle
                
        return forwarded_flits

    def __repr__(self) -> str:
        return f"Router@{self.router_id}"