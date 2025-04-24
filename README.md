# Skill Extraction from Images and PDFs

This application extracts skills from resumes and certification documents, categorizing them as backed or unbacked skills with proficiency levels.

## Key Features

-   **Structured Document Conversion**: Converts documents to a standardized JSON structure that preserves layout and identifies sections
-   **Extract text from PDF files and images** with layout preservation
-   **Identify skills from extracted text** with section awareness
-   **Categorize skills as backed** (with certifications) or unbacked
-   **Assign proficiency levels** (Beginner, Intermediate, Advanced, Expert)
-   **Calculate confidence scores** for extracted skills
-   **Enhanced certification detection** that better identifies certificates and links them to skills
-   **Improved OCR for images** with better preprocessing and layout analysis

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Install Tesseract OCR for image processing
3. Install spaCy language model: `python -m spacy download en_core_web_lg`
4. Download NLTK data: `python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"`

## Usage

### Basic Usage

```
python main.py --input path/to/file.pdf --output results.json
```

### Process all files in a directory

```bash
python main.py --input examples/ --batch
```

### Additional options

```
--tesseract-path PATH  Path to Tesseract OCR executable (if not in PATH)
--skills-db PATH       Path to custom skills database JSON
--cert-db PATH         Path to custom certifications database JSON
--verbose              Enable detailed logging
--update-db            Update skill/certification databases with new entries
--force                Process files even if naming convention isn't followed
--use-structured-format Disable structured format converter (enabled by default)
```

## Structured Format Benefits

The application automatically:

-   Identifies document sections (education, experience, skills, etc.)
-   Preserves the layout and structure of the document
-   Improves extraction accuracy for well-formatted documents
-   Provides better context for skill extraction

## Output Files

When running in batch mode, the following files are created:

-   `batch_results.json`: Comprehensive results from all processed files
-   `consolidated_profile.json`: Consolidated profile with all skills and certifications
-   `extracted_text.json`: Raw extracted text from all documents

## Project Structure

-   `main.py`: Entry point for the application
-   `extractors/`: Contains modules for text extraction from different file types
    -   `pdf_extractor.py`: Extracts text from PDF files
    -   `image_extractor.py`: Extracts text from images using OCR
    -   `structured_converter.py`: Converts documents to structured JSON format
-   `processors/`: Contains modules for processing and analyzing extracted text
    -   `skill_extractor.py`: Skill extractor for structured documents
    -   `certification_extractor.py`: Certification extractor for structured documents
    -   `proficiency_calculator.py`: Calculates skill proficiency levels
-   `models/`: Contains data models and skill classification logic
-   `utils/`: Contains utility functions

## Implementation Details

This project uses open-source libraries for all text processing and skill extraction:

-   **spaCy**: For named entity recognition and text processing
-   **Transformers & Sentence-Transformers**: For semantic understanding of skills and certifications
-   **Scikit-learn**: For classification and confidence scoring
-   **NLTK**: For natural language preprocessing
