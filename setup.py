import importlib.util
from setuptools import setup, find_packages
from pathlib import Path


root = Path(__file__).absolute().parent

with root.joinpath("README.md").open() as fh:
    long_description = fh.read()

spec = importlib.util.spec_from_file_location("curricula_grade", str(root.joinpath("curricula_grade", "version.py")))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

setup(
    name="curricula-grade",
    version=module.version,
    description="A grading toolkit for evaluating student code.",
    url="https://github.com/curriculagg/curricula",
    author="Noah Kim",
    author_email="noahbkim@gmail.com",

    # Extra
    long_description=long_description,
    long_description_content_type="text/markdown",

    # Python
    python_requires=">=3.9",

    # Packaging
    packages=find_packages(),
    include_package_data=True,
    install_requires=[f"curricula=={module.version}"],
    zip_safe=False)
