#!/usr/bin/env python3
"""
Sodalite News Management Script
Manages UI updates and news announcements for the Sodalite frontend
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# News types and their default configurations
NEWS_TYPES = {
    "outage": {
        "severity": "high",
        "icon": "alert-triangle",
        "color": "destructive",
        "show_when_offline": True
    },
    "maintenance": {
        "severity": "medium",
        "icon": "wrench",
        "color": "warning",
        "show_when_offline": True
    },
    "update": {
        "severity": "low",
        "icon": "info",
        "color": "primary",
        "show_when_offline": False
    },
    "announcement": {
        "severity": "low",
        "icon": "megaphone",
        "color": "primary",
        "show_when_offline": False
    }
}

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
COLORS = ["primary", "secondary", "destructive", "warning", "success"]
ICONS = ["info", "alert-triangle", "wrench", "megaphone", "check-circle", "x-circle"]

def load_news_file(file_path: str = "ui_updates.json") -> Dict[str, Any]:
    """Load existing news file or create new structure"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "news": []
        }
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)

def save_news_file(data: Dict[str, Any], file_path: str = "ui_updates.json") -> None:
    """Save news data to file"""
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ News updated successfully! Saved to {file_path}")

def add_news_item(
    title: str,
    message: str,
    news_type: str = "announcement",
    severity: str = None,
    duration_hours: int = 24,
    show_when_offline: bool = None,
    icon: str = None,
    color: str = None
) -> Dict[str, Any]:
    """Create a new news item"""

    # Get defaults from news type
    defaults = NEWS_TYPES.get(news_type, NEWS_TYPES["announcement"])

    # Generate unique ID
    timestamp = datetime.utcnow()
    news_id = f"{news_type}-{timestamp.strftime('%Y-%m-%d-%H%M%S')}"

    # Calculate expiration
    expires = timestamp + timedelta(hours=duration_hours)

    return {
        "id": news_id,
        "type": news_type,
        "severity": severity or defaults["severity"],
        "title": title,
        "message": message,
        "timestamp": timestamp.isoformat() + "Z",
        "expires": expires.isoformat() + "Z",
        "show_when_offline": show_when_offline if show_when_offline is not None else defaults["show_when_offline"],
        "icon": icon or defaults["icon"],
        "color": color or defaults["color"]
    }

def list_news_items(data: Dict[str, Any], show_expired: bool = False) -> None:
    """List all news items"""
    news_items = data.get("news", [])

    if not news_items:
        print("📰 No news items found.")
        return

    now = datetime.utcnow()
    active_items = []
    expired_items = []

    for item in news_items:
        expires = datetime.fromisoformat(item["expires"].replace("Z", "+00:00"))
        if expires > now:
            active_items.append(item)
        else:
            expired_items.append(item)

    print(f"📰 News Items (Last updated: {data.get('last_updated', 'Unknown')})")
    print("=" * 60)

    if active_items:
        print(f"\n🟢 Active Items ({len(active_items)}):")
        for item in active_items:
            print(f"  • [{item['severity'].upper()}] {item['title']}")
            print(f"    Type: {item['type']} | Expires: {item['expires']}")
            print(f"    Message: {item['message'][:80]}{'...' if len(item['message']) > 80 else ''}")
            print()

    if expired_items and show_expired:
        print(f"\n🔴 Expired Items ({len(expired_items)}):")
        for item in expired_items:
            print(f"  • [{item['severity'].upper()}] {item['title']}")
            print(f"    Type: {item['type']} | Expired: {item['expires']}")
            print()

def remove_news_item(data: Dict[str, Any], item_id: str) -> bool:
    """Remove a news item by ID"""
    news_items = data.get("news", [])
    original_length = len(news_items)

    data["news"] = [item for item in news_items if item["id"] != item_id]

    return len(data["news"]) < original_length

def cleanup_expired(data: Dict[str, Any]) -> int:
    """Remove expired news items"""
    now = datetime.utcnow()
    news_items = data.get("news", [])
    original_length = len(news_items)

    data["news"] = [
        item for item in news_items
        if datetime.fromisoformat(item["expires"].replace("Z", "+00:00")) > now
    ]

    removed_count = original_length - len(data["news"])
    return removed_count

def main():
    parser = argparse.ArgumentParser(description="Manage Sodalite UI news updates")
    parser.add_argument("--file", "-f", default="ui_updates.json", help="News file path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add news command
    add_parser = subparsers.add_parser("add", help="Add a news item")
    add_parser.add_argument("title", help="News title")
    add_parser.add_argument("message", help="News message")
    add_parser.add_argument("--type", choices=list(NEWS_TYPES.keys()),
                           default="announcement", help="News type")
    add_parser.add_argument("--severity", choices=SEVERITY_LEVELS, help="Severity level")
    add_parser.add_argument("--hours", type=int, default=24, help="Duration in hours")
    add_parser.add_argument("--offline", action="store_true", help="Show when offline")
    add_parser.add_argument("--icon", choices=ICONS, help="Icon name")
    add_parser.add_argument("--color", choices=COLORS, help="Color theme")

    # List news command
    list_parser = subparsers.add_parser("list", help="List news items")
    list_parser.add_argument("--expired", action="store_true", help="Show expired items")

    # Remove news command
    remove_parser = subparsers.add_parser("remove", help="Remove a news item")
    remove_parser.add_argument("item_id", help="News item ID to remove")

    # Cleanup command
    subparsers.add_parser("cleanup", help="Remove expired news items")

    # Quick commands for common scenarios
    outage_parser = subparsers.add_parser("outage", help="Quick add server outage")
    outage_parser.add_argument("message", help="Outage message")
    outage_parser.add_argument("--hours", type=int, default=12, help="Expected duration")

    maintenance_parser = subparsers.add_parser("maintenance", help="Quick add maintenance")
    maintenance_parser.add_argument("message", help="Maintenance message")
    maintenance_parser.add_argument("--hours", type=int, default=6, help="Expected duration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load existing data
    data = load_news_file(args.file)

    if args.command == "add":
        news_item = add_news_item(
            title=args.title,
            message=args.message,
            news_type=args.type,
            severity=args.severity,
            duration_hours=args.hours,
            show_when_offline=args.offline,
            icon=args.icon,
            color=args.color
        )
        data["news"].append(news_item)
        save_news_file(data, args.file)
        print(f"📰 Added news item: {args.title}")

    elif args.command == "list":
        list_news_items(data, args.expired)

    elif args.command == "remove":
        if remove_news_item(data, args.item_id):
            save_news_file(data, args.file)
            print(f"🗑️  Removed news item: {args.item_id}")
        else:
            print(f"❌ News item not found: {args.item_id}")

    elif args.command == "cleanup":
        removed = cleanup_expired(data)
        if removed > 0:
            save_news_file(data, args.file)
            print(f"🧹 Removed {removed} expired news items")
        else:
            print("✨ No expired items to remove")

    elif args.command == "outage":
        news_item = add_news_item(
            title="Server Outage",
            message=args.message,
            news_type="outage",
            duration_hours=args.hours
        )
        data["news"].append(news_item)
        save_news_file(data, args.file)
        print(f"🚨 Added outage notice: {args.message}")

    elif args.command == "maintenance":
        news_item = add_news_item(
            title="Scheduled Maintenance",
            message=args.message,
            news_type="maintenance",
            duration_hours=args.hours
        )
        data["news"].append(news_item)
        save_news_file(data, args.file)
        print(f"🔧 Added maintenance notice: {args.message}")

if __name__ == "__main__":
    main()
