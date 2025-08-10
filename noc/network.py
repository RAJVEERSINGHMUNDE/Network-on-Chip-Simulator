import math
from .router import Router, Port

class Network:
    def __init__(self, config: dict, topology_override: str = None):
        self.config = config
        self.num_gpus = config['num_gpus']
        self.grid_width, self.grid_height = None, None
        self.routers: dict[any, Router] = {}
        self.connections: dict[Router, dict[int, tuple]] = {}
        self.node_to_router_map: dict[int, tuple] = {}
        topology_name = topology_override if topology_override else self.config.get('topology', 'mesh')
        print(f"{topology_name}")

        if topology_name in ['mesh', 'torus']:
            if not math.sqrt(self.num_gpus).is_integer():
                raise ValueError("Not a Perfect Square")
            self.grid_width = int(math.sqrt(self.num_gpus))
            self.grid_height = self.grid_width

        if topology_name == 'mesh': self._create_mesh()
        elif topology_name == 'torus': self._create_torus()
        elif topology_name == 'fat_tree': self._create_fat_tree()
        else: raise ValueError(f"Unknown topology: {topology_name}")
        self.router_port_to_node_map: dict[tuple[Router, Port], int] = \
            {val: key for key, val in self.node_to_router_map.items()}

    def _create_mesh(self):
        num_vcs = self.config['num_virtual_channels']
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                self.routers[coords] = Router(coords, num_ports=5, num_vcs=num_vcs, network=self, config=self.config)
                self.node_to_router_map[y * self.grid_width + x] = (self.routers[coords], Port.LOCAL.value)
        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            if y > 0: self.connections[router][Port.NORTH.value] = (self.routers[(x, y - 1)], Port.SOUTH.value)
            if x < self.grid_width - 1: self.connections[router][Port.EAST.value] = (self.routers[(x + 1, y)], Port.WEST.value)
            if y < self.grid_height - 1: self.connections[router][Port.SOUTH.value] = (self.routers[(x, y + 1)], Port.NORTH.value)
            if x > 0: self.connections[router][Port.WEST.value] = (self.routers[(x - 1, y)], Port.EAST.value)

    def _create_torus(self):
        num_vcs = self.config['num_virtual_channels']
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                coords = (x, y)
                self.routers[coords] = Router(coords, num_ports=5, num_vcs=num_vcs, network=self, config=self.config)
                self.node_to_router_map[y * self.grid_width + x] = (self.routers[coords], Port.LOCAL.value)
        for coords, router in self.routers.items():
            x, y = coords
            self.connections[router] = {}
            self.connections[router][Port.NORTH.value] = (self.routers[(x, (y - 1 + self.grid_height) % self.grid_height)], Port.SOUTH.value)
            self.connections[router][Port.EAST.value] = (self.routers[((x + 1) % self.grid_width, y)], Port.WEST.value)
            self.connections[router][Port.SOUTH.value] = (self.routers[(x, (y + 1) % self.grid_height)], Port.NORTH.value)
            self.connections[router][Port.WEST.value] = (self.routers[((x - 1 + self.grid_width) % self.grid_width, y)], Port.EAST.value)

    def _create_fat_tree(self):
        k = self.config.get('fat_tree_k', 4)
        if k % 2 != 0: raise ValueError("k has to even.")
        num_pods, nodes_per_switch = k, k // 2
        num_edge_switches, num_core_switches = num_pods * nodes_per_switch, (k // 2)**2
        expected_nodes = num_edge_switches * nodes_per_switch
        if self.num_gpus != expected_nodes: raise ValueError(f"k={k} Fat-Tree only supports {expected_nodes} nodes, not {self.num_gpus}")
        num_vcs = self.config['num_virtual_channels']
        core_switches = [Router(f'c_{i}', num_ports=k, num_vcs=num_vcs, network=self, config=self.config) for i in range(num_core_switches)]
        edge_switches = [Router(f'e_{p}_{s}', num_ports=k, num_vcs=num_vcs, network=self, config=self.config) for p in range(num_pods) for s in range(k//2)]
        for r in core_switches + edge_switches: self.routers[r.router_id] = r
        for i in range(num_edge_switches):
            edge_router = edge_switches[i]
            pod, switch_in_pod = i // (k // 2), i % (k // 2)
            for j in range(k // 2):
                core_switch_idx = switch_in_pod * (k // 2) + j
                core_router = core_switches[core_switch_idx]
                edge_up_port, core_down_port = nodes_per_switch + j, pod
                if edge_router not in self.connections: self.connections[edge_router] = {}
                if core_router not in self.connections: self.connections[core_router] = {}
                self.connections[edge_router][edge_up_port] = (core_router, core_down_port)
                self.connections[core_router][core_down_port] = (edge_router, edge_up_port)
        for i in range(num_edge_switches):
            for j in range(nodes_per_switch):
                node_id = i * nodes_per_switch + j
                self.node_to_router_map[node_id] = (edge_switches[i], j)

    def get_router(self, router_id: any) -> Router:
        return self.routers.get(router_id)

    def __repr__(self) -> str:
        return f"Network(Topology: {self.config.get('topology', 'mesh')})"