# Product Image Enhancer

An AI-powered pipeline that enhances product images based on current fashion trends and customer preferences.

## Overview

This project combines:
1. Customer purchase prediction using XGBoost
2. Design/fashion trend analysis using Groq API
3. Product image enhancement using Flux API

## Pipeline Steps

1. **Data Collection**
   - Collects fashion trends from Reddit using PRAW
   - Processes customer behavior data
   - Saves Reddit data with timestamp

2. **Purchase Prediction**
   - Uses XGBoost model to predict next purchases
   - Features include browsing history and purchase patterns
   - Outputs customer-category predictions with confidence scores

3. **Trend Analysis**
   - Analyzes Reddit data using Groq API (Mixtral-8x7b-32768)
   - Extracts environment, lighting, colors, and style trends
   - Generates structured scene descriptions

4. **Image Enhancement**
   - Uses professional photography parameters:
     - Camera: 85mm lens, f/4.0, sharp focus
     - Composition: Rule of thirds, medium depth, bokeh effect
     - Quality: 8K ultra-detailed output
   - Enhances product images using Flux API
   - Applies trend-based backgrounds

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/product_image_enhancer.git
   cd product_image_enhancer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.template` to `.env`:
     ```bash
     cp .env.template .env
     ```
   - Edit `.env` with your API keys:
     - Get Reddit API credentials from https://www.reddit.com/prefs/apps
     - Get Groq API key from https://console.groq.com
     - Get Flux API key from https://flux.ai

4. Create necessary directories:
   ```bash
   mkdir -p data/{raw_images,output/{masks,enhanced,debug},analysis}
   ```

5. Run the pipeline:
   ```bash
   python src/main.py
   ```

## Project Structure

```
product_image_enhancer/
├── src/                    # Source code
│   ├── mask_generator.py   # Mask creation logic
│   ├── background_generator.py  # Background enhancement
│   ├── fashion_trend_analyzer.py  # Trend analysis
│   └── reddit_data_collector.py   # Data collection
├── data/                   # Data directory
│   ├── raw_images/        # Input product images
│   └── output/            # Generated content
├── docs/                   # Documentation
└── tests/                 # Test files
```

## Security Note

This project requires several API keys to function. Never commit your `.env` file or expose your API keys. The `.env.template` file shows what environment variables are needed, but you must obtain your own API keys from the respective services.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 