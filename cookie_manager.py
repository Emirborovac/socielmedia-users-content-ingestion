"""
Cookie Manager Module - Handles cookie rotation and failure tracking

This module manages cookies for social media scraping:
- Tracks cookie failures
- Rotates to next available cookie
- Burns cookies after 3 failures
- Platform-specific cookie management
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Optional, List


class CookieManager:
    """Manages cookies for a specific social media platform"""
    
    def __init__(self, platform: str):
        """
        Initialize cookie manager for a platform.
        
        Args:
            platform: Platform name (instagram, tiktok, facebook, x, youtube)
        """
        self.platform = platform.lower()
        self.base_path = Path(f"./cookies/{self.platform}")
        self.active_path = self.base_path / "active"
        self.burnt_path = self.base_path / "burnt"
        self.failures_file = self.base_path / "cookie_failures.json"
        
        # Ensure directories exist
        self.active_path.mkdir(parents=True, exist_ok=True)
        self.burnt_path.mkdir(parents=True, exist_ok=True)
        
        # Load failure tracking data
        self.failures = self._load_failures()
    
    def _load_failures(self) -> dict:
        """Load cookie failure counts from JSON file"""
        if self.failures_file.exists():
            try:
                with open(self.failures_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Could not load failures file: {e}")
                return {}
        return {}
    
    def _save_failures(self):
        """Save cookie failure counts to JSON file"""
        try:
            with open(self.failures_file, 'w') as f:
                json.dump(self.failures, f, indent=2)
        except Exception as e:
            logging.error(f"Could not save failures file: {e}")
    
    def get_active_cookies(self) -> List[Path]:
        """
        Get list of all active cookie files.
        
        Returns:
            List of Path objects for cookie files
        """
        cookie_files = []
        
        # Get all .txt files in active directory
        for file_path in self.active_path.glob("*.txt"):
            if file_path.is_file():
                cookie_files.append(file_path)
        
        # Sort by name for consistent ordering
        cookie_files.sort()
        
        return cookie_files
    
    def get_active_cookie(self) -> Optional[str]:
        """
        Get path to an available active cookie file.
        Prioritizes cookies with fewer failures.
        
        Returns:
            String path to cookie file, or None if no cookies available
        """
        active_cookies = self.get_active_cookies()
        
        if not active_cookies:
            logging.error(f"No active cookies found for {self.platform}")
            return None
        
        # Sort by failure count (lowest first)
        active_cookies.sort(key=lambda p: self.get_failure_count(str(p)))
        
        # Return the cookie with lowest failures
        selected_cookie = str(active_cookies[0])
        logging.info(f"Selected cookie: {selected_cookie} (failures: {self.get_failure_count(selected_cookie)})")
        
        return selected_cookie
    
    def get_failure_count(self, cookie_path: str) -> int:
        """
        Get failure count for a specific cookie.
        
        Args:
            cookie_path: Path to cookie file
            
        Returns:
            Number of failures for this cookie
        """
        # Use filename as key (more reliable than full path)
        cookie_name = Path(cookie_path).name
        return self.failures.get(cookie_name, 0)
    
    def mark_failure(self, cookie_path: str) -> int:
        """
        Mark a failure for a cookie and check if it should be burned.
        
        Args:
            cookie_path: Path to cookie file that failed
            
        Returns:
            New failure count for this cookie
        """
        cookie_name = Path(cookie_path).name
        
        # Increment failure count
        current_failures = self.failures.get(cookie_name, 0)
        new_failures = current_failures + 1
        self.failures[cookie_name] = new_failures
        
        # Save to disk
        self._save_failures()
        
        logging.warning(f"Cookie {cookie_name} failure #{new_failures}")
        
        # Check if should burn (3+ failures)
        if new_failures >= 3:
            logging.error(f"Cookie {cookie_name} has {new_failures} failures - burning it!")
            self.burn_cookie(cookie_path)
        
        return new_failures
    
    def mark_success(self, cookie_path: str):
        """
        Mark a successful operation - reset failure count.
        
        Args:
            cookie_path: Path to cookie file that succeeded
        """
        cookie_name = Path(cookie_path).name
        
        # Reset failure count
        if cookie_name in self.failures:
            old_count = self.failures[cookie_name]
            self.failures[cookie_name] = 0
            self._save_failures()
            logging.info(f"Cookie {cookie_name} success - reset failure count from {old_count} to 0")
    
    def burn_cookie(self, cookie_path: str) -> bool:
        """
        Move a cookie to the burnt folder.
        
        Args:
            cookie_path: Path to cookie file to burn
            
        Returns:
            True if successfully burned, False otherwise
        """
        try:
            source = Path(cookie_path)
            
            if not source.exists():
                logging.error(f"Cookie file does not exist: {cookie_path}")
                return False
            
            # Move to burnt folder
            destination = self.burnt_path / source.name
            shutil.move(str(source), str(destination))
            
            logging.info(f"🔥 Burned cookie: {source.name} -> burnt folder")
            
            # Remove from failures tracking (it's burnt now)
            cookie_name = source.name
            if cookie_name in self.failures:
                del self.failures[cookie_name]
                self._save_failures()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to burn cookie {cookie_path}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get statistics about cookie status.
        
        Returns:
            Dictionary with cookie statistics
        """
        active_cookies = self.get_active_cookies()
        burnt_cookies = list(self.burnt_path.glob("*.txt"))
        
        return {
            "platform": self.platform,
            "active_count": len(active_cookies),
            "burnt_count": len(burnt_cookies),
            "active_cookies": [p.name for p in active_cookies],
            "failures": self.failures
        }

