# AI GPU Grid: A Scalable NoC Simulator

## 1\. Project Overview

This project provides a Python-based functional simulator for a scalable Network-on-Chip (NoC) designed to interconnect a grid of GPUs. The primary goal is to explore architectural and protocol-level innovations for GPU-to-GPU communication. The simulator is designed to be parameterizable and scalable, allowing for the analysis of key performance metrics like latency and bandwidth under various synthetic workloads.

## 2\. Key Architectural Choices

The simulator implements a set of foundational architectural choices designed for high performance and effective modeling.

  * **Protocol:** AXI/CHI-like packet-based communication. The simulator abstracts high-level memory transactions into packets that are injected into the NoC for transmission.
  * **Topology:** A 2D Mesh. This topology was chosen for its simple, regular structure and ease of scalability. Each router connects to four neighbors (North, East, South, West) and one local processing node (GPU).
  * **Flow Control:** Wormhole Switching with Virtual Channels (VCs). Packets are broken into smaller flits. To improve performance and mitigate Head-of-Line (HoL) blocking, each physical input port is equipped with multiple virtual channels, allowing separate packet flows to bypass each other.
  * **Routing Algorithm:** The simulator supports multiple routing strategies:
      * **Deterministic XY Routing:** A simple, deadlock-free algorithm where packets are routed fully in the X-dimension before being routed in the Y-dimension.
      * **Adaptive Routing:** A dynamic, load-aware algorithm where routers check the buffer occupancy of their neighbors to avoid sending traffic toward congested hotspots, providing a more balanced network load.

## 3\. Project Structure

The project is organized into a modular structure to separate concerns between the NoC components, simulation engine, and analysis tools.

```
ai_gpu_grid_sim/
├── config.yaml          # Simulation parameters
├── main.py              # Main entry point to run the simulation
├── noc/
│   ├── packet.py        # Defines Packet and Flit data structures
│   ├── router.py        # Implements the Router logic with VC and adaptive routing
│   ├── network.py       # Builds the 2D Mesh topology of routers
│   ├── node.py          # Models the GPU node and traffic generation
│   └── simulator.py     # The main simulation engine that orchestrates the components
├── metrics/
│   └── tracker.py       # Collects and calculates performance metrics
└── vis/
    ├── stats_plot.py    # Generates latency vs. injection rate plots
    └── topology.py      # Visualizes the network topology using NetworkX
```

## 4\. Code Implementation Details

### `noc/router.py`

This is the most critical module, containing the logic for a single router. It is designed to be highly flexible.

  * **VC-aware Buffers**: The router's input ports are structured as a list of independent virtual channel buffers (`deque` objects), allowing for parallel packet flows through a single physical port.
  * **Dual-Mode Routing**: The `process_cycle` method can operate in one of two modes based on the configuration:
    1.  **XY Mode**: It uses simple, deterministic XY logic to compute the output port for a flit.
    2.  **Adaptive Mode**: It computes a set of all productive paths and queries the buffer fullness of the downstream neighbors for each path. It then selects the path leading to the least congested neighbor, dynamically routing around traffic hotspots.
  * **Fair Arbitration**: A round-robin arbiter is used to ensure that all virtual channels get a fair chance to access an output port, preventing starvation.

### `noc/node.py`

This module models the GPU node that generates and consumes traffic.

  * **Traffic Generation**: The `_generate_traffic` method creates packets based on the configured `injection_rate`.
  * **Pattern-based Destinations**: A helper method, `_get_destination`, implements various traffic patterns (`uniform_random`, `transpose`, `hotspot`) by selecting a destination address according to the pattern's logic.
  * **Packetization**: The `_packetize` method breaks a logical `Packet` into a sequence of `Flit`s and assigns the entire packet to a single virtual channel for its journey through the network.

## 5\. How to Run the Simulator

1.  **Installation**: Ensure you have Python and the required libraries installed.

    ```bash
    pip install PyYAML numpy matplotlib networkx
    ```

2.  **Configuration**: Edit the `config.yaml` file to set your desired parameters.

      * `num_gpus`: Number of nodes (must be a perfect square).
      * `traffic_pattern`: `uniform_random`, `transpose`, or `hotspot`.
      * `injection_rate`: Probability (0.0 to 1.0) of a node generating a packet each cycle.
      * `routing_algo`: `XY` or `adaptive`.
      * `num_virtual_channels`: Number of VCs per port (e.g., 4).
      * `simulation_cycles`: The duration of the simulation.

3.  **Execution**: Run the main script from your terminal.

    ```bash
    python main.py
    ```

4.  **Visualization**: To generate plots, navigate to the `vis` directory and run the scripts.

    ```bash
    cd vis
    python stats_plot.py
    python topology.py
    ```

## 6\. Performance Analysis & Results

Performance testing under the stressful `transpose` traffic pattern clearly demonstrates the value of the architectural improvements.

1.  **Baseline (XY Routing, No VCs)**: The initial network saturated at a very low injection rate (\~0.09 packets/node/cycle). This was caused by severe Head-of-Line (HoL) blocking, where a single stalled packet could block an entire input buffer.

2.  **Improvement with Virtual Channels**: Introducing 4 VCs dramatically improved performance. By allowing packets to bypass each other, the network was able to handle a much higher traffic load, pushing the saturation point to an injection rate of \~0.12.

3.  **Final Architecture (VCs + Adaptive Routing)**: The final architecture provided the best performance. By combining the HoL-blocking mitigation of VCs with the load-balancing capability of adaptive routing, the network's efficiency was maximized. The adaptive algorithm successfully routed traffic around hotspots, further increasing the network's saturation threshold and lowering latency at high loads compared to the VC-only implementation.

## 7\. Future Work

This simulator provides a strong foundation for further research. Potential extensions include:

  * **Deeper Protocol Modeling**: Implement specific CHI messages to model cache coherence traffic.
  * **New Topologies**: Extend the `Network` class to support other interconnect topologies, such as Torus or Dragonfly.
  * **Power and Area Modeling**: Add simple energy models to estimate power consumption based on router activity (buffer reads/writes, crossbar traversals).
  * **Architectural and Topology Enhancements**:

    Implement a Hierarchical Network Model: The current flat mesh topology can be evolved into a two-level hierarchical network. This would involve simulating multiple NoC clusters (nodes) connected by a higher-level switched fabric, reflecting modern rack-scale designs.

    Model a Flattened Butterfly Topology: For the intra-node fabric, implement a Flattened Butterfly topology as proposed in the design. This would allow for a direct, quantitative comparison against the 2D Mesh to evaluate its superior performance-to-area ratio for GPU-specific "many-to-few" traffic patterns.

    Extend to 3D Topologies: To align with the industry trend of 3D integration, enhance the Network class to support 3D mesh configurations (e.g., 4x4x2). This would enable the modeling of vertically stacked chiplets and the analysis of reduced wire-length latency.

  * **Advanced Protocol Feature Modeling (AMBA 5 CHI)**:

    Implement Cache Stashing: Introduce a new transaction type that allows a node (e.g., a GPU) to push a cache line directly into another node's cache (e.g., a CPU's L3). This involves modifying the node and tracker logic to simulate this direct data transfer, bypassing main memory and reducing latency in producer-consumer workloads.

    Model Far Atomic Operations: Offload atomic operations (e.g., AtomicAdd) from the compute nodes to the interconnect itself. This can be modeled by creating specific atomic packet types that are handled at a designated "Home Node," reducing traffic for shared variables and synchronization primitives.

    Introduce Quality of Service (QoS): Add a QoS field to packets and update the router's arbitration logic to prioritize high-QoS traffic. This would allow for the analysis of how prioritizing latency-sensitive memory reads over bulk data transfers affects overall application performance in a congested network.

  * **Advanced Simulation and Verification**:

    Incorporate Realistic Application Workloads: Move beyond synthetic patterns by driving the simulator with real memory access traces. These traces can be collected from GPU applications like large-scale graph traversal algorithms or representative deep learning models to evaluate the interconnect under realistic, bursty, and data-dependent traffic.

    Integrate a Power Estimation Model: Enhance the MetricsTracker to include power analysis. By assigning an energy cost to fundamental operations (e.g., buffer read/write, crossbar traversal), the simulator can report on average power consumption and energy-per-bit, adding a critical metric to the PPA (Power, Performance, Area) analysis.

    Port to a Cycle-Accurate Simulator: For final validation, the architectural principles confirmed in this Python model can be ported to a cycle-accurate simulator like gem5. Leveraging gem5's native support for the AMBA 5 CHI protocol and detailed GPU models would allow for performance validation against a full software stack.

  * **Physical Layer Evolution**:

    Model a Co-Packaged Optics (CPO) Fabric: For the inter-node network, model a switched fabric that uses co-packaged optics. This would involve adjusting the link latency and power consumption parameters to reflect the significant advantages of optical signaling over electrical connections for rack-scale distances, future-proofing the design.