from setuptools import setup, find_packages

setup(
    name="rbxl-extractor",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "robloxpy",
        "pillow",
    ],
    entry_points={
        "console_scripts": [
            "rbxl-extractor=rbxl_extractor.main:main",
        ],
    },
    author="Your Name",
    description="A tool to extract assets from Roblox .rbxl files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
)