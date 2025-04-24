# Resume and Certification Skill Parser

This tool extracts skills from resumes and certification documents (PDF and image files) and calculates proficiency levels for those skills.

## Features

-   Extracts text from PDF files using `pdfplumber`
-   Extracts text from images (PNG, JPG, etc.) using `pytesseract`
-   Identifies skills using NLP and pattern matching
-   Calculates proficiency levels (Beginner, Intermediate, Advanced, Expert) based on context
-   Outputs results in JSON format

## How it Works

The system follows these steps:

1. **Document Processing**: Converts PDF or image files to text
2. **Skill Extraction**: Identifies technical and soft skills in the text
3. **Context Analysis**: Extracts the surrounding context for each skill
4. **Proficiency Calculation**: Determines the proficiency level based on:
    - Keyword indicators in context (e.g., "basic", "intermediate", "advanced")
    - Experience duration (e.g., "2 years", "5+ years")
    - Certifications and their levels
    - Project complexity and responsibility indicators

## Requirements

-   Python 3.6+
-   pdfplumber
-   pytesseract
-   Pillow
-   spaCy (with en_core_web_sm or en_core_web_md model)
-   Tesseract OCR (for image processing)

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Install spaCy language model:

```bash
python -m spacy download en_core_web_sm
```

3. Install Tesseract OCR:
    - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
    - Linux: `sudo apt-get install tesseract-ocr`
    - Mac: `brew install tesseract`

## Usage

### Command Line

Process a single file or directory:

```bash
python extract_and_process.py --input path/to/resume.pdf --output results.json
```

Or process all files in a directory:

```bash
python extract_and_process.py --input path/to/documents/ --output results.json
```

### Options

-   `--input`, `-i`: Path to input file or directory (required)
-   `--output`, `-o`: Path to output JSON file
-   `--skills-db`, `-s`: Path to custom skills database JSON file
-   `--tesseract-path`, `-t`: Path to Tesseract OCR executable
-   `--verbose`, `-v`: Enable verbose output

### Example

```bash
python example_run.py
```

This will process any PDF or image files in the `examples` directory and save the results to `parsed_skills.json`.

## Output Format

The output is a JSON file with the following structure:

```json
{
    "resume.pdf": {
        "file": "resume.pdf",
        "skills": [
            {
                "name": "Python",
                "proficiency": "Advanced",
                "confidence": 0.85,
                "is_technical": true
            },
            {
                "name": "Leadership",
                "proficiency": "Intermediate",
                "confidence": 0.7,
                "is_technical": false
            }
        ],
        "text_length": 15320
    },
    "certification.pdf": {
        "file": "certification.pdf",
        "skills": [
            {
                "name": "AWS",
                "proficiency": "Expert",
                "confidence": 0.9,
                "is_technical": true
            }
        ],
        "text_length": 5240
    }
}
```

## Customization

### Custom Skills Database

You can provide your own skills database as a JSON file with the following structure:

```json
{
    "technical_skills": ["Python", "Java", "Machine Learning"],
    "soft_skills": ["Leadership", "Communication", "Teamwork"]
}
```

## How Proficiency is Calculated

The proficiency calculator analyzes several factors:

1. **Keyword Indicators**: Words like "basic", "advanced", or "expert" near the skill mention
2. **Duration**: Experience time mentioned (e.g., "2 years of Python experience")
3. **Cognitive Complexity**: Action verbs associated with the skill (e.g., "designed", "implemented")
4. **Project Scale**: Size and complexity of projects (e.g., "small project", "enterprise system")
5. **Responsibility Level**: Level of responsibility (e.g., "assisted with", "led the team")
6. **Certification Level**: Level of relevant certifications (e.g., "associate", "professional")

Each factor contributes to the overall proficiency calculation, resulting in one of four levels:

-   **Beginner**: Basic knowledge, minimal experience
-   **Intermediate**: Practical application, some experience
-   **Advanced**: Significant experience, leadership
-   **Expert**: Deep expertise, authority in the field

## Extending the System

To extend or customize the system:

1. **Adding More Skills**: Modify the default skills list in `SkillProcessor._load_skills_data()`
2. **Custom Proficiency Indicators**: Extend the indicator lists in `ProficiencyCalculator.__init__()`
3. **New Document Types**: Add new extractors to the `DocumentProcessor` class
