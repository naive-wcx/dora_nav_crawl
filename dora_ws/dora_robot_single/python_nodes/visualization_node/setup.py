from setuptools import setup, find_packages

setup(
    name="visualization_node",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "dora-rs",
        "pyarrow",
        "rerun-sdk",
        "opencv-python",
        "numpy",
        "pillow"
    ],
    python_requires=">=3.7",
)
