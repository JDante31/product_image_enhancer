from datetime import datetime
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
# import matplotlib.pyplot  # Only needed for debug visualization


from .utils import get_data_path

class MaskGenerator:
    """Creates binary masks for product images by processing the alpha channel."""

    # Core parameters for mask generation
    ALPHA_THRESHOLD = 127  # Threshold for binary mask creation
    EDGE_LOW = 100        # Lower threshold for edge detection
    EDGE_HIGH = 200       # Upper threshold for edge detection
    SUPERSAMPLE_FACTOR = 4  # Factor for high-resolution processing
    
    def __init__(self, debug=False):
        """Initialize mask generator.
        
        Args:
            debug (bool): Whether to save debug visualizations
        """
        self.debug = debug
        if debug:
            self.debug_dir = get_data_path('output/debug/mask_analysis')
    
    # Debug visualization methods (commented out as they're not essential)
    """
    def _save_debug_image(self, image, step_name, timestamp):
        if not self.debug:
            return
        
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        image.save(str(self.debug_dir / f"{timestamp}_{step_name}.png"))
    
    def _create_comparison_image(self, original, alpha, mask, timestamp):
        if not self.debug:
            return
            
        width, height = original.size
        comparison = Image.new('RGB', (width * 4, height))
        
        # Original on pink background
        img_array = np.array(original.convert('RGBA'))
        background = np.full((height, width, 3), [255, 0, 255])
        alpha_norm = np.array(alpha)[:, :, np.newaxis] / 255.0
        composite = (img_array[:, :, :3] * alpha_norm + 
                    background * (1 - alpha_norm)).astype(np.uint8)
        
        # Place images side by side
        comparison.paste(Image.fromarray(composite), (0, 0))
        comparison.paste(Image.fromarray(np.array(alpha)), (width, 0))
        comparison.paste(mask.convert('RGB'), (width * 2, 0))
        
        # Show masked result
        result = composite.copy()
        result[np.array(mask) == 255] = [255, 0, 255]
        comparison.paste(Image.fromarray(result), (width * 3, 0))
        
        self._save_debug_image(comparison, "8_final_comparison", timestamp)
    """
    
    def create_mask(self, image_path):
        """Create binary mask separating product from background.
        
        Args:
            image_path (str): Path to product image
            
        Returns:
            PIL.Image: Binary mask (black=product, white=background)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # 1. Extract alpha channel
        original = Image.open(image_path).convert('RGBA')
        width, height = original.size
        alpha = original.split()[3]
        alpha_array = np.array(alpha)
        
        """
        if self.debug:
            # Visualize alpha distribution
            alpha_hist = cv2.calcHist([alpha_array], [0], None, [256], [0, 256])
            plt.figure(figsize=(10, 4))
            plt.plot(alpha_hist)
            plt.title('Alpha Channel Distribution')
            plt.savefig(str(self.debug_dir / f"{timestamp}_1_alpha_distribution.png"))
            plt.close()
        """
        
        # 2. Create initial binary mask
        initial_mask = np.where(alpha_array > self.ALPHA_THRESHOLD, 0, 255).astype(np.uint8)
        # self._save_debug_image(initial_mask, "2_initial_binary", timestamp)
        
        # 3. Supersample for better edge quality
        super_size = (width * self.SUPERSAMPLE_FACTOR, 
                     height * self.SUPERSAMPLE_FACTOR)
        mask_large = cv2.resize(initial_mask, super_size, 
                              interpolation=cv2.INTER_LINEAR)
        mask_large = np.where(mask_large > self.ALPHA_THRESHOLD, 0, 255).astype(np.uint8)
        # self._save_debug_image(mask_large, "3_supersampled", timestamp)
        
        # 4. Edge detection and refinement
        edges = cv2.Canny(mask_large, self.EDGE_LOW, self.EDGE_HIGH)
        # self._save_debug_image(edges, "4_edge_detection", timestamp)
        
        kernel = np.ones((3,3), np.uint8)
        edge_zone = cv2.dilate(edges, kernel, iterations=1)
        # self._save_debug_image(edge_zone, "5_transition_zone", timestamp)
        
        # 5. Create final mask
        final_high_res = mask_large.copy()
        # self._save_debug_image(final_high_res, "6_final_highres", timestamp)
        
        # 6. Downsample to original size
        final_mask_array = cv2.resize(final_high_res, (width, height), 
                                    interpolation=cv2.INTER_LINEAR)
        final_mask_array = np.where(final_mask_array > self.ALPHA_THRESHOLD, 
                                  0, 255).astype(np.uint8)
        final_mask = Image.fromarray(final_mask_array)
        
        # self._save_debug_image(final_mask, "7_final_mask", timestamp)
        # self._create_comparison_image(original, alpha, final_mask, timestamp)
        
        return final_mask

"""
def main():
    # Test function - not needed for production
    images_dir = get_data_path('raw_images')
    masks_dir = get_data_path('output/masks')
    
    generator = MaskGenerator(debug=True)
    image_path = images_dir / "pants_wolfskin.png"
    mask = generator.create_mask(str(image_path))
    
    mask_path = masks_dir / "test_mask.png"
    mask.save(str(mask_path))
    print(f"Mask saved to: {mask_path}")

if __name__ == "__main__":
    main()
""" 