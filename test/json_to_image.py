import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, List, Any
import numpy as np


class JsonToImageConverter:
    """Convert JSON land subdivision data to visualization images."""
    
    def __init__(self, output_dir: str = "output_images"):
        """
        Initialize the converter.
        
        Args:
            output_dir: Directory to save output images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Color scheme
        self.colors = {
            'boundary': '#2c3e50',
            'road': '#34495e',
            'background': '#ecf0f1'
        }
    
    def load_json(self, json_path: str) -> Dict[str, Any]:
        """Load JSON data from file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_json_string(self, json_string: str) -> Dict[str, Any]:
        """Load JSON data from string."""
        return json.loads(json_string)
    
    def draw_polygon(self, ax, coordinates: List[List[float]], 
                     color: str, alpha: float = 0.7, 
                     edgecolor: str = 'black', linewidth: float = 2,
                     label: str = None):
        """Draw a polygon on the axes."""
        polygon = patches.Polygon(
            coordinates,
            closed=True,
            facecolor=color,
            edgecolor=edgecolor,
            alpha=alpha,
            linewidth=linewidth,
            label=label
        )
        ax.add_patch(polygon)
    
    def convert_to_image(self, data: Dict[str, Any], 
                        output_filename: str = None,
                        dpi: int = 300,
                        figsize: tuple = (12, 12)) -> str:
        """
        Convert JSON data to image.
        
        Args:
            data: JSON data dictionary
            output_filename: Output filename (auto-generated if None)
            dpi: Image resolution
            figsize: Figure size in inches
            
        Returns:
            Path to saved image
        """
        # Create figure
        fig, ax = plt.subplots(figsize=figsize, facecolor=self.colors['background'])
        ax.set_facecolor(self.colors['background'])
        
        # Draw boundary
        if 'boundary' in data and 'coordinates' in data['boundary']:
            boundary_coords = data['boundary']['coordinates']
            self.draw_polygon(
                ax, 
                boundary_coords, 
                color='white',
                edgecolor=self.colors['boundary'],
                linewidth=3,
                alpha=1.0,
                label='Boundary'
            )
        
        # Draw assets
        if 'assets' in data:
            for asset in data['assets']:
                asset_type = asset.get('type', 'unknown')
                asset_id = asset.get('asset_id', 'unknown')
                
                # Get color from JSON or use default based on asset type
                if 'color' in asset:
                    color = asset['color']
                elif asset_type == 'road':
                    color = self.colors['road']
                elif asset_type == 'factory':
                    color = '#e74c3c'  # Default red for factory
                elif asset_type == 'building':
                    color = '#3498db'  # Default blue for building
                elif asset_type == 'park':
                    color = '#2ecc71'  # Default green for park
                else:
                    color = '#95a5a6'  # Default gray
                
                # Handle assets with direct coordinates
                if 'coordinates' in asset and 'polygons' not in asset:
                    coords = asset['coordinates']
                    description = asset.get('description', asset_type)
                    self.draw_polygon(
                        ax,
                        coords,
                        color=color,
                        alpha=0.8,
                        edgecolor='black',
                        linewidth=1.5,
                        label=f"{asset_id} ({description})"
                    )
                
                # Handle assets with polygons (multiple shapes)
                elif 'polygons' in asset:
                    for i, polygon_data in enumerate(asset['polygons']):
                        polygon_name = polygon_data.get('name', f'Polygon {i+1}')
                        coords = polygon_data['coordinates']
                        
                        label = f"{asset_id} - {polygon_name}" if i == 0 else None
                        self.draw_polygon(
                            ax,
                            coords,
                            color=color,
                            alpha=0.8,
                            edgecolor='black',
                            linewidth=1.5,
                            label=label
                        )
        
        # Set up plot
        project_name = data.get('project_name', 'Unknown Project')
        ax.set_title(f"{project_name}", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('X (meters)', fontsize=12)
        ax.set_ylabel('Y (meters)', fontsize=12)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Add legend
        ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
        
        # Add info text
        if 'boundary' in data:
            area = data['boundary'].get('area_m2', 'N/A')
            info_text = f"Area: {area} m²"
            ax.text(0.02, 0.98, info_text, 
                   transform=ax.transAxes,
                   fontsize=10,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Auto-adjust limits with padding
        ax.autoscale()
        ax.margins(0.1)
        
        plt.tight_layout()
        
        # Save figure
        if output_filename is None:
            output_filename = f"{project_name.replace(' ', '_')}.png"
        
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                   facecolor=self.colors['background'])
        plt.close()
        
        return str(output_path)
    
    def convert_from_file(self, json_path: str, 
                         output_filename: str = None,
                         dpi: int = 300) -> str:
        """
        Convert JSON file to image.
        
        Args:
            json_path: Path to JSON file
            output_filename: Output filename (auto-generated if None)
            dpi: Image resolution
            
        Returns:
            Path to saved image
        """
        data = self.load_json(json_path)
        return self.convert_to_image(data, output_filename, dpi)
    
    def convert_from_string(self, json_string: str,
                           output_filename: str = None,
                           dpi: int = 300) -> str:
        """
        Convert JSON string to image.
        
        Args:
            json_string: JSON data as string
            output_filename: Output filename (auto-generated if None)
            dpi: Image resolution
            
        Returns:
            Path to saved image
        """
        data = self.load_json_string(json_string)
        return self.convert_to_image(data, output_filename, dpi)


def main():
    """Example usage - Load from JSON file and convert to image."""
    import os
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the JSON file
    json_file_path = os.path.join(script_dir, "sample_data.json")
    
    # Output directory in the test folder
    output_dir = os.path.join(script_dir, "output_images")
    
    # Create converter
    converter = JsonToImageConverter(output_dir=output_dir)
    
    # Convert from JSON file
    output_path = converter.convert_from_file(json_file_path)
    print(f"✅ Image saved to: {output_path}")
    print(f"📁 JSON source: {json_file_path}")
    print(f"📂 Output directory: {output_dir}")


if __name__ == "__main__":
    main()
