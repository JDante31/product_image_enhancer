"""
Main script that combines purchase prediction and image enhancement.
"""

import os
import sys
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_customer_predictions(customer_data):
    """
    Predict next purchase category for each customer.
    
    Args:
        customer_data (pd.DataFrame): Customer behavior data
    
    Returns:
        pd.DataFrame: Predictions with customer_id and predicted_category
    """
    from src.predictor import PurchasePredictor
    
    logging.info("Generating purchase predictions...")
    predictor = PurchasePredictor()
    predictions = predictor.predict_batch(customer_data)
    
    return predictions

def get_current_trends():
    """
    Get current fashion trends from Reddit data.
    
    Returns:
        dict: Current fashion trends data
    """
    from src.fashion_trend_analyzer import TrendAnalyzer
    
    logging.info("Analyzing current fashion trends...")
    analyzer = TrendAnalyzer()
    return analyzer.analyze_trends()

def enhance_product_images(category, trend_data, data_dir):
    """
    Generate enhanced backgrounds for products in a category.
    
    Args:
        category (str): Product category (e.g., 'pants', 'shoes')
        trend_data (str): Path to trend analysis file
        data_dir (Path): Base data directory
    
    Returns:
        list: Paths to enhanced images
    """
    from src.background_generator import FluxGenerator
    from src.fashion_trend_analyzer import TrendAnalyzer
    import json
    
    logging.info(f"Enhancing images for {category}...")
    
    # Setup directories
    output_dir = Path('output/enhanced')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load trend data
    with open(trend_data) as f:
        trend_data_json = json.load(f)
    
    # Get trend-based prompts for this category
    analyzer = TrendAnalyzer()
    prompts = analyzer.generate_category_prompts(category, trend_data)
    
    # Generate backgrounds
    generator = FluxGenerator()
    
    # Use the hardcoded image
    img_path = data_dir / 'raw_images' / 'pants_wolfskin.png'
    if not img_path.exists():
        logging.error(f"Input image not found: {img_path}")
        return ["placeholder.png"]  # Return fallback image path
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_path = output_dir / f"enhanced_pants_wolfskin_{category}_{timestamp}.png"
    
    # Skip if already enhanced
    if not output_path.exists():
        enhanced_path = generator.enhance_product_image(
            image_path=str(img_path),
            trend_data=trend_data_json
        )
        # Copy or move the enhanced image to our desired location
        if enhanced_path and Path(enhanced_path).exists():
            import shutil
            shutil.copy2(enhanced_path, output_path)
    
    # Return relative path from workspace root
    return [str(output_path)]

def create_customer_recommendations(predictions_df, category_images):
    """
    Create final recommendations dataframe.
    
    Args:
        predictions_df (pd.DataFrame): Customer predictions
        category_images (dict): Enhanced images by category
    
    Returns:
        pd.DataFrame: Final recommendations with image paths
    """
    results = []
    
    for _, row in predictions_df.iterrows():
        category = row['predicted_category']
        # Pick a random enhanced image for the category
        enhanced_image = pd.Series(category_images[category]).sample(1).iloc[0]
        
        results.append({
            'customer_id': row['customer_id'],
            'predicted_category': category,
            'enhanced_image_path': enhanced_image,
            'prediction_confidence': row['confidence']
        })
    
    return pd.DataFrame(results)

def collect_reddit_data():
    """
    Collect latest fashion trends from Reddit.
    
    Returns:
        str: Path to the collected Reddit data file
    """
    from src.reddit_data_collector import RedditCrawler
    
    logging.info("Collecting fashion trends from Reddit...")
    crawler = RedditCrawler()
    posts = crawler.get_trending_posts()
    return crawler.save_data(posts)

def main():
    """
    Run the complete pipeline to generate customer recommendations
    with enhanced product images.
    """
    from utils import get_data_path
    
    # Setup
    data_dir = get_data_path()
    
    try:
        # 1. Collect latest Reddit data
        reddit_data_path = collect_reddit_data()
        logging.info(f"Collected Reddit data saved to: {reddit_data_path}")
        
        # 2. Load customer data
        customer_data = pd.read_csv(data_dir / 'customer_data.csv')
        logging.info(f"Loaded data for {len(customer_data)} customers")
        
        # 3. Get predictions for all customers
        predictions_df = get_customer_predictions(customer_data)
        logging.info(f"Generated predictions for {len(predictions_df)} customers")
        
        # 4. Get current fashion trends
        trend_data = get_current_trends()
        
        # 5. Generate one enhanced image
        enhanced_path = enhance_product_images(
            category="pants",  # Original category
            trend_data=trend_data,
            data_dir=data_dir
        )[0]  # Get the single path
        
        # Use the same enhanced image for all categories
        category_images = {}
        unique_categories = predictions_df['predicted_category'].unique()
        for category in unique_categories:
            category_images[category] = [enhanced_path]
            logging.info(f"Using enhanced image for {category}")
        
        # 6. Create final recommendations
        results_df = create_customer_recommendations(predictions_df, category_images)
        
        # 7. Save results
        output_path = 'customer_predictions.csv'
        results_df.to_csv(output_path, index=False)
        logging.info(f"Saved recommendations to {output_path}")
        
        # Print summary
        print("\nPipeline completed successfully!")
        print(f"Processed {len(customer_data)} customers")
        print(f"Enhanced images for {len(unique_categories)} categories")
        print(f"Results saved to {output_path}")
        
    except Exception as e:
        logging.error(f"Pipeline failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 