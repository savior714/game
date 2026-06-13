import sys
import os
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.sync_engine import LinearClient, load_env

def run():
    load_env()
    api_key = os.environ.get("LINEAR_API_KEY")
    client = LinearClient(api_key)
    teams = client.list_teams()
    team_id = teams[0]["id"]
    query = """
    query {
      team(id: "%s") {
        issues(first: 100) {
          nodes {
            id
            title
            identifier
          }
        }
      }
    }
    """ % team_id
    
    res = client._query(query)
    issues = res.get("team", {}).get("issues", {}).get("nodes", [])
    
    from scripts.linear_sync.lib.issue_factory import KOREAN_CHAR_RE, KOREAN_TRANSLATION_MAP
    
    count = 0
    for issue in issues:
        title = issue['title']
        original_title = title
        
        if "(상세 내용 참조)" in title:
            title = title.replace("(상세 내용 참조)", "").strip()
            
        title = re.sub(
            r"^(?:🗺️\s*)?(?:Project Blueprint|Blueprint|계획서)?\s*(?::\s*)?",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        
        if not KOREAN_CHAR_RE.search(title):
            words = re.split(r"([_\s\-]+)", title)
            translated_title = ""
            for word in words:
                if word.strip():
                    word_lower = word.lower()
                    if word_lower in KOREAN_TRANSLATION_MAP:
                        translated_title += KOREAN_TRANSLATION_MAP[word_lower]
                    else:
                        translated_title += word
                else:
                    translated_title += word
            
            title = translated_title.strip()
            if not KOREAN_CHAR_RE.search(title):
                title = f"{title} 관련 작업"
                
        if title != original_title:
            print(f"Updating {issue['identifier']}: '{original_title}' -> '{title}'")
            try:
                client.update_issue(issue['id'], title=title)
                count += 1
            except Exception as e:
                print(f"Failed to update {issue['identifier']}: {e}")
                
    print(f"Updated {count} issues.")

run()
