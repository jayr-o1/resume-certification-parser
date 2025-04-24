#!/usr/bin/env python3
"""
Resume and Certification Parser

This script processes resume and certification files (PDF and images), extracts text 
using pdfplumber, and identifies skills with their proficiency levels.

The proficiency levels are calculated based on factors found in the resume and certifications.
"""

import os
import sys
import json
import argparse
import logging
import glob
import pdfplumber
from PIL import Image
import pytesseract
import spacy
import re
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('resume_cert_parser')

# Try loading the language model for NLP processing
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("Spacy model not found. Installing en_core_web_sm...")
        import subprocess
        subprocess.call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")

# Define proficiency levels
PROFICIENCY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]

class SkillProcessor:
    """
    Class for extracting and processing skills from text.
    """
    
    def __init__(self, skills_db_path=None):
        """
        Initialize the skill processor with a skills database.
        
        Args:
            skills_db_path (str, optional): Path to custom skills database JSON file
        """
        self.skills_data = self._load_skills_data(skills_db_path)
        self.technical_skills = self.skills_data.get("technical_skills", [])
        self.soft_skills = self.skills_data.get("soft_skills", [])
        
        # Prepare skill variations for better matching
        self.skill_variations = self._prepare_skill_variations()
        
    def _load_skills_data(self, skills_db_path):
        """
        Load skills data from a JSON file
        
        Args:
            skills_db_path (str, optional): Path to skills database JSON file
            
        Returns:
            dict: Skills data
        """
        default_db = {
            "technical_skills": [
                "Python", "Java", "JavaScript", "SQL", "C++", "C#", "Ruby", "PHP",
                "Swift", "Go", "Rust", "HTML", "CSS", "React", "Angular", "Vue.js",
                "Node.js", "Express", "Django", "Flask", "Spring", "Ruby on Rails",
                "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy", "R",
                "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Git",
                "Linux", "Windows Server", "macOS", "Android", "iOS", "Agile",
                "Scrum", "Kanban", "DevOps", "CI/CD", "REST API", "GraphQL",
                "MongoDB", "PostgreSQL", "MySQL", "SQLite", "Oracle", "Redis",
                "Elasticsearch", "PowerBI", "Tableau", "Excel", "VBA", "JIRA",
                "Confluence", "Photoshop", "Illustrator", "Figma", "Sketch"
            ],
            "soft_skills": [
                "Communication", "Teamwork", "Problem Solving", "Critical Thinking",
                "Creativity", "Leadership", "Time Management", "Adaptability",
                "Collaboration", "Emotional Intelligence", "Negotiation", "Conflict Resolution",
                "Decision Making", "Organization", "Attention to Detail", "Initiative",
                "Interpersonal Skills", "Flexibility", "Multitasking", "Presentation",
                "Public Speaking", "Writing", "Active Listening", "Customer Service",
                "Strategic Planning", "Analytical Thinking", "Research", "Mentoring"
            ]
        }
        
        if not skills_db_path or not os.path.exists(skills_db_path):
            logger.warning("Skills database not provided or not found. Using default skills list.")
            return default_db
            
        try:
            with open(skills_db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading skills database: {str(e)}")
            return default_db
    
    def _prepare_skill_variations(self):
        """
        Prepare variations of skill names for better matching
        
        Returns:
            dict: Skill variations mapped to canonical skill names
        """
        variations = {}
        
        # Add variations for technical skills
        for skill in self.technical_skills:
            # Add the original skill
            variations[skill.lower()] = skill
            
            # Add without punctuation
            clean_skill = re.sub(r'[^\w\s]', '', skill)
            if clean_skill.lower() != skill.lower():
                variations[clean_skill.lower()] = skill
                
            # Add common abbreviations
            if skill == "JavaScript":
                variations["js"] = skill
            elif skill == "TypeScript":
                variations["ts"] = skill
            elif skill == "Python":
                variations["py"] = skill
            
            # Add framework variations
            if "." in skill:
                # For skills like "Vue.js", also match "Vue"
                base_name = skill.split('.')[0]
                variations[base_name.lower()] = skill
        
        # Add variations for soft skills
        for skill in self.soft_skills:
            variations[skill.lower()] = skill
            
            # Handle multi-word skills
            if " " in skill:
                words = skill.split()
                # Add both hyphenated and non-hyphenated versions
                variations["-".join(words).lower()] = skill
                variations["".join(words).lower()] = skill
        
        return variations
    
    def extract_skills(self, text):
        """
        Extract skills from text using NLP and pattern matching
        
        Args:
            text (str): Text to extract skills from
            
        Returns:
            list: List of extracted skill dictionaries
        """
        extracted_skills = []
        
        # Extract using NLP
        doc = nlp(text)
        
        # Look for skills in the text
        for token in doc:
            cleaned_token = token.text.lower()
            if cleaned_token in self.skill_variations:
                canonical_name = self.skill_variations[cleaned_token]
                skill_dict = {
                    "name": canonical_name,
                    "context": self._get_context(doc, token),
                    "is_technical": canonical_name in self.technical_skills,
                    "is_backed": False,  # Default to not backed
                    "source": "nlp_token"
                }
                extracted_skills.append(skill_dict)
        
        # Extract skills from multi-token entities
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower()
            if chunk_text in self.skill_variations:
                canonical_name = self.skill_variations[chunk_text]
                skill_dict = {
                    "name": canonical_name,
                    "context": self._get_context(doc, chunk),
                    "is_technical": canonical_name in self.technical_skills,
                    "is_backed": False,  # Default to not backed
                    "source": "nlp_chunk"
                }
                extracted_skills.append(skill_dict)
        
        # Extract skills using regex patterns
        extracted_skills.extend(self._extract_with_patterns(text))
        
        # Deduplicate skills
        return self._deduplicate_skills(extracted_skills)
    
    def _get_context(self, doc, target, window=5):
        """
        Get the context surrounding a token or span
        
        Args:
            doc (spacy.Doc): The spaCy document
            target: The token or span to get context for
            window (int): The number of tokens before and after to include
            
        Returns:
            str: The context string
        """
        if hasattr(target, 'i'):  # Token
            start = max(0, target.i - window)
            end = min(len(doc), target.i + window + 1)
        else:  # Span
            start = max(0, target.start - window)
            end = min(len(doc), target.end + window)
        
        return doc[start:end].text
    
    def _extract_with_patterns(self, text):
        """
        Extract skills using regex patterns
        
        Args:
            text (str): Text to extract skills from
            
        Returns:
            list: List of extracted skill dictionaries
        """
        extracted_skills = []
        
        # Common patterns in resumes and certifications
        patterns = [
            # Skills in lists
            r'(?:^|\n)[\s\-•*>]+([^•\n]+)',
            # Skills in technology/skills sections
            r'(?:technologies|technical skills|tools|languages|frameworks|skills)(?:[:\s]+)([^\n]+)',
            # Skills in parentheses
            r'\(([^)]+)\)',
            # Skills as comma or semicolon separated lists
            r'(?:proficient in|experience with|knowledge of|familiar with|skilled in)[\s:]+([^\.;]+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get the matched text and its surrounding context
                match_text = match.group(1).strip()
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # Check for individual skills within matches (comma/semicolon separated)
                for skill_candidate in re.split(r'[,;/]', match_text):
                    skill_candidate = skill_candidate.strip().lower()
                    if skill_candidate in self.skill_variations:
                        canonical_name = self.skill_variations[skill_candidate]
                        skill_dict = {
                            "name": canonical_name,
                            "context": context,
                            "is_technical": canonical_name in self.technical_skills,
                            "is_backed": False,  # Default to not backed
                            "source": "pattern_match"
                        }
                        extracted_skills.append(skill_dict)
        
        return extracted_skills
    
    def _deduplicate_skills(self, skills):
        """
        Deduplicate skills by name and retain the best context
        
        Args:
            skills (list): List of skill dictionaries
            
        Returns:
            list: Deduplicated list of skill dictionaries
        """
        # Group skills by name
        skill_groups = defaultdict(list)
        for skill in skills:
            skill_groups[skill["name"]].append(skill)
        
        # For each skill name, select the skill with the richest context
        deduplicated_skills = []
        for skill_name, skill_instances in skill_groups.items():
            # Sort by context length (richest context)
            sorted_instances = sorted(skill_instances, key=lambda x: len(x["context"]), reverse=True)
            deduplicated_skills.append(sorted_instances[0])
        
        return deduplicated_skills

    def mark_backed_skills(self, resume_skills, certification_skills):
        """
        Mark skills that are backed by certifications
        
        Args:
            resume_skills (list): List of skill dictionaries from resume
            certification_skills (list): List of skill dictionaries from certifications
            
        Returns:
            list: Updated resume skills with backed information
        """
        # Create a set of skill names from certifications
        cert_skill_names = {skill["name"] for skill in certification_skills}
        
        # Mark resume skills as backed if they appear in certifications
        for skill in resume_skills:
            if skill["name"] in cert_skill_names:
                skill["is_backed"] = True
                logger.info(f"Marked skill {skill['name']} as backed by certification")
        
        return resume_skills


class ProficiencyCalculator:
    """
    Calculate proficiency levels for skills based on context
    """
    
    def __init__(self):
        """Initialize the proficiency calculator with indicators"""
        # Proficiency levels and indicators similar to the existing proficiency calculator
        self.proficiency_indicators = {
            # Beginner level keywords (rule-following, assisted work)
            "Beginner": [
                "basic", "familiar", "learning", "entry-level", "fundamental", "coursework", 
                "introduction", "beginner", "novice", "studied", "exposure to", "classroom",
                "training", "guided", "assisted", "supervised", "academic", "course", "101",
                "recently", "new to"
            ],
            
            # Intermediate level keywords (independent work, practical experience)
            "Intermediate": [
                "applied", "practical", "experience", "implemented", "developed", "built",
                "created", "designed", "intermediate", "proficient", "competent", "functional",
                "working knowledge", "solid understanding", "hands-on", "1-3 years", "participated in",
                "contributed to", "team member", "handled", "responsible for", "managed", "maintained"
            ],
            
            # Advanced level keywords (mastery, leadership, complex problem solving)
            "Advanced": [
                "advanced", "extensive", "expert", "specialized", "in-depth", "thorough",
                "comprehensive", "mastery", "proficiency", "seasoned", "strong", "3-5 years",
                "led", "orchestrated", "architected", "complex", "mentor", "trained others",
                "significant", "major", "key contributor", "senior", "optimization", "innovative",
                "solutions"
            ],
            
            # Expert level keywords (thought leadership, innovation, strategic impact)
            "Expert": [
                "expert", "authority", "specialist", "thought leader", "5+ years", "deep expertise",
                "recognized", "acclaimed", "pioneered", "strategic", "outstanding", "exceptional",
                "cutting-edge", "industry leader", "speaker", "published", "researcher", "invented",
                "patent", "revolutionized", "transformed", "principal", "consultant", "advisor"
            ]
        }
        
        # Duration indicators based on research on skill acquisition times
        self.duration_indicators = {
            "Beginner": [
                r"(?<!\d)(\d{1,2})\s*(?:day|week|month)s?",
                r"less than (?:a|one|1)\s*year",
                r"recently",
                r"(?<!\d)1\s*year"
            ],
            
            "Intermediate": [
                r"(?<!\d)([1-3])\s*years?",
                r"(?:a|one|1)\s*year",
                r"couple\s*(?:of)?\s*years"
            ],
            
            "Advanced": [
                r"(?<!\d)([3-5])\s*years?",
                r"several\s*years",
                r"extensive experience"
            ],
            
            "Expert": [
                r"(?<!\d)([5-9]|1\d+)\s*years?",
                r"(?<!\d)\d{2,}\s*years?",
                r"over (?:a|one)?\s*decade",
                r"decades of",
                r"(?:long|extensive)\s*(?:career|history|background)"
            ]
        }
        
        # Certification indicators
        self.certification_indicators = {
            "Beginner": [
                "fundamentals", "foundations", "associate", "entry", "basic", "introduction"
            ],
            
            "Intermediate": [
                "practitioner", "professional", "regular", "standard", "applied", "certified"
            ],
            
            "Advanced": [
                "advanced", "expert", "senior", "specialist", "professional", "architect"
            ],
            
            "Expert": [
                "master", "distinguished", "elite", "principal", "fellow", "authority",
                "subject matter expert", "distinguished"
            ]
        }
        
        # Action verb indicators that indicate proficiency level
        self.action_verb_indicators = {
            "Beginner": [
                "assisted", "helped", "observed", "learned", "studied", "participated", 
                "followed", "understood", "familiar", "used"
            ],
            
            "Intermediate": [
                "implemented", "developed", "built", "created", "designed", "managed", 
                "performed", "conducted", "handled", "organized", "maintained", "deployed"
            ],
            
            "Advanced": [
                "led", "directed", "optimized", "enhanced", "improved", "analyzed", 
                "architected", "mentored", "trained", "designed", "oversaw", "orchestrated"
            ],
            
            "Expert": [
                "pioneered", "innovated", "revolutionized", "transformed", "established", 
                "authored", "invented", "discovered", "mastered", "spoke", "published"
            ]
        }
    
    def calculate_proficiency(self, skill_name, context, certification_text=None, is_backed=False):
        """
        Calculate proficiency level for a skill based on its context
        
        Args:
            skill_name (str): The name of the skill
            context (str): The context around the skill mention
            certification_text (str, optional): Text from certifications
            is_backed (bool): Whether the skill is backed by a certification
            
        Returns:
            tuple: (proficiency_level, confidence_score)
        """
        # Initialize scores for each proficiency level
        scores = {level: 0 for level in PROFICIENCY_LEVELS}
        
        # Score based on keyword indicators in context
        for level, indicators in self.proficiency_indicators.items():
            for indicator in indicators:
                if re.search(r'\b' + re.escape(indicator) + r'\b', context, re.IGNORECASE):
                    scores[level] += 1
        
        # Score based on duration indicators in context
        for level, patterns in self.duration_indicators.items():
            for pattern in patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    scores[level] += 2  # Duration is a stronger indicator
        
        # Score based on action verbs in context
        for level, verbs in self.action_verb_indicators.items():
            for verb in verbs:
                # Look for verbs near the skill name
                pattern = r'(?i)(?:' + re.escape(verb) + r'.*?\b' + re.escape(skill_name) + r'\b|\b' + re.escape(skill_name) + r'\b.*?' + re.escape(verb) + r')'
                if re.search(pattern, context, re.IGNORECASE):
                    scores[level] += 1.5  # Action verbs are strong indicators
        
        # If certification text is provided, check for certification indicators
        if certification_text:
            for level, indicators in self.certification_indicators.items():
                for indicator in indicators:
                    # Look for indicators near the skill name in certification text
                    pattern = r'(?i)(?:' + re.escape(skill_name) + r'.*?\b' + re.escape(indicator) + r'\b|\b' + re.escape(indicator) + r'\b.*?' + re.escape(skill_name) + r')'
                    if re.search(pattern, certification_text, re.IGNORECASE):
                        scores[level] += 3  # Certification indicators are strongest
        
        # If skill is backed by certification, boost scores for Intermediate and above
        if is_backed:
            scores["Beginner"] += 1
            scores["Intermediate"] += 2
            scores["Advanced"] += 1
            logger.info(f"Boosting proficiency scores for backed skill: {skill_name}")
            
        # Default boost for all skills to prevent everything being classified as Beginner
        # This assumes people wouldn't list skills they're not at least somewhat proficient in
        scores["Intermediate"] += 1
        
        # For technical skills, assume a higher baseline
        if skill_name in ["Python", "Java", "JavaScript", "SQL", "C++", "C#"]:
            scores["Intermediate"] += 1
        
        # Determine the proficiency level with the highest score
        max_score = max(scores.values())
        if max_score == 0:
            # Default to Intermediate if no indicators found
            return "Intermediate", 0.6
        
        # Get the highest scoring level
        proficiency_level = max(scores.items(), key=lambda x: x[1])[0]
        
        # Calculate confidence based on the difference between the highest and second highest score
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1:
            score_diff = sorted_scores[0] - sorted_scores[1]
            confidence = min(0.6 + (score_diff * 0.1), 1.0)
        else:
            confidence = 0.7
        
        logger.info(f"Calculated proficiency for {skill_name}: {proficiency_level} (Confidence: {confidence:.2f})")
        logger.info(f"Scores: {scores}")
        
        return proficiency_level, confidence


class DocumentProcessor:
    """
    Process PDF and image documents to extract text
    """
    
    def __init__(self, tesseract_path=None):
        """
        Initialize the document processor
        
        Args:
            tesseract_path (str, optional): Path to tesseract executable
        """
        self.tesseract_path = tesseract_path
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def process_file(self, file_path):
        """
        Process a file to extract text
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: Extracted text
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self._extract_from_pdf(file_path)
        elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self._extract_from_image(file_path)
        else:
            logger.error(f"Unsupported file type: {file_extension}")
            return ""
    
    def _extract_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file using pdfplumber
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            return ""
    
    def _extract_from_image(self, image_path):
        """
        Extract text from an image file using pytesseract
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Extracted text
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            
            # Log more information about the extraction process
            logger.info(f"Extracted {len(text)} characters from image")
            logger.info(f"Image size: {image.size}")
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {str(e)}")
            return ""

    def is_resume(self, file_path):
        """
        Determine if a file is likely a resume
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            bool: True if the file is likely a resume, False otherwise
        """
        return "resume" in file_path.lower()
    
    def is_certification(self, file_path):
        """
        Determine if a file is likely a certification
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            bool: True if the file is likely a certification, False otherwise
        """
        lower_path = file_path.lower()
        return ("cert" in lower_path or 
                "certificate" in lower_path or 
                "credential" in lower_path or 
                "diploma" in lower_path)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract skills from resumes and certifications with proficiency levels.'
    )
    
    parser.add_argument('--input', '-i', required=True,
                      help='Path to input file or directory with resume and certification files')
    parser.add_argument('--output', '-o',
                      help='Path to the output JSON file')
    parser.add_argument('--skills-db', '-s',
                      help='Path to custom skills database JSON file')
    parser.add_argument('--tesseract-path', '-t',
                      help='Path to Tesseract OCR executable')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose output')
    
    return parser.parse_args()


def process_files(input_path, args):
    """
    Process files to extract skills with proficiency levels
    
    Args:
        input_path (str): Path to input file or directory
        args (Namespace): Command line arguments
        
    Returns:
        dict: Results containing extracted skills with proficiency levels
    """
    # Initialize processors
    document_processor = DocumentProcessor(args.tesseract_path)
    skill_processor = SkillProcessor(args.skills_db)
    proficiency_calculator = ProficiencyCalculator()
    
    all_results = {}
    
    # Handle directory input
    if os.path.isdir(input_path):
        # Get all PDF and image files in the directory
        file_patterns = ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.tiff', '*.bmp']
        files = []
        for pattern in file_patterns:
            files.extend(glob.glob(os.path.join(input_path, pattern)))
        
        if not files:
            logger.error(f"No supported files found in directory: {input_path}")
            return all_results
        
        # Categorize files
        resume_files = [f for f in files if document_processor.is_resume(f)]
        cert_files = [f for f in files if document_processor.is_certification(f)]
        other_files = [f for f in files if f not in resume_files and f not in cert_files]
        
        logger.info(f"Found {len(resume_files)} resume files, {len(cert_files)} certification files, and {len(other_files)} other files")
        
        # First, process certification files to get skills
        cert_skills = []
        cert_texts = {}
        
        for file_path in cert_files:
            logger.info(f"Processing certification file: {file_path}")
            extracted_text = document_processor.process_file(file_path)
            
            if not extracted_text:
                logger.error(f"Failed to extract text from {file_path}")
                continue
            
            cert_texts[file_path] = extracted_text
            file_skills = skill_processor.extract_skills(extracted_text)
            
            logger.info(f"Extracted {len(file_skills)} skills from certification: {file_path}")
            cert_skills.extend(file_skills)
            
            # Save certification results
            processed_skills = []
            for skill in file_skills:
                # For certifications, automatically set a higher proficiency level
                proficiency_level, confidence = proficiency_calculator.calculate_proficiency(
                    skill["name"], skill["context"], certification_text=extracted_text
                )
                
                skill_with_proficiency = {
                    "name": skill["name"],
                    "proficiency": proficiency_level,
                    "confidence": confidence,
                    "is_technical": skill.get("is_technical", True),
                    "is_backed": True,  # Skills from certifications are inherently backed
                    "source": skill.get("source", "certification")
                }
                
                processed_skills.append(skill_with_proficiency)
            
            # Add to results
            all_results[os.path.basename(file_path)] = {
                "file": os.path.basename(file_path),
                "file_type": "certification",
                "skills": processed_skills,
                "text_length": len(extracted_text)
            }
        
        # Then, process resume files and mark backed skills
        for file_path in resume_files:
            # Process resume and mark skills that are backed by certifications
            file_results = process_single_file(
                file_path, 
                document_processor, 
                skill_processor, 
                proficiency_calculator, 
                args,
                cert_skills=cert_skills,
                cert_texts=cert_texts
            )
            
            if file_results:
                all_results[os.path.basename(file_path)] = file_results
        
        # Process any remaining files
        for file_path in other_files:
            file_results = process_single_file(
                file_path, 
                document_processor, 
                skill_processor, 
                proficiency_calculator, 
                args
            )
            
            if file_results:
                all_results[os.path.basename(file_path)] = file_results
    
    # Handle single file input
    elif os.path.isfile(input_path):
        file_results = process_single_file(
            input_path, 
            document_processor, 
            skill_processor, 
            proficiency_calculator, 
            args
        )
        
        if file_results:
            all_results[os.path.basename(input_path)] = file_results
    
    else:
        logger.error(f"Input path does not exist: {input_path}")
    
    return all_results


def process_single_file(file_path, document_processor, skill_processor, proficiency_calculator, args, cert_skills=None, cert_texts=None):
    """
    Process a single file to extract skills with proficiency levels
    
    Args:
        file_path (str): Path to the file
        document_processor (DocumentProcessor): Document processor instance
        skill_processor (SkillProcessor): Skill processor instance
        proficiency_calculator (ProficiencyCalculator): Proficiency calculator instance
        args (Namespace): Command line arguments
        cert_skills (list, optional): Skills extracted from certifications
        cert_texts (dict, optional): Texts extracted from certifications
        
    Returns:
        dict: Results containing extracted skills with proficiency levels
    """
    logger.info(f"Processing file: {file_path}")
    
    # Determine file type
    is_resume = document_processor.is_resume(file_path)
    is_certification = document_processor.is_certification(file_path)
    file_type = "resume" if is_resume else "certification" if is_certification else "other"
    
    # Extract text from the document
    extracted_text = document_processor.process_file(file_path)
    
    if not extracted_text:
        logger.error(f"Failed to extract text from {file_path}")
        return None
    
    # Extract skills from the text
    extracted_skills = skill_processor.extract_skills(extracted_text)
    
    if args.verbose:
        logger.info(f"Extracted {len(extracted_skills)} skills from {file_path}")
    
    # If this is a resume and we have certification skills, mark backed skills
    if is_resume and cert_skills:
        extracted_skills = skill_processor.mark_backed_skills(extracted_skills, cert_skills)
    
    # Calculate proficiency levels for each skill
    processed_skills = []
    for skill in extracted_skills:
        # Get certification text for this skill if available
        cert_text = ""
        if cert_texts:
            for cert_file, text in cert_texts.items():
                if skill["name"].lower() in text.lower():
                    cert_text += text + " "
        
        proficiency_level, confidence = proficiency_calculator.calculate_proficiency(
            skill["name"], 
            skill["context"],
            certification_text=cert_text if cert_text else None,
            is_backed=skill.get("is_backed", False)
        )
        
        # Add proficiency information to the skill
        skill_with_proficiency = {
            "name": skill["name"],
            "proficiency": proficiency_level,
            "confidence": confidence,
            "is_technical": skill.get("is_technical", True),
            "is_backed": skill.get("is_backed", False),
            "source": skill.get("source", "unknown")
        }
        
        processed_skills.append(skill_with_proficiency)
        
        if args.verbose:
            backed_status = "Backed" if skill.get("is_backed", False) else "Unbacked"
            logger.info(f"Skill: {skill['name']}, Proficiency: {proficiency_level}, Confidence: {confidence:.2f}, Status: {backed_status}")
    
    # Sort skills by name
    processed_skills.sort(key=lambda x: x["name"])
    
    return {
        "file": os.path.basename(file_path),
        "file_type": file_type,
        "skills": processed_skills,
        "text_length": len(extracted_text)
    }


def save_results(results, output_path):
    """
    Save results to a JSON file
    
    Args:
        results (dict): Results to save
        output_path (str): Path to the output JSON file
    """
    if not output_path:
        # Default output path
        output_path = "extracted_skills.json"
    
    try:
        # Get resume results
        resume_results = None
        for file_name, file_data in results.items():
            if file_data.get("file_type") == "resume":
                resume_results = file_data
                break
        
        # If no resume was found, just use the first file's results
        if not resume_results and results:
            resume_results = next(iter(results.values()))
        
        # Get certification skills
        cert_skills = []
        for file_name, file_data in results.items():
            if file_data.get("file_type") == "certification":
                cert_skills.extend([skill["name"] for skill in file_data.get("skills", [])])
        
        # Create a focused output with just the resume skills
        if resume_results:
            focused_output = {
                "file": resume_results["file"],
                "skills": resume_results["skills"],
                "certifications": list(set(cert_skills))
            }
            
            with open(output_path, 'w') as f:
                json.dump(focused_output, f, indent=2)
            logger.info(f"Focused results saved to {output_path}")
        else:
            # If no resume was found, save the full results
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Full results saved to {output_path}")
            
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        # Fallback to saving the full results
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Full results saved to {output_path} (fallback)")
        except Exception as e2:
            logger.error(f"Error saving fallback results: {str(e2)}")


def main():
    """Main function"""
    args = parse_arguments()
    
    # Process files and extract skills with proficiency levels
    results = process_files(args.input, args)
    
    # Save results
    save_results(results, args.output)


if __name__ == "__main__":
    main() 