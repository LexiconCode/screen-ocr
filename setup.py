import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="screen-ocr",
    version="0.2.0",
    author="James Stout",
    author_email="james.wolf.stout@gmail.com",
    description="Library for processing screen contents using OCR",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wolfmanstout/screen-ocr",
    packages=["screen_ocr"],
    install_requires=[
        "numpy",
        "pillow",
        "rapidfuzz",
        "scikit-image",
    ],
    # See README.md for backend recommendations.
    extras_require={
        "tesseract": ["pytesseract", "pandas"],
        "winrt": ["winrt"],
        "easyocr": ["easyocr"],
    },
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
