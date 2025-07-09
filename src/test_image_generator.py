#!/usr/bin/env python3
"""
Test Image Generator for PRig
Creates comprehensive test images for photo printer quality assessment.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
import numpy as np


class TestImageGenerator:
    """Generates various test images for printer quality assessment."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="prig_test_"))
        self.image_size = (1800, 1200)  # 4x6 at 300 DPI
        
    def generate_test_suite(self, printer_info) -> List[Tuple[Path, str]]:
        """Generate complete test suite for a printer."""
        test_images = []
        
        # Color accuracy tests
        test_images.append(self.create_color_bars())
        test_images.append(self.create_color_gradients())
        test_images.append(self.create_primary_colors())
        
        # Sharpness and detail tests
        test_images.append(self.create_resolution_test())
        test_images.append(self.create_fine_details())
        test_images.append(self.create_text_clarity())
        
        # Tone and contrast tests
        test_images.append(self.create_grayscale_gradient())
        test_images.append(self.create_contrast_test())
        
        # Printer-specific tests
        test_images.append(self.create_edge_bleeding_test())
        test_images.append(self.create_saturation_test())
        
        return test_images
        
    def create_color_bars(self) -> Tuple[Path, str]:
        """Create standard color bars for color accuracy testing."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Standard color bars
        colors = [
            (255, 255, 255),  # White
            (255, 255, 0),    # Yellow
            (0, 255, 255),    # Cyan
            (0, 255, 0),      # Green
            (255, 0, 255),    # Magenta
            (255, 0, 0),      # Red
            (0, 0, 255),      # Blue
            (0, 0, 0)         # Black
        ]
        
        bar_width = self.image_size[0] // len(colors)
        
        for i, color in enumerate(colors):
            x1 = i * bar_width
            x2 = (i + 1) * bar_width
            draw.rectangle([x1, 0, x2, self.image_size[1]], fill=color)
            
        # Add labels
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()
            
        labels = ['White', 'Yellow', 'Cyan', 'Green', 'Magenta', 'Red', 'Blue', 'Black']
        for i, label in enumerate(labels):
            x = i * bar_width + bar_width // 2
            y = self.image_size[1] - 100
            text_color = (0, 0, 0) if i < 4 else (255, 255, 255)
            draw.text((x, y), label, font=font, fill=text_color, anchor="mm")
            
        path = self.temp_dir / "color_bars.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Color Bars Test"
        
    def create_color_gradients(self) -> Tuple[Path, str]:
        """Create RGB color gradients for smooth color transition testing."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Create RGB gradients
        gradient_height = self.image_size[1] // 3
        
        # Red gradient
        for x in range(self.image_size[0]):
            color_val = int(255 * x / self.image_size[0])
            draw.line([(x, 0), (x, gradient_height)], fill=(color_val, 0, 0))
            
        # Green gradient
        for x in range(self.image_size[0]):
            color_val = int(255 * x / self.image_size[0])
            draw.line([(x, gradient_height), (x, gradient_height * 2)], fill=(0, color_val, 0))
            
        # Blue gradient
        for x in range(self.image_size[0]):
            color_val = int(255 * x / self.image_size[0])
            draw.line([(x, gradient_height * 2), (x, self.image_size[1])], fill=(0, 0, color_val))
            
        path = self.temp_dir / "color_gradients.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "RGB Gradients Test"
        
    def create_primary_colors(self) -> Tuple[Path, str]:
        """Create primary color patches for color accuracy."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Primary and secondary colors in patches
        colors = [
            ((255, 0, 0), "Red"),
            ((0, 255, 0), "Green"), 
            ((0, 0, 255), "Blue"),
            ((255, 255, 0), "Yellow"),
            ((255, 0, 255), "Magenta"),
            ((0, 255, 255), "Cyan")
        ]
        
        patch_width = self.image_size[0] // 3
        patch_height = self.image_size[1] // 2
        
        for i, (color, name) in enumerate(colors):
            row = i // 3
            col = i % 3
            
            x1 = col * patch_width
            y1 = row * patch_height
            x2 = x1 + patch_width
            y2 = y1 + patch_height
            
            draw.rectangle([x1, y1, x2, y2], fill=color)
            
            # Add label
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            except:
                font = ImageFont.load_default()
                
            text_color = (255, 255, 255) if sum(color) < 400 else (0, 0, 0)
            draw.text((x1 + patch_width//2, y1 + patch_height//2), name, 
                     font=font, fill=text_color, anchor="mm")
            
        path = self.temp_dir / "primary_colors.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Primary Colors Test"
        
    def create_resolution_test(self) -> Tuple[Path, str]:
        """Create resolution test pattern with various line widths."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Create test patterns with decreasing line widths
        center_x = self.image_size[0] // 2
        center_y = self.image_size[1] // 2
        
        # Concentric circles with decreasing spacing
        for i in range(1, 20):
            radius = i * 30
            line_width = max(1, 6 - i // 3)
            draw.ellipse([center_x - radius, center_y - radius, 
                         center_x + radius, center_y + radius], 
                        outline=(0, 0, 0), width=line_width)
            
        # Radial lines
        for angle in range(0, 360, 15):
            x1 = center_x + int(200 * np.cos(np.radians(angle)))
            y1 = center_y + int(200 * np.sin(np.radians(angle)))
            x2 = center_x + int(400 * np.cos(np.radians(angle)))
            y2 = center_y + int(400 * np.sin(np.radians(angle)))
            draw.line([x1, y1, x2, y2], fill=(0, 0, 0), width=2)
            
        path = self.temp_dir / "resolution_test.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Resolution Test Pattern"
        
    def create_fine_details(self) -> Tuple[Path, str]:
        """Create fine detail test with small patterns."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Create checkerboard pattern with varying sizes
        for size in [4, 8, 16, 32]:
            offset_x = (size - 4) * 100
            offset_y = (size - 4) * 50
            
            for x in range(0, 400, size * 2):
                for y in range(0, 400, size * 2):
                    # Checkerboard pattern
                    draw.rectangle([offset_x + x, offset_y + y, 
                                   offset_x + x + size, offset_y + y + size], 
                                  fill=(0, 0, 0))
                    draw.rectangle([offset_x + x + size, offset_y + y + size, 
                                   offset_x + x + size * 2, offset_y + y + size * 2], 
                                  fill=(0, 0, 0))
                                  
        path = self.temp_dir / "fine_details.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Fine Details Test"
        
    def create_text_clarity(self) -> Tuple[Path, str]:
        """Create text clarity test with various font sizes."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        test_text = "PRig Test - The quick brown fox jumps over the lazy dog"
        font_sizes = [12, 16, 20, 24, 32, 48, 64]
        
        y_offset = 50
        for size in font_sizes:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
            except:
                font = ImageFont.load_default()
                
            draw.text((50, y_offset), f"{size}pt: {test_text}", 
                     font=font, fill=(0, 0, 0))
            y_offset += size + 20
            
        path = self.temp_dir / "text_clarity.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Text Clarity Test"
        
    def create_grayscale_gradient(self) -> Tuple[Path, str]:
        """Create grayscale gradient for tone reproduction testing."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Smooth gradient from black to white
        for x in range(self.image_size[0]):
            gray_val = int(255 * x / self.image_size[0])
            draw.line([(x, 0), (x, self.image_size[1])], fill=(gray_val, gray_val, gray_val))
            
        # Add gray scale steps
        step_width = self.image_size[0] // 10
        for i in range(10):
            gray_val = int(255 * i / 9)
            x1 = i * step_width
            x2 = (i + 1) * step_width
            draw.rectangle([x1, self.image_size[1] - 200, x2, self.image_size[1]], 
                          fill=(gray_val, gray_val, gray_val))
            
        path = self.temp_dir / "grayscale_gradient.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Grayscale Gradient Test"
        
    def create_contrast_test(self) -> Tuple[Path, str]:
        """Create contrast test pattern."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Black and white contrast pattern
        square_size = 100
        for x in range(0, self.image_size[0], square_size * 2):
            for y in range(0, self.image_size[1], square_size * 2):
                # Create checkerboard
                draw.rectangle([x, y, x + square_size, y + square_size], fill=(0, 0, 0))
                draw.rectangle([x + square_size, y + square_size, 
                               x + square_size * 2, y + square_size * 2], fill=(0, 0, 0))
                               
        path = self.temp_dir / "contrast_test.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Contrast Test Pattern"
        
    def create_edge_bleeding_test(self) -> Tuple[Path, str]:
        """Create test for edge bleeding and registration."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Sharp color transitions
        section_width = self.image_size[0] // 4
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 0, 0)]
        
        for i, color in enumerate(colors):
            x1 = i * section_width
            x2 = (i + 1) * section_width
            draw.rectangle([x1, 0, x2, self.image_size[1]], fill=color)
            
        # Add thin lines for registration test
        for i in range(1, 4):
            x = i * section_width
            draw.line([(x, 0), (x, self.image_size[1])], fill=(255, 255, 255), width=2)
            
        path = self.temp_dir / "edge_bleeding.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Edge Bleeding Test"
        
    def create_saturation_test(self) -> Tuple[Path, str]:
        """Create color saturation test."""
        img = Image.new('RGB', self.image_size, 'white')
        draw = ImageDraw.Draw(img)
        
        # Create saturation levels for each primary color
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        color_names = ['Red', 'Green', 'Blue']
        
        section_height = self.image_size[1] // 3
        
        for i, (base_color, name) in enumerate(zip(colors, color_names)):
            y1 = i * section_height
            y2 = (i + 1) * section_height
            
            # Create saturation gradient
            for x in range(self.image_size[0]):
                saturation = x / self.image_size[0]
                color = tuple(int(c * saturation) for c in base_color)
                draw.line([(x, y1), (x, y2)], fill=color)
                
        path = self.temp_dir / "saturation_test.jpg"
        img.save(path, "JPEG", quality=95)
        return path, "Color Saturation Test"
        
    def cleanup(self):
        """Clean up temporary files."""
        for file in self.temp_dir.glob("*"):
            file.unlink()
        self.temp_dir.rmdir()