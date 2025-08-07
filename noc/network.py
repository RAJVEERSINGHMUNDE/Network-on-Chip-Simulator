# ai_gpu_grid_sim/noc/network.py (Corrected)

import math
from .router import Router, Port

class Network:
    def __init__(self, config: dict):
        if not math.sqrt(config['num_gpus']).is_integer():
            raise ValueError("num_gpus must be a perfect square for a 2D Mesh.")
        
        self.config = config # Store config
        self.num_gpus = config['num_gpus']
        self.num_vcs = config['num_virtual_channels']
        self.grid_width = int(math.sqrt(self.num_gpus))
        self.grid_height = self.grid_width
        
        self.routers: dict[tuple[int, int], Router] = {}
        self.connections: dict[Router, dict[Port, tuple[Router, Port]]] = {}

        self._create_routers()
        self._establish_connections()

    def _create_routers(self):
        print(f"Creating a {self.grid_width}x{self.grid_height} router grid with {self.num_vcs} VCs...")
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                # Pass self (the network) and the config to the Router
                self.routers[coords] = Router(x, y, self.grid_width, self.num_vcs, self, self.config)

    # _establish_connections, get_router, and __repr__ remain the same...
    def _establish_connections(self):
        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            if y > 0: self.connections[router][Port.NORTH] = (self.routers[(x, y - 1)], Port.SOUTH)
            if x < self.grid_width - 1: self.connections[router][Port.EAST] = (self.routers[(x + 1, y)], Port.WEST)
            if y < self.grid_height - 1: self.connections[router][Port.SOUTH] = (self.routers[(x, y + 1)], Port.NORTH)
            if x > 0: self.connections[router][Port.WEST] = (self.routers[(x - 1, y)], Port.EAST)

    def get_router(self, x: int, y: int) -> Router:
        return self.routers.get((x, y))

    def __repr__(self) -> str:
        return f"Network({self.grid_width}x{self.grid_height} Mesh, {self.num_vcs} VCs)"