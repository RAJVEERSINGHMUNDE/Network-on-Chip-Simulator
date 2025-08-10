# Project Abstract: A Multi-Stage Approach to Designing a Hybrid Network-on-Chip

### 1. Project Methodology

Our project follows a structured three-stage approach to design, test, and implement a Network-on-Chip (NoC) architecture for AI accelerators.

* **Stage 1: High-Level Python Simulation (Partially Completed)**
    We developed a custom "cycle-accurate" simulator in Python to quickly model and explore different NoC architectures. This tool, along with knowledge from technical literature, allowed us to test ideas rapidly and led to our current hybrid design.

* **Stage 2: Performance Testing with gem5 (Future Work)**
    The next stage is to model our finalized Python architecture in gem5. This will help validate our performance results in a realistic environment with full system components like CPU/GPU cores and memory controllers.

* **Stage 3: RTL Implementation in Verilog (Future Work)**
    The final stage is to implement the validated architecture in SystemVerilog to produce a synthesizable hardware design.

### 2. Python Simulator Design

Our Python simulator is built with three primary configurable components:

* **Topologies:** We have implemented standard monolithic topologies including 2D Mesh, 2D Torus, and Fat-Tree. Based on our findings, we also implemented a hybrid architecture composed of two parallel electrical networks.
* **Routing Algorithms:** The simulator supports both deterministic (XY-dimension ordered) and adaptive routing, where paths are chosen based on network congestion.
* **Traffic Patterns:** We can simulate generic traffic like uniform random and hotspot patterns. We also created an "All-Reduce Workload" to better emulate communication traces from real deep learning applications.

To help with network congestion, we also implemented virtual channels.

### 3. Performance Analysis and Architectural Evolution

The decision to build a hybrid architecture was driven by performance data from our simulator.

* **Monolithic Architectures:** Our tests showed that while a 2D Mesh has excellent low latency for localized traffic (≈30 cycles), its limited bisection bandwidth makes it inefficient for large-scale collective operations like All-Reduce. Conversely, our Fat-Tree implementation consistently showed very high baseline latency (400-700 cycles). We also briefly explored and then abandoned flattened butterfly and dragonfly architectures after literature review suggested they were less relevant to our specific AI workload goals.

* **The Hybrid Solution:** The limitations of monolithic topologies led us to explore an application-aware hybrid architecture. We modified the simulator to run two distinct electrical networks in parallel:
    1.  A **Primary 2D Mesh Network** for default, point-to-point traffic.
    2.  A **Secondary Fat-Tree Network** to act as a dedicated "expressway" for the bandwidth-heavy All-Reduce workload.

### 4. Future Work and Focus

Our primary focus is to use the simulator to fully characterize the performance of this hybrid electrical architecture. We aim to measure the benefits of offloading collective traffic and analyze the trade-offs between network performance, router buffer sizing, and complexity.

A key part of the future gem5 and RTL stages will be to integrate our NoC with industry-standard on-chip protocols, as we have not yet focused on the complexity they may add. The router designs will later be adapted to support protocols like AMBA AXI4 or the AMBA Coherent Hub Interface (CHI).

### 5. Scope and Current Limitations

This initial project phase was focused on high-level architectural exploration in Python. This strategic choice has several implications for the project's current state.

* **Rationale for Python over SystemC:** We deliberately chose not to use SystemC at this stage to prioritize rapid design iteration and architectural agility. The ability to quickly prototype in Python was essential to our discovery of the hybrid model. However, this means our current model does not have the detailed transaction-level modeling (TLM) that SystemC provides.

* **Simulator Validation Status:** The simulator is still in an active development phase and is not yet fully validated against known benchmarks. The performance of the Fat-Tree topology, in particular, requires further tuning and investigation.