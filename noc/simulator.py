# ai_gpu_grid_sim/noc/simulator.py (Corrected)

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
        for i in range(self.num_gpus):
            y = i // self.network.grid_width
            x = i % self.network.grid_width
            node = Node(
                node_id=i,
                coords=(x, y),
                config=self.config,
                tracker=self.tracker
            )
            self.nodes.append(node)
        
        self.node_router_map: dict[Node, Router] = {}
        for i, node in enumerate(self.nodes):
            y = i // self.network.grid_width
            x = i % self.network.grid_width
            
            # --- THIS IS THE FIX ---
            # Pass the coordinates as a single tuple to match the method definition
            self.node_router_map[node] = self.network.get_router((x, y))
            
        self.current_cycle = 0

    def _single_cycle(self):
        """Executes all the logic for a single clock cycle."""
        forwarding_decisions = {}
        for router in self.network.routers.values():
            forwarding_decisions[router] = router.process_cycle()

        for router, decisions in forwarding_decisions.items():
            for out_port, flit in decisions.items():
                if out_port == Port.LOCAL:
                    continue
                
                dest_router, dest_in_port = self.network.connections[router][out_port]
                dest_router.input_buffers[dest_in_port][flit.vc_id].append(flit)

        for node, router in self.node_router_map.items():
            if node.injection_queue:
                flit_to_inject = node.injection_queue.popleft()
                router.input_buffers[Port.LOCAL][flit_to_inject.vc_id].append(flit_to_inject)

        for node, router in self.node_router_map.items():
            if Port.LOCAL in forwarding_decisions[router]:
                ejected_flit = forwarding_decisions[router][Port.LOCAL]
                node.receive_flit(ejected_flit, self.current_cycle)

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