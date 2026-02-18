#!/usr/bin/env python3
"""
Smart recall system for automatic context retrieval.
Extracts topics from current context and searches relevant sessions.
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Set
from collections import Counter
import time

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from search_index import search_sessions
from telemetry import get_collector, get_current_session_id
from quality_scoring.scorer import QualityScorer


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from text.

    Args:
        text: Input text to analyze
        min_length: Minimum keyword length
        max_keywords: Maximum keywords to return

    Returns:
        List of important keywords
    """
    # Convert to lowercase
    text_lower = text.lower()

    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
        'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
        'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
        'few', 'more', 'most', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now', 'get',
        'make', 'go', 'see', 'know', 'take', 'use', 'find', 'give', 'tell',
        'work', 'call', 'try', 'ask', 'need', 'feel', 'become', 'leave',
        'put', 'mean', 'keep', 'let', 'begin', 'seem', 'help', 'talk',
        'turn', 'start', 'show', 'move', 'like', 'live', 'believe',
        'happen', 'write', 'sit', 'stand', 'lose', 'pay', 'meet', 'run',
        'im', 'ive', 'id', 'ill', 'youre', 'youve', 'youd', 'youll',
        'hes', 'shes', 'its', 'were', 'theyre', 'theyve', 'theyd',
        'dont', 'doesnt', 'didnt', 'wont', 'wouldnt', 'couldnt', 'shouldnt',
        'cant', 'cannot', 'isnt', 'arent', 'wasnt', 'werent', 'hasnt', 'havent'
    }

    # Extract words
    words = re.findall(r'\b[a-z]+\b', text_lower)

    # Filter by length and stop words
    filtered_words = [
        word for word in words
        if len(word) >= min_length and word not in stop_words
    ]

    # Count frequency
    word_counts = Counter(filtered_words)

    # Get top keywords
    top_keywords = [word for word, count in word_counts.most_common(max_keywords)]

    return top_keywords


def extract_technical_terms(text: str) -> Set[str]:
    """
    Extract technical terms and acronyms from text.

    Args:
        text: Input text

    Returns:
        Set of technical terms
    """
    terms = set()

    # Find acronyms (2-5 uppercase letters)
    acronyms = re.findall(r'\b[A-Z]{2,5}\b', text)
    terms.update(acronym.lower() for acronym in acronyms)

    # Find camelCase/PascalCase terms
    camel_case = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b|\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', text)
    terms.update(term.lower() for term in camel_case)

    # Find snake_case terms
    snake_case = re.findall(r'\b[a-z]+_[a-z_]+\b', text)
    terms.update(term for term in snake_case)

    # Find kebab-case terms
    kebab_case = re.findall(r'\b[a-z]+-[a-z-]+\b', text)
    terms.update(term for term in kebab_case)

    # Find file extensions and tech keywords
    tech_patterns = [
        r'\b(?:python|javascript|typescript|react|vue|angular|django|flask|fastapi|node|npm|pip|docker|kubernetes|aws|azure|gcp)\b',
        r'\b(?:api|rest|graphql|sql|nosql|database|redis|mongodb|postgres|mysql)\b',
        r'\b(?:git|github|gitlab|ci|cd|devops|testing|pytest|jest|unit|integration)\b',
        r'\b(?:frontend|backend|fullstack|microservice|serverless|cloud)\b',
        r'\b(?:security|authentication|authorization|oauth|jwt|encryption)\b',
        r'\b(?:performance|optimization|scaling|caching|monitoring)\b'
    ]

    for pattern in tech_patterns:
        matches = re.findall(pattern, text.lower())
        terms.update(matches)

    return terms


def analyze_context(context_text: str) -> Dict[str, any]:
    """
    Analyze context text and extract search terms.

    Args:
        context_text: Text to analyze

    Returns:
        Dictionary with keywords, technical terms, and suggested query
    """
    # Extract keywords
    keywords = extract_keywords(context_text, max_keywords=10)

    # Extract technical terms
    tech_terms = extract_technical_terms(context_text)

    # Combine for search query
    all_terms = list(set(keywords) | tech_terms)

    # Create search query (top 5 most relevant terms)
    # Prioritize technical terms, then keywords
    priority_terms = list(tech_terms)[:3] + keywords[:2]
    search_query = ' '.join(priority_terms[:5])

    return {
        'keywords': keywords,
        'tech_terms': list(tech_terms),
        'all_terms': all_terms,
        'search_query': search_query
    }


def smart_recall(
    context_text: str = None,
    index_path: Path = None,
    search_mode: str = "auto",
    limit: int = 3,
    min_relevance: float = 0.3,
    verbose: bool = False
) -> List[Dict]:
    """
    Smart recall: analyze context and search for relevant sessions.

    Args:
        context_text: Context to analyze (from beads, git, or user input)
        index_path: Path to session index
        search_mode: Search mode (auto/hybrid/bm25/semantic)
        limit: Maximum results to return
        min_relevance: Minimum relevance score threshold
        verbose: Print analysis details

    Returns:
        List of relevant sessions with scores
    """
    # Initialize telemetry
    collector = get_collector()
    start_time = time.time()

    if index_path is None:
        index_path = Path(".claude/context/sessions/index.json")
        if not index_path.is_absolute():
            index_path = Path.cwd() / index_path

    if not index_path.exists():
        if verbose:
            print("No session index found. Run auto_capture.py to create sessions.", file=sys.stderr)
        return []

    # If no context provided, try to infer from environment
    if context_text is None:
        context_text = infer_context()

    if not context_text:
        if verbose:
            print("No context to analyze.", file=sys.stderr)
        return []

    # Analyze context
    analysis = analyze_context(context_text)

    # Log context analysis telemetry
    analysis_time_ms = (time.time() - start_time) * 1000
    collector.log_event({
        "event_id": None,  # Will be generated by log_event
        "event_type": "context_analyzed",
        "trigger_source": "smart_recall",
        "trigger_mode": "proactive" if context_text is None else "manual",
        "session_id": get_current_session_id(),
        "context": {
            "context_length": len(context_text),
            "keywords": analysis['keywords'][:5],  # Top 5
            "technical_terms": analysis['tech_terms'][:5],  # Top 5
            "search_query": analysis['search_query']
        },
        "performance": {
            "analysis_time_ms": analysis_time_ms
        }
    })

    if verbose:
        print("\n=== Smart Recall Analysis ===", file=sys.stderr)
        print(f"Keywords: {', '.join(analysis['keywords'][:5])}", file=sys.stderr)
        print(f"Technical terms: {', '.join(analysis['tech_terms'][:5])}", file=sys.stderr)
        print(f"Search query: {analysis['search_query']}", file=sys.stderr)
        print("=" * 50 + "\n", file=sys.stderr)

    # Search for relevant sessions
    search_start = time.time()
    results = search_sessions(
        query=analysis['search_query'],
        index_path=index_path,
        search_mode=search_mode,
        limit=limit * 2  # Get more results, then filter by relevance
    )
    search_time_ms = (time.time() - search_start) * 1000

    # Filter by minimum relevance
    filtered_results = [
        result for result in results
        if result.get('relevance_score', 0) >= min_relevance
    ]

    # Return top N results
    final_results = filtered_results[:limit]

    # Log smart recall completion telemetry (will update with excerpt stats after formatting)
    total_time_ms = (time.time() - start_time) * 1000
    event_id = collector.start_event(
        event_type="smart_recall_completed",
        context={
            "trigger_source": "smart_recall",
            "trigger_mode": "proactive" if context_text is None else "manual",
            "session_id": get_current_session_id(),
            "query": {
                "raw_query": analysis['search_query'],
                "extracted_keywords": analysis['keywords'][:5],
                "technical_terms": analysis['tech_terms'][:5]
            },
            "search_config": {
                "mode": search_mode,
                "limit": limit,
                "min_relevance": min_relevance
            },
            "results": {
                "count": len(final_results),
                "retrieved_sessions": [r['id'] for r in final_results],
                "filtered_from": len(results),
                "filtered_out": len(filtered_results) - len(final_results)
            },
            "performance": {
                "total_latency_ms": total_time_ms,
                "breakdown": {
                    "analysis_ms": analysis_time_ms,
                    "search_ms": search_time_ms
                }
            }
        }
    )

    # Store event_id in results for later update with excerpt stats
    for result in final_results:
        result['_recall_event_id'] = event_id

    # Quality evaluation (gated by sampling rate and budget)
    try:
        scorer = QualityScorer()
        scorer.evaluate(
            event_id=event_id or '',
            query=analysis['search_query'],
            results=final_results,
            config_dict={'mode': search_mode, 'limit': limit},
        )
    except Exception:
        pass  # Non-fatal — never block recall for quality scoring

    collector.end_event(event_id, outcome={"success": True})

    return final_results


def infer_context() -> str:
    """
    Infer context from environment (beads issues, git status, etc.).

    Returns:
        Inferred context text
    """
    context_parts = []

    # Try to get open beads issues
    try:
        from subprocess import run, PIPE
        result = run(['bd', 'list', '--status=open', '--status=in_progress'],
                    capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            context_parts.append(result.stdout)
    except Exception:
        pass

    # Try to get recent git commits
    try:
        result = run(['git', 'log', '-5', '--oneline'],
                    capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            context_parts.append(result.stdout)
    except Exception:
        pass

    # Try to get git branch name
    try:
        result = run(['git', 'branch', '--show-current'],
                    capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            context_parts.append(result.stdout.strip())
    except Exception:
        pass

    return '\n'.join(context_parts)


def format_recall_output(results: List[Dict], context_text: str = None, include_excerpts: bool = True) -> tuple[str, Dict]:
    """
    Format recall results for display.

    Args:
        results: Search results
        context_text: Original context (optional)
        include_excerpts: Whether to include transcript excerpts (default: True)

    Returns:
        Tuple of (formatted output string, excerpt stats dict)
    """
    if not results:
        return "No relevant sessions found.", {}

    output = []
    output.append("=" * 60)
    output.append("🧠 Smart Recall: Relevant Context Found")
    output.append("=" * 60)

    if context_text:
        analysis = analyze_context(context_text)
        output.append(f"\n📊 Analyzed: {', '.join(analysis['tech_terms'][:3] + analysis['keywords'][:2])}")

    output.append(f"\n🔍 Found {len(results)} relevant session(s):\n")

    # Try to import transcript extraction
    extract_context_fn = None
    if include_excerpts:
        try:
            from extract_transcript_context import extract_relevant_context
            extract_context_fn = extract_relevant_context
        except ImportError:
            pass

    # Track excerpt statistics
    import time as time_module
    excerpt_stats = {
        "enabled": include_excerpts and extract_context_fn is not None,
        "sessions_with_excerpts": 0,
        "total_sessions": len(results),
        "total_excerpt_chars": 0,
        "total_extraction_time_ms": 0,
        "excerpts_by_session": []
    }

    for i, result in enumerate(results, 1):
        score = result.get('relevance_score', 0)
        confidence = "HIGH" if score > 0.7 else "MEDIUM" if score > 0.4 else "LOW"

        output.append(f"{i}. {result['id']} (Score: {score:.2f} {confidence})")
        output.append(f"   Summary: {result['summary']}")
        output.append(f"   Topics: {', '.join(result['topics'][:5])}")

        # Show score breakdown if available
        if 'bm25_score' in result and 'semantic_score' in result:
            output.append(f"   BM25: {result['bm25_score']:.2f} | "
                        f"Semantic: {result['semantic_score']:.2f} | "
                        f"Mode: {result.get('search_mode', 'unknown')}")

        # Extract and show relevant transcript excerpts
        if extract_context_fn and context_text:
            sessions_dir = Path(".claude/context/sessions")
            if not sessions_dir.is_absolute():
                sessions_dir = Path.cwd() / sessions_dir

            excerpt_start = time_module.time()
            excerpt = extract_context_fn(
                session_file=result['file'],
                query=context_text,
                sessions_dir=sessions_dir,
                max_excerpts=2,
                max_chars_per_excerpt=800
            )
            excerpt_time_ms = (time_module.time() - excerpt_start) * 1000

            if excerpt:
                output.append("")
                output.append(excerpt)

                # Track stats
                excerpt_stats["sessions_with_excerpts"] += 1
                excerpt_stats["total_excerpt_chars"] += len(excerpt)
                excerpt_stats["total_extraction_time_ms"] += excerpt_time_ms
                excerpt_stats["excerpts_by_session"].append({
                    "session_id": result['id'],
                    "char_count": len(excerpt),
                    "extraction_ms": round(excerpt_time_ms, 2)
                })

        output.append(f"   File: .claude/context/sessions/{result['file']}")
        output.append("")

    output.append("=" * 60)
    if include_excerpts and extract_context_fn:
        output.append("✅ Shown: Metadata + relevant conversation excerpts")
        output.append("💡 Use Read tool on transcript .jsonl files for complete conversation history")
    else:
        output.append("💡 Use Read tool to view full session files for more details")
    output.append("=" * 60)

    # Calculate summary stats
    if excerpt_stats["sessions_with_excerpts"] > 0:
        excerpt_stats["avg_chars_per_session"] = round(
            excerpt_stats["total_excerpt_chars"] / excerpt_stats["sessions_with_excerpts"]
        )
        excerpt_stats["avg_extraction_ms"] = round(
            excerpt_stats["total_extraction_time_ms"] / excerpt_stats["sessions_with_excerpts"], 2
        )

    return '\n'.join(output), excerpt_stats


def main():
    """CLI interface for smart recall."""
    import argparse

    parser = argparse.ArgumentParser(description='Smart context recall')
    parser.add_argument('--context', help='Context text to analyze')
    parser.add_argument('--context-file', help='Read context from file')
    parser.add_argument('--index', default='.claude/context/sessions/index.json', help='Index path')
    parser.add_argument('--mode', default='auto', choices=['auto', 'hybrid', 'bm25', 'semantic'])
    parser.add_argument('--limit', type=int, default=3, help='Max results')
    parser.add_argument('--min-relevance', type=float, default=0.3, help='Min relevance score')
    parser.add_argument('--verbose', action='store_true', help='Show analysis details')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    # Get collector for flush at end
    collector = get_collector()

    # Get context
    context_text = args.context
    if args.context_file:
        context_text = Path(args.context_file).read_text()

    # Resolve index path
    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = Path.cwd() / index_path

    # Smart recall
    results = smart_recall(
        context_text=context_text,
        index_path=index_path,
        search_mode=args.mode,
        limit=args.limit,
        min_relevance=args.min_relevance,
        verbose=args.verbose
    )

    # Output
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        # Include excerpts by default, unless JSON output requested
        formatted_output, excerpt_stats = format_recall_output(results, context_text, include_excerpts=True)
        print(formatted_output)

        # Log excerpt stats as separate telemetry event
        if excerpt_stats.get("enabled"):
            collector.log_event({
                "event_id": None,
                "event_type": "excerpt_extraction_completed",
                "session_id": get_current_session_id(),
                "recall_event_id": results[0].get('_recall_event_id') if results else None,
                "excerpts": excerpt_stats,
                "timestamp": None  # Will be added by collector
            })

    # Flush telemetry before exit
    collector.flush()


if __name__ == "__main__":
    main()
