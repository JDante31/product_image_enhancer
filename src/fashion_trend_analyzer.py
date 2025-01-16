"""
Fashion trend analyzer module.
"""

# Standard library imports
import json
import time
from datetime import datetime
import re
from pathlib import Path
import os

# Third-party imports
from groq import Groq
from dotenv import load_dotenv
import tiktoken
from nltk.corpus import stopwords
import nltk

# Local imports
from src.config.llm_prompts import get_prompt_with_data
from src.config.generation_config import enhance_llama_prompt
from src.utils import get_data_path

class TrendAnalyzer:
    """Analyzes fashion trends from Reddit data using the Groq API."""
    
    # Analysis limits
    MAX_TOKENS = 5000
    MAX_POSTS = 50
    MAX_TITLE_WORDS = 15
    MAX_DESC_WORDS = 30
    MAX_COMMENT_WORDS = 20
    MAX_COMMENTS = 3
    
    def __init__(self):
        """Initialize the analyzer with API credentials."""
        load_dotenv()
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=self.api_key)
    
    def _count_tokens(self, text):
        """Count tokens in text using tiktoken."""
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text.split()) * 1.3
    
    def _retry_with_backoff(self, func, max_retries=3, initial_delay=1):
        """Retry a function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"\nRate limit hit. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                raise e
    
    def _load_latest_reddit_data(self):
        """Load the most recent Reddit data file."""
        data_dir = get_data_path('reddit')
        files = list(data_dir.glob("reddit_data_*.json"))
        latest_file = max(files)
        with open(latest_file) as f:
            data = json.load(f)
        return data['p']
    
    def _clean_text(self, text):
        """Clean and normalize text for analysis."""
        # Common words to remove
        stop_words = set(stopwords.words('english'))
        stop_words.update({
            'http', 'https', 'www', 'com', 'reddit', 'imgur',
            'edit', 'deleted', 'removed', 'comment', 'post',
            'think', 'know', 'like', 'just', 'want', 'got',
            'really', 'would', 'could', 'should', 'much',
            'lol', 'lmao', 'tbh', 'imo', 'imho', 'til',
            'today', 'yesterday', 'tomorrow', 'week', 'month'
        })
        
        # Clean text
        text = text.lower()
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        
        words = [
            word for word in text.split()
            if word not in stop_words
            and len(word) > 2
            and not all(c == word[0] for c in word)
        ]
        
        return ' '.join(words)
    
    def _prepare_reddit_data(self, posts):
        """Filter and clean Reddit posts for analysis."""
        # Sort by engagement
        sorted_posts = sorted(
            posts,
            key=lambda x: x['s'] + x['nc'],
            reverse=True
        )
        
        filtered_posts = []
        for post in sorted_posts[:self.MAX_POSTS]:
            if cleaned_title := self._clean_text(post['t']):
                filtered_post = {
                    "t": ' '.join(cleaned_title.split()[:self.MAX_TITLE_WORDS])
                }
                
                if post.get('d'):
                    if cleaned_desc := self._clean_text(post['d']):
                        filtered_post['d'] = ' '.join(
                            cleaned_desc.split()[:self.MAX_DESC_WORDS]
                        )
                
                if post.get('c'):
                    cleaned_comments = []
                    for comment in post['c'][:self.MAX_COMMENTS]:
                        if cleaned_comment := self._clean_text(comment):
                            cleaned_comments.append(
                                ' '.join(cleaned_comment.split()[:self.MAX_COMMENT_WORDS])
                            )
                    if cleaned_comments:
                        filtered_post['c'] = cleaned_comments
                
                filtered_posts.append(filtered_post)
        
        return filtered_posts
    
    def analyze_trends(self):
        """Analyze fashion trends from Reddit data.
        
        Returns:
            str: Path to the saved analysis results file
        """
        # Load and prepare data
        posts = self._load_latest_reddit_data()
        filtered_posts = self._prepare_reddit_data(posts)
        
        # Prepare prompt
        reddit_data_str = json.dumps(filtered_posts, separators=(',', ':'))
        prompt = get_prompt_with_data(reddit_data_str)
        
        # Check token limit
        prompt_tokens = self._count_tokens(prompt)
        if prompt_tokens > self.MAX_TOKENS:
            raise ValueError("Prompt too long for context window")
        
        # Make API call
        def make_api_call():
            return self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1000,
                top_p=1,
                response_format={"type": "json_object"}
            )
        
        # Get and process response
        completion = self._retry_with_backoff(make_api_call)
        response_tokens = self._count_tokens(completion.choices[0].message.content)
        scene_data = json.loads(completion.choices[0].message.content)
        
        enhanced_prompt = enhance_llama_prompt(scene_data)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = get_data_path('analysis')
        output_file = output_dir / f"trend_analysis_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'scene_description': scene_data,
                'enhanced_prompt': enhanced_prompt,
                'token_usage': {
                    'prompt_tokens': prompt_tokens,
                    'response_tokens': response_tokens,
                    'total_tokens': prompt_tokens + response_tokens
                }
            }, f, indent=2)
        
        return str(output_file)
    
    def generate_category_prompts(self, category, trend_data):
        """Generate prompts for a specific product category based on trend data.
        
        Args:
            category (str): Product category (e.g., 'pants', 'shoes')
            trend_data (str): Path to trend analysis file
            
        Returns:
            str: Enhanced prompt for the category
        """
        # Load trend data
        with open(trend_data) as f:
            data = json.load(f)
        
        # Get base prompt
        base_prompt = data['enhanced_prompt']
        
        # Add category-specific elements
        category_prompt = f"{base_prompt}\nProduct category: {category}"
        
        return category_prompt

def main():
    """Run the trend analyzer."""
    analyzer = TrendAnalyzer()
    analysis_file = analyzer.analyze_trends()
    print(f"Analysis saved to: {analysis_file}")

if __name__ == "__main__":
    main() 