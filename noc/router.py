# ai_gpu_grid_sim/noc/router.py (Final Version)

import collections
import math
from enum import IntEnum, auto

from .packet import Flit

# Forward declaration for type hinting
class Network:
    pass

class Port(IntEnum):
    # Grid ports (0-4 are reserved for this)
    NORTH, EAST, SOUTH, WEST, LOCAL = 0, 1, 2, 3, 4
    # Generic ports for high-radix routers
    PORT_0, PORT_1, PORT_2, PORT_3, PORT_4, PORT_5, PORT_6, PORT_7 = 0, 1, 2, 3, 4, 5, 6, 7
    PORT_8, PORT_9, PORT_10, PORT_11, PORT_12, PORT_13, PORT_14, PORT_15 = 8, 9, 10, 11, 12, 13, 14, 15

class Router:
    def __init__(self, router_id: any, num_ports: int, num_vcs: int, network: 'Network', config: dict):
        self.router_id = router_id
        self.num_ports = num_ports
        self.num_vcs = num_vcs
        self.network = network
        self.config = config
        self.buffer_depth = config.get('router_buffer_size', 8)
        self.input_buffers: dict[int, list] = {p: [collections.deque() for _ in range(num_vcs)] for p in range(num_ports)}
        self.vc_arbiter_state: dict[int, int] = {p: 0 for p in range(num_ports)}
        
        self.type, self.pod_id, self.switch_id, self.coords, self.grid_width = None, None, None, None, None
        if isinstance(router_id, tuple): # Grid topology
            self.coords = router_id
            self.grid_width = network.grid_width
        elif isinstance(router_id, str) and '_' in router_id: # Fat-Tree
            parts = router_id.split('_')
            if parts[0] == 'e': self.type, self.pod_id, self.switch_id = 'edge', int(parts[1]), int(parts[2])
            elif parts[0] == 'c': self.type, self.switch_id = 'core', int(parts[1])

    def _get_dest_coords(self, flit: Flit) -> tuple:
        if self.grid_width is None: return (None, None)
        return (flit.dest_address % self.grid_width, flit.dest_address // self.grid_width)

    def _get_buffer_fullness(self, port: int) -> float:
        if port not in self.network.connections.get(self, {}): return 1.0
        dest_router, dest_in_port = self.network.connections[self][port]
        total_used = sum(len(vc) for vc in dest_router.input_buffers[dest_in_port])
        return total_used / (self.num_vcs * self.buffer_depth)

    def _compute_route_adaptive(self, flit: Flit) -> int:
        dest_x, dest_y = self._get_dest_coords(flit)
        if (dest_x, dest_y) == self.coords: return Port.LOCAL.value
        possible_ports = []
        if dest_x > self.coords[0]: possible_ports.append(Port.EAST.value)
        if dest_x < self.coords[0]: possible_ports.append(Port.WEST.value)
        if dest_y > self.coords[1]: possible_ports.append(Port.SOUTH.value)
        if dest_y < self.coords[1]: possible_ports.append(Port.NORTH.value)
        if not possible_ports: return Port.LOCAL.value
        return min(possible_ports, key=lambda p: self._get_buffer_fullness(p))

    def _compute_route_xy(self, flit: Flit) -> int:
        dest_x, dest_y = self._get_dest_coords(flit)
        if self.network.config.get('topology') == 'torus':
            if dest_x != self.coords[0]:
                dist_right = (dest_x - self.coords[0] + self.grid_width) % self.grid_width
                return Port.EAST.value if dist_right <= self.grid_width / 2 else Port.WEST.value
            elif dest_y != self.coords[1]:
                dist_south = (dest_y - self.coords[1] + self.grid_width) % self.grid_width
                return Port.SOUTH.value if dist_south <= self.grid_width / 2 else Port.NORTH.value
        else: # Mesh
            if dest_x != self.coords[0]: return Port.EAST.value if dest_x > self.coords[0] else Port.WEST.value
            elif dest_y != self.coords[1]: return Port.SOUTH.value if dest_y > self.coords[1] else Port.NORTH.value
        return Port.LOCAL.value

    def _get_fat_tree_dest_info(self, dest_address: int):
        k = self.config.get('fat_tree_k', 4)
        nodes_per_switch = k // 2
        edge_switches_per_pod = k // 2
        dest_edge_id = dest_address // nodes_per_switch
        dest_pod = dest_edge_id // edge_switches_per_pod
        return dest_edge_id, dest_pod

    def _compute_route_fat_tree(self, flit: Flit) -> int:
        k = self.config.get('fat_tree_k', 4)
        nodes_per_switch = k // 2
        dest_edge_id, dest_pod = self._get_fat_tree_dest_info(flit.dest_address)
        if self.type == 'edge':
            current_edge_id = self.pod_id * (k//2) + self.switch_id
            if dest_edge_id == current_edge_id: return flit.dest_address % nodes_per_switch
            else: return nodes_per_switch + (flit.packet_id % (k // 2))
        elif self.type == 'core': return dest_pod
        raise TypeError("Unknown router type for Fat-Tree")

    def _compute_route_fat_tree_adaptive(self, flit: Flit) -> int:
        k = self.config.get('fat_tree_k', 4)
        nodes_per_switch = k // 2
        dest_edge_id, dest_pod = self._get_fat_tree_dest_info(flit.dest_address)

        if self.type == 'edge':
            current_edge_id = self.pod_id * (k//2) + self.switch_id
            if dest_edge_id == current_edge_id:
                return flit.dest_address % nodes_per_switch
            else:
                # Find the least congested "up" port
                up_ports = range(nodes_per_switch, k)
                return min(up_ports, key=lambda p: self._get_buffer_fullness(p))
        elif self.type == 'core':
            return dest_pod # Down path is deterministic
        raise TypeError("Unknown router type for Fat-Tree")

    def _get_base_k_digits(self, address, k, n):
        digits = []
        for _ in range(n):
            digits.append(address % k)
            address //= k
        return digits[::-1]

    def _compute_route_butterfly(self, flit: Flit) -> int:
        k = self.config.get('k_radix', 4)
        n = int(math.log(self.config['num_gpus'], k))
        dest_addr = flit.dest_address
        if self.router_id == dest_addr: return Port.PORT_0.value
        my_digits = self._get_base_k_digits(self.router_id, k, n)
        dest_digits = self._get_base_k_digits(dest_addr, k, n)
        for i in range(n):
            if my_digits[i] != dest_digits[i]:
                dim = n - 1 - i
                my_digit_in_dim = (self.router_id // (k**dim)) % k
                dest_digit_in_dim = (dest_addr // (k**dim)) % k
                port_offset = (dest_digit_in_dim - my_digit_in_dim + k) % k
                port_id = 1 + (n - 1 - dim) * (k - 1) + (port_offset - 1)
                return port_id
        return Port.PORT_0.value

    def process_cycle(self) -> dict[int, Flit]:
        routing_requests: dict[int, list] = collections.defaultdict(list)
        for in_port, vcs in self.input_buffers.items():
            for vc_id, buffer in enumerate(vcs):
                if buffer:
                    head_flit = buffer[0]
                    topology = self.config.get('topology')
                    routing_algo = self.config.get('routing_algo')

                    # --- New Routing Factory Logic ---
                    out_port = -1
                    if topology == 'flattened_butterfly':
                        out_port = self._compute_route_butterfly(head_flit)
                    elif topology == 'fat_tree':
                        if routing_algo == 'adaptive':
                            out_port = self._compute_route_fat_tree_adaptive(head_flit)
                        else: # Default to non-adaptive
                            out_port = self._compute_route_fat_tree(head_flit)
                    else: # Grid Topologies (Mesh, Torus)
                        if routing_algo == 'adaptive':
                            out_port = self._compute_route_adaptive(head_flit)
                        else: # Default to XY
                            out_port = self._compute_route_xy(head_flit)
                    
                    routing_requests[out_port].append((head_flit, in_port, vc_id))

        forwarded_flits: dict[int, Flit] = {}
        for out_port, requests in routing_requests.items():
            if not requests: continue
            start_index = self.vc_arbiter_state.get(out_port, 0)
            for i in range(len(requests)):
                winner_index = (start_index + i) % len(requests)
                _flit, in_port, vc_id = requests[winner_index]
                self.vc_arbiter_state[out_port] = (winner_index + 1) % len(requests)
                forwarded_flits[out_port] = self.input_buffers[in_port][vc_id].popleft()
                break
        return forwarded_flits

    def __repr__(self) -> str:
        return f"Router({self.router_id})"