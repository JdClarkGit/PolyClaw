#!/usr/bin/env python3
"""
PolyClaw - AI Trading Intelligence for Polymarket

Install with: pip install polyclaw
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip() 
        for line in requirements_path.read_text().split("\n")
        if line.strip() and not line.startswith("#") and not line.startswith("-")
    ]

setup(
    name="polyclaw",
    version="1.0.0",
    author="JdClarkGit",
    author_email="polyclaw@example.com",
    description="AI Trading Intelligence for Polymarket - Your personal prediction market assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JdClarkGit/PolyClaw",
    project_urls={
        "Bug Reports": "https://github.com/JdClarkGit/PolyClaw/issues",
        "Source": "https://github.com/JdClarkGit/PolyClaw",
        "Documentation": "https://github.com/JdClarkGit/PolyClaw/tree/main/docs",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs"]),
    py_modules=[
        "cli",
        "app",
        "daemon",
        "gateway",
        "tui",
        "analytics",
        "ai_analysis",
        "strategy_engine",
        "notifications",
        "terminal_analytics",
        "discord_bot",
        "telegram_bot",
    ],
    include_package_data=True,
    package_data={
        "": ["*.html", "*.md", "*.json", "*.sh"],
    },
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "polyclaw=cli:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords=[
        "polymarket",
        "prediction-markets",
        "trading",
        "ai",
        "assistant",
        "analytics",
        "whale-tracking",
        "strategy",
        "kalshi",
    ],
)
