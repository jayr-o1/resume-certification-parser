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
import openai

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
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        self.skills_data = self._load_skills_data(skills_db_path)
        self.technical_skills = self.skills_data.get("technical_skills", [])
        self.soft_skills = self.skills_data.get("soft_skills", [])
        
        # Load industry-specific skills
        self.industry_skills = {}
        for key in self.skills_data:
            if key.endswith('_skills') and key not in ["technical_skills", "soft_skills"]:
                industry_name = key.split('_')[0]
                self.industry_skills[industry_name] = self.skills_data[key]
                
        # Store all skills in one list for convenience
        self.all_skills = self.technical_skills + self.soft_skills
        for industry_skill_list in self.industry_skills.values():
            self.all_skills.extend(industry_skill_list)
        
        # Remove duplicates while preserving order
        self.all_skills = list(dict.fromkeys(self.all_skills))
        
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
                "Python", "Java", "JavaScript", "SQL", "C++", "Ruby", "PHP",
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
    
    def update_for_industry(self, industry):
        """
        Update the processor to prioritize skills for a specific industry
        
        Args:
            industry (str): The detected industry
            
        Returns:
            None
        """
        # Reset skill priorities based on industry
        self.industry_priority_skills = []
        
        # Add industry-specific skills as priority if available
        if industry in self.industry_skills:
            self.industry_priority_skills = self.industry_skills[industry]
            logger.info(f"Added {len(self.industry_priority_skills)} priority skills for {industry} industry")
        
        # For technology industry, prioritize technical skills
        if industry == "technology":
            self.industry_priority_skills.extend(self.technical_skills)
        
        # For education industry, prioritize education skills
        elif industry == "education":
            # Education skills might already be in industry skills, but ensure they're included
            education_keywords = ["teaching", "education", "curriculum", "instruction", "learning"]
            for skill in self.all_skills:
                if any(keyword in skill.lower() for keyword in education_keywords):
                    if skill not in self.industry_priority_skills:
                        self.industry_priority_skills.append(skill)
        
        # Remove duplicates
        self.industry_priority_skills = list(dict.fromkeys(self.industry_priority_skills))
    
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
            
            # Add without punctuation, but be careful with C#
            # Don't add 'c' as a variation for C#
            clean_skill = re.sub(r'[^\w\s]', '', skill)
            if clean_skill.lower() != skill.lower() and skill != "C#":
                variations[clean_skill.lower()] = skill
                
            # Add common abbreviations
            if skill == "JavaScript":
                variations["js"] = skill
            elif skill == "TypeScript":
                variations["ts"] = skill
            elif skill == "Python":
                variations["py"] = skill
            elif skill == "Microsoft SQL Server":
                variations["sql server"] = skill
                variations["ms sql"] = skill
                variations["mssql"] = skill
            elif skill == "PostgreSQL":
                variations["postgres"] = skill
            
            # Database-specific variations
            if skill == "PL/SQL":
                variations["plsql"] = skill
                variations["pl sql"] = skill
            elif skill == "T-SQL":
                variations["tsql"] = skill
                variations["t sql"] = skill
            elif skill == "ER Diagrams":
                variations["entity relationship diagrams"] = skill
                variations["er diagram"] = skill
                variations["erd"] = skill
            
            # Data-related terms
            if skill == "ETL Processes":
                variations["etl"] = skill
                variations["extract transform load"] = skill
            elif skill == "Backup & Recovery":
                variations["backup and recovery"] = skill
                variations["database backup"] = skill
            
            # Add framework variations
            if "." in skill:
                # For skills like "Vue.js", also match "Vue"
                base_name = skill.split('.')[0]
                variations[base_name.lower()] = skill
            
            # Handle multi-word technical skills
            if " " in skill:
                words = skill.split()
                # For longer skills, also match the key part
                if len(words) >= 2:
                    # Add the last word for things like "Microsoft SQL Server" -> "Server"
                    if len(words[-1]) > 3:  # Only if the last word is substantive
                        variations[words[-1].lower()] = skill
                    
                    # Add first + last for things like "Microsoft SQL Server" -> "Microsoft Server"
                    if len(words) >= 3:
                        variations[words[0].lower() + " " + words[-1].lower()] = skill
                    
                    # Add just first word for technical products
                    if words[0] not in ["data", "database", "software", "web", "mobile"]:
                        variations[words[0].lower()] = skill
        
        # Add variations for soft skills
        for skill in self.soft_skills:
            variations[skill.lower()] = skill
            
            # Handle multi-word skills
            if " " in skill:
                words = skill.split()
                # Add both hyphenated and non-hyphenated versions
                variations["-".join(words).lower()] = skill
                variations["".join(words).lower()] = skill
                
                # For education-related terms
                if skill in ["Curriculum Development", "Instructional Design", 
                            "Student-Centered Learning", "Classroom Teaching",
                            "Online Teaching", "Assessment & Evaluation"]:
                    # Add the key word as variation
                    key_word = words[0].lower()
                    if key_word not in ["and", "of", "for", "with"]:
                        variations[key_word] = skill
                        
                    # Add common variations specific to education field
                    if skill == "Curriculum Development":
                        variations["curriculum design"] = skill
                        variations["curriculum creation"] = skill
                    elif skill == "Student-Centered Learning":
                        variations["student centered"] = skill
                        variations["learner centered"] = skill
                    elif skill == "Assessment & Evaluation":
                        variations["assessment"] = skill
                        variations["evaluation"] = skill
                        variations["assessment and evaluation"] = skill
        
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
        
        # Extract skills using pattern matching first
        pattern_skills = self._extract_with_patterns(text)
        
        # Use a mapping to track skill mentions with confidence scores
        skill_mentions = {}
        
        # Add pattern-matched skills to the mentions dictionary
        for skill in pattern_skills:
            skill_name = skill["name"]
            if skill_name not in skill_mentions:
                skill_mentions[skill_name] = {
                    "mentions": 1,
                    "context": [skill["context"]],
                    "sources": ["pattern_match"],
                    "is_technical": skill["is_technical"],
                    "is_backed": False,
                    "priority": skill.get("priority", 0)
                }
            else:
                skill_mentions[skill_name]["mentions"] += 1
                skill_mentions[skill_name]["context"].append(skill["context"])
                if "pattern_match" not in skill_mentions[skill_name]["sources"]:
                    skill_mentions[skill_name]["sources"].append("pattern_match")
                # Use the highest priority found
                skill_mentions[skill_name]["priority"] = max(skill_mentions[skill_name]["priority"], skill.get("priority", 0))
        
        # Look for skills in the text using NLP tokens
        for token in doc:
            cleaned_token = token.text.lower()
            if cleaned_token in self.skill_variations:
                canonical_name = self.skill_variations[cleaned_token]
                
                # Skip if token is too generic or commonly used in other contexts
                if len(token.text) < 2 and token.text.lower() not in ["r", "c"]:
                    continue
                    
                # Get surrounding context
                context = self._get_context(doc, token)
                
                # Skip if context suggests it's not a skill mention
                if self._is_not_skill_context(context, canonical_name):
                    continue
                
                # Add to skill mentions
                if canonical_name not in skill_mentions:
                    skill_mentions[canonical_name] = {
                        "mentions": 1,
                        "context": [context],
                        "sources": ["nlp_token"],
                        "is_technical": canonical_name in self.technical_skills,
                        "is_backed": False,
                        "priority": 0  # Default lower priority for NLP tokens
                    }
                else:
                    skill_mentions[canonical_name]["mentions"] += 1
                    skill_mentions[canonical_name]["context"].append(context)
                    if "nlp_token" not in skill_mentions[canonical_name]["sources"]:
                        skill_mentions[canonical_name]["sources"].append("nlp_token")
        
        # Extract skills from multi-token entities
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower()
            if chunk_text in self.skill_variations:
                canonical_name = self.skill_variations[chunk_text]
                
                # Get surrounding context
                context = self._get_context(doc, chunk)
                
                # Skip if context suggests it's not a skill mention
                if self._is_not_skill_context(context, canonical_name):
                    continue
                
                # Add to skill mentions
                if canonical_name not in skill_mentions:
                    skill_mentions[canonical_name] = {
                        "mentions": 1,
                        "context": [context],
                        "sources": ["nlp_chunk"],
                        "is_technical": canonical_name in self.technical_skills,
                        "is_backed": False,
                        "priority": 0  # Default lower priority for NLP chunks
                    }
                else:
                    skill_mentions[canonical_name]["mentions"] += 1
                    skill_mentions[canonical_name]["context"].append(context)
                    if "nlp_chunk" not in skill_mentions[canonical_name]["sources"]:
                        skill_mentions[canonical_name]["sources"].append("nlp_chunk")
        
        # Convert skill mentions to skill dictionaries, filtering out low-confidence skills
        for skill_name, data in skill_mentions.items():
            # Verification step: ensure skill is actually in the text with proper boundaries
            explicit_mention = re.search(r'\b' + re.escape(skill_name) + r'\b', text, re.IGNORECASE)
            if not explicit_mention:
                # Skip skills not explicitly mentioned
                continue
                
            # Special case for programming languages and one-letter skills
            special_skills = ["C++", "C#", "R", "Go", "C", "J"]
            if skill_name in special_skills:
                # Require stronger evidence for these often mis-detected skills
                strong_evidence = (
                    data["priority"] >= 2 or  # High priority section
                    data["mentions"] >= 2 or  # Multiple mentions
                    self._is_programming_context(text, skill_name)  # Clear programming context
                )
                
                if not strong_evidence:
                    # Skip ambiguous skills without strong evidence
                    continue
            
            # Skip skills with only one mention from a single source unless it's in a strong context
            has_strong_context = any(self._is_strong_skill_context(ctx, skill_name) for ctx in data["context"])
            
            # Apply stricter filters based on confidence factors
            if (data["mentions"] < 2 and len(data["sources"]) < 2 and not has_strong_context and data["priority"] < 2):
                # Skip low-confidence skills
                continue
                
            # Get the richest context
            best_context = max(data["context"], key=len)
            
            # Add the skill
            skill_dict = {
                "name": skill_name,
                "context": best_context,
                "is_technical": data["is_technical"],
                "is_backed": data["is_backed"],
                "source": ",".join(data["sources"]),
                "confidence_boost": data["priority"] * 0.1  # Convert priority to confidence boost
            }
            extracted_skills.append(skill_dict)
        
        return extracted_skills
    
    def _is_not_skill_context(self, context, skill_name):
        """
        Check if the context suggests this is not actually a skill mention
        
        Args:
            context (str): Context around the potential skill
            skill_name (str): The skill name
            
        Returns:
            bool: True if this is not a skill context, False otherwise
        """
        # Negative contexts that suggest this is not a skill mention
        negative_patterns = [
            r"not familiar with " + re.escape(skill_name),
            r"no experience (?:with|in) " + re.escape(skill_name),
            r"would like to learn " + re.escape(skill_name),
            r"interested in learning " + re.escape(skill_name),
            r"plan(?:s|ning)? to learn " + re.escape(skill_name)
        ]
        
        # Check if any negative pattern matches
        for pattern in negative_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
                
        # For programming languages, check if they're mentioned in education context only
        if skill_name in ["C++", "Java", "Python", "JavaScript"]:
            education_only_patterns = [
                r"course(?:s|work)? (?:in|on) " + re.escape(skill_name),
                r"(?:introduction|intro) to " + re.escape(skill_name),
                r"studied " + re.escape(skill_name)
            ]
            
            # If it appears in education context, ensure it also appears elsewhere
            education_matches = any(re.search(pattern, context, re.IGNORECASE) for pattern in education_only_patterns)
            
            if education_matches and not re.search(r"experience (?:with|in|using) " + re.escape(skill_name), context, re.IGNORECASE):
                return True
                
        return False
        
    def _is_strong_skill_context(self, context, skill_name):
        """
        Check if the context strongly indicates this is a skill
        
        Args:
            context (str): Context around the potential skill
            skill_name (str): The skill name
            
        Returns:
            bool: True if this is a strong skill context, False otherwise
        """
        # Patterns indicating strong skill evidence
        strong_patterns = [
            r"experience (?:with|in|using) " + re.escape(skill_name),
            r"proficient (?:in|with) " + re.escape(skill_name),
            r"knowledge of " + re.escape(skill_name),
            r"skilled (?:in|with) " + re.escape(skill_name),
            r"expertise (?:in|with) " + re.escape(skill_name),
            r"practiced (?:in|with) " + re.escape(skill_name),
            r"(?:extensive|advanced) " + re.escape(skill_name),
            r"skills?:.*" + re.escape(skill_name),
            r"technologies:.*" + re.escape(skill_name),
            r"technical skills:.*" + re.escape(skill_name),
            r"languages:.*" + re.escape(skill_name),
            r"programming:.*" + re.escape(skill_name),
            r"database:.*" + re.escape(skill_name) 
        ]
        
        # Check if any strong pattern matches
        for pattern in strong_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
                
        return False
    
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
    
    def _extract_with_patterns(self, resume_text, industry="general"):
        """
        Extract skills using regex patterns
        
        Args:
            resume_text (str): The resume text
            industry (str): The detected industry
            
        Returns:
            list: List of extracted skills
        """
        self.logger.info(f"Extracting skills using patterns for industry: {industry}")
        extracted_skills = []
        
        # Dictionary of general skill extraction patterns
        general_patterns = {
            # Skills explicitly listed in skills/core competencies sections (highest priority)
            "skills_section": [
                r"(?:key\s+)?skills\s*(?::|include|:include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"technical\s+skills\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"core\s+competencies\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"areas\s+of\s+expertise\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"specialties\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"professional\s+skills\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
            ],
            
            # Technical skills/tools/languages sections (high priority)
            "technical_section": [
                r"technologies.*?(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"programming\s+languages.*?(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"software.*?(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"tools.*?(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"platforms.*?(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
            ],
            
            # Strong/proficient in sections (medium priority)
            "proficiency_section": [
                r"(?:strong|proficient)\s+in\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"expertise\s+in\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"knowledge\s+of\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                r"experience\s+with\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
            ],
            
            # Bullet points that mention skills (lower priority)
            "bullet_points": [
                r"•\s*(?:utilized|used|applied|implemented|developed\s+with)\s+([\w\s,&/\-()+]+)",
                r"•\s*(?:strong|proficient)\s+in\s+([\w\s,&/\-()+]+)",
                r"•\s*(?:expertise|experience)\s+(?:in|with)\s+([\w\s,&/\-()+]+)"
            ]
        }
        
        # Industry-specific patterns
        industry_patterns = {
            "healthcare": {
                "clinical_skills": [
                    r"clinical\s+skills\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"medical\s+(?:skills|expertise)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"patient\s+care\s*(?:skills|competencies)?\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
                ]
            },
            "finance": {
                "financial_skills": [
                    r"financial\s+(?:skills|analysis)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"accounting\s+(?:skills|expertise)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"banking\s+(?:skills|expertise)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
                ]
            },
            "education": {
                "teaching_skills": [
                    r"teaching\s+(?:skills|methods)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"classroom\s+(?:skills|management)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"instructional\s+(?:skills|methods)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
                ]
            },
            "legal": {
                "legal_skills": [
                    r"legal\s+(?:skills|expertise)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"(?:litigation|contract)\s+(?:skills|expertise)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
                ]
            },
            "marketing": {
                "marketing_skills": [
                    r"marketing\s+(?:skills|strategies)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"digital\s+marketing\s*(?:skills|tools)?\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"brand(?:ing)?\s+(?:skills|strategies)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
                ]
            },
            "sales": {
                "sales_skills": [
                    r"sales\s+(?:skills|techniques)\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"account\s+management\s*(?:skills)?\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})",
                    r"business\s+development\s*(?:skills)?\s*(?::|include)?\s*((?:[\w\s,&/\-()+]+(?:,|and|;|\n|\r|\|(?=\s*[\w\s]+))){2,})"
                ]
            }
        }
        
        # Add related industries for cross-functional roles
        related_industries = {
            "technology": ["finance", "healthcare"],  # Tech often crosses into finance and healthcare
            "healthcare": ["technology"],  # Healthcare increasingly uses technology
            "finance": ["technology", "legal"],  # Finance often involves tech and legal
            "education": ["technology"],  # Education increasingly uses technology
            "legal": ["finance"],  # Legal often involves finance
            "sales": ["marketing"],  # Sales and marketing are closely related
            "marketing": ["sales", "technology"]  # Marketing increasingly involves tech and sales
        }
        
        # Select patterns to use based on industry
        patterns_to_use = general_patterns.copy()
        
        # Add industry-specific patterns if available
        if industry in industry_patterns:
            for category, pattern_list in industry_patterns[industry].items():
                patterns_to_use[category] = pattern_list
                self.logger.info(f"Added {len(pattern_list)} {industry}-specific patterns for {category}")
                
        # Add related industry patterns if applicable
        if industry in related_industries:
            for related_industry in related_industries[industry]:
                if related_industry in industry_patterns:
                    for category, pattern_list in industry_patterns[related_industry].items():
                        if category not in patterns_to_use:
                            patterns_to_use[category] = []
                        patterns_to_use[category].extend(pattern_list)
                        self.logger.info(f"Added {len(pattern_list)} {related_industry}-specific patterns (related to {industry})")
        
        # Define confidence boosts by pattern category
        confidence_boosts = {
            "skills_section": 0.15,
            "technical_section": 0.10,
            "proficiency_section": 0.08,
            "bullet_points": 0.05,
            "clinical_skills": 0.15,  # Healthcare
            "financial_skills": 0.15,  # Finance
            "teaching_skills": 0.15,  # Education
            "legal_skills": 0.15,  # Legal
            "marketing_skills": 0.15,  # Marketing
            "sales_skills": 0.15  # Sales
        }
        
        # Process each pattern category
        for category, patterns in patterns_to_use.items():
            for pattern in patterns:
                matches = re.finditer(pattern, resume_text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Extract the skills list from the match
                    skills_list = match.group(1).strip() if match.groups() else match.group(0).strip()
                    
                    # Split the skills list using multiple delimiters
                    skills = re.split(r',|\bAND\b|;|\n|\r|\|(?=\s*[\w\s]+)', skills_list, flags=re.IGNORECASE)
                    
                    for skill in skills:
                        skill = skill.strip()
                        
                        # Skip if too short or too long
                        if len(skill) < 2 or len(skill) > 50:
                            continue
                            
                        # Skip if contains only numbers or special characters
                        if not re.search(r'[a-zA-Z]', skill):
                            continue
                        
                        # Skip common false positives
                        if skill.lower() in ["and", "or", "in", "with", "using", "to", "of"]:
                            continue
                        
                        # Normalize skill name
                        normalized_skill = skill.strip().title()
                        
                        # Calculate confidence boost based on pattern category
                        boost = confidence_boosts.get(category, 0)
                        
                        # Add to extracted skills with source information
                        extracted_skills.append({
                            'name': normalized_skill,
                            'source': 'pattern',
                            'confidence_boost': boost,
                            'pattern_category': category,
                            'context': skill,  # Adding the context field with the skill itself as initial context
                            'is_technical': normalized_skill in self.technical_skills  # Add is_technical field
                        })
        
        self.logger.info(f"Extracted {len(extracted_skills)} skills using patterns for {industry} industry")
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

    def _is_programming_context(self, text, skill_name):
        """
        Check if a skill is mentioned in a programming or technology context
        
        Args:
            text (str): The full text to check
            skill_name (str): The skill name
            
        Returns:
            bool: True if in programming context, False otherwise
        """
        # Define programming context patterns
        programming_patterns = [
            r'programming\s+languages?.*\b' + re.escape(skill_name) + r'\b',
            r'software\s+development.*\b' + re.escape(skill_name) + r'\b',
            r'technical\s+skills?.*\b' + re.escape(skill_name) + r'\b',
            r'technologies.*\b' + re.escape(skill_name) + r'\b',
            r'languages.*\b' + re.escape(skill_name) + r'\b',
            r'proficient\s+in.*\b' + re.escape(skill_name) + r'\b',
            r'skills.*\b' + re.escape(skill_name) + r'\b',
            r'\b' + re.escape(skill_name) + r'\b\s+programming',
            r'\b' + re.escape(skill_name) + r'\b\s+development'
        ]
        
        # Database-specific context patterns
        database_patterns = [
            r'database.*\b' + re.escape(skill_name) + r'\b',
            r'query\s+languages?.*\b' + re.escape(skill_name) + r'\b',
            r'data\s+technologies.*\b' + re.escape(skill_name) + r'\b',
            r'data\s+warehousing.*\b' + re.escape(skill_name) + r'\b',
            r'sql.*\b' + re.escape(skill_name) + r'\b',
            r'schema.*\b' + re.escape(skill_name) + r'\b',
            r'data\s+modeling.*\b' + re.escape(skill_name) + r'\b',
            r'etl.*\b' + re.escape(skill_name) + r'\b'
        ]
        
        # Teaching and education context patterns
        teaching_patterns = [
            r'teaching.*\b' + re.escape(skill_name) + r'\b',
            r'education.*\b' + re.escape(skill_name) + r'\b',
            r'curriculum.*\b' + re.escape(skill_name) + r'\b',
            r'instruction.*\b' + re.escape(skill_name) + r'\b',
            r'classroom.*\b' + re.escape(skill_name) + r'\b',
            r'learning.*\b' + re.escape(skill_name) + r'\b',
            r'assessment.*\b' + re.escape(skill_name) + r'\b',
            r'student.*\b' + re.escape(skill_name) + r'\b'
        ]
        
        # Version control context patterns
        vcs_patterns = [
            r'version\s+control.*\b' + re.escape(skill_name) + r'\b',
            r'code\s+management.*\b' + re.escape(skill_name) + r'\b',
            r'repository.*\b' + re.escape(skill_name) + r'\b',
            r'git.*\b' + re.escape(skill_name) + r'\b'
        ]
        
        # All patterns to check
        all_patterns = programming_patterns + database_patterns + teaching_patterns + vcs_patterns
        
        # Check if any pattern matches
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in all_patterns)


class ProficiencyCalculator:
    """
    Calculate proficiency levels for skills based on context
    """
    
    def __init__(self, technical_skills=None, industry="general"):
        """
        Initialize the proficiency calculator with indicators
        
        Args:
            technical_skills (list): List of technical skills
            industry (str): The detected industry
        """
        # Store technical skills reference
        self.technical_skills = technical_skills or []
        
        # Store the industry
        self.industry = industry
        
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
        
        # Industry-specific proficiency indicators
        self.industry_proficiency_indicators = {
            "healthcare": {
                "Beginner": ["observed", "shadowed", "assisted with", "under supervision", "training in"],
                "Intermediate": ["performed", "conducted", "administered", "provided care", "treated", "diagnosed"],
                "Advanced": ["specialized in", "led treatment", "clinical expertise", "refined protocols", "chief"],
                "Expert": ["pioneered treatment", "published research", "board certified", "fellowship", "chief medical"]
            },
            "education": {
                "Beginner": ["student teaching", "teaching assistant", "substitute", "tutored", "assisted teacher"],
                "Intermediate": ["taught", "instructed", "facilitated", "developed curriculum", "assessed", "graded"],
                "Advanced": ["master teacher", "department chair", "curriculum specialist", "instructional coach"],
                "Expert": ["principal", "superintendent", "published educator", "professor", "education consultant"]
            },
            "finance": {
                "Beginner": ["bookkeeping", "data entry", "reconciled", "tracked expenses", "junior"],
                "Intermediate": ["analyzed", "prepared reports", "forecasted", "budgeted", "audited"],
                "Advanced": ["managed portfolio", "led audits", "oversaw", "senior analyst", "authorized"],
                "Expert": ["chief financial", "partner", "director of finance", "certified", "strategized"]
            },
            "legal": {
                "Beginner": ["researched", "reviewed documents", "assisted attorneys", "drafted", "paralegal"],
                "Intermediate": ["represented clients", "prepared briefs", "conducted discovery", "negotiated"],
                "Advanced": ["led litigation", "specialized practice", "argued cases", "senior counsel"],
                "Expert": ["partner", "judge", "general counsel", "chief legal officer", "law professor"]
            },
            "marketing": {
                "Beginner": ["assisted with campaigns", "coordinated", "monitored", "updated content", "tracked"],
                "Intermediate": ["created campaigns", "managed social media", "analyzed metrics", "developed content"],
                "Advanced": ["led marketing", "brand strategy", "marketing director", "optimized campaigns"],
                "Expert": ["chief marketing", "transformed brand", "award-winning", "innovative strategy", "thought leader"]
            },
            "sales": {
                "Beginner": ["prospected", "qualified leads", "customer service", "support", "assisted"],
                "Intermediate": ["achieved quota", "closed deals", "managed accounts", "retained clients", "exceeded goals"],
                "Advanced": ["top performer", "president's club", "managed territory", "key accounts", "sales leader"],
                "Expert": ["VP of sales", "chief revenue", "built sales organization", "transformed sales", "award-winning"]
            }
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
                "maintained", "handled", "processed", "operated", "organized", "executed",
                "conducted", "administered", "coordinated", "produced", "performed"
            ],
            
            "Advanced": [
                "led", "directed", "guided", "oversaw", "supervised", "trained", "mentored",
                "architected", "designed", "optimized", "improved", "enhanced", "streamlined",
                "innovated", "transformed", "revamped", "restructured", "analyzed", "solved"
            ],
            
            "Expert": [
                "spearheaded", "pioneered", "established", "founded", "authored", "published",
                "revolutionized", "redefined", "conceptualized", "formulated", "invented",
                "patented", "keynoted", "consulted", "advised", "strategized", "envisioned"
            ]
        }
        
    def update_for_industry(self, industry):
        """
        Update proficiency indicators for a specific industry
        
        Args:
            industry (str): The detected industry
        """
        self.industry = industry
        
        # Add industry-specific indicators to the general ones if available
        if industry in self.industry_proficiency_indicators:
            for level, indicators in self.industry_proficiency_indicators[industry].items():
                self.proficiency_indicators[level].extend(indicators)
                logger.info(f"Added {len(indicators)} {industry}-specific {level} indicators")
        
    def calculate_proficiency(self, skill_name, context, certification_text=None, is_backed=False, confidence_boost=0):
        """
        Calculate proficiency level for a skill based on its context
        
        Args:
            skill_name (str): The name of the skill
            context (str): The context around the skill mention
            certification_text (str, optional): Text from certifications
            is_backed (bool): Whether the skill is backed by a certification
            confidence_boost (float): Additional confidence boost from extraction method
            
        Returns:
            tuple: (proficiency_level, confidence_score)
        """
        # Initialize scores for each proficiency level
        scores = {level: 0 for level in PROFICIENCY_LEVELS}
        
        # Check if this is a technical or language skill
        is_tech_skill = self.technical_skills and skill_name in self.technical_skills
        is_language = skill_name.lower() in ["python", "java", "javascript", "sql", "c++", "r", "php"]
        
        # Extract sentences mentioning the skill for more precise context analysis
        skill_sentences = []
        for sentence in re.split(r'[.!?]+', context):
            if re.search(r'\b' + re.escape(skill_name) + r'\b', sentence, re.IGNORECASE):
                skill_sentences.append(sentence.strip())
        
        # If no specific sentences found, use the whole context
        if not skill_sentences:
            skill_sentences = [context]
            
        # Analyze each sentence for proficiency indicators
        for sentence in skill_sentences:
            # Look for proficiency indicators in this specific sentence
            for level, indicators in self.proficiency_indicators.items():
                for indicator in indicators:
                    if re.search(r'\b' + re.escape(indicator) + r'\b', sentence, re.IGNORECASE):
                        scores[level] += 1
            
            # Look for duration indicators in this specific sentence
            for level, patterns in self.duration_indicators.items():
                for pattern in patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        scores[level] += 2  # Duration is a stronger indicator
            
            # Look for action verbs in this specific sentence
            for level, verbs in self.action_verb_indicators.items():
                for verb in verbs:
                    # Look for verbs near the skill name
                    pattern = r'(?i)(?:' + re.escape(verb) + r'.*?\b' + re.escape(skill_name) + r'\b|\b' + re.escape(skill_name) + r'\b.*?' + re.escape(verb) + r')'
                    if re.search(pattern, sentence, re.IGNORECASE):
                        scores[level] += 1.5  # Action verbs are strong indicators
        
        # If certification text is provided, check for certification indicators
        if certification_text:
            for level, indicators in self.certification_indicators.items():
                for indicator in indicators:
                    # Look for indicators near the skill name in certification text
                    pattern = r'(?i)(?:' + re.escape(skill_name) + r'.*?\b' + re.escape(indicator) + r'\b|\b' + re.escape(indicator) + r'\b.*?' + re.escape(skill_name) + r')'
                    if re.search(pattern, certification_text, re.IGNORECASE):
                        scores[level] += 3  # Certification indicators are strongest
        
        # If skill is backed by certification, boost scores appropriately
        if is_backed:
            scores["Beginner"] += 1
            scores["Intermediate"] += 2
            scores["Advanced"] += 1
            logger.info(f"Boosting proficiency scores for backed skill: {skill_name}")
            
        # Add industry-specific context boost
        if self.industry != "general":
            # For technical skills in tech industry, boost intermediate
            if self.industry == "technology" and is_tech_skill:
                scores["Intermediate"] += 0.5
                
            # For healthcare skills in healthcare industry, boost appropriately
            elif self.industry == "healthcare" and skill_name in ["Patient Care", "Clinical Assessment", "Medical Terminology"]:
                scores["Intermediate"] += 0.5
                
            # For education skills in education industry
            elif self.industry == "education" and skill_name in ["Curriculum Development", "Classroom Management", "Student Assessment"]:
                scores["Intermediate"] += 0.5
                
            # For finance skills in finance industry
            elif self.industry == "finance" and skill_name in ["Financial Analysis", "Accounting", "Financial Reporting"]:
                scores["Intermediate"] += 0.5
        
        # For technical skills, add baseline boost based on context
        if is_tech_skill:
            # Check if skill is mentioned in a key skills section or with strong indicators
            tech_skill_patterns = [
                r"technical skills.*" + re.escape(skill_name),
                r"programming languages.*" + re.escape(skill_name),
                r"database technologies.*" + re.escape(skill_name),
                r"development tools.*" + re.escape(skill_name),
                r"proficient in.*" + re.escape(skill_name)
            ]
            
            if any(re.search(pattern, context, re.IGNORECASE) for pattern in tech_skill_patterns):
                scores["Intermediate"] += 1.5
        
        # Look for actual work or project experience with the skill
        experience_patterns = [
            r"(?:developed|built|created|implemented|designed).*" + re.escape(skill_name),
            r"project.*" + re.escape(skill_name),
            r"application.*" + re.escape(skill_name),
            r"system.*" + re.escape(skill_name),
            r"production.*" + re.escape(skill_name)
        ]
        
        # Add industry-specific experience patterns
        if self.industry == "healthcare":
            experience_patterns.extend([
                r"(?:treated|diagnosed|cared for).*" + re.escape(skill_name),
                r"patient.*" + re.escape(skill_name),
                r"clinical.*" + re.escape(skill_name),
                r"medical.*" + re.escape(skill_name)
            ])
        elif self.industry == "education":
            experience_patterns.extend([
                r"(?:taught|instructed|educated).*" + re.escape(skill_name),
                r"classroom.*" + re.escape(skill_name),
                r"student.*" + re.escape(skill_name),
                r"curriculum.*" + re.escape(skill_name)
            ])
        elif self.industry == "finance":
            experience_patterns.extend([
                r"(?:analyzed|prepared|audited).*" + re.escape(skill_name),
                r"financial.*" + re.escape(skill_name),
                r"accounting.*" + re.escape(skill_name),
                r"report.*" + re.escape(skill_name)
            ])
        
        if any(re.search(pattern, context, re.IGNORECASE) for pattern in experience_patterns):
            # Evidence of actual use boosts Intermediate and Advanced scores
            scores["Intermediate"] += 1
            scores["Advanced"] += 0.5
        
        # Determine the proficiency level with the highest score
        max_score = max(scores.values())
        
        # Default to Beginner if no strong indicators
        if max_score < 1:
            # Default assumptions based on skill type
            if is_language:
                return "Beginner", 0.6 + confidence_boost
            else:
                return "Beginner", 0.5 + confidence_boost
        
        # Get the highest scoring level
        proficiency_level = max(scores.items(), key=lambda x: x[1])[0]
        
        # Calculate confidence based on the difference between the highest and second highest score
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1 and sorted_scores[0] > 0:
            score_diff = sorted_scores[0] - sorted_scores[1]
            # Base confidence on score difference with minimum threshold
            confidence = min(0.5 + (score_diff * 0.1) + confidence_boost, 0.9)
        else:
            confidence = 0.6 + confidence_boost
        
        # Cap confidence for certain scenarios
        if not is_backed and proficiency_level in ["Advanced", "Expert"]:
            # Non-backed advanced claims have slightly lower confidence
            confidence = min(confidence, 0.8)
            
        # Adjust proficiency based on context if confidence is low
        if confidence < 0.65 and proficiency_level in ["Advanced", "Expert"]:
            # Downgrade to Intermediate if confidence is too low for Advanced/Expert
            proficiency_level = "Intermediate"
            
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
    proficiency_calculator = ProficiencyCalculator(skill_processor.technical_skills)
    
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
        # Verify that the skill is actually mentioned in the text with strict boundary checking
        skill_name = skill["name"]
        explicit_mention = re.search(r'\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE)
        
        if not explicit_mention:
            if args.verbose:
                logger.warning(f"Skipping skill {skill_name} - not explicitly mentioned in text")
            continue
            
        # Special validation for potentially ambiguous skills
        if skill_name in ["C++", "R"]:
            # More strict verification - ensure it's in a skills or programming context
            programming_context = any([
                re.search(r'programming.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                re.search(r'languages.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                re.search(r'skills.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                re.search(r'technologies.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                re.search(r'proficient.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                re.search(r'experience.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE)
            ])
            
            if not programming_context:
                if args.verbose:
                    logger.warning(f"Skipping ambiguous skill {skill_name} - not in proper context")
                continue
        
        # Get certification text for this skill if available
        cert_text = ""
        if cert_texts:
            for cert_file, text in cert_texts.items():
                if skill["name"].lower() in text.lower():
                    cert_text += text + " "
        
        # Get the confidence boost if available
        confidence_boost = skill.get("confidence_boost", 0)
        
        # Calculate proficiency
        proficiency_level, confidence = proficiency_calculator.calculate_proficiency(
            skill["name"], 
            skill["context"],
            certification_text=cert_text if cert_text else None,
            is_backed=skill.get("is_backed", False),
            confidence_boost=confidence_boost
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


def detect_industry(text):
    """
    Detect the likely industry based on resume content
    
    Args:
        text (str): The resume text
        
    Returns:
        tuple: (primary_industry, industry_scores) - The likely industry and scores for all industries
    """
    # Industry indicators - key terms that signal a particular industry
    industry_indicators = {
        "technology": [
            "software", "programming", "developer", "engineering", "code", "web", "app", 
            "database", "frontend", "backend", "devops", "IT", "computer science",
            "algorithm", "technical", "system", "cloud", "API", "github", "stack",
            "agile", "scrum", "sprint", "javascript", "python", "java", "C++"
        ],
        "healthcare": [
            "patient", "clinical", "medical", "healthcare", "diagnosis", "treatment", 
            "hospital", "doctor", "nurse", "physician", "therapy", "therapeutic", 
            "pharmaceutical", "medicine", "care", "health", "clinic", "pharmacy",
            "EMR", "EHR", "patient care", "bedside", "HIPAA", "medical record"
        ],
        "finance": [
            "financial", "finance", "accounting", "audit", "tax", "investment", "banking", 
            "portfolio", "asset", "stock", "equity", "market", "trading", "revenue", 
            "fiscal", "budget", "forecast", "profit", "loss", "ROI", "capital",
            "expense", "cost analysis", "reconciliation", "ledger", "GAAP"
        ],
        "education": [
            "teaching", "education", "school", "student", "curriculum", "classroom", 
            "instruction", "learning", "academic", "professor", "teacher", "faculty", 
            "course", "grade", "assessment", "lesson", "pedagogy", "educational",
            "training", "mentoring", "tutoring", "lecture", "seminar", "syllabus"
        ],
        "legal": [
            "legal", "law", "attorney", "counsel", "litigation", "paralegal", 
            "contract", "compliance", "regulation", "court", "case", "plaintiff", 
            "defendant", "judicial", "statute", "rights", "legal research",
            "deposition", "arbitration", "mediation", "negotiation", "brief"
        ],
        "marketing": [
            "marketing", "brand", "advertising", "campaign", "market research", "social media", 
            "digital marketing", "SEO", "content", "promotion", "customer", "consumer", 
            "product", "analytics", "audience", "engagement", "strategy", "creative",
            "conversion", "lead generation", "funnel", "CRM", "media buying"
        ],
        "consulting": [
            "consulting", "consultant", "client", "solution", "business strategy", 
            "advisory", "management consulting", "project", "engagement", "stakeholder", 
            "recommendation", "analysis", "implement", "transformation", "optimize",
            "problem-solving", "deliverable", "presentation", "proposal", "business case"
        ],
        "hr": [
            "human resources", "HR", "recruiting", "recruitment", "talent", "hiring", 
            "onboarding", "employee", "personnel", "compensation", "benefits", 
            "performance review", "training", "development", "workforce", "culture",
            "diversity", "inclusion", "labor relations", "employment", "HR information system"
        ],
        "data_science": [
            "data science", "machine learning", "AI", "artificial intelligence", "analytics", 
            "big data", "data mining", "statistical", "algorithm", "model", "prediction", 
            "clustering", "classification", "regression", "NLP", "neural network",
            "data visualization", "dashboard", "business intelligence", "insight"
        ],
        "design": [
            "design", "UX", "UI", "user experience", "graphic", "visual", "creative", 
            "layout", "wireframe", "prototype", "typography", "color", "art", 
            "illustration", "brand", "mockup", "interface", "interaction design",
            "user research", "usability", "accessibility", "responsive"
        ],
        "sales": [
            "sales", "selling", "revenue", "quota", "pipeline", "prospect", "lead", 
            "customer", "client", "account", "closing", "negotiation", "CRM", 
            "territory", "business development", "deal", "opportunity", "sales funnel",
            "commission", "upsell", "cross-sell", "target", "forecast"
        ]
    }
    
    # Count indicators for each industry
    counts = {industry: 0 for industry in industry_indicators}
    
    # Normalize the text for better matching
    normalized_text = text.lower()
    
    for industry, indicators in industry_indicators.items():
        for indicator in indicators:
            # Count explicit mentions
            explicit_count = len(re.findall(r'\b' + re.escape(indicator.lower()) + r'\b', normalized_text))
            counts[industry] += explicit_count
    
    # Add weighting for section headers
    industry_section_patterns = {
        "technology": [r'technical skills', r'programming', r'software development', r'engineering'],
        "healthcare": [r'clinical experience', r'medical', r'patient care', r'healthcare'],
        "finance": [r'financial', r'accounting', r'investment', r'banking'],
        "education": [r'teaching experience', r'education', r'academic', r'instructional'],
        "legal": [r'legal experience', r'law', r'legal research', r'litigation'],
        "marketing": [r'marketing experience', r'advertising', r'brand', r'campaign'],
        "consulting": [r'consulting experience', r'client engagement', r'advisory'],
        "hr": [r'human resources', r'recruiting', r'talent', r'hr'],
        "data_science": [r'data science', r'analytics', r'machine learning', r'statistical'],
        "design": [r'design experience', r'creative', r'ux', r'ui'],
        "sales": [r'sales experience', r'business development', r'account management']
    }
    
    for industry, patterns in industry_section_patterns.items():
        for pattern in patterns:
            section_matches = re.findall(r'\b' + re.escape(pattern) + r'[:\s]', normalized_text, re.IGNORECASE)
            # Section headers get extra weight
            counts[industry] += len(section_matches) * 5
    
    # Get primary industry (highest score)
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    primary_industry = sorted_counts[0][0] if sorted_counts[0][1] > 0 else "general"
    
    # Calculate confidence scores - normalize to sum to 1.0
    total = sum(counts.values())
    if total > 0:
        scores = {industry: count/total for industry, count in counts.items()}
    else:
        scores = {industry: 0 for industry in counts}
        scores["general"] = 1.0  # Default to general if no industry detected
    
    logger.info(f"Detected primary industry: {primary_industry} with scores: {sorted_counts[:3]}")
    
    return primary_industry, scores


def main():
    """Main function"""
    args = parse_arguments()
    
    # Process files and extract skills with proficiency levels
    results = process_files(args.input, args)
    
    # Save results
    save_results(results, args.output)


if __name__ == "__main__":
    main() 