"""
Configuration for prompt generation and image creation pipeline.
"""

# generation_config.py
#
# This configuration file defines the parameters and settings used in the image generation
# and enhancement pipeline. It includes:
# 1. Photography parameters for consistent, professional-looking results
# 2. Flux API parameters for stable image generation
# 3. Functions to construct and enhance prompts
#
# These configurations ensure that all generated images maintain high quality
# and consistent style across different products.

# Photography parameters define the technical aspects of how the product should be captured
# or rendered in the final image. These settings mimic professional product photography.
PHOTOGRAPHY_PARAMS = {
    # Camera settings mimic a professional product photography setup
    "camera": {
        "angle": "straight-on product photography angle",  # Standard product view
        "height": "eye-level",                            # Natural viewing height
        "lens": "85mm lens",                             # Portrait lens for minimal distortion
        "aperture": "f/4.0",                             # Balanced depth of field
        "focus": "sharp focus"                           # Ensures product clarity
    },
    # Composition settings ensure visually appealing results
    "composition": {
        "rule_of_thirds": True,                          # Classic composition principle
        "depth": "medium",                               # Balanced foreground/background
        "background": "subtle bokeh effect",             # Soft background blur
        "symmetry": "balanced"                           # Even visual weight
    },
    # Quality settings ensure high-resolution, detailed output
    "quality": {
        "resolution": "high resolution",                 # Clear, detailed images
        "detail": "ultra detailed",                      # Maximum product detail
        "lighting": "professional studio quality",       # Clean, even lighting
        "render": "8k"                                  # Maximum output quality
    }
}

# Flux API parameters control the image generation process
FLUX_PARAMS = {
    # Negative prompt helps avoid common image generation issues
    "negative_prompt": (
        "text, watermarks, logos, blurry product, distorted proportions, "
        "deformed product, altered product appearance, poor quality, artifacts, "
        "noise, grain, duplicate products, missing product parts"
    ),
    "num_inference_steps": 50,    # Balance between quality and speed
    "guidance_scale": 30.0,       # How closely to follow the prompt
    "prompt_upsampling": True,    # Improve prompt understanding
    "scheduler": "dpm++",         # Diffusion scheduler
    "seed": 42                    # Fixed seed for reproducibility
}

# API Configuration
FLUX_API = {
    "url": "https://api.bfl.ml/v1/flux-pro-1.0-fill",  # Complete API endpoint
    "timeout": 300,  # 5 minutes timeout for API calls
}

def enhance_llama_prompt(llama_response):
    """
    Create an optimized image generation prompt from the LLM's scene description.
    
    Args:
        llama_response (dict): Scene description from the LLM
        
    Returns:
        str: Optimized image generation prompt
        
    Raises:
        KeyError: If required fields are missing
    """
    try:
        scene = llama_response['scene_description']
        
        # Build prompt with precise ordering for image generation
        prompt_parts = [
            # Technical quality requirements (always first)
            f"{PHOTOGRAPHY_PARAMS['quality']['render']} {PHOTOGRAPHY_PARAMS['quality']['detail']} product photography",
            f"{PHOTOGRAPHY_PARAMS['quality']['resolution']}, sharp detail, {PHOTOGRAPHY_PARAMS['quality']['lighting']}",
            
            # Camera and lighting setup
            f"{PHOTOGRAPHY_PARAMS['camera']['lens']}, {PHOTOGRAPHY_PARAMS['camera']['aperture']}, {PHOTOGRAPHY_PARAMS['camera']['focus']}",
            
            # Scene elements from analysis (in order of importance)
            scene['lighting'].strip('.'),
            scene['environment'].strip('.'),
            
            # Visual details from analysis
            f"materials: {', '.join(scene['textures'])}",
            f"colors: {', '.join(scene['colors'])}",
            
            # Mood and composition from analysis
            scene['mood'].strip('.'),
            f"balanced composition with {PHOTOGRAPHY_PARAMS['composition']['background']}, {PHOTOGRAPHY_PARAMS['composition']['depth']} depth",
            
            # Final quality assurance
            "professional color grading, studio quality"
        ]
        
        # Join with commas and clean up any double spaces or periods
        prompt = ", ".join(part.strip() for part in prompt_parts if part.strip())
        prompt = prompt.replace("..", ".").replace(" ,", ",").strip(".")
        
        return prompt
        
    except KeyError as e:
        raise KeyError(f"Missing required field in scene description: {e}")

def prepare_flux_request(enhanced_prompt, product_image, product_mask):
    """
    Prepare a complete request for the Flux AI API.
    
    Args:
        enhanced_prompt (str): The enhanced prompt from enhance_llama_prompt()
        product_image (str): Base64 encoded product image
        product_mask (str): Base64 encoded product mask
        
    Returns:
        dict: Complete request payload for the Flux API
    """
    return {
        "prompt": enhanced_prompt,
        "negative_prompt": (
            "text, watermarks, logos, blurry, distorted, deformed, "
            "bad quality, low quality, artifacts, noise, grain, duplicate, "
            "missing parts, cropped, out of frame, worst quality, "
            "low resolution, bad composition, unprofessional"
        ),
        "num_inference_steps": 50,
        "guidance_scale": 30.0,
        "prompt_upsampling": True,
        "scheduler": "dpm++",
        "seed": 42
    } 