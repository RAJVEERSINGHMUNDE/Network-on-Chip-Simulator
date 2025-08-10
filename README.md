# [cite_start]Hybrid Network-on-Chip Simulator for AI/ML Acceleration [cite: 1]

[cite_start]This project provides a custom, cycle-accurate simulator built in Python to explore and analyze Network-on-Chip (NoC) architectures for AI and Machine Learning accelerators[cite: 110]. [cite_start]The primary goal is to move beyond standard monolithic topologies [cite: 3] and investigate the performance of application-aware hybrid network designs.

## Features

The simulator supports a wide range of configurable components to allow for detailed architectural exploration:

* [cite_start]**Network Topologies** [cite: 48]
    * [cite_start]**Monolithic:** 2D Mesh, 2D Torus, and Fat-Tree. [cite: 48]
    * [cite_start]**Hybrid Electrical:** A dual-network fabric composed of a primary 2D Mesh and a secondary Fat-Tree network. [cite: 48, 59, 60, 61]
* [cite_start]**Routing Algorithms** [cite: 48]
    * [cite_start]**Deterministic:** Dimension-ordered XY routing for grid topologies and standard up/down routing for Fat-Trees. [cite: 48]
    * [cite_start]**Adaptive:** Congestion-aware routing that selects paths based on network buffer fullness. [cite: 48]
* [cite_start]**Traffic Patterns** [cite: 48]
    * [cite_start]**Synthetic:** Uniform Random and Hotspot patterns for general performance analysis. [cite: 48]
    * [cite_start]**Workload-Driven:** An "All-Reduce Workload" designed to emulate communication traces from real deep learning applications. [cite: 5, 48]
* **Congestion Management**
    * [cite_start]**Virtual Channels (VCs):** Implemented to help manage router contention and improve network throughput. [cite: 57]

## Project Structure

The simulator is organized into several key modules: