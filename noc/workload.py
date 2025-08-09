# ai_gpu_grid_sim/noc/workload.py

import random
from .node import Node
from .packet import Packet, PacketType, FlitType
from metrics.tracker import MetricsTracker

class AllReduceWorkload:
    """
    Manages the simulation of a Ring All-Reduce communication collective.
    This pattern consists of two phases:
    1. Scatter-Reduce: Each node sums a chunk of data from its peers. After N-1 steps,
       each node holds one fully reduced chunk.
    2. All-Gather: Each node sends its fully reduced chunk to all other nodes. After
       N-1 steps, all nodes have a complete, final copy of all data.
    """
    def __init__(self, config: dict, tracker: MetricsTracker, nodes: list[Node]):
        self.config = config
        self.tracker = tracker
        self.nodes = nodes
        self.num_nodes = len(nodes)
        
        # Workload parameters
        self.data_size = config['workload']['all_reduce_data_size']
        self.chunk_size_flits = config['workload']['all_reduce_chunk_size_flits']

        # State tracking for each node
        self.node_states = [{'phase': 'IDLE', 'step': 0, 'received_mask': 0} for _ in range(self.num_nodes)]

    def initialize(self, start_cycle: int):
        """Kicks off the All-Reduce operation by starting the Scatter-Reduce phase."""
        print(f"[{start_cycle}] WORKLOAD: Starting Ring All-Reduce for {self.num_nodes} nodes.")
        for i in range(self.num_nodes):
            self.node_states[i]['phase'] = 'SCATTER_REDUCE'
            self._send_next_packet(i, start_cycle)

    def on_packet_received(self, node_id: int, src_id: int, current_cycle: int):
        """Callback triggered by the simulator when a node receives a TAIL flit."""
        state = self.node_states[node_id]
        if state['phase'] == 'IDLE':
            return

        # Advance the state and send the next packet in the sequence
        state['step'] += 1
        self._send_next_packet(node_id, current_cycle)

        # Check for phase transition
        if state['phase'] == 'SCATTER_REDUCE' and state['step'] == self.num_nodes - 1:
            state['phase'] = 'ALL_GATHER'
            state['step'] = 0
            self._send_next_packet(node_id, current_cycle)
            print(f"[{current_cycle}] WORKLOAD: Node {node_id} completed Scatter-Reduce.")

        elif state['phase'] == 'ALL_GATHER' and state['step'] == self.num_nodes - 1:
            state['phase'] = 'IDLE' # This node is done
            print(f"[{current_cycle}] WORKLOAD: Node {node_id} completed All-Reduce.")


    def _send_next_packet(self, node_id: int, current_cycle: int):
        """Instructs a node to create and inject the correct packet for its current state."""
        state = self.node_states[node_id]
        if state['phase'] == 'IDLE' or state['step'] >= self.num_nodes - 1:
            return

        # Determine destination based on the ring
        dest_id = (node_id + 1) % self.num_nodes
        
        # Inject the packet via the node's injection method
        self.nodes[node_id].inject_workload_packet(
            dest_id=dest_id,
            packet_size_flits=self.chunk_size_flits,
            current_cycle=current_cycle,
            # Use a unique transaction ID to represent the workload step
            transaction_id=(node_id << 16) | (state['phase'] == 'ALL_GATHER') << 8 | state['step']
        )