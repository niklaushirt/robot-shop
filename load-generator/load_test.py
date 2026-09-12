#!/usr/bin/env python3
"""
Load Generator for Checkout Recommendations Memory Leak Demo

This script generates load against the checkout-recommendations service
to trigger the memory leak by creating many unique cache entries.
"""

import requests
import time
import random
import sys
import argparse
from datetime import datetime
from typing import Dict, Any

# Service endpoints
RECOMMENDATIONS_URL = "http://checkout-recommendations:8080"
CART_URL = "http://cart:8080"
CATALOGUE_URL = "http://catalogue:8080"

# For local testing
if len(sys.argv) > 1 and sys.argv[1] == "--local":
    RECOMMENDATIONS_URL = "http://localhost:8080"
    CART_URL = "http://localhost:8080"
    CATALOGUE_URL = "http://localhost:8080"


class LoadGenerator:
    """Generate load to trigger memory leak in checkout-recommendations"""
    
    def __init__(self, base_url: str = RECOMMENDATIONS_URL):
        self.base_url = base_url
        self.request_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get current cache statistics"""
        try:
            response = requests.get(f"{self.base_url}/cache/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"Error getting cache stats: {e}", "ERROR")
        return {}
    
    def get_recommendations(self, cart_id: str) -> Dict[str, Any]:
        """Call recommendations API"""
        try:
            response = requests.get(
                f"{self.base_url}/recommendations/{cart_id}",
                timeout=10
            )
            self.request_count += 1
            
            if response.status_code == 200:
                return response.json()
            else:
                self.error_count += 1
                self.log(f"Error response: {response.status_code}", "WARN")
                
        except Exception as e:
            self.error_count += 1
            self.log(f"Request failed: {e}", "ERROR")
        
        return {}
    
    def generate_unique_cart_id(self) -> str:
        """Generate unique cart IDs to create different cache entries"""
        # Use timestamp and random to ensure uniqueness
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(1000, 9999)
        return f"cart-{timestamp}-{random_suffix}"
    
    def run_load_test(self, 
                      duration_minutes: int = 60,
                      requests_per_minute: int = 10,
                      use_unique_carts: bool = True):
        """
        Run load test to trigger memory leak
        
        Args:
            duration_minutes: How long to run the test
            requests_per_minute: Request rate
            use_unique_carts: If True, uses unique cart IDs (triggers leak faster)
        """
        self.log("=" * 70)
        self.log("🚀 Starting Memory Leak Load Test")
        self.log("=" * 70)
        self.log(f"Duration: {duration_minutes} minutes")
        self.log(f"Rate: {requests_per_minute} requests/minute")
        self.log(f"Unique carts: {use_unique_carts}")
        self.log(f"Target URL: {self.base_url}")
        self.log("=" * 70)
        
        end_time = time.time() + (duration_minutes * 60)
        delay_between_requests = 60.0 / requests_per_minute
        
        # Get initial cache stats
        initial_stats = self.get_cache_stats()
        self.log(f"Initial cache: {initial_stats.get('cache_entries', 0)} entries")
        
        try:
            while time.time() < end_time:
                # Generate cart ID
                if use_unique_carts:
                    cart_id = self.generate_unique_cart_id()
                else:
                    # Reuse same cart IDs (won't trigger leak as much)
                    cart_id = f"test-cart-{random.randint(1, 10)}"
                
                # Make request
                result = self.get_recommendations(cart_id)
                
                # Log progress every 10 requests
                if self.request_count % 10 == 0:
                    stats = self.get_cache_stats()
                    cache_entries = stats.get('cache_entries', 0)
                    cache_mb = stats.get('cache_size_mb', 0)
                    elapsed = time.time() - self.start_time
                    rate = self.request_count / elapsed * 60 if elapsed > 0 else 0
                    
                    self.log(
                        f"📊 Requests: {self.request_count} | "
                        f"Cache: {cache_entries} entries ({cache_mb:.2f} MB) | "
                        f"Rate: {rate:.1f} req/min | "
                        f"Errors: {self.error_count}"
                    )
                
                # Wait before next request
                time.sleep(delay_between_requests)
                
        except KeyboardInterrupt:
            self.log("\n⚠️  Test interrupted by user", "WARN")
        
        # Final statistics
        self.log("=" * 70)
        self.log("📈 Final Statistics")
        self.log("=" * 70)
        
        final_stats = self.get_cache_stats()
        elapsed = time.time() - self.start_time
        
        self.log(f"Total requests: {self.request_count}")
        self.log(f"Total errors: {self.error_count}")
        self.log(f"Duration: {elapsed/60:.1f} minutes")
        self.log(f"Average rate: {self.request_count/elapsed*60:.1f} req/min")
        self.log(f"Initial cache: {initial_stats.get('cache_entries', 0)} entries")
        self.log(f"Final cache: {final_stats.get('cache_entries', 0)} entries")
        self.log(f"Cache growth: {final_stats.get('cache_entries', 0) - initial_stats.get('cache_entries', 0)} entries")
        self.log(f"Final memory: {final_stats.get('cache_size_mb', 0):.2f} MB")
        self.log("=" * 70)
    
    def run_burst_test(self, burst_size: int = 100, num_bursts: int = 10):
        """
        Run burst test - send many requests quickly, then pause
        This simulates traffic spikes and accelerates memory leak
        """
        self.log("=" * 70)
        self.log("💥 Starting Burst Load Test")
        self.log("=" * 70)
        self.log(f"Burst size: {burst_size} requests")
        self.log(f"Number of bursts: {num_bursts}")
        self.log("=" * 70)
        
        initial_stats = self.get_cache_stats()
        
        for burst_num in range(1, num_bursts + 1):
            self.log(f"\n🔥 Burst {burst_num}/{num_bursts}")
            
            burst_start = time.time()
            
            for i in range(burst_size):
                cart_id = self.generate_unique_cart_id()
                self.get_recommendations(cart_id)
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{burst_size}", end="\r")
            
            burst_duration = time.time() - burst_start
            
            # Get stats after burst
            stats = self.get_cache_stats()
            self.log(
                f"  Completed in {burst_duration:.1f}s | "
                f"Cache: {stats.get('cache_entries', 0)} entries "
                f"({stats.get('cache_size_mb', 0):.2f} MB)"
            )
            
            # Pause between bursts
            if burst_num < num_bursts:
                self.log("  Pausing 30 seconds...")
                time.sleep(30)
        
        # Final stats
        final_stats = self.get_cache_stats()
        self.log("\n" + "=" * 70)
        self.log("📈 Burst Test Complete")
        self.log("=" * 70)
        self.log(f"Total requests: {self.request_count}")
        self.log(f"Cache growth: {final_stats.get('cache_entries', 0) - initial_stats.get('cache_entries', 0)} entries")
        self.log(f"Final memory: {final_stats.get('cache_size_mb', 0):.2f} MB")
        self.log("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Load generator for checkout-recommendations memory leak demo"
    )
    parser.add_argument(
        "--mode",
        choices=["sustained", "burst"],
        default="sustained",
        help="Load test mode (default: sustained)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in minutes for sustained test (default: 60)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=10,
        help="Requests per minute for sustained test (default: 10)"
    )
    parser.add_argument(
        "--burst-size",
        type=int,
        default=100,
        help="Number of requests per burst (default: 100)"
    )
    parser.add_argument(
        "--num-bursts",
        type=int,
        default=10,
        help="Number of bursts (default: 10)"
    )
    parser.add_argument(
        "--url",
        default=RECOMMENDATIONS_URL,
        help=f"Base URL for recommendations service (default: {RECOMMENDATIONS_URL})"
    )
    
    args = parser.parse_args()
    
    generator = LoadGenerator(base_url=args.url)
    
    if args.mode == "sustained":
        generator.run_load_test(
            duration_minutes=args.duration,
            requests_per_minute=args.rate
        )
    else:
        generator.run_burst_test(
            burst_size=args.burst_size,
            num_bursts=args.num_bursts
        )


if __name__ == "__main__":
    main()

# Made with Bob
