# ai_gpu_grid_sim/noc/simulator.py (Consolidated Fix)

import math
from .network import Network
from .node import Node
from .router import Router, Port
from metrics.tracker import MetricsTracker

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
        
        self.nodes: list[Node] = []
        # Create nodes, assigning coordinates only if it's a grid topology
        for i in range(self.num_gpus):
            coords = None
            if self.network.grid_width is not None:
                 coords = (i % self.network.grid_width, i // self.network.grid_width)
            node = Node(node_id=i, coords=coords, config=self.config, tracker=self.tracker)
            self.nodes.append(node)
        
        # The Network class is responsible for creating the node-to-router map for ALL topologies.
        # The simulator simply uses the map provided by the network.
        self.node_to_router_map = self.network.node_to_router_map

        # Create the reverse map for easy lookup during ejection
        self.router_port_to_node_map: dict[tuple[Router, Port], int] = \
            {val: key for key, val in self.node_to_router_map.items()}
            
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
                # If the destination is a node (ejection), skip the router-to-router transfer
                if (router, out_port) in self.router_port_to_node_map:
                    continue
                
                # Otherwise, find the destination router and move the flit
                dest_router, dest_in_port = self.network.connections[router][out_port]
                dest_router.input_buffers[dest_in_port][flit.vc_id].append(flit)

        # 3. Move flits from Nodes to Routers (Injection)
        # Iterate over the master list of node objects to ensure correctness
        for node in self.nodes:
            if node.injection_queue:
                flit_to_inject = node.injection_queue.popleft()
                # Look up the connection using the node's ID
                router, port_on_router = self.node_to_router_map[node.node_id]
                # Place the flit into the correct input buffer and VC on the router
                router.input_buffers[port_on_router][flit_to_inject.vc_id].append(flit_to_inject)

        # 4. Move flits from Routers to Nodes (Ejection)
        for router, decisions in forwarding_decisions.items():
            for out_port, ejected_flit in decisions.items():
                # Check if the destination is a node
                if (router, out_port) in self.router_port_to_node_map:
                    dest_node_id = self.router_port_to_node_map[(router, out_port)]
                    self.nodes[dest_node_id].receive_flit(ejected_flit, self.current_cycle)

        # 5. Nodes generate new traffic for the *next* cycle
        for node in self.nodes:
            node.process_cycle(self.current_cycle)
            
        self.current_cycle += 1

    def run(self, num_cycles: int):
        """Runs the simulation for a specified number of cycles."""
        print(f"Running simulation for {num_cycles} cycles...")
        for i in range(num_cycles):
            if i % 100 == 0 and i > 0:
                print(f"--- Cycle {i} ---")
            self._single_cycle()
        print(f"--- Cycle {self.current_cycle} ---")
        print("Simulation finished.")