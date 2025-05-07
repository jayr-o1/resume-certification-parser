# Resume and Certification Skill Analyzer

A tool to extract skills from resumes and certifications, determine which skills are supported by certifications, and calculate proficiency levels.

## Features

-   **Resume Analysis**: Extract skills from PDF resumes using NLP techniques
-   **Certification Recognition**: Identify certifications and associate skills with them
-   **Skill Proficiency Calculation**: Calculate proficiency levels for extracted skills
-   **Certification Backing**: Determine which skills are backed by certifications
-   **API Interface**: Upload files via REST API or web interface
-   **Markdown & JSON Output**: Get results in structured formats

## Quick Start

### Installation

1. Clone this repository
2. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

### Web Interface

Start the API server:

```
python api.py
```

Then open your browser to http://localhost:5000 to use the web interface.

### Command Line Usage

Process files from the command line:

```
python resume_analyzer.py --input examples/ --output results/
```

-   `--input`: Directory containing resume(s) and certification files (PDF, PNG, JPG)
-   `--output`: Directory to save output files (will be created if it doesn't exist)

### API Usage

Start the API server:

```
python api.py
```

#### Extract Skills (POST /api/extract)

Upload files using a multipart/form-data request:

```bash
curl -X POST http://localhost:5000/api/extract \
  -F "files=@examples/Jayce Losero Resume.pdf" \
  -F "files=@examples/Jayce Losero Python Certificate.png"
```

Response:

```json
{
    "session_id": "12345678-1234-5678-1234-567812345678",
    "message": "Successfully processed 2 files",
    "result": {
        "file": "Jayce Losero Resume.pdf",
        "skills": [
            {
                "name": "Python",
                "proficiency": "Expert",
                "confidence": 0.92,
                "is_technical": true,
                "is_backed": true
            }
            // More skills...
        ],
        "certifications": ["Jayce Losero Python Certificate.png"]
    },
    "result_urls": {
        "json": "/api/results/12345678-1234-5678-1234-567812345678/skills.json",
        "markdown": "/api/results/12345678-1234-5678-1234-567812345678/skills_summary.md"
    }
}
```

#### Get Results (GET /api/results/{session_id}/{filename})

```bash
curl -X GET http://localhost:5000/api/results/12345678-1234-5678-1234-567812345678/skills.json
curl -X GET http://localhost:5000/api/results/12345678-1234-5678-1234-567812345678/skills_summary.md
```

## Project Structure

-   `api.py`: Web API for file processing
-   `resume_analyzer.py`: Main CLI entry point
-   `skills_extractor.py`: Skills extraction logic
-   `summarize_skills.py`: Summary generation
-   `extract_and_process.py`: Core processing logic
-   `templates/index.html`: Web interface
-   `examples/`: Example files for testing
-   `results/`: Output directory for CLI results
-   `api_results/`: Output directory for API results
-   `uploads/`: Temporary directory for API file uploads

## Output Format

### JSON Format (skills.json)

```json
{
    "file": "Resume.pdf",
    "skills": [
        {
            "name": "Python",
            "proficiency": "Expert",
            "confidence": 0.92,
            "is_technical": true,
            "is_backed": true
        }
        // More skills...
    ],
    "certifications": ["Python Certificate.png"]
}
```

### Markdown Format (skills_summary.md)

The markdown summary contains:

-   File name
-   List of certifications
-   Tables of technical and soft skills with proficiency levels
-   Certification-backed skills are marked with ✓

## Supported File Types

-   Resumes: PDF
-   Certifications: PDF, PNG, JPG, JPEG, TIFF

## Tools, Models and Techniques

### NLP and Machine Learning

-   **spaCy Models**: Uses the `en_core_web_sm` or `en_core_web_md` language models for natural language processing

    -   File: `processors/sentence_skill_extractor.py` (lines 10-15)

    ```python
    try:
        nlp = spacy.load("en_core_web_md")
    except OSError:
        nlp = spacy.load("en_core_web_sm")
    ```

-   **Dependency Parsing**: Analyzes grammatical structure of sentences to identify skill relationships

    -   File: `processors/sentence_skill_extractor.py` (lines 193-203)

    ```python
    if token.dep_ == "prep" and token.text.lower() in ["in", "with"]:
        for child in token.children:
            if child.dep_ in ["pobj", "dobj"]:
                phrase = self._get_full_phrase(child)
                self._process_potential_skill(phrase, sent.text, extracted_skills)
    ```

-   **Noun Chunk Extraction**: Identifies potential skill phrases based on grammatical structure

    -   File: `processors/sentence_skill_extractor.py` (lines 176-182)

    ```python
    for chunk in sent.noun_chunks:
        # Skip very short chunks
        if len(chunk.text.split()) < 2:
            continue
        # Check if this might be a skill phrase
        self._process_potential_skill(chunk.text, sent.text, extracted_skills)
    ```

-   **Pattern-Based Skill Extraction**: Uses regex patterns to identify skill indicators

    -   File: `processors/sentence_skill_extractor.py` (lines 34-56)

    ```python
    self.skill_indicators = [
        r"experienced in ([\w\s,&/\-+]+)",
        r"expertise in ([\w\s,&/\-+]+)",
        r"skilled in ([\w\s,&/\-+]+)",
        # ...more patterns
    ]
    ```

-   **Multi-Method Extraction**: Combines multiple extraction techniques for better coverage

    -   File: `api.py` (lines ~190-196)

    ```python
    # Extract skills with industry context using traditional methods
    file_skills = skill_processor.extract_skills(extracted_text)

    # Additionally, extract skills from sentences in the resume
    sentence_skills = sentence_extractor.extract_skills_from_text(extracted_text)

    # Combine skills from both extraction methods
    file_skills.extend(sentence_skills)
    ```

-   **Industry-Specific Extraction**: Tailors extraction based on detected industry
    -   File: `extract_and_process.py` (lines ~600-680)
    ```python
    industry_patterns = {
        "healthcare": {
            "clinical_skills": [
                r"clinical\s+skills\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                # ...more patterns
            ]
        },
        # ...more industries
    }
    ```

### Validation and Classification

-   **Rule-Based Validation**: Filters out non-skills using predefined rules

    -   File: `processors/skill_validator.py` (lines ~80-120)

    ```python
    def _is_invalid_skill(self, skill_name: str) -> bool:
        # Convert to lowercase for comparison
        name_lower = skill_name.lower()

        # Special exception for known technical terms
        technical_exceptions = [
            "database management", "database systems", # ...more exceptions
        ]

        if any(exception in name_lower for exception in technical_exceptions):
            return False

        # Check against the list of invalid skills
        for invalid_skill in self.invalid_skills:
            if invalid_skill in name_lower:
                return True
    ```

-   **Skill Database Verification**: Validates skills against a comprehensive database

    -   File: `utils/skill_database.py` (lines ~190-195)

    ```python
    def is_known_skill(self, skill_name: str) -> bool:
        return skill_name.lower() in self.skill_lookup
    ```

-   **Technical vs. Soft Skill Classification**: Automatically categorizes skills

    -   File: `utils/skill_database.py` (lines ~205-220)

    ```python
    def get_skill_category(self, skill_name: str) -> str:
        canonical = self.get_canonical_name(skill_name)

        if canonical in self.technical_skills:
            return "technical"
        elif canonical in self.soft_skills:
            return "soft"
        else:
            # Check domain skills
            for domain, skills in self.domain_skills.items():
                if canonical in skills:
                    return domain

        return "unknown"
    ```

-   **Confidence Scoring**: Assigns varying confidence based on extraction method and context
    -   File: `processors/sentence_skill_extractor.py` (lines ~260-270)
    ```python
    extracted_skills.append({
        "name": canonical_name,
        "confidence_score": 0.9,  # High confidence for database match
        "source": "sentence_extraction",
        "context": context,
        "is_technical": (category == "technical")
    })
    ```

### Text Processing

-   **Text Segmentation**: Breaks text into lines and sentences for better context

    -   File: `processors/sentence_skill_extractor.py` (line 125)

    ```python
    lines = re.split(r'[\.\n]', text)
    ```

-   **String Cleaning**: Removes unnecessary prefixes, suffixes, and punctuation

    -   File: `processors/sentence_skill_extractor.py` (lines ~290-310)

    ```python
    def _clean_skill_text(self, text: str) -> str:
        # Remove common prefixes and articles
        prefixes = ["a ", "an ", "the ", "some ", "many ", "various ", "excellent ",
                   "strong ", "advanced ", "proven ", "effective ", "demonstrated "]

        clean_text = text.strip()
        for prefix in prefixes:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):]

        # Remove trailing punctuation and whitespace
        clean_text = clean_text.strip(" .,;:-")

        # Capitalize first letter of each word for consistency
        clean_text = ' '.join(word.capitalize() for word in clean_text.split())

        return clean_text
    ```

-   **Compound Term Detection**: Identifies multi-word technical terms that should be kept together

    -   File: `processors/sentence_skill_extractor.py` (lines ~70-80)

    ```python
    self.technical_compounds = [
        "database management systems", "systems database management",
        "relational databases", "data modeling", "version control",
        # ...more terms
    ]
    ```

-   **Deduplication**: Removes duplicate skills while preserving the highest confidence ones
    -   File: `processors/sentence_skill_extractor.py` (lines ~340-350)
    ```python
    def _deduplicate_skills(self, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        skill_map = {}

        for skill in skills:
            skill_name = skill["name"]
            confidence = skill["confidence_score"]

            if skill_name not in skill_map or confidence > skill_map[skill_name]["confidence_score"]:
                skill_map[skill_name] = skill

        return list(skill_map.values())
    ```

### Domain-Specific Techniques

-   **Proficiency Calculation**: Infers skill levels from contextual clues

    -   File: `extract_and_process.py` (lines ~1000-1150)

    ```python
    def calculate_proficiency(self, skill_name, context, certification_text=None, is_backed=False, confidence_boost=0):
        # Implementation calculating proficiency based on context
    ```

-   **Skill Relationship Analysis**: Identifies related skills in technical domains

    -   File: `utils/skill_database.py` (lines ~225-260)

    ```python
    def get_related_skills(self, skill_name: str, limit: int = 5) -> List[str]:
        # ...
        tech_stacks = {
            "web_frontend": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "Angular", "Vue.js"],
            # ...more stacks
        }
        # ...implementation
    ```

-   **Industry Detection**: Analyzes text to determine the most likely industry
    -   File: `extract_and_process.py` (lines ~1610-1730)
    ```python
    def detect_industry(text):
        # Implementation of industry detection algorithm
    ```

### Document Processing

-   **PDF Text Extraction**: Extracts text content from PDF documents

    -   File: `extract_and_process.py` (lines ~1214-1230)

    ```python
    def _extract_from_pdf(self, pdf_path):
        extracted_text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    extracted_text += page.extract_text() or ""
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
        return extracted_text
    ```

-   **OCR Processing**: Performs OCR on images for text extraction

    -   File: `extract_and_process.py` (lines ~1235-1255)

    ```python
    def _extract_from_image(self, image_path):
        try:
            image = Image.open(image_path)
            extracted_text = pytesseract.image_to_string(image)
            return extracted_text
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            return ""
    ```

-   **Document Classification**: Automatically distinguishes between resumes and certifications

    -   File: `extract_and_process.py` (lines ~1258-1285)

    ```python
    def is_resume(self, file_path):
        # Implementation of resume detection logic

    def is_certification(self, file_path):
        # Implementation of certification detection logic
    ```

## License

MIT
