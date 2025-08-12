"""
Update Manager - Handles incremental updates and git-friendly changes
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)


class UpdateManager:
    """Manages updates to model entries with git-friendly practices"""
    
    def __init__(self, models_root: Path = Path("models")):
        self.models_root = models_root
        self.update_log_path = Path("data/intermediate/update_log.json")
        self.update_log = self.load_update_log()
    
    def load_update_log(self) -> Dict:
        """Load the update log tracking what's been extracted"""
        if self.update_log_path.exists():
            with open(self.update_log_path, 'r') as f:
                return json.load(f)
        return {
            "services": {},
            "last_update": None
        }
    
    def save_update_log(self):
        """Save the update log"""
        self.update_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.update_log_path, 'w') as f:
            json.dump(self.update_log, f, indent=2)
    
    def should_update_service(self, service_name: str, new_data: Dict) -> bool:
        """
        Determine if a service should be updated based on:
        1. If it's never been updated
        2. If there's significantly new content
        3. If it's been more than X days since last update
        """
        service_key = service_name.lower().replace(' ', '-')
        
        # Always update if never seen before
        if service_key not in self.update_log.get("services", {}):
            logger.info(f"First time seeing {service_name}, will update")
            return True
        
        last_update = self.update_log["services"][service_key]
        
        # Check if enough time has passed (e.g., 7 days)
        last_date = datetime.fromisoformat(last_update["timestamp"])
        days_since = (datetime.now() - last_date).days
        if days_since > 7:
            logger.info(f"{service_name} hasn't been updated in {days_since} days, will update")
            return True
        
        # Check if we have significantly more content
        old_counts = last_update.get("content_counts", {})
        new_counts = {
            "tips": len(new_data.get("tips", [])),
            "problems": len(new_data.get("problems", [])),
            "cost_info": len(new_data.get("cost_info", [])),
            "settings": len(new_data.get("settings", []))
        }
        
        total_old = sum(old_counts.values())
        total_new = sum(new_counts.values())
        
        # Update if we have 30% more content
        if total_new > total_old * 1.3:
            logger.info(f"{service_name} has {total_new} items vs {total_old} before, will update")
            return True
        
        logger.info(f"{service_name} doesn't need update (last: {days_since} days ago, content: {total_new} vs {total_old})")
        return False
    
    def merge_with_existing(self, service_name: str, new_data: Dict, merge_strategy: str = "overwrite") -> Dict:
        """
        Merge new data with existing data
        
        Strategies:
        - overwrite: Replace everything (default, git-friendly)
        - merge: Combine lists, keeping unique items
        - augment: Only add new items, never remove
        """
        if merge_strategy == "overwrite":
            # Default behavior - complete replacement
            return new_data
        
        # For future: implement merge and augment strategies if needed
        # These would load existing files and combine data
        
        return new_data
    
    def record_update(self, service_name: str, data: Dict, extraction_stats: Dict = None):
        """Record that a service was updated"""
        service_key = service_name.lower().replace(' ', '-')
        
        self.update_log["services"][service_key] = {
            "timestamp": datetime.now().isoformat(),
            "content_counts": {
                "tips": len(data.get("tips", [])),
                "problems": len(data.get("problems", [])),
                "cost_info": len(data.get("cost_info", [])),
                "settings": len(data.get("settings", []))
            },
            "extraction_stats": extraction_stats or {},
            "content_hash": self.calculate_content_hash(data)
        }
        self.update_log["last_update"] = datetime.now().isoformat()
        self.save_update_log()
    
    def calculate_content_hash(self, data: Dict) -> str:
        """Calculate a hash of the content for change detection"""
        # Sort and serialize the content for consistent hashing
        content = {
            "tips": sorted(data.get("tips", [])),
            "problems": sorted(data.get("problems", [])),
            "cost_info": sorted(data.get("cost_info", [])),
            "settings": sorted(data.get("settings", []))
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def generate_update_summary(self) -> str:
        """Generate a summary of recent updates for git commit messages"""
        if not self.update_log.get("services"):
            return "Initial extraction"
        
        # Find services updated in this session
        now = datetime.now()
        recent_updates = []
        
        for service, info in self.update_log["services"].items():
            update_time = datetime.fromisoformat(info["timestamp"])
            if (now - update_time).seconds < 3600:  # Within last hour
                counts = info["content_counts"]
                total = sum(counts.values())
                recent_updates.append(f"{service} ({total} items)")
        
        if recent_updates:
            return f"Updated {len(recent_updates)} services: {', '.join(recent_updates[:3])}"
        return "Updated service documentation"
    
    def get_stale_services(self, days: int = 30) -> List[str]:
        """Get list of services that haven't been updated recently"""
        stale = []
        cutoff = datetime.now()
        
        for service, info in self.update_log.get("services", {}).items():
            update_time = datetime.fromisoformat(info["timestamp"])
            if (cutoff - update_time).days > days:
                stale.append(service)
        
        return stale
    
    def get_update_status(self) -> Dict:
        """Get overall update status for monitoring"""
        if not self.update_log.get("services"):
            return {
                "total_services": 0,
                "last_update": None,
                "stale_services": [],
                "recent_updates": []
            }
        
        now = datetime.now()
        recent = []
        stale = []
        
        for service, info in self.update_log["services"].items():
            update_time = datetime.fromisoformat(info["timestamp"])
            days_ago = (now - update_time).days
            
            if days_ago < 7:
                recent.append(service)
            elif days_ago > 30:
                stale.append(service)
        
        return {
            "total_services": len(self.update_log["services"]),
            "last_update": self.update_log.get("last_update"),
            "stale_services": stale,
            "recent_updates": recent,
            "update_frequency": self.calculate_update_frequency()
        }
    
    def calculate_update_frequency(self) -> str:
        """Calculate how often updates are happening"""
        if not self.update_log.get("services"):
            return "No updates yet"
        
        timestamps = [
            datetime.fromisoformat(info["timestamp"])
            for info in self.update_log["services"].values()
        ]
        
        if len(timestamps) < 2:
            return "Single update"
        
        timestamps.sort()
        total_span = (timestamps[-1] - timestamps[0]).days
        
        if total_span == 0:
            return "All updated today"
        
        avg_days = total_span / len(timestamps)
        return f"Average {avg_days:.1f} days between updates"


def test_update_manager():
    """Test the update manager"""
    manager = UpdateManager()
    
    # Test data
    sample_data = {
        "tips": ["Use API v2", "Set temperature to 0.7"],
        "problems": ["Rate limiting", "Memory issues"],
        "cost_info": ["$10/month"],
        "settings": ["max_tokens=500"]
    }
    
    # Check if update needed
    should_update = manager.should_update_service("Test Service", sample_data)
    print(f"Should update Test Service: {should_update}")
    
    # Record update
    manager.record_update("Test Service", sample_data, {"posts_analyzed": 50})
    
    # Get status
    status = manager.get_update_status()
    print(f"\nUpdate Status:")
    print(f"  Total services: {status['total_services']}")
    print(f"  Last update: {status['last_update']}")
    print(f"  Stale services: {status['stale_services']}")
    print(f"  Recent updates: {status['recent_updates']}")
    
    # Generate commit message
    commit_msg = manager.generate_update_summary()
    print(f"\nSuggested commit message: {commit_msg}")


if __name__ == "__main__":
    test_update_manager()