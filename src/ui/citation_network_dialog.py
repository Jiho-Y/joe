"""
Citation Network Visualization Dialog.

Displays interactive citation network graph using NetworkX and Matplotlib.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict
import numpy as np


class CitationNetworkDialog(QDialog):
    """Citation network visualization dialog."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.graph = None
        self.papers_map = {}  # {paper_id: paper_data}

        self.init_ui()
        self.build_graph()
        self.draw_graph()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Citation Network")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)

        # Info label
        info_label = QLabel("Citation network shows relationships between papers")
        layout.addWidget(info_label)

        # Controls
        controls_layout = self.create_controls()
        layout.addLayout(controls_layout)

        # Matplotlib figure
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Statistics
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        # Buttons
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_network)

        export_btn = QPushButton("Export Graph...")
        export_btn.clicked.connect(self.export_graph)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_controls(self) -> QHBoxLayout:
        """Create control widgets."""
        layout = QHBoxLayout()

        # Layout algorithm
        layout_group = QGroupBox("Layout")
        layout_form = QFormLayout()

        self.layout_combo = QComboBox()
        self.layout_combo.addItems([
            "Spring (Force-directed)",
            "Circular",
            "Hierarchical",
            "Kamada-Kawai",
            "Shell"
        ])
        self.layout_combo.currentTextChanged.connect(self.on_layout_changed)
        layout_form.addRow("Algorithm:", self.layout_combo)

        layout_group.setLayout(layout_form)
        layout.addWidget(layout_group)

        # Display options
        display_group = QGroupBox("Display")
        display_form = QFormLayout()

        self.show_labels_check = QCheckBox("Show labels")
        self.show_labels_check.setChecked(True)
        self.show_labels_check.stateChanged.connect(self.on_display_changed)
        display_form.addRow("", self.show_labels_check)

        self.show_arrows_check = QCheckBox("Show arrows")
        self.show_arrows_check.setChecked(True)
        self.show_arrows_check.stateChanged.connect(self.on_display_changed)
        display_form.addRow("", self.show_arrows_check)

        display_group.setLayout(display_form)
        layout.addWidget(display_group)

        # Filters
        filter_group = QGroupBox("Filters")
        filter_form = QFormLayout()

        self.min_citations_spin = QSpinBox()
        self.min_citations_spin.setRange(0, 100)
        self.min_citations_spin.setValue(0)
        self.min_citations_spin.valueChanged.connect(self.on_filter_changed)
        filter_form.addRow("Min citations:", self.min_citations_spin)

        filter_group.setLayout(filter_form)
        layout.addWidget(filter_group)

        layout.addStretch()

        return layout

    def build_graph(self):
        """Build citation network graph from database."""
        self.graph = nx.DiGraph()

        # Get all papers
        papers = self.db.get_all_papers()

        if not papers:
            return

        # Add nodes
        for paper in papers:
            paper_id = paper['id']
            self.papers_map[paper_id] = paper

            # Node attributes
            self.graph.add_node(
                paper_id,
                title=paper['title'][:50],  # Truncate for display
                year=paper.get('year', 0),
                full_title=paper['title']
            )

        # Get citations from database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT citing_paper_id, cited_paper_id, confidence
            FROM Citations
        """)

        citations = cursor.fetchall()

        # Add edges
        for citation in citations:
            citing_id = citation['citing_paper_id']
            cited_id = citation['cited_paper_id']
            confidence = citation['confidence']

            # Only add if both nodes exist
            if citing_id in self.graph.nodes and cited_id in self.graph.nodes:
                self.graph.add_edge(citing_id, cited_id, weight=confidence)

        print(f"Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

    def draw_graph(self):
        """Draw the citation network graph."""
        self.figure.clear()

        if not self.graph or self.graph.number_of_nodes() == 0:
            ax = self.figure.add_subplot(111)
            ax.text(
                0.5, 0.5,
                "No citation data available.\n\n"
                "Import more papers or extract references\n"
                "to build the citation network.",
                ha='center', va='center',
                fontsize=12, color='gray'
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas.draw()
            self.update_statistics()
            return

        ax = self.figure.add_subplot(111)

        # Apply filters
        filtered_graph = self.apply_filters()

        if filtered_graph.number_of_nodes() == 0:
            ax.text(
                0.5, 0.5,
                "No papers match the current filters.",
                ha='center', va='center',
                fontsize=12, color='gray'
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas.draw()
            return

        # Choose layout
        layout_name = self.layout_combo.currentText()
        pos = self.compute_layout(filtered_graph, layout_name)

        # Node sizes based on in-degree (citations received)
        in_degrees = dict(filtered_graph.in_degree())
        max_in_degree = max(in_degrees.values()) if in_degrees else 1
        node_sizes = [300 + (in_degrees.get(node, 0) / max(max_in_degree, 1)) * 700
                      for node in filtered_graph.nodes()]

        # Node colors based on year
        years = [filtered_graph.nodes[node].get('year') or 0 for node in filtered_graph.nodes()]
        if years:
            # Filter out None and 0 values for min/max calculation
            valid_years = [y for y in years if y and y > 0]
            if valid_years:
                min_year = min(valid_years)
                max_year = max(valid_years)
                year_range = max(max_year - min_year, 1)
                node_colors = [(y - min_year) / year_range if y and y > 0 else 0.5 for y in years]
            else:
                node_colors = [0.5] * len(filtered_graph.nodes())
        else:
            node_colors = [0.5] * len(filtered_graph.nodes())

        # Draw nodes
        nx.draw_networkx_nodes(
            filtered_graph, pos,
            node_size=node_sizes,
            node_color=node_colors,
            cmap=plt.cm.viridis,
            alpha=0.8,
            ax=ax
        )

        # Draw edges
        if self.show_arrows_check.isChecked():
            nx.draw_networkx_edges(
                filtered_graph, pos,
                edge_color='gray',
                alpha=0.4,
                arrows=True,
                arrowsize=10,
                ax=ax
            )
        else:
            nx.draw_networkx_edges(
                filtered_graph, pos,
                edge_color='gray',
                alpha=0.4,
                arrows=False,
                ax=ax
            )

        # Draw labels
        if self.show_labels_check.isChecked():
            labels = {node: filtered_graph.nodes[node]['title']
                      for node in filtered_graph.nodes()}
            nx.draw_networkx_labels(
                filtered_graph, pos,
                labels,
                font_size=8,
                font_color='black',
                ax=ax
            )

        ax.set_title("Citation Network", fontsize=14, fontweight='bold')
        ax.axis('off')

        self.canvas.draw()
        self.update_statistics(filtered_graph)

    def compute_layout(self, graph, layout_name: str) -> Dict:
        """Compute graph layout positions."""
        if "Spring" in layout_name:
            return nx.spring_layout(graph, k=1, iterations=50)
        elif "Circular" in layout_name:
            return nx.circular_layout(graph)
        elif "Hierarchical" in layout_name:
            try:
                return nx.kamada_kawai_layout(graph)
            except:
                return nx.spring_layout(graph)
        elif "Kamada" in layout_name:
            return nx.kamada_kawai_layout(graph)
        elif "Shell" in layout_name:
            return nx.shell_layout(graph)
        else:
            return nx.spring_layout(graph)

    def apply_filters(self) -> nx.DiGraph:
        """Apply filters to graph."""
        filtered = self.graph.copy()

        # Filter by minimum citations
        min_citations = self.min_citations_spin.value()
        if min_citations > 0:
            nodes_to_remove = [
                node for node in filtered.nodes()
                if filtered.in_degree(node) < min_citations
            ]
            filtered.remove_nodes_from(nodes_to_remove)

        return filtered

    def update_statistics(self, graph=None):
        """Update statistics label."""
        if graph is None:
            graph = self.graph

        if not graph or graph.number_of_nodes() == 0:
            self.stats_label.setText("No data")
            return

        num_nodes = graph.number_of_nodes()
        num_edges = graph.number_of_edges()

        # Most cited papers
        in_degrees = sorted(graph.in_degree(), key=lambda x: x[1], reverse=True)
        most_cited = in_degrees[:3] if in_degrees else []

        # Most citing papers
        out_degrees = sorted(graph.out_degree(), key=lambda x: x[1], reverse=True)
        most_citing = out_degrees[:3] if out_degrees else []

        stats_text = f"<b>Network Statistics:</b><br>"
        stats_text += f"Papers: {num_nodes} | Citations: {num_edges}<br>"

        if most_cited:
            stats_text += f"<br><b>Most cited:</b><br>"
            for node_id, count in most_cited:
                if count > 0:
                    title = graph.nodes[node_id]['title']
                    stats_text += f"• {title} ({count} citations)<br>"

        self.stats_label.setText(stats_text)

    def on_layout_changed(self):
        """Handle layout algorithm change."""
        self.draw_graph()

    def on_display_changed(self):
        """Handle display option change."""
        self.draw_graph()

    def on_filter_changed(self):
        """Handle filter change."""
        self.draw_graph()

    def refresh_network(self):
        """Refresh the network from database."""
        self.build_graph()
        self.draw_graph()

        QMessageBox.information(
            self,
            "Network Refreshed",
            f"Loaded {self.graph.number_of_nodes()} papers and "
            f"{self.graph.number_of_edges()} citations."
        )

    def export_graph(self):
        """Export graph to file."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Citation Network",
            "citation_network.png",
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg)"
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Citation network exported to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export graph:\n{str(e)}"
                )
