#!/usr/bin/env python3
"""
DWG to DXF Converter Module for REMB

This module provides DWG to DXF conversion capabilities using multiple methods:
1. ODA File Converter (Windows/Linux - recommended)
2. LibreDWG (Linux/Colab fallback)
3. Teigha File Converter (legacy support)

Based on: https://github.com/tomer7X/DWG_TO_DXF
"""

import os
import subprocess
import tempfile
import shutil
import platform
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import zipfile


class DWGConverter:
    """
    DWG to DXF Converter with multiple backend support.
    
    Usage:
        converter = DWGConverter()
        dxf_path = converter.convert("input.dwg", "output.dxf")
    """
    
    # ODA File Converter download URLs
    ODA_WINDOWS_URL = "https://download.opendesign.com/guestfiles/ODAFileConverter/ODAFileConverter_24.4.0_setup.exe"
    ODA_LINUX_URL = "https://download.opendesign.com/guestfiles/ODAFileConverter/ODAFileConverter_QT5_lnxX64_8.2dll_24.10.tar.gz"
    
    def __init__(self, oda_path: Optional[str] = None):
        """
        Initialize the DWG converter.
        
        Args:
            oda_path: Optional path to ODA File Converter executable
        """
        self.oda_path = oda_path
        self.system = platform.system()
        self._setup_converter()
    
    def _setup_converter(self):
        """Detect and setup the best available converter."""
        # Try to find ODA File Converter
        if self.oda_path and os.path.exists(self.oda_path):
            self.converter_type = "oda"
            return
        
        # Check common installation paths
        common_paths = self._get_common_oda_paths()
        for path in common_paths:
            if os.path.exists(path):
                self.oda_path = path
                self.converter_type = "oda"
                return
        
        # Try LibreDWG (for Linux/Colab)
        if self._check_libredwg():
            self.converter_type = "libredwg"
            return
        
        # No converter found
        self.converter_type = None
    
    def _get_common_oda_paths(self) -> list:
        """Get common ODA File Converter installation paths."""
        paths = []
        
        if self.system == "Windows":
            paths.extend([
                r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
                r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
                os.path.join(os.path.dirname(__file__), "ODA", "ODAFileConverter 24.4.0", "ODAFileConverter.exe"),
                os.path.join(os.getcwd(), "ODA", "ODAFileConverter 24.4.0", "ODAFileConverter.exe"),
            ])
        else:  # Linux/Mac
            paths.extend([
                "/usr/bin/ODAFileConverter",
                "/usr/local/bin/ODAFileConverter",
                os.path.expanduser("~/ODAFileConverter/ODAFileConverter"),
                "/opt/ODAFileConverter/ODAFileConverter",
            ])
        
        return paths
    
    def _check_libredwg(self) -> bool:
        """Check if LibreDWG is available."""
        try:
            result = subprocess.run(
                ["dwg2dxf", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_libredwg_colab(self) -> bool:
        """
        Install LibreDWG on Google Colab.
        
        Returns:
            True if installation successful
        """
        try:
            print("📦 Installing LibreDWG for DWG conversion...")
            
            # Install via apt
            subprocess.run(
                ["apt-get", "update"],
                capture_output=True,
                check=True
            )
            subprocess.run(
                ["apt-get", "install", "-y", "libredwg-tools"],
                capture_output=True,
                check=True
            )
            
            # Verify installation
            if self._check_libredwg():
                self.converter_type = "libredwg"
                print("✅ LibreDWG installed successfully")
                return True
            else:
                print("❌ LibreDWG installation failed")
                return False
                
        except Exception as e:
            print(f"❌ Error installing LibreDWG: {e}")
            return False
    
    def install_oda_colab(self) -> bool:
        """
        Install ODA File Converter on Google Colab.
        
        Returns:
            True if installation successful
        """
        try:
            print("📦 Downloading ODA File Converter for Linux...")
            
            # Create temp directory
            oda_dir = "/content/oda"
            os.makedirs(oda_dir, exist_ok=True)
            
            # Download and extract
            tar_path = os.path.join(oda_dir, "oda.tar.gz")
            urllib.request.urlretrieve(self.ODA_LINUX_URL, tar_path)
            
            # Extract
            subprocess.run(
                ["tar", "-xzf", tar_path, "-C", oda_dir],
                check=True
            )
            
            # Find executable
            for root, dirs, files in os.walk(oda_dir):
                for file in files:
                    if file == "ODAFileConverter":
                        exe_path = os.path.join(root, file)
                        os.chmod(exe_path, 0o755)
                        self.oda_path = exe_path
                        self.converter_type = "oda"
                        print(f"✅ ODA File Converter installed: {exe_path}")
                        return True
            
            print("❌ ODA File Converter executable not found")
            return False
            
        except Exception as e:
            print(f"❌ Error installing ODA: {e}")
            return False
    
    def convert(self, dwg_path: str, output_path: Optional[str] = None, 
                version: str = "ACAD2018") -> Optional[str]:
        """
        Convert DWG file to DXF.
        
        Args:
            dwg_path: Path to input DWG file
            output_path: Optional path for output DXF file
            version: AutoCAD version for output (default: ACAD2018)
        
        Returns:
            Path to output DXF file, or None if conversion failed
        """
        if not os.path.exists(dwg_path):
            print(f"❌ DWG file not found: {dwg_path}")
            return None
        
        # Generate output path if not provided
        if output_path is None:
            output_path = os.path.splitext(dwg_path)[0] + ".dxf"
        
        # Try conversion based on available converter
        if self.converter_type == "oda":
            return self._convert_with_oda(dwg_path, output_path, version)
        elif self.converter_type == "libredwg":
            return self._convert_with_libredwg(dwg_path, output_path)
        else:
            print("❌ No DWG converter available")
            print("   Try: converter.install_libredwg_colab() or converter.install_oda_colab()")
            return None
    
    def _convert_with_oda(self, dwg_path: str, output_path: str, 
                          version: str) -> Optional[str]:
        """Convert using ODA File Converter."""
        try:
            input_dir = os.path.dirname(os.path.abspath(dwg_path))
            input_file = os.path.basename(dwg_path)
            output_dir = os.path.dirname(os.path.abspath(output_path))
            
            os.makedirs(output_dir, exist_ok=True)
            
            # ODA command format:
            # ODAFileConverter <input_folder> <output_folder> <output_version> <output_type> <recurse> <audit> <input_filter>
            cmd = [
                self.oda_path,
                input_dir,
                output_dir,
                version,     # Output version (ACAD2018, ACAD2013, etc.)
                "DXF",       # Output type
                "0",         # Don't recurse subdirectories
                "1",         # Audit and fix errors
                input_file   # Filter to specific file
            ]
            
            print(f"🔄 Converting: {dwg_path}")
            result = subprocess.run(cmd, capture_output=True, text=True, shell=(self.system == "Windows"))
            
            # Check if output was created
            expected_output = os.path.join(
                output_dir, 
                os.path.splitext(input_file)[0] + ".dxf"
            )
            
            if os.path.exists(expected_output):
                # Move to requested output path if different
                if expected_output != output_path:
                    shutil.move(expected_output, output_path)
                print(f"✅ Converted: {output_path}")
                return output_path
            else:
                print(f"❌ Conversion failed. ODA output: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ ODA conversion error: {e}")
            return None
    
    def _convert_with_libredwg(self, dwg_path: str, output_path: str) -> Optional[str]:
        """Convert using LibreDWG."""
        try:
            print(f"🔄 Converting with LibreDWG: {dwg_path}")
            
            result = subprocess.run(
                ["dwg2dxf", "-o", output_path, dwg_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"✅ Converted: {output_path}")
                return output_path
            else:
                print(f"❌ LibreDWG conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ LibreDWG conversion error: {e}")
            return None
    
    def batch_convert(self, input_dir: str, output_dir: Optional[str] = None,
                      version: str = "ACAD2018") -> list:
        """
        Batch convert all DWG files in a directory.
        
        Args:
            input_dir: Directory containing DWG files
            output_dir: Optional output directory (default: input_dir/dxf)
            version: AutoCAD version for output
        
        Returns:
            List of converted DXF file paths
        """
        if output_dir is None:
            output_dir = os.path.join(input_dir, "dxf")
        
        os.makedirs(output_dir, exist_ok=True)
        
        converted = []
        dwg_files = list(Path(input_dir).glob("*.dwg")) + list(Path(input_dir).glob("*.DWG"))
        
        print(f"📂 Found {len(dwg_files)} DWG files in {input_dir}")
        
        for dwg_file in dwg_files:
            output_path = os.path.join(output_dir, dwg_file.stem + ".dxf")
            result = self.convert(str(dwg_file), output_path, version)
            if result:
                converted.append(result)
        
        print(f"✅ Converted {len(converted)}/{len(dwg_files)} files")
        return converted
    
    def get_status(self) -> dict:
        """Get converter status information."""
        return {
            "system": self.system,
            "converter_type": self.converter_type,
            "oda_path": self.oda_path,
            "available": self.converter_type is not None
        }


def convert_dwg_to_dxf(dwg_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Simple function to convert DWG to DXF.
    
    Args:
        dwg_path: Path to input DWG file
        output_path: Optional path for output DXF file
    
    Returns:
        Path to output DXF file, or None if conversion failed
    """
    converter = DWGConverter()
    return converter.convert(dwg_path, output_path)


def setup_dwg_converter_colab() -> DWGConverter:
    """
    Setup DWG converter for Google Colab environment.
    
    Returns:
        Configured DWGConverter instance
    """
    converter = DWGConverter()
    
    if converter.converter_type is None:
        # Try LibreDWG first (lighter weight)
        if not converter.install_libredwg_colab():
            # Fall back to ODA
            converter.install_oda_colab()
    
    return converter


# For testing
if __name__ == "__main__":
    converter = DWGConverter()
    status = converter.get_status()
    print(f"DWG Converter Status:")
    print(f"  System: {status['system']}")
    print(f"  Converter: {status['converter_type']}")
    print(f"  Available: {status['available']}")
