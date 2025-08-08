# ai_gpu_grid_sim/noc/router.py (Corrected)

import collections
import random
from enum import Enum, auto

from .packet import Flit

class Network:
    pass

class Port(Enum):
    NORTH = auto()
    EAST = auto()
    SOUTH = auto()
    WEST = auto()
    LOCAL = auto()

class Router:
    def __init__(self, x_coord: int, y_coord: int, grid_width: int, num_vcs: int, network: 'Network', config: dict):
        self.coords = (x_coord, y_coord)
        self.grid_width = grid_width
        self.num_vcs = num_vcs
        self.network = network
        self.config = config # Store the main config
        
        self.input_buffers: dict[Port, list[collections.deque]] = {
            p: [collections.deque() for _ in range(num_vcs)] for p in Port
        }
        self.vc_arbiter_state: dict[Port, int] = {p: 0 for p in Port}
        self.buffer_depth = config.get('router_buffer_size', 8)

    # _get_dest_coords remains the same...
    def _get_dest_coords(self, flit: Flit) -> tuple[int, int]:
        dest_id = flit.dest_address
        dest_y = dest_id // self.grid_width
        dest_x = dest_id % self.grid_width
        return (dest_x, dest_y)

    def _get_buffer_fullness(self, port: Port) -> float:
        if port not in self.network.connections[self]:
            return 1.0
        
        dest_router, dest_in_port = self.network.connections[self][port]
        total_used = sum(len(vc) for vc in dest_router.input_buffers[dest_in_port])
        total_capacity = self.num_vcs * self.buffer_depth
        return total_used / total_capacity if total_capacity > 0 else 1.0

    def _compute_route_adaptive(self, flit: Flit) -> Port:
        dest_x, dest_y = self._get_dest_coords(flit)
        if (dest_x, dest_y) == self.coords:
            return Port.LOCAL

        possible_ports = []
        if dest_x > self.coords[0]: possible_ports.append(Port.EAST)
        if dest_x < self.coords[0]: possible_ports.append(Port.WEST)
        if dest_y > self.coords[1]: possible_ports.append(Port.SOUTH)
        if dest_y < self.coords[1]: possible_ports.append(Port.NORTH)

        best_port = min(possible_ports, key=lambda p: self._get_buffer_fullness(p))
        return best_port
    
    def _compute_route_xy(self, flit: Flit) -> Port:
        """Original XY routing logic, now with Torus shortest-path awareness."""
        dest_x, dest_y = self._get_dest_coords(flit)
        
        # If we're a Torus, check for shorter wrap-around path
        if self.network.config.get('topology') == 'torus':
            # Check X-dimension
            if dest_x != self.coords[0]:
                # Distance going right vs wrapping around left
                dist_right = (dest_x - self.coords[0] + self.grid_width) % self.grid_width
                dist_left = (self.coords[0] - dest_x + self.grid_width) % self.grid_width
                if dist_right < dist_left:
                    return Port.EAST
                else:
                    return Port.WEST
            # Check Y-dimension
            elif dest_y != self.coords[1]:
                # Distance going south vs wrapping around north
                dist_south = (dest_y - self.coords[1] + self.grid_width) % self.grid_width
                dist_north = (self.coords[1] - dest_y + self.grid_width) % self.grid_width
                if dist_south < dist_north:
                    return Port.SOUTH
                else:
                    return Port.NORTH
            else:
                return Port.LOCAL
        
        # Original Mesh logic (fallback)
        else:
            if dest_x != self.coords[0]:
                return Port.EAST if dest_x > self.coords[0] else Port.WEST
            elif dest_y != self.coords[1]:
                return Port.SOUTH if dest_y > self.coords[1] else Port.NORTH
            else:
                return Port.LOCAL

    def process_cycle(self) -> dict[Port, Flit]:
        routing_requests: dict[Port, list[tuple[Flit, int]]] = collections.defaultdict(list)
        
        for in_port, vcs in self.input_buffers.items():
            for vc_id, buffer in enumerate(vcs):
                if buffer:
                    head_flit = buffer[0]
                    
                    # --- CORRECTED LINE ---
                    # Access config directly from self, not through self.network
                    if self.config['routing_algo'] == 'adaptive':
                        out_port = self._compute_route_adaptive(head_flit)
                    else:
                        out_port = self._compute_route_xy(head_flit)

                    routing_requests[out_port].append((head_flit, in_port, vc_id))

        forwarded_flits: dict[Port, Flit] = {}
        for out_port, requests in routing_requests.items():
            if not requests: continue
            
            start_index = self.vc_arbiter_state[out_port]
            num_requests = len(requests)
            
            for i in range(num_requests):
                winner_index = (start_index + i) % num_requests
                _flit, in_port, vc_id = requests[winner_index]
                self.vc_arbiter_state[out_port] = (winner_index + 1) % num_requests
                winning_flit = self.input_buffers[in_port][vc_id].popleft()
                forwarded_flits[out_port] = winning_flit
                break
                
        return forwarded_flits

    def __repr__(self) -> str:
        return f"Router@{self.coords}"