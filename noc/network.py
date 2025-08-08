# ai_gpu_grid_sim/noc/network.py (Corrected)

import math
from .router import Router, Port

class Network:
    def __init__(self, config: dict):
        self.config = config
        self.num_gpus = config['num_gpus']
        
        # --- THIS IS THE FIX ---
        # Calculate grid dimensions here to make them available to the Simulator.
        # This assumes a square grid for mesh/torus topologies.
        if not math.sqrt(self.num_gpus).is_integer():
            raise ValueError("Mesh/Torus topology requires num_gpus to be a perfect square.")
        self.grid_width = int(math.sqrt(self.num_gpus))
        self.grid_height = self.grid_width
        
        self.routers: dict[any, Router] = {}
        self.connections: dict[Router, dict[Port, tuple[Router, Port]]] = {}

        # --- Topology Factory ---
        topology_name = self.config.get('topology', 'mesh')
        if topology_name == 'mesh':
            self._create_mesh()
        elif topology_name == 'torus':
            self._create_torus()
        elif topology_name == 'flattened_butterfly':
            raise NotImplementedError("Flattened Butterfly topology is not yet implemented.")
        elif topology_name == 'dragonfly':
            raise NotImplementedError("Dragonfly topology is not yet implemented.")
        else:
            raise ValueError(f"Unknown topology: {topology_name}")

    def _create_mesh(self):
        """Builds a 2D Mesh topology and its connections."""
        num_vcs = self.config['num_virtual_channels']
        print(f"Creating a {self.grid_width}x{self.grid_height} mesh router grid with {num_vcs} VCs...")

        # Create routers
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                self.routers[coords] = Router(x, y, self.grid_width, num_vcs, self, self.config)
        
        # Establish connections
        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            if y > 0: self.connections[router][Port.NORTH] = (self.routers[(x, y - 1)], Port.SOUTH)
            if x < self.grid_width - 1: self.connections[router][Port.EAST] = (self.routers[(x + 1, y)], Port.WEST)
            if y < self.grid_height - 1: self.connections[router][Port.SOUTH] = (self.routers[(x, y + 1)], Port.NORTH)
            if x > 0: self.connections[router][Port.WEST] = (self.routers[(x - 1, y)], Port.EAST)

    def _create_torus(self):
        """Builds a 2D Torus topology and its connections."""
        num_vcs = self.config['num_virtual_channels']
        print(f"Creating a {self.grid_width}x{self.grid_height} torus router grid with {num_vcs} VCs...")

        # Create routers (same as mesh)
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                self.routers[coords] = Router(x, y, self.grid_width, num_vcs, self, self.config)
        
        # Establish connections with wrap-around links
        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            # North connection (with wrap-around)
            north_neighbor = (self.routers[(x, (y - 1 + self.grid_height) % self.grid_height)], Port.SOUTH)
            self.connections[router][Port.NORTH] = north_neighbor
            
            # East connection (with wrap-around)
            east_neighbor = (self.routers[((x + 1) % self.grid_width, y)], Port.WEST)
            self.connections[router][Port.EAST] = east_neighbor
            
            # South connection (with wrap-around)
            south_neighbor = (self.routers[(x, (y + 1) % self.grid_height)], Port.NORTH)
            self.connections[router][Port.SOUTH] = south_neighbor
            
            # West connection (with wrap-around)
            west_neighbor = (self.routers[((x - 1 + self.grid_width) % self.grid_width, y)], Port.EAST)
            self.connections[router][Port.WEST] = west_neighbor

    def get_router(self, router_id: any) -> Router:
        """Returns the router with the specified ID."""
        return self.routers.get(router_id)

    def __repr__(self) -> str:
        return f"Network(Topology: {self.config.get('topology', 'mesh')})"