"""
Reddit data collector module for fashion trends.
"""

# Standard library imports
import os
import json
from datetime import datetime
from pathlib import Path
import re

# Third-party imports
import praw
from dotenv import load_dotenv

# Local imports
from .utils import get_data_path

class RedditCrawler:
    """Collects fashion-related data from Reddit."""
    
    # Subreddits to monitor for fashion trends
    SUBREDDITS = [
        'designporn',        # Design aesthetics
        'interiordesign',    # Interior spaces
        'photography',       # Photography techniques
        'streetwear',        # Urban style
        'malefashion',       # High-end menswear
        'femalefashion',     # High-end womenswear
        'womensstreetwear',  # Women's street fashion
        'japanesestreetwear' # Japanese influence
    ]
    
    # Collection parameters
    MAX_COMMENTS = 3
    DEFAULT_TIME_FILTER = 'week'
    DEFAULT_POST_LIMIT = 30
    
    # Keywords for filtering relevant content
    VISUAL_KEYWORDS = [
        # Physical environments
        'background', 'light', 'space', 'room', 'street', 'environment',
        'studio', 'outdoor', 'indoor', 'natural', 'artificial', 'urban',
        'architecture', 'interior', 'exterior',
        
        # Lighting conditions
        'lighting', 'sunlight', 'shadow', 'bright', 'dark', 'moody', 'dramatic',
        'soft', 'harsh', 'warm', 'cool', 'ambient', 'golden hour',
        
        # Style elements
        'aesthetic', 'mood', 'vibe', 'atmosphere', 'texture', 'pattern', 'color',
        'minimalist', 'modern', 'vintage', 'retro', 'contemporary', 'classic',
        
        # Visual composition
        'composition', 'perspective', 'depth', 'focus', 'sharp', 'contrast',
        'balance', 'symmetry', 'proportion', 'detail', 'silhouette', 'shape',
        
        # Materials and textures
        'wood', 'metal', 'glass', 'concrete', 'brick', 'stone', 'leather',
        'smooth', 'rough', 'matte', 'glossy', 'textured', 'patterned'
    ]
    
    def __init__(self):
        """Initialize Reddit crawler with API credentials."""
        load_dotenv()
        
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'VibeyCrawler/0.1')
        
        if not all([client_id, client_secret]):
            raise ValueError("Missing Reddit API credentials in .env file")
        
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Reddit client: {str(e)}")
    
    def _has_relevant_keywords(self, text):
        """Check if text contains visual keywords."""
        if not text:
            return False
        return any(keyword in text.lower() for keyword in self.VISUAL_KEYWORDS)
    
    def _clean_text(self, text):
        """Remove URLs and markdown from text."""
        if not text:
            return ""
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove markdown links
        text = re.sub(r'http\S+', '', text)         # Remove URLs
        return text.strip()
    
    def _extract_post_data(self, post):
        """Extract relevant data from a Reddit post.
        
        Args:
            post: PRAW post object
            
        Returns:
            dict: Post data (title, description, comments, score)
            None: If post is not relevant
        
        Raises:
            ValueError: If post object is invalid
        """
        if not post:
            raise ValueError("Invalid post object")
            
        try:
            title = post.title.strip()
            description = post.selftext.strip() if hasattr(post, 'selftext') else ""
            
            # Get top non-stickied comments
            post.comments.replace_more(limit=0)
            comments = []
            for comment in post.comments[:self.MAX_COMMENTS]:
                if comment.body.strip() and not comment.stickied:
                    comments.append(self._clean_text(comment.body))
            
            # Check relevance
            if not any([
                self._has_relevant_keywords(title),
                self._has_relevant_keywords(description),
                any(self._has_relevant_keywords(c) for c in comments)
            ]):
                return None
            
            return {
                "t": title,
                "d": description if description else None,
                "c": comments if comments else None,
                "s": post.score,
                "nc": post.num_comments
            }
        except Exception as e:
            print(f"Error extracting post data: {str(e)}")
            return None
    
    def get_trending_posts(self, time_filter=None, limit=None):
        """Collect trending fashion posts from monitored subreddits.
        
        Args:
            time_filter (str, optional): Time period to analyze (default: week)
            limit (int, optional): Maximum posts per subreddit (default: 10)
            
        Returns:
            list: Relevant fashion posts with metadata
            
        Raises:
            ConnectionError: If Reddit API is unavailable
        """
        time_filter = time_filter or self.DEFAULT_TIME_FILTER
        limit = limit or self.DEFAULT_POST_LIMIT
        all_posts = []
        
        for subreddit_name in self.SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = subreddit.top(time_filter=time_filter, limit=limit)
                
                for post in posts:
                    if post_data := self._extract_post_data(post):
                        all_posts.append(post_data)
                        
            except Exception as e:
                print(f"Error scraping r/{subreddit_name}: {str(e)}")
        
        if not all_posts:
            print("Warning: No relevant posts found")
        
        return all_posts
    
    def save_data(self, posts):
        """Save collected posts with timestamp.
        
        Args:
            posts (list): Post data to save
            
        Returns:
            str: Path to saved file
            None: If no posts to save
            
        Raises:
            IOError: If unable to save data
        """
        if not posts:
            return None
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            data_dir = get_data_path('reddit')
            output_file = data_dir / f"reddit_data_{timestamp}.json"
            
            data = {
                "ts": datetime.now().isoformat(),
                "p": posts
            }
            
            with open(output_file, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
            
            return str(output_file)
        except Exception as e:
            raise IOError(f"Failed to save data: {str(e)}")

def main():
    """Run Reddit crawler to collect fashion data."""
    try:
        crawler = RedditCrawler()
        posts = crawler.get_trending_posts()
        
        if saved_path := crawler.save_data(posts):
            print(f"Data saved to: {saved_path}")
        else:
            print("No data was collected.")
    except Exception as e:
        print(f"Error running crawler: {str(e)}")
        raise

if __name__ == "__main__":
    main() 