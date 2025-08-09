# ai_gpu_grid_sim/noc/network.py (Corrected for all topologies)

import math
from .router import Router, Port

class Network:
    def __init__(self, config: dict):
        self.config = config
        self.num_gpus = config['num_gpus']
        self.grid_width = None
        self.grid_height = None
        
        self.routers: dict[any, Router] = {}
        self.connections: dict[Router, dict[Port, tuple[Router, Port]]] = {}
        self.node_to_router_map: dict[int, tuple[Router, Port]] = {}

        topology_name = self.config.get('topology', 'mesh')
        
        if topology_name in ['mesh', 'torus']:
            if not math.sqrt(self.num_gpus).is_integer():
                raise ValueError("Mesh/Torus topology requires num_gpus to be a perfect square.")
            self.grid_width = int(math.sqrt(self.num_gpus))
            self.grid_height = self.grid_width

        if topology_name == 'mesh':
            self._create_mesh()
        elif topology_name == 'torus':
            self._create_torus()
        elif topology_name == 'fat_tree':
            self._create_fat_tree()
        else:
            raise ValueError(f"Unknown topology: {topology_name}")

    def _create_mesh(self):
        """Builds a 2D Mesh topology and its connections."""
        num_vcs = self.config['num_virtual_channels']
        print(f"Creating a {self.grid_width}x{self.grid_height} mesh router grid with {num_vcs} VCs...")

        # Create routers with 5 ports (N, E, S, W, Local)
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                self.routers[coords] = Router(coords, num_ports=5, num_vcs=num_vcs, network=self, config=self.config)
        
        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            # Connect to neighbors using integer port numbers
            if y > 0: self.connections[router][Port.NORTH.value] = (self.routers[(x, y - 1)], Port.SOUTH.value)
            if x < self.grid_width - 1: self.connections[router][Port.EAST.value] = (self.routers[(x + 1, y)], Port.WEST.value)
            if y < self.grid_height - 1: self.connections[router][Port.SOUTH.value] = (self.routers[(x, y + 1)], Port.NORTH.value)
            if x > 0: self.connections[router][Port.WEST.value] = (self.routers[(x - 1, y)], Port.EAST.value)
            
            # Map the node at these coordinates to the router's LOCAL port
            node_id = y * self.grid_width + x
            self.node_to_router_map[node_id] = (router, Port.LOCAL.value)

    def _create_torus(self):
        """Builds a 2D Torus topology and its connections."""
        num_vcs = self.config['num_virtual_channels']
        print(f"Creating a {self.grid_width}x{self.grid_height} torus router grid with {num_vcs} VCs...")

        # Create routers with 5 ports
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                self.routers[coords] = Router(coords, num_ports=5, num_vcs=num_vcs, network=self, config=self.config)

        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            # Torus connections with wraparound, using integer port numbers
            north_neighbor = self.routers[(x, (y - 1 + self.grid_height) % self.grid_height)]
            east_neighbor = self.routers[((x + 1) % self.grid_width, y)]
            south_neighbor = self.routers[(x, (y + 1) % self.grid_height)]
            west_neighbor = self.routers[((x - 1 + self.grid_width) % self.grid_width, y)]

            self.connections[router][Port.NORTH.value] = (north_neighbor, Port.SOUTH.value)
            self.connections[router][Port.EAST.value] = (east_neighbor, Port.WEST.value)
            self.connections[router][Port.SOUTH.value] = (south_neighbor, Port.NORTH.value)
            self.connections[router][Port.WEST.value] = (west_neighbor, Port.EAST.value)

            node_id = y * self.grid_width + x
            self.node_to_router_map[node_id] = (router, Port.LOCAL.value)

    def _create_fat_tree(self):
        """Builds a k-ary 2-level Fat-Tree topology."""
        k = self.config.get('fat_tree_k', 4)
        if k % 2 != 0: raise ValueError("fat_tree_k must be an even number.")

        num_pods = k
        num_edge_switches = num_pods * (k // 2)
        num_core_switches = (k // 2)**2
        nodes_per_edge_switch = k // 2
        
        expected_nodes = num_edge_switches * nodes_per_edge_switch
        if self.num_gpus != expected_nodes:
            raise ValueError(f"A k={k} Fat-Tree supports {expected_nodes} nodes, but num_gpus is set to {self.num_gpus}")

        num_vcs = self.config['num_virtual_channels']
        print(f"Creating a k={k} Fat-Tree with {num_core_switches} Core and {num_edge_switches} Edge switches...")

        # Create Core and Edge switches (routers)
        # For a k-ary fat-tree, each switch has k ports.
        core_switches = [Router(router_id=f'c_{i}', num_ports=k, num_vcs=num_vcs, network=self, config=self.config) for i in range(num_core_switches)]
        edge_switches = [Router(router_id=f'e_{i}', num_ports=k, num_vcs=num_vcs, network=self, config=self.config) for i in range(num_edge_switches)]
        for r in core_switches + edge_switches:
            self.routers[r.router_id] = r

        # Use integer port numbers for up/down links in fat-tree
        for i in range(num_edge_switches):
            edge_router = edge_switches[i]
            self.connections[edge_router] = {}
            pod = i // (k // 2)
            for j in range(k // 2):
                core_switch_idx = (i % (k // 2)) * (k // 2) + j
                core_router = core_switches[core_switch_idx]
                if core_router not in self.connections:
                    self.connections[core_router] = {}

                edge_up_port = nodes_per_edge_switch + j  # integer port
                core_down_port = pod * (k//2) + (i % (k//2))  # integer port
                self.connections[edge_router][edge_up_port] = (core_router, core_down_port)
                self.connections[core_router][core_down_port] = (edge_router, edge_up_port)

        node_id_counter = 0
        for i, edge_router in enumerate(edge_switches):
            for j in range(nodes_per_edge_switch):
                node_id = node_id_counter
                edge_down_port = j  # integer port
                self.node_to_router_map[node_id] = (edge_router, edge_down_port)
                node_id_counter += 1

    def get_router(self, router_id: any) -> Router:
        """Returns the router with the specified ID."""
        return self.routers.get(router_id)

    def __repr__(self) -> str:
        return f"Network(Topology: {self.config.get('topology', 'mesh')})"