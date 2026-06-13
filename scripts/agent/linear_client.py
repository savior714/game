import time
import random
import logging
from typing import Dict, Any, Optional
import requests

from scripts.observability.api_errors import api_error_timer

logger = logging.getLogger(__name__)

class LinearClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.linear.app/graphql"
        
    def execute_write(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a GraphQL write mutation to Linear API with exponential backoff.
        Retries up to 5 times on 429 errors with delays: 1, 2, 4, 8, 16 seconds + jitter.
        """
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                with api_error_timer("linear", "POST", self.base_url, retry_count=attempt):
                    response = requests.post(
                        self.base_url,
                        json={"query": query, "variables": variables or {}},
                        headers=headers,
                        timeout=10
                    )
                
                if response.status_code == 429:
                    if attempt == max_retries:
                        response.raise_for_status()
                        
                    # Calculate delay: 2^attempt (1, 2, 4, 8, 16) + jitter
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    logger.warning(f"Rate limited (429). Retrying in {delay:.2f}s (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                # Retry on 429 HTTPError
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 429:
                    if attempt == max_retries:
                        raise
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    logger.warning(f"Rate limited (429). Retrying in {delay:.2f}s (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    raise

