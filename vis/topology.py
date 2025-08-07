# ai_gpu_grid_sim/vis/topology.py

import yaml
import networkx as nx
import matplotlib.pyplot as plt
import math

def visualize_topology():
    """
    Reads the config, builds a graph of the 2D Mesh topology,
    and visualizes it using NetworkX and Matplotlib.
    """
    # Load configuration to get network size
    with open('../config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    num_nodes = config.get('num_gpus', 16)
    
    if not math.sqrt(num_nodes).is_integer():
        print(f"Error: num_gpus ({num_nodes}) must be a perfect square.")
        return

    grid_dim = int(math.sqrt(num_nodes))
    print(f"Visualizing a {grid_dim}x{grid_dim} mesh topology...")

    # Create a NetworkX graph
    G = nx.Graph()
    
    # Node positions for a clean grid layout
    pos = {}

    # Add nodes and define their positions
    for y in range(grid_dim):
        for x in range(grid_dim):
            node_id = y * grid_dim + x
            G.add_node(node_id)
            # Position nodes in a grid, inverting y-axis for matrix-like layout
            pos[node_id] = (x, -y)
    
    # Add edges to connect nodes in a mesh
    for y in range(grid_dim):
        for x in range(grid_dim):
            node_id = y * grid_dim + x
            # Connect to the node to the right
            if x < grid_dim - 1:
                right_neighbor_id = y * grid_dim + (x + 1)
                G.add_edge(node_id, right_neighbor_id)
            # Connect to the node below
            if y < grid_dim - 1:
                bottom_neighbor_id = (y + 1) * grid_dim + x
                G.add_edge(node_id, bottom_neighbor_id)
                
    # --- Drawing the graph ---
    plt.figure(figsize=(8, 8))
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color='skyblue',
        node_size=1000,
        edge_color='gray',
        font_size=10,
        font_weight='bold'
    )
    plt.title(f'{grid_dim}x{grid_dim} Mesh Topology')
    
    output_filename = 'network_topology.png'
    plt.savefig(output_filename)
    print(f"Topology graph saved to {output_filename}")
    plt.show()


if __name__ == "__main__":
    visualize_topology()