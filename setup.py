#!/usr/bin/env python3
"""
Setup script for Context Recall System Python package.
Makes the system pip-installable.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="claude-recall",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automatic context recall system for Claude Code conversations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/claude-recall",
    packages=find_packages(where="scripts"),
    package_dir={"": "scripts"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "rank-bm25>=0.2.2",
    ],
    extras_require={
        "semantic": [
            "sentence-transformers>=2.2.0",
            "torch>=1.11.0",
            "transformers>=4.41.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "claude-recall=scripts.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "config/*.json",
            "*.md",
            "*.txt",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/your-org/claude-recall/issues",
        "Source": "https://github.com/your-org/claude-recall",
        "Documentation": "https://github.com/your-org/claude-recall#readme",
    },
)
