#!/usr/bin/env python3
"""Setup script for ralph-loop."""

from setuptools import setup, find_packages

setup(
    name="ralph-loop",
    version="1.0.0",
    description="Provider-agnostic orchestration loop for agent-driven development",
    author="Mental-NV",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "jsonschema>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ralph=ralph.cli:main",
        ],
    },
    package_data={
        "ralph": ["schemas/*.json"],
    },
    include_package_data=True,
)
