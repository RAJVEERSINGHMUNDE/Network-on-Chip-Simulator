# AI GPU Grid: A Scalable NoC Simulator

## 1\. Project Overview

This project provides a Python-based functional simulator for a scalable Network-on-Chip (NoC) designed to interconnect a grid of GPUs. [cite\_start]The primary goal is to explore architectural and protocol-level innovations for GPU-to-GPU communication[cite: 1]. [cite\_start]The simulator is designed to be parameterizable and scalable for up to 32 GPUs, allowing for the analysis of key performance metrics like latency and bandwidth under various synthetic workloads[cite: 1].

## 2\. Architectural Design

The simulator implements a set of foundational architectural choices designed for simplicity and effective performance modeling.

  * **Protocol:** AXI/CHI-like packet-based communication. The simulator abstracts transactions into packets that are injected into the NoC.
  * **Topology:** A 2D Mesh. [cite\_start]This topology was chosen for its simple, regular structure and ease of scalability[cite: 7]. [cite\_start]Each router connects to four neighbors (North, East, South, West) and one local processing node (GPU)[cite: 8].
  * **Routing Algorithm:** Deterministic XY Routing. [cite\_start]To prevent deadlock and simplify logic, packets are routed fully in the X-dimension before being routed in the Y-dimension[cite: 38].
  * **Flow Control:** Flit-level wormhole switching. Packets are broken down into smaller flits, which are the basic unit of transfer. [cite\_start]This allows for low-latency transmission and small router buffers[cite: 40].

## 3\. Project Structure

The project is organized into a modular structure to separate concerns between the NoC components, simulation engine, and metrics analysis.

```
ai_gpu_grid_sim/
├── config.yaml          # Simulation parameters
├── main.py              # Main entry point to run the simulation
├── noc/
│   ├── packet.py        # Defines Packet and Flit data structures
│   ├── router.py        # Implements the Router logic and XY routing
│   ├── network.py       # Builds the 2D Mesh topology of routers
│   ├── node.py          # Models the GPU node, traffic generation, and packetization
│   └── simulator.py     # The main simulation engine that orchestrates the components
├── metrics/
│   └── tracker.py       # Collects and calculates performance metrics
└── vis/
    ├── topology.py      # (Future) NetworkX visualizer
    └── stats_plot.py    # (Future) Matplotlib for plotting results
```

## 4\. Code Implementation Details

### `noc/packet.py`

This file defines the fundamental data structures for communication.

  * **`Packet`**: A `@dataclass` representing a complete message from a source to a destination. [cite\_start]It contains fields specified in the design, such as `src_address`, `dest_address`, and `data_payload`[cite: 18].
  * **`Flit`**: A `@dataclass` representing the smaller Flow Control unit. A `Packet` is broken into one or more `Flit`s.
  * **`FlitType`**: An `Enum` (`HEAD`, `BODY`, `TAIL`) used by flits to signal the start and end of a packet, which is essential for wormhole switching and packet reassembly.

### `noc/router.py`

This module contains the logic for a single router in the mesh.

  * **`Router` Class**:
      * **Initialization**: Each router is initialized with its `(x, y)` coordinates in the grid. It creates a dictionary of input buffers, one for each `Port` (`NORTH`, `EAST`, `SOUTH`, `WEST`, `LOCAL`). Each buffer is a `collections.deque` for efficient FIFO operations.
      * **Routing Logic (`_compute_route`)**: This method implements deterministic XY routing. It compares the flit's destination coordinates to its own. If the x-coordinates differ, it routes `EAST` or `WEST`. Only when the x-coordinates match does it route `NORTH` or `SOUTH`. If both match, it routes to the `LOCAL` port.
      * **Processing Cycle (`process_cycle`)**: This method models a simplified two-stage router pipeline:
        1.  **Route Calculation**: It inspects the head flit of every input buffer and computes its required output port.
        2.  **Arbitration**: It groups requests by the desired output port. For each output port, a simple arbiter selects one winning flit, which is then removed from its input buffer and staged for forwarding.

### `noc/network.py`

This module acts as a factory for building the network topology.

  * **`Network` Class**:
      * **Router Creation**: It calculates the grid dimensions from `num_gpus` and instantiates all the `Router` objects, storing them in a dictionary keyed by their `(x, y)` coordinates.
      * **Connection Mapping**: Its most critical function is to build `self.connections`, a lookup table that explicitly maps a router's output port to its neighbor's corresponding input port (e.g., `Router(0,0)`'s `EAST` port connects to `Router(1,0)`'s `WEST` port). This map is used by the simulator to move flits between routers.

### `noc/node.py`

This module models the GPU node that generates and consumes traffic.

  * **`Node` Class**:
      * **Packetization (`_packetize`)**: Breaks a `Packet` into a sequence of `Flit`s, correctly assigning `HEAD`, `BODY`, and `TAIL` types.
      * **Traffic Generation (`_generate_traffic`)**: In each cycle, based on the `injection_rate`, it decides whether to create a new packet. The packet's destination is determined by the `_get_destination` helper method.
      * **Destination Logic (`_get_destination`)**: This method implements the different traffic patterns based on the `traffic_pattern` from the config file (`uniform_random`, `transpose`, `hotspot`).

### `noc/simulator.py`

This is the orchestrator that drives the entire simulation.

  * **`Simulator` Class**:
      * **Initialization**: Creates the `Network`, the `MetricsTracker`, and all the `Node` objects, passing the necessary configuration to each.
      * **Main Loop (`run`)**: Iterates for the number of specified cycles, calling the `_single_cycle` method each time.
      * **Single Cycle Logic (`_single_cycle`)**: The order of operations is crucial for correct simulation:
        1.  **Routers Process**: All routers determine which flits to forward based on their state at the *start* of the cycle.
        2.  **Flits Move**: Flits are moved between routers and from nodes to routers based on the decisions made in the previous step.
        3.  **Nodes Generate**: Nodes create new packets that will be available for injection in the *next* cycle.

## 5\. How to Run the Simulator

1.  **Installation**: Ensure you have Python and the `PyYAML` library installed.

    ```bash
    pip install PyYAML
    ```

2.  **Configuration**: Edit the `config.yaml` file to set your desired parameters.

      * `num_gpus`: Number of nodes (must be a perfect square).
      * `traffic_pattern`: `uniform_random`, `transpose`, or `hotspot`.
      * `injection_rate`: Probability (0.0 to 1.0) of a node generating a packet each cycle. A higher rate means more network traffic.
      * `simulation_cycles`: The duration of the simulation.

3.  **Execution**: Run the main script from your terminal.

    ```bash
    python main.py
    ```

## 6\. Example Results & Analysis

The simulator can show how different traffic patterns affect network performance.

  * **Uniform Random (injection\_rate: 0.05)**
      * Average Packet Latency: \~11.28 cycles
  * **Transpose (injection\_rate: 0.05)**
      * Average Packet Latency: \~12.60 cycles

The higher latency in the transpose pattern is expected and demonstrates that the simulator correctly models the increased network contention caused by this more stressful traffic pattern.

## 7\. Future Work and Improvements

The current framework provides a strong foundation for further exploration. The next logical steps for improving the project are:

  * **Implement Virtual Channels (VCs)**: To mitigate head-of-line blocking and improve throughput.
  * **Develop Visualization Scripts**: To automatically plot latency vs. injection rate graphs using `matplotlib`.
  * **Add Adaptive Routing Algorithms**: To allow routers to dynamically route around congested areas.