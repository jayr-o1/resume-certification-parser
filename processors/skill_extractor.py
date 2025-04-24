import json
import re
import os
import spacy
import logging
from collections import defaultdict

try:
    # Try loading the language model for NER
    nlp = spacy.load("en_core_web_md")
except OSError:
    # Fall back to a simpler model if the larger one isn't available
    nlp = spacy.load("en_core_web_sm")
    
logger = logging.getLogger('skill_extractor')

class SkillExtractor:
    """
    Skill extractor that works with structured document formats
    for more accurate skill identification
    """
    
    def __init__(self, skills_db_path=None):
        """
        Initialize the skill extractor
        
        Args:
            skills_db_path (str, optional): Path to custom skills database JSON file
        """
        self.skills_data = self._load_skills_data(skills_db_path)
        self.technical_skills = self.skills_data.get("technical_skills", [])
        self.soft_skills = self.skills_data.get("soft_skills", [])
        
        # Prepare skill name variations
        self.skill_variations = self._prepare_skill_variations()
        
        # Regular expressions for skill detection
        self.skill_patterns = self._compile_skill_patterns()
        
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
        
    def _compile_skill_patterns(self):
        """
        Compile regular expressions for skill detection
        
        Returns:
            list: Compiled regular expression patterns
        """
        patterns = []
        
        # Pattern for skills in lists (with bullets, etc.)
        patterns.append(re.compile(r'(?:^|\n)[\s\-•*>]+([^•\n]+)'))
        
        # Pattern for skills in technology sections
        patterns.append(re.compile(r'(?:technologies|technical skills|tools|languages|frameworks)(?:[:\s]+)([^\n]+)', re.IGNORECASE))
        
        # Pattern for skills in parentheses
        patterns.append(re.compile(r'\(([^)]+)\)'))
        
        # Pattern for comma or semicolon separated lists
        patterns.append(re.compile(r'([^,;]+)(?:[,;]|$)'))
        
        return patterns
        
    def extract_skills(self, structured_doc):
        """
        Extract skills from a structured document
        
        Args:
            structured_doc (dict): Structured document representation
            
        Returns:
            list: List of extracted skills with metadata
        """
        extracted_skills = []
        sections_with_skills = {}
        
        # Process based on document type
        doc_type = structured_doc.get("document_type", "unknown")
        
        # First, process section-based extraction
        if "sections" in structured_doc:
            sections = structured_doc["sections"]
            
            # Extract from explicit skills sections
            if "skills" in sections:
                skill_lines = sections["skills"]
                skill_section_skills = self._extract_from_lines(skill_lines, "skills_section")
                extracted_skills.extend(skill_section_skills)
                sections_with_skills["skills_section"] = skill_section_skills
                
            # Extract from summary sections
            if "summary" in sections:
                summary_lines = sections["summary"]
                summary_skills = self._extract_from_lines(summary_lines, "summary")
                extracted_skills.extend(summary_skills)
                sections_with_skills["summary"] = summary_skills
                
            # For resumes, also extract from experience sections
            if doc_type == "resume" and "experience" in sections:
                experience_lines = sections["experience"]
                experience_skills = self._extract_from_lines(experience_lines, "experience")
                extracted_skills.extend(experience_skills)
                sections_with_skills["experience"] = experience_skills
            
            # For certifications, focus on the certification content
            if doc_type == "certification" and "certifications" in sections:
                cert_lines = sections["certifications"]
                cert_skills = self._extract_from_lines(cert_lines, "certification_content")
                extracted_skills.extend(cert_skills)
                sections_with_skills["certification_content"] = cert_skills
        
        # Next, process layout-based extraction for PDF
        if "pages" in structured_doc:
            for page in structured_doc["pages"]:
                # Process tables which often contain skills
                if "tables" in structured_doc.get("structure", {}):
                    for table in structured_doc["structure"]["tables"]:
                        if table["page"] == page["number"]:
                            table_skills = self._extract_from_table(table, "table_content")
                            extracted_skills.extend(table_skills)
                            if "table_content" not in sections_with_skills:
                                sections_with_skills["table_content"] = []
                            sections_with_skills["table_content"].extend(table_skills)
                
                # Process words with positions for layout-aware extraction
                if "words" in page:
                    words_skills = self._extract_from_positioned_words(page["words"], "positioned_content")
                    extracted_skills.extend(words_skills)
                    if "positioned_content" not in sections_with_skills:
                        sections_with_skills["positioned_content"] = []
                    sections_with_skills["positioned_content"].extend(words_skills)
        
        # For image-based documents, try OCR layout information
        if "layout" in structured_doc:
            layout_skills = self._extract_from_ocr_layout(structured_doc["layout"], "ocr_layout")
            extracted_skills.extend(layout_skills)
            sections_with_skills["ocr_layout"] = layout_skills
        
        # Finally, use NLP-based extraction on the raw text as a fallback
        if "raw_text" in structured_doc:
            nlp_skills = self._extract_with_nlp(structured_doc["raw_text"], "nlp_extraction")
            extracted_skills.extend(nlp_skills)
            sections_with_skills["nlp_extraction"] = nlp_skills
            
        # Deduplicate skills while preserving the highest confidence and metadata
        deduplicated_skills = self._deduplicate_skills(extracted_skills)
        
        return deduplicated_skills, sections_with_skills
        
    def _extract_from_lines(self, lines, source):
        """
        Extract skills from a list of text lines
        
        Args:
            lines (list): List of text lines
            source (str): Source section name
            
        Returns:
            list: Extracted skills with metadata
        """
        extracted_skills = []
        
        for line in lines:
            # Clean the line
            clean_line = line.strip()
            if not clean_line:
                continue
                
            # Check if the line itself is a skill
            skill_match = self._match_skill(clean_line)
            if skill_match:
                extracted_skills.append({
                    "name": skill_match,
                    "confidence_score": 0.85,  # High confidence for direct matches
                    "source": source,
                    "context": clean_line
                })
                continue
                
            # Check for skills in the line
            # First, try to split by common delimiters
            if any(delim in clean_line for delim in [',', ';', '|', '•', '·']):
                # Split by delimiters and check each part
                for delimiter in [',', ';', '|', '•', '·']:
                    if delimiter in clean_line:
                        parts = [p.strip() for p in clean_line.split(delimiter)]
                        for part in parts:
                            if not part:
                                continue
                            skill_match = self._match_skill(part)
                            if skill_match:
                                extracted_skills.append({
                                    "name": skill_match,
                                    "confidence_score": 0.8,
                                    "source": source,
                                    "context": clean_line
                                })
            else:
                # Apply NLP to extract potential skill entities
                doc = nlp(clean_line)
                
                # Look for noun phrases that might be skills
                for chunk in doc.noun_chunks:
                    skill_match = self._match_skill(chunk.text)
                    if skill_match:
                        extracted_skills.append({
                            "name": skill_match,
                            "confidence_score": 0.7,
                            "source": source,
                            "context": clean_line
                        })
                
                # Check for patterns that often indicate skills
                for pattern in self.skill_patterns:
                    matches = pattern.findall(clean_line)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        match = match.strip()
                        if not match:
                            continue
                        skill_match = self._match_skill(match)
                        if skill_match:
                            extracted_skills.append({
                                "name": skill_match,
                                "confidence_score": 0.75,
                                "source": source,
                                "context": clean_line
                            })
        
        return extracted_skills
        
    def _extract_from_table(self, table, source):
        """
        Extract skills from a table
        
        Args:
            table (dict): Table information
            source (str): Source section name
            
        Returns:
            list: Extracted skills with metadata
        """
        extracted_skills = []
        
        # Extract skills from table content
        if "content" in table and table["content"]:
            for row in table["content"]:
                for cell in row:
                    if cell and isinstance(cell, str):
                        # Clean the cell content
                        clean_cell = cell.strip()
                        if not clean_cell:
                            continue
                        
                        # Check if the cell content is a skill
                        skill_match = self._match_skill(clean_cell)
                        if skill_match:
                            extracted_skills.append({
                                "name": skill_match,
                                "confidence_score": 0.9,  # High confidence for skills in tables
                                "source": source,
                                "context": f"Table cell: {clean_cell}"
                            })
                            continue
                            
                        # Check for skills in the cell content
                        if any(delim in clean_cell for delim in [',', ';', '|']):
                            # Split by delimiters and check each part
                            for delimiter in [',', ';', '|']:
                                if delimiter in clean_cell:
                                    parts = [p.strip() for p in clean_cell.split(delimiter)]
                                    for part in parts:
                                        if not part:
                                            continue
                                        skill_match = self._match_skill(part)
                                        if skill_match:
                                            extracted_skills.append({
                                                "name": skill_match,
                                                "confidence_score": 0.85,
                                                "source": source,
                                                "context": f"Table cell: {clean_cell}"
                                            })
        
        return extracted_skills
        
    def _extract_from_positioned_words(self, words, source):
        """
        Extract skills from positioned words
        
        Args:
            words (list): List of words with position information
            source (str): Source section name
            
        Returns:
            list: Extracted skills with metadata
        """
        extracted_skills = []
        
        # Group words by their y-position (approximate lines)
        lines_by_y = defaultdict(list)
        
        for word in words:
            if "top" in word:
                # Round to the nearest multiple of 5 to group words in the same line
                y_key = round(word["top"] / 5) * 5
                lines_by_y[y_key].append(word)
        
        # Sort each line by x-position and create line text
        for y_key, line_words in lines_by_y.items():
            sorted_words = sorted(line_words, key=lambda w: w.get("x0", 0))
            line_text = " ".join(w.get("text", "") for w in sorted_words)
            
            # Skip empty lines
            if not line_text.strip():
                continue
                
            # Check if the line is a skill or contains skills
            skill_match = self._match_skill(line_text)
            if skill_match:
                extracted_skills.append({
                    "name": skill_match,
                    "confidence_score": 0.8,
                    "source": source,
                    "context": line_text
                })
                continue
                
            # Check for skills in the line
            if any(delim in line_text for delim in [',', ';', '|']):
                # Split by delimiters and check each part
                for delimiter in [',', ';', '|']:
                    if delimiter in line_text:
                        parts = [p.strip() for p in line_text.split(delimiter)]
                        for part in parts:
                            if not part:
                                continue
                            skill_match = self._match_skill(part)
                            if skill_match:
                                extracted_skills.append({
                                    "name": skill_match,
                                    "confidence_score": 0.75,
                                    "source": source,
                                    "context": line_text
                                })
        
        return extracted_skills
        
    def _extract_from_ocr_layout(self, layout_data, source):
        """
        Extract skills from OCR layout data
        
        Args:
            layout_data (dict): OCR layout information
            source (str): Source section name
            
        Returns:
            list: Extracted skills with metadata
        """
        extracted_skills = []
        
        # Skip if layout data doesn't contain text
        if not layout_data or "text" not in layout_data:
            return extracted_skills
            
        # Group OCR results by line
        line_texts = []
        current_line = []
        current_line_num = -1
        
        for i in range(len(layout_data["text"])):
            text = layout_data["text"][i]
            if not text.strip():
                continue
                
            line_num = layout_data.get("line_num", [])[i] if "line_num" in layout_data else -1
            
            if line_num != current_line_num and current_line:
                line_texts.append(" ".join(current_line))
                current_line = []
                
            current_line.append(text)
            current_line_num = line_num
            
        if current_line:
            line_texts.append(" ".join(current_line))
            
        # Process each line
        for line in line_texts:
            clean_line = line.strip()
            if not clean_line:
                continue
                
            # Check if the line itself is a skill
            skill_match = self._match_skill(clean_line)
            if skill_match:
                extracted_skills.append({
                    "name": skill_match,
                    "confidence_score": 0.75,  # Lower confidence for OCR results
                    "source": source,
                    "context": clean_line
                })
                continue
                
            # Check for skills in the line
            if any(delim in clean_line for delim in [',', ';', '|']):
                # Split by delimiters and check each part
                for delimiter in [',', ';', '|']:
                    if delimiter in clean_line:
                        parts = [p.strip() for p in clean_line.split(delimiter)]
                        for part in parts:
                            if not part:
                                continue
                            skill_match = self._match_skill(part)
                            if skill_match:
                                extracted_skills.append({
                                    "name": skill_match,
                                    "confidence_score": 0.7,
                                    "source": source,
                                    "context": clean_line
                                })
        
        return extracted_skills
        
    def _extract_with_nlp(self, text, source):
        """
        Extract skills using NLP
        
        Args:
            text (str): Text to analyze
            source (str): Source section name
            
        Returns:
            list: Extracted skills with metadata
        """
        extracted_skills = []
        
        # Skip if text is empty
        if not text.strip():
            return extracted_skills
            
        # Process with spaCy
        doc = nlp(text)
        
        # Look for noun phrases that might be skills
        for chunk in doc.noun_chunks:
            skill_match = self._match_skill(chunk.text)
            if skill_match:
                extracted_skills.append({
                    "name": skill_match,
                    "confidence_score": 0.6,  # Lower confidence for NLP extraction
                    "source": source,
                    "context": chunk.sent.text if hasattr(chunk, 'sent') else ""
                })
        
        # Extract skills from sentences with skill indicators
        skill_indicators = ["proficient in", "experience with", "skilled in", "knowledge of", 
                           "expertise in", "familiar with", "worked with", "used"]
                           
        for sent in doc.sents:
            sent_text = sent.text.lower()
            
            for indicator in skill_indicators:
                if indicator in sent_text:
                    # Extract the part after the indicator
                    parts = sent_text.split(indicator, 1)
                    if len(parts) > 1:
                        after_part = parts[1]
                        
                        # Check for comma-separated skills
                        skill_parts = [p.strip() for p in re.split(r'[,;]', after_part)]
                        
                        for part in skill_parts:
                            # Stop at end of sentence or another indicator
                            if "." in part:
                                part = part.split(".", 1)[0]
                                
                            # Clean up and match skill
                            clean_part = re.sub(r'[^\w\s]', '', part).strip()
                            skill_match = self._match_skill(clean_part)
                            
                            if skill_match:
                                extracted_skills.append({
                                    "name": skill_match,
                                    "confidence_score": 0.65,
                                    "source": source,
                                    "context": sent.text
                                })
        
        return extracted_skills
        
    def _match_skill(self, text):
        """
        Match a text to a known skill
        
        Args:
            text (str): Text to match
            
        Returns:
            str or None: Matched skill name or None
        """
        # Clean and normalize the text
        cleaned_text = text.strip().lower()
        cleaned_text = re.sub(r'[^\w\s]', '', cleaned_text)
        
        # Direct match
        if cleaned_text in self.skill_variations:
            return self.skill_variations[cleaned_text]
            
        # Check for substring matches (for multi-word skills)
        for skill_text, canonical_skill in self.skill_variations.items():
            if len(skill_text) > 3 and skill_text in cleaned_text:
                # Make sure it's a full word match, not part of another word
                if re.search(r'\b' + re.escape(skill_text) + r'\b', cleaned_text):
                    return canonical_skill
        
        # No match found
        return None
        
    def _deduplicate_skills(self, skills):
        """
        Deduplicate skills while preserving the highest confidence and metadata
        
        Args:
            skills (list): List of skill dictionaries
            
        Returns:
            list: Deduplicated skills
        """
        skill_map = {}
        
        for skill in skills:
            skill_name = skill["name"]
            confidence = skill["confidence_score"]
            
            if skill_name not in skill_map or confidence > skill_map[skill_name]["confidence_score"]:
                skill_map[skill_name] = skill
                
        return list(skill_map.values()) 