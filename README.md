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

## License

MIT
