# noc/simulator.py

from .network import Network
from .node import Node
from .router import Router
from metrics.tracker import MetricsTracker
from .workload import AllReduceWorkload

class Simulator:
    def __init__(self, config: dict):
        print("Initializing simulator...")
        self.config = config
        self.architecture = config.get('architecture', 'monolithic')
        self.num_gpus = config['num_gpus']
        self.tracker = MetricsTracker()

        self.primary_network: Network | None = None
        self.secondary_network: Network | None = None

        if self.architecture == 'hybrid_electrical':
            primary_topo = self.config.get('topology', 'mesh')
            secondary_topo = self.config['hybrid_electrical_config']['secondary_topology']
            self.primary_network = Network(config, topology_override=primary_topo)
            self.secondary_network = Network(config, topology_override=secondary_topo)
        else:
            self.primary_network = Network(config)

        self.nodes: list[Node] = []
        for i in range(self.num_gpus):
            coords = None
            if self.primary_network and self.primary_network.grid_width is not None:
                coords = (i % self.primary_network.grid_width, i // self.primary_network.grid_width)
            node = Node(node_id=i, coords=coords, config=self.config, tracker=self.tracker)
            self.nodes.append(node)

        self.workload = None
        if self.config.get('traffic_pattern') == 'all_reduce':
            self.workload = AllReduceWorkload(self.config, self.tracker, self.nodes)
        
        self.current_cycle = 0
    
    def run(self, num_cycles: int):
        """
        Runs the simulation.
        - If a workload is present, it runs until the workload is complete.
        - Otherwise, it runs for the fixed number of cycles specified.
        """
        # --- START: MODIFIED RUN LOGIC ---
        if self.workload:
            print("Running workload-driven simulation until completion...")
            self.workload.initialize(self.current_cycle)

            # Safety break to prevent infinite loops in case of a bug
            timeout_cycles = self.config.get('simulation_timeout_cycles', 500000)

            while not self.workload.is_complete():
                self._single_cycle()
                if self.current_cycle > timeout_cycles:
                    print(f"ERROR: Simulation timed out after {timeout_cycles} cycles. Possible deadlock or bug.")
                    break
        else:
            # Original behavior for synthetic traffic
            print(f"Running simulation for {num_cycles} cycles...")
            for i in range(num_cycles):
                if i % 500 == 0 and i > 0:
                    print(f"--- Cycle {i} ---")
                self._single_cycle()
        
        print(f"--- Simulation finished at cycle {self.current_cycle} ---")
        # --- END: MODIFIED RUN LOGIC ---


    def _process_network_cycle(self, network: Network | None):
        """Helper function to run one cycle for a given network instance."""
        if not network: return

        forwarding_decisions = {r: r.process_cycle() for r in network.routers.values()}

        for router, decisions in forwarding_decisions.items():
            for out_port, flit in decisions.items():
                if (router, out_port) in network.router_port_to_node_map:
                    continue
                dest_router, dest_in_port = network.connections[router][out_port]
                dest_router.input_buffers[dest_in_port][flit.vc_id].append(flit)

        for router, decisions in forwarding_decisions.items():
            for out_port, ejected_flit in decisions.items():
                if (router, out_port) in network.router_port_to_node_map:
                    dest_node_id = network.router_port_to_node_map[(router, out_port)]
                    packet_info = self.nodes[dest_node_id].receive_flit(ejected_flit, self.current_cycle)
                    if self.workload and packet_info:
                        self.workload.on_packet_received(
                            node_id=packet_info['dest_address'],
                            src_id=packet_info['src_address'],
                            current_cycle=self.current_cycle
                        )

    def _single_cycle(self):
        # 1. Process a full cycle for EACH network
        self._process_network_cycle(self.primary_network)
        self._process_network_cycle(self.secondary_network)

        # 2. Inject flits from Nodes into the correct network
        for node in self.nodes:
            if node.injection_queue:
                flit_to_inject = node.injection_queue[0]

                if flit_to_inject.use_secondary_network and self.secondary_network:
                    flit = node.injection_queue.popleft()
                    router, port = self.secondary_network.node_to_router_map[node.node_id]
                    router.input_buffers[port][flit.vc_id].append(flit)
                else:
                    flit = node.injection_queue.popleft()
                    router, port = self.primary_network.node_to_router_map[node.node_id]
                    router.input_buffers[port][flit.vc_id].append(flit)

        # 3. Nodes generate new traffic for the *next* cycle
        if not self.workload:
            for node in self.nodes:
                node.process_cycle(self.current_cycle)

        self.current_cycle += 1

    def run(self, num_cycles: int):
        print(f"Running simulation for {num_cycles} cycles...")
        if self.workload:
            self.workload.initialize(self.current_cycle)
        for i in range(num_cycles):
            if i % 500 == 0 and i > 0:
                print(f"--- Cycle {i} ---")
            self._single_cycle()
        print(f"--- Cycle {self.current_cycle} ---")
        print("Simulation finished.")