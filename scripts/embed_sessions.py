#!/usr/bin/env python3
"""
Generate embeddings for session summaries using sentence-transformers.
Supports batch processing with progress bar.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

# Feature detection for optional dependencies
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("WARNING: sentence-transformers not installed. Install with:", file=sys.stderr)
    print("  python3 -m pip install --user -r .claude/skills/recall/requirements-optional.txt", file=sys.stderr)
    sys.exit(1)


class EmbeddingGenerator:
    """Generate and manage embeddings for session summaries."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.

        Args:
            model_name: Name of sentence-transformers model to use
        """
        self.model_name = model_name
        self.model = None
        self.embedding_dim = None

    def load_model(self):
        """Load the sentence transformer model (lazy loading)."""
        if self.model is None:
            print(f"Loading model: {self.model_name}...", file=sys.stderr)
            self.model = SentenceTransformer(self.model_name)
            # Get embedding dimension from model
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"Model loaded ({self.embedding_dim} dimensions)", file=sys.stderr)

    def generate_text_for_embedding(self, session: Dict) -> str:
        """
        Generate text representation for embedding.
        Weighted combination of summary, topics, and files.

        Args:
            session: Session metadata dict

        Returns:
            Text string for embedding
        """
        parts = []

        # Summary (highest weight - most semantic content)
        summary = session.get('summary', '').strip()
        if summary:
            parts.append(summary)
            parts.append(summary)  # Repeat for weight

        # Topics (medium weight - categorical information)
        topics = session.get('topics', [])
        if topics:
            parts.append(' '.join(topics))

        # Files modified (lower weight - structural information)
        files = session.get('files_modified', [])
        if files:
            # Extract just filenames, not full paths
            filenames = [Path(f).name for f in files[:10]]  # Limit to 10 files
            parts.append(' '.join(filenames))

        # Beads issues (contextual information)
        beads = session.get('beads_issues', [])
        if beads:
            parts.append(' '.join(beads[:5]))  # Limit to 5 issues

        return ' '.join(parts)

    def generate_embeddings(self, sessions: List[Dict], show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for a list of sessions.

        Args:
            sessions: List of session metadata dicts
            show_progress: Show progress bar

        Returns:
            numpy array of embeddings (n_sessions, embedding_dim)
        """
        self.load_model()

        # Generate text for each session
        texts = [self.generate_text_for_embedding(s) for s in sessions]

        # Generate embeddings in batch
        print(f"Generating embeddings for {len(sessions)} sessions...", file=sys.stderr)

        if show_progress:
            # Use model's built-in progress bar
            embeddings = self.model.encode(
                texts,
                show_progress_bar=True,
                batch_size=32,
                convert_to_numpy=True
            )
        else:
            embeddings = self.model.encode(
                texts,
                show_progress_bar=False,
                batch_size=32,
                convert_to_numpy=True
            )

        # Normalize embeddings for cosine similarity via dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        return embeddings


def load_index(index_path: Path) -> Dict:
    """Load session index."""
    if not index_path.exists():
        return {'sessions': [], 'last_updated': None, 'bm25_index': None}

    with open(index_path, 'r') as f:
        return json.load(f)


def save_embeddings(embeddings: np.ndarray, output_path: Path):
    """
    Save embeddings to compressed NPZ format.

    Args:
        embeddings: numpy array of embeddings
        output_path: Path to save NPZ file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, embeddings=embeddings)
    print(f"Saved embeddings to: {output_path}", file=sys.stderr)


def update_index_with_embeddings(index: Dict, index_path: Path, embedding_path: Path):
    """
    Update index.json with embedding metadata.

    Args:
        index: Index dictionary
        index_path: Path to index.json
        embedding_path: Path to embeddings.npz
    """
    # Add embedding metadata
    if 'embedding_index' not in index:
        index['embedding_index'] = {}

    index['embedding_index'].update({
        'model': 'all-MiniLM-L6-v2',
        'embedding_dim': 384,
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'embedding_file': str(embedding_path.name),
        'num_sessions': len(index['sessions'])
    })

    # Mark all sessions as having embeddings
    for session in index['sessions']:
        session['has_embedding'] = True
        session['needs_embedding'] = False

    # Save updated index
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"Updated index with embedding metadata", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for session summaries')
    parser.add_argument(
        '--index',
        default='.claude/context/sessions/index.json',
        help='Path to session index'
    )
    parser.add_argument(
        '--output',
        default='.claude/context/sessions/embeddings.npz',
        help='Path to save embeddings'
    )
    parser.add_argument(
        '--model',
        default='all-MiniLM-L6-v2',
        help='Sentence transformer model to use'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate embeddings even if they exist'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    # Resolve paths
    index_path = Path(args.index)
    if not index_path.is_absolute():
        index_path = Path.cwd() / index_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    # Check if embeddings already exist
    if output_path.exists() and not args.force:
        print(f"Embeddings already exist at: {output_path}", file=sys.stderr)
        print("Use --force to regenerate", file=sys.stderr)
        sys.exit(0)

    # Load index
    print(f"Loading index from: {index_path}", file=sys.stderr)
    index = load_index(index_path)
    sessions = index.get('sessions', [])

    if not sessions:
        print("No sessions found in index", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(sessions)} sessions", file=sys.stderr)

    # Generate embeddings
    generator = EmbeddingGenerator(model_name=args.model)
    embeddings = generator.generate_embeddings(
        sessions,
        show_progress=not args.no_progress
    )

    # Save embeddings
    save_embeddings(embeddings, output_path)

    # Update index with embedding metadata
    update_index_with_embeddings(index, index_path, output_path)

    # Print summary
    print("\n" + "=" * 60, file=sys.stderr)
    print("Embedding generation complete!", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Sessions: {len(sessions)}", file=sys.stderr)
    print(f"Model: {args.model}", file=sys.stderr)
    print(f"Dimensions: {embeddings.shape[1]}", file=sys.stderr)
    print(f"Storage: {output_path.stat().st_size / 1024:.1f} KB", file=sys.stderr)
    print(f"Per session: {output_path.stat().st_size / len(sessions) / 1024:.2f} KB", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()
