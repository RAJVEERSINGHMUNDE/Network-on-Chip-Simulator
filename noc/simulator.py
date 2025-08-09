# noc/simulator.py

import math
from .network import Network
from .node import Node
from .router import Router, Port
from metrics.tracker import MetricsTracker
# Import the workload manager
from .workload import AllReduceWorkload

class Simulator:
    """
    The main simulation engine. It initializes the system and runs the
    cycle-by-cycle simulation of the Network-on-Chip.
    """
    def __init__(self, config: dict):
        """
        Initializes the simulator with the given configuration dictionary.
        """
        print("Initializing simulator...")
        self.config = config
        self.num_gpus = config['num_gpus']
        
        self.network = Network(config=config)
        self.tracker = MetricsTracker()
        
        # Create the nodes first, as they are needed by the workload manager
        self.nodes: list[Node] = []
        for i in range(self.num_gpus):
            coords = None
            if self.network.grid_width is not None:
                 coords = (i % self.network.grid_width, i // self.network.grid_width)
            node = Node(node_id=i, coords=coords, config=self.config, tracker=self.tracker)
            self.nodes.append(node)
        
        # This map is provided by the network object after it's created
        self.node_to_router_map = self.network.node_to_router_map

        # Create the reverse map for easy lookup during ejection
        self.router_port_to_node_map: dict[tuple[Router, Port], int] = \
            {val: key for key, val in self.node_to_router_map.items()}
            
        # --- FIX: Initialize the workload manager LAST ---
        # This ensures self.config, self.tracker, and self.nodes are all available.
        self.workload = None
        if self.config.get('traffic_pattern') == 'all_reduce':
            self.workload = AllReduceWorkload(self.config, self.tracker, self.nodes)
            
        self.current_cycle = 0

    def _single_cycle(self):
        """Executes all the logic for a single clock cycle."""
        # 1. Routers decide where to forward flits from their input buffers
        forwarding_decisions = {}
        for router in self.network.routers.values():
            forwarding_decisions[router] = router.process_cycle()

        # 2. Move flits between routers based on forwarding decisions
        for router, decisions in forwarding_decisions.items():
            for out_port, flit in decisions.items():
                if (router, out_port) in self.router_port_to_node_map:
                    continue
                dest_router, dest_in_port = self.network.connections[router][out_port]
                dest_router.input_buffers[dest_in_port][flit.vc_id].append(flit)

        # 3. Move flits from Nodes to Routers (Injection)
        for node in self.nodes:
            if node.injection_queue:
                flit_to_inject = node.injection_queue.popleft()
                router, port_on_router = self.node_to_router_map[node.node_id]
                router.input_buffers[port_on_router][flit_to_inject.vc_id].append(flit_to_inject)

        # 4. Move flits from Routers to Nodes (Ejection) & Notify Workload
        for router, decisions in forwarding_decisions.items():
            for out_port, ejected_flit in decisions.items():
                if (router, out_port) in self.router_port_to_node_map:
                    dest_node_id = self.router_port_to_node_map[(router, out_port)]
                    dest_node = self.nodes[dest_node_id]
                    packet_info = dest_node.receive_flit(ejected_flit, self.current_cycle)

                    # If a workload is active and a full packet was received, notify it.
                    if self.workload and packet_info:
                        self.workload.on_packet_received(
                            node_id=packet_info['dest_address'],
                            src_id=packet_info['src_address'],
                            current_cycle=self.current_cycle
                        )

        # 5. Nodes generate new traffic for the *next* cycle (if not using a workload)
        if not self.workload:
            for node in self.nodes:
                node.process_cycle(self.current_cycle)
            
        self.current_cycle += 1

    def run(self, num_cycles: int):
        """Runs the simulation for a specified number of cycles."""
        print(f"Running simulation for {num_cycles} cycles...")
        
        # If a workload is present, initialize it at the start of the simulation.
        if self.workload:
            self.workload.initialize(self.current_cycle)

        for i in range(num_cycles):
            if i % 100 == 0 and i > 0:
                print(f"--- Cycle {i} ---")
            self._single_cycle()
            
        print(f"--- Cycle {self.current_cycle} ---")
        print("Simulation finished.")