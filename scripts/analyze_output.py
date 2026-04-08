#!/usr/bin/env python3
"""Quick analysis script for classification output."""

import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python analyze_output.py <output_file.json>")
    sys.exit(1)

output_file = Path(sys.argv[1])

with open(output_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Summary
meta = data['metadata']
print("\n" + "=" * 70)
print("CLASSIFICATION SUMMARY")
print("=" * 70)
print(f"Total posts:           {meta['total_posts']}")
print(f"Successful:            {meta['successful_classifications']}")
print(f"Failed:                {meta['failed_classifications']}")
print(f"Success rate:          {meta['successful_classifications']/meta['total_posts']*100:.1f}%")
print(f"Processing time:       {meta['processing_time_seconds']:.1f}s ({meta['processing_time_seconds']/60:.1f} minutes)")
print(f"Model:                 {meta['model_used']}")
print()

# Analyze complaints
complaints = [p for p in data['posts'] if p.get('classification') and p['classification']['is_complaint']]
non_complaints = [p for p in data['posts'] if p.get('classification') and not p['classification']['is_complaint']]

print("COMPLAINT ANALYSIS")
print("-" * 70)
print(f"Complaints:            {len(complaints)} ({len(complaints)/meta['successful_classifications']*100:.1f}%)")
print(f"Non-complaints:        {len(non_complaints)} ({len(non_complaints)/meta['successful_classifications']*100:.1f}%)")
print()

# Intensity breakdown
intensity_counts = {}
for p in data['posts']:
    if c := p.get('classification'):
        intensity = c['intensity']
        intensity_counts[intensity] = intensity_counts.get(intensity, 0) + 1

print("INTENSITY DISTRIBUTION")
print("-" * 70)
for intensity in ['low', 'medium', 'high']:
    count = intensity_counts.get(intensity, 0)
    pct = count / meta['successful_classifications'] * 100 if meta['successful_classifications'] > 0 else 0
    print(f"{intensity.capitalize():<10} {count:>4} ({pct:>5.1f}%)")
print()

# Top themes
theme_counts = {}
for p in complaints:
    theme = p['classification']['theme']
    theme_counts[theme] = theme_counts.get(theme, 0) + 1

print("ALL COMPLAINT THEMES")
print("-" * 70)
print(f"Total unique themes: {len(theme_counts)}")
print()
sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
for theme, count in sorted_themes:
    pct = count / len(complaints) * 100 if complaints else 0
    print(f"{count:>3} ({pct:>5.1f}%)  {theme}")
print()

# Sample complaints
print("SAMPLE COMPLAINTS (first 10)")
print("-" * 70)
for i, post in enumerate(complaints[:10], 1):
    # Title is nested in the 'post' dict
    title = post.get('post', {}).get('title', 'N/A')[:65]
    theme = post['classification']['theme']
    intensity = post['classification']['intensity']
    subreddit = post.get('subreddit', 'N/A')
    print(f"{i}. [{intensity}] {theme}")
    print(f"   r/{subreddit} | {title}...")
    print()

# Failed posts
failed = [p for p in data['posts'] if p.get('classification_error')]
if failed:
    print("\nFAILED POSTS")
print("-" * 70)
for i, post in enumerate(failed, 1):
    title = post.get('post', {}).get('title', 'N/A')[:65]
    error = post.get('classification_error', 'unknown')
    attempts = post.get('classification_attempts', 0)
    subreddit = post.get('subreddit', 'N/A')
    print(f"{i}. r/{subreddit} | {title}...")
    print(f"   Error: {error} (after {attempts} attempts)")
    print()

# High intensity complaints
high_intensity = [p for p in data['posts'] if p.get('classification') and p['classification']['intensity'] == 'high' and p['classification']['is_complaint']]
if len(high_intensity) > 10:
    print(f"\nHIGH INTENSITY COMPLAINTS (showing 10 of {len(high_intensity)})")
else:
    print(f"\nHIGH INTENSITY COMPLAINTS ({len(high_intensity)} total)")
    print("-" * 70)
for i, post in enumerate(high_intensity[:10], 1):
    title = post.get('post', {}).get('title', 'N/A')[:65]
    theme = post['classification']['theme']
    subreddit = post.get('subreddit', 'N/A')
    print(f"{i}. [{theme}]")
    print(f"   r/{subreddit} | {title}...")
    print()
