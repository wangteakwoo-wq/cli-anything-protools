from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-protools",
    version="1.0.0",
    description="CLI-Anything harness for Avid Pro Tools — agent-native DAW control",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "python-rtmidi>=1.5.0",
        "pyaaf2>=1.7.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-protools=cli_anything.protools.protools_cli:main",
        ],
    },
    python_requires=">=3.10",
)
