import sqlite3
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class LinearProvider:
    """
    Provides read access to Linear issues via a local SQLite mirror DB
    instead of polling the Linear API directly.
    """
    
    # The minimal GraphQL query fields needed for the local DB mirror
    MINIMAL_ISSUE_QUERY = """
    query Issue($identifier: String!) {
      issue(id: $identifier) {
        id
        identifier
        title
        state {
          name
        }
        priority
      }
    }
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_issue(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single issue by its identifier from the local mirror DB.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, identifier, title, state, priority
                FROM issues
                WHERE identifier = ?
            ''', (identifier,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
