from .node import Node

class AllReduceWorkload:

    def __init__(self, config: dict, tracker, nodes: list[Node]):
        self.config = config
        self.tracker = tracker
        self.nodes = nodes
        self.num_nodes = len(nodes)
        
        self.data_size = config.get('workload', {}).get('all_reduce_data_size', 1)
        self.chunk_size_flits = config.get('workload', {}).get('all_reduce_chunk_size_flits', 4)

        self.node_states = [{'phase': 'IDLE', 'step': 0, 'chunk_idx': 0} for _ in range(self.num_nodes)]

    def initialize(self, start_cycle: int):

        print(f"[{start_cycle}] WORKLOAD: Starting Ring All-Reduce for {self.num_nodes} nodes, {self.data_size} chunks.")
        if self.data_size <= 0:
            for i in range(self.num_nodes):
                self.node_states[i]['phase'] = 'IDLE'
            return
            
        for i in range(self.num_nodes):
            self.node_states[i]['phase'] = 'SCATTER_REDUCE'
            self._send_next_packet(i, start_cycle)


    def is_complete(self) -> bool:
        for state in self.node_states:
            if state['phase'] != 'IDLE':
                return False
        return True

    def on_packet_received(self, node_id: int, src_id: int, current_cycle: int):
        state = self.node_states[node_id]
        if state['phase'] == 'IDLE':
            return

        current_phase = state['phase']
        is_phase_complete = state['step'] == self.num_nodes - 2

        if current_phase == 'SCATTER_REDUCE' and is_phase_complete:
            state['phase'] = 'ALL_GATHER'
            state['step'] = 0
        elif current_phase == 'ALL_GATHER' and is_phase_complete:
            state['chunk_idx'] += 1
            if state['chunk_idx'] >= self.data_size:
                state['phase'] = 'IDLE' 
            else:
                state['phase'] = 'SCATTER_REDUCE'
                state['step'] = 0
        else:
            state['step'] += 1
        
        self._send_next_packet(node_id, current_cycle)

    def _send_next_packet(self, node_id: int, current_cycle: int):
        state = self.node_states[node_id]
        if state['phase'] == 'IDLE':
            return

        dest_id = (node_id + 1) % self.num_nodes
        
        self.nodes[node_id].inject_workload_packet(
            dest_id=dest_id,
            packet_size_flits=self.chunk_size_flits,
            current_cycle=current_cycle,
            transaction_id=(node_id << 20) | (state['chunk_idx'] << 12) | (state['phase'] == 'ALL_GATHER') << 8 | state['step']
        )