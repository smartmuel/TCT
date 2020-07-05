import setuptools
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--trusted-host","pypi.org", "--trusted-host","files.pythonhosted.org"])

with open("README.md", "r") as fh:
    long_description = fh.read()

Lib = ["Selenium", "requests","paramiko","pandas","bps_restpy","chromedriver_autoinstaller"]
for i in Lib:
    try:
        install(i)
    except:
        print(f"Falled to Download {i}")

setuptools.setup(
    name="TCT", # Replace with your own username
    version="",
    author="Example Author",
    author_email="author@example.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
