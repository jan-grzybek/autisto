import os
import setuptools

VERSION = "1.1rc0"


def load_readme():
    with open(os.path.join(os.path.dirname(__file__), "README.md")) as f:
        readme = f.read()
    return readme


def load_requirements(file_name):
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)) as f:
        requirements = f.readlines()
    return [req.replace("\n", "") for req in requirements]


if __name__ == "__main__":
    entry_points = {
        "console_scripts": [
            "autisto = autisto.utils:check_setup"
        ]
    }

    python_requires = '>=3.10'
    install_requires = load_requirements("requirements.txt")

    packages = [
        "autisto"
    ]

    project_urls = {
        "GitHub": "https://github.com/jan-grzybek/autisto"
    }

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3 :: Only"
    ]

    setuptools.setup(
        name="autisto",
        version=VERSION,
        author="Jan Grzybek",
        author_email="lyre_embassy_0n@icloud.com",
        description="Basic accounting (?) program integrated with Google Sheets to fulfill my own autistic needs of "
                    "tracking the shit owned.",
        long_description=load_readme(),
        long_description_content_type="text/markdown",
        entry_points=entry_points,
        license="MIT",  # some serious research ...
        install_requires=install_requires,
        python_requires=python_requires,
        packages=packages,
        classifiers=classifiers,
        project_urls=project_urls
    )
