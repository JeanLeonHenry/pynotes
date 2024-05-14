from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    requires = []
    for index, line in enumerate(f.readlines()):
        if "pytest" not in line and index != 0:
            requires.append(line.rstrip())

setup(
    name="pynotes",
    version="23.11.dev1",
    description="This util aimed at teachers turns a spreadsheet into reports.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JeanLeonHenry/pynotes",
    install_requires=requires,
)
