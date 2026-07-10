import json
from pathlib import Path

# Load data
with open('metadata/source-index.json', 'r') as f:
    source_index = json.load(f)

# Load SUMMARY.md to understand current structure
summary_path = Path('src/SUMMARY.md')
summary_content = summary_path.read_text()

# High quality candidates (score >= 16)
candidates = []
for item in source_index['files']:
    if item.get('score', 0) >= 16:
        # Check if unmapped or low confidence mapping
        mapped_chapters = item.get('mapped_chapters', [])
        if not mapped_chapters or len([c for c in mapped_chapters if c.get('confidence') in ['high', 'medium']]) == 0:
            candidates.append(item)

print(f"Total high quality candidates (>=16 score): {len(candidates)}")

# Evaluation function
def evaluate_candidate(candidate):
    score = 0
    
    # 1. Material richness (0-5 points)
    # Count related items in same category
    related_count = 0
    for other in source_index['files']:
        if (other != candidate and 
            other.get('score', 0) >= 16 and
            candidate.get('section') == other.get('section')):
            related_count += 1
    
    if related_count >= 3:
        score += 5
    elif related_count >= 2:
        score += 4
    elif related_count >= 1:
        score += 3
    else:
        score += 2
    
    # 2. Relevance to book objectives (0-5 points)
    section = candidate.get('section', '')
    title_lower = candidate.get('title', '').lower()
    
    # Core performance topics
    core_topics = ['memory', 'startup', 'rendering', 'gpu', 'cpu', 'power', 'anr', 'responsiveness']
    high_relevance_topics = ['network', 'storage', 'profiling']
    
    if any(topic in section.lower() or topic in title_lower for topic in core_topics):
        score += 5
    elif any(topic in section.lower() or topic in title_lower for topic in high_relevance_topics):
        score += 4
    else:
        score += 2
    
    # 3. Reader demand (0-5 points)
    # Based on topic popularity and interview frequency
    demand_topics = [
        'memory', 'startup', 'gpu', 'rendering', 'battery', 
        'anr', 'binder', 'profiling', 'optimization'
    ]
    
    if any(topic in title_lower for topic in demand_topics):
        score += 5
    elif 'ai' in title_lower or 'agent' in title_lower:
        score += 4  # AI is hot but might be more niche
    else:
        score += 2
    
    # 4. Timeliness (0-5 points)
    title_lower = candidate.get('title', '').lower()
    
    if 'android 17' in title_lower:
        score += 5
    elif '2026' in title_lower or 'ai' in title_lower:
        score += 4
    else:
        score += 2
    
    return score

# Evaluate all candidates
evaluated_candidates = []
for candidate in candidates:
    score = evaluate_candidate(candidate)
    evaluated_candidates.append({
        'title': candidate.get('title', ''),
        'score': score,
        'original_score': candidate.get('score', 0),
        'section': candidate.get('section', ''),
        'chapter': candidate.get('chapter', ''),
        'url': candidate.get('url', ''),
        'path': candidate.get('path', '')
    })

# Sort by score (descending)
qualified_candidates = [c for c in evaluated_candidates if c['score'] >= 14]
qualified_candidates.sort(key=lambda x: x['score'], reverse=True)

print(f"\nQualified candidates (>=14 points): {len(qualified_candidates)}")
print("\n" + "="*80)
print("QUALIFIED CANDIDATES ( ranked by score ):")
print("="*80)

for i, candidate in enumerate(qualified_candidates, 1):
    print(f"\n{i}. [Score: {candidate['score']}/20] {candidate['title']}")
    print(f"   Original score: {candidate['original_score']}")
    print(f"   Section: {candidate['section']}")
    print(f"   Chapter: {candidate['chapter']}")
    print(f"   URL/Path: {candidate['url'] or candidate['path']}")

if len(qualified_candidates) == 0:
    print("\n❌ No qualified candidates found (all < 14 points)")
    
print("\n" + "="*80)
print("NEXT STEPS:")
print("="*80)
if len(qualified_candidates) > 0:
    print("✅ Should create new chapters for all qualified candidates")
    print(f"✅ Total new chapters to create: {len(qualified_candidates)}")
else:
    print("❌ No new chapters should be created")
    print("💡 Consider exploring different directions or deeper analysis")