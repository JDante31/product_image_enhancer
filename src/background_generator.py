"""
Background generator module for product images.
"""

# Standard library imports
import os
import json
import time
import base64
from datetime import datetime
from pathlib import Path
import io

# Third-party imports
from PIL import Image
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Local imports
from src.config.generation_config import FLUX_PARAMS, FLUX_API
from src.mask_generator import MaskGenerator
from src.utils import get_data_path

class FluxGenerator:
    """Enhances product images with AI-generated backgrounds."""
    
    # API configuration
    MAX_WAIT_TIME = 600  # Maximum total wait time (10 minutes)
    INITIAL_RETRY_DELAY = 2  # Initial delay between retries
    MAX_RETRY_DELAY = 30    # Maximum delay between retries
    
    def __init__(self, require_api=True):
        """Initialize background generator.
        
        Args:
            require_api (bool): Enable API-based generation
        """
        load_dotenv()
        self.api_key = os.getenv('BFL_API_KEY')
        self.require_api = require_api
        
        if require_api and not self.api_key:
            raise ValueError("BFL_API_KEY not found in environment variables")
        
        # Simplified headers to match example
        self.headers = {
            "Content-Type": "application/json",
            "X-Key": self.api_key if self.api_key else ""
        }
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retries = Retry(
            total=5,                  # Total number of retries
            backoff_factor=1,         # Exponential backoff
            status_forcelist=[429, 500, 502, 503, 504]  # Retry on these statuses
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        get_data_path('output/enhanced')
    
    def __del__(self):
        """Cleanup session on object destruction."""
        if hasattr(self, 'session'):
            self.session.close()
    
    def _encode_image(self, image_path):
        """Convert image to base64 string."""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except IOError as e:
            raise IOError(f"Failed to read image file {image_path}: {str(e)}")
    
    def _wait_for_result(self, task_id):
        """Poll API until task completion with exponential backoff.
        
        Args:
            task_id (str): Task identifier from API
            
        Returns:
            str: URL to download the result
            
        Raises:
            TimeoutError: If task takes too long
            requests.exceptions.RequestException: For API/network errors
        """
        start_time = time.time()
        current_delay = self.INITIAL_RETRY_DELAY
        
        while time.time() - start_time < self.MAX_WAIT_TIME:
            try:
                # Use the correct get_result endpoint
                response = self.session.get(
                    "https://api.bfl.ml/v1/get_result",
                    headers=self.headers,
                    params={"id": task_id},
                    timeout=30
                )
                
                if response.status_code == 429:  # Rate limit
                    print("Rate limit hit, waiting longer...")
                    time.sleep(min(current_delay * 2, self.MAX_RETRY_DELAY))
                    continue
                
                response.raise_for_status()
                
                # Print raw response for debugging
                print(f"Response: {response.text}")
                
                data = response.json()
                if data.get('status') == "Task not found":
                    print(f"Task {task_id} not found, retrying...")
                elif data.get('status') == "Ready" and data.get('result'):
                    result_url = data['result'].get('sample')
                    if result_url:
                        return result_url
                    else:
                        raise ValueError("No sample URL in result")
                elif data.get('status') == "Pending":
                    print(f"Task still processing... ({int(time.time() - start_time)}s elapsed)")
                
            except requests.exceptions.RequestException as e:
                print(f"Request error: {str(e)}")
            
            # Exponential backoff with max delay
            time.sleep(current_delay)
            current_delay = min(current_delay * 2, self.MAX_RETRY_DELAY)
        
        total_time = int(time.time() - start_time)
        raise TimeoutError(f"Task timed out after {total_time} seconds")
    
    def _load_latest_trend_analysis(self):
        """Load most recent trend analysis results."""
        try:
            analysis_dir = get_data_path('analysis')
            files = list(analysis_dir.glob("trend_analysis_*.json"))
            if not files:
                raise FileNotFoundError("No trend analysis files found")
            
            latest_file = max(files)
            with open(latest_file) as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load trend analysis: {str(e)}")
    
    def enhance_product_image(self, image_path, mask_path=None, trend_data=None):
        """Enhance product image with AI-generated background.
        
        Args:
            image_path (str): Path to product image
            mask_path (str, optional): Path to pre-generated mask
            trend_data (dict, optional): Trend analysis data
            
        Returns:
            str: Path to enhanced image
            None: If API access is disabled
            
        Raises:
            ValueError: For invalid inputs
            IOError: For file operations
            requests.exceptions.RequestException: For API/network errors
            TimeoutError: If task takes too long
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        try:
            # Load and prepare image
            with Image.open(image_path) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Generate or load mask
                if not mask_path:
                    print("Generating new mask...")
                    mask_generator = MaskGenerator()
                    mask = mask_generator.create_mask(image_path)
                    
                    mask_dir = get_data_path('output/masks')
                    mask_path = mask_dir / f"product_mask_{timestamp}.png"
                    mask.save(str(mask_path))
                
                # Load trend data if not provided
                if trend_data is None:
                    trend_data = self._load_latest_trend_analysis()
                
                if not self.require_api:
                    return None
                
                # Prepare and send API request
                payload = {
                    "image": self._encode_image(str(image_path)),
                    "mask": self._encode_image(str(mask_path)),
                    "prompt": trend_data['enhanced_prompt'],
                    **FLUX_PARAMS
                }
                
                # Print request details for debugging
                print(f"Sending request to: {FLUX_API['url']}")
                print(f"Headers: {self.headers}")
                print("Payload keys:", list(payload.keys()))
                
                response = self.session.post(
                    FLUX_API["url"],
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                # Print raw response for debugging
                print(f"Initial response: {response.text}")
                
                response.raise_for_status()
                
                # Process result
                data = response.json()
                task_id = data.get('id')
                if not task_id:
                    raise ValueError("No task ID in API response")
                
                print(f"Task submitted (ID: {task_id})")
                result_url = self._wait_for_result(task_id)
                
                # Download result
                response = self.session.get(result_url, timeout=30)
                response.raise_for_status()
                
                # Save enhanced image
                enhanced_img = Image.open(io.BytesIO(response.content))
                output_dir = get_data_path('output/enhanced')
                output_path = output_dir / f"product_enhanced_{timestamp}.png"
                enhanced_img.save(str(output_path))
                
                print(f"Enhanced image saved to: {output_path}")
                return str(output_path)
                
        except (IOError, ValueError) as e:
            raise type(e)(str(e))
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")

def main():
    """Run background generator on a test image."""
    try:
        images_dir = get_data_path('raw_images')
        masks_dir = get_data_path('output/masks')
        
        generator = FluxGenerator()
        image_path = images_dir / "pants_wolfskin.png"
        mask_path = masks_dir / "product_mask.png"
        
        if not mask_path.exists():
            print(f"Mask not found at {mask_path}")
            print("Please run main.py first to generate the mask")
            return
        
        enhanced_path = generator.enhance_product_image(
            str(image_path),
            mask_path=str(mask_path)
        )
        print(f"Enhanced image saved to: {enhanced_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 