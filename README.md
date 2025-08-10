# Project Abstract: A Multi-Stage Approach to Designing a Hybrid Network-on-Chip

### 1. Project Methodology

Our project follows a structured three-stage approach to design, test, and implement a Network-on-Chip (NoC) architecture for AI accelerators.

* **Stage 1: High-Level Python Simulation (Partially Completed)**
    [cite_start]We developed a custom "cycle-accurate" simulator in Python to quickly model and explore different NoC architectures[cite: 10]. [cite_start]This tool, along with knowledge from technical literature, allowed us to test ideas rapidly and led to our current hybrid design[cite: 12].

* **Stage 2: Performance Testing with gem5 (Future Work)**
    [cite_start]The next stage is to model our finalized Python architecture in gem5[cite: 13]. [cite_start]This will help validate our performance results in a realistic environment with full system components like CPU/GPU cores and memory controllers[cite: 14, 15].

* **Stage 3: RTL Implementation in Verilog (Future Work)**
    [cite_start]The final stage is to implement the validated architecture in SystemVerilog to produce a synthesizable hardware design[cite: 16, 17].

### 2. Python Simulator Design

[cite_start]Our Python simulator is built with three primary configurable components[cite: 48]:

* **Topologies:** We have implemented standard monolithic topologies including 2D Mesh, 2D Torus, and Fat-Tree. [cite_start]Based on our findings, we also implemented a hybrid architecture composed of two parallel electrical networks[cite: 48, 59].
* [cite_start]**Routing Algorithms:** The simulator supports both deterministic (XY-dimension ordered) and adaptive routing, where paths are chosen based on network congestion[cite: 48].
* **Traffic Patterns:** We can simulate generic traffic like uniform random and hotspot patterns. [cite_start]We also created an "All-Reduce Workload" to better emulate communication traces from real deep learning applications[cite: 5, 48].

[cite_start]To help with network congestion, we also implemented virtual channels[cite: 57].

### 3. Performance Analysis and Architectural Evolution

The decision to build a hybrid architecture was driven by performance data from our simulator.

* [cite_start]**Monolithic Architectures:** Our tests showed that while a 2D Mesh has excellent low latency for localized traffic (≈30 cycles), its limited bisection bandwidth makes it inefficient for large-scale collective operations like All-Reduce[cite: 49]. [cite_start]Conversely, our Fat-Tree implementation consistently showed very high baseline latency (400-700 cycles)[cite: 53, 54]. [cite_start]We also briefly explored and then abandoned flattened butterfly and dragonfly architectures after literature review suggested they were less relevant to our specific AI workload goals[cite: 56].

* [cite_start]**The Hybrid Solution:** The limitations of monolithic topologies led us to explore an application-aware hybrid architecture[cite: 58]. [cite_start]We modified the simulator to run two distinct electrical networks in parallel[cite: 59]:
    1.  [cite_start]A **Primary 2D Mesh Network** for default, point-to-point traffic[cite: 60].
    2.  [cite_start]A **Secondary Fat-Tree Network** to act as a dedicated "expressway" for the bandwidth-heavy All-Reduce workload[cite: 61].

    [cite_start]As shown in the graph below, this hybrid approach yields a highly predictable, low latency for the All-Reduce workload, as the traffic is offloaded to a dedicated network[cite: 81].

    ![Hybrid All-Reduce Performance Graph](https://googleusercontent.com/file_content/5)

### 4. Future Work and Focus

[cite_start]Our primary focus is to use the simulator to fully characterize the performance of this hybrid electrical architecture[cite: 98]. [cite_start]We aim to measure the benefits of offloading collective traffic and analyze the trade-offs between network performance, router buffer sizing, and complexity[cite: 99].

[cite_start]A key part of the future gem5 and RTL stages will be to integrate our NoC with industry-standard on-chip protocols, as we have not yet focused on the complexity they may add[cite: 6, 107]. [cite_start]The router designs will later be adapted to support protocols like AMBA AXI4 or the AMBA Coherent Hub Interface (CHI)[cite: 108].

### 5. Scope and Current Limitations

[cite_start]This initial project phase was focused on high-level architectural exploration in Python[cite: 110]. [cite_start]This strategic choice has several implications for the project's current state[cite: 111].

* [cite_start]**Rationale for Python over SystemC:** We deliberately chose not to use SystemC at this stage to prioritize rapid design iteration and architectural agility[cite: 103, 104, 112]. [cite_start]The ability to quickly prototype in Python was essential to our discovery of the hybrid model[cite: 113]. [cite_start]However, this means our current model does not have the detailed transaction-level modeling (TLM) that SystemC provides[cite: 105, 114].

* [cite_start]**Simulator Validation Status:** The simulator is still in active development and is not yet fully validated against known benchmarks[cite: 116]. [cite_start]Recent results for the All-Reduce workload produced counter-intuitive performance curves that required significant effort to fix[cite: 117]. [cite_start]The performance of the Fat-Tree topology, in particular, requires further tuning and investigation[cite: 119].