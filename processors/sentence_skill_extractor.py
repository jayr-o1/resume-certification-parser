import re
import logging
import spacy
from typing import List, Dict, Any, Set, Optional
from utils.skill_database import SkillDatabase

# Initialize logging
logger = logging.getLogger('sentence_skill_extractor')

try:
    # Try loading the language model for NER and dependency parsing
    nlp = spacy.load("en_core_web_md")
except OSError:
    # Fall back to a simpler model if the larger one isn't available
    nlp = spacy.load("en_core_web_sm")
    logger.warning("Using smaller spaCy model. For better results, install en_core_web_md")

class SentenceSkillExtractor:
    """
    Specialized extractor that identifies skills within sentences and descriptive text
    using natural language processing and contextual clues.
    """
    
    def __init__(self, custom_db_path: Optional[str] = None):
        """
        Initialize the sentence skill extractor
        
        Args:
            custom_db_path (str, optional): Path to custom skills database
        """
        # Initialize skill database for validation and matching
        self.skill_db = SkillDatabase(custom_db_path)
        
        # Compile skill indication patterns - phrases that suggest skills
        self.skill_indicators = [
            r"experienced in ([\w\s,&/\-+]+)",
            r"expertise in ([\w\s,&/\-+]+)",
            r"skilled in ([\w\s,&/\-+]+)",
            r"proficient in ([\w\s,&/\-+]+)",
            r"knowledge of ([\w\s,&/\-+]+)",
            r"familiar with ([\w\s,&/\-+]+)",
            r"specializing in ([\w\s,&/\-+]+)",
            r"certified in ([\w\s,&/\-+]+)",
            r"trained in ([\w\s,&/\-+]+)",
            r"experience with ([\w\s,&/\-+]+)",
            r"background in ([\w\s,&/\-+]+)",
            r"abilities in ([\w\s,&/\-+]+)",
            r"competent in ([\w\s,&/\-+]+)",
            r"capability in ([\w\s,&/\-+]+)",
            r"([\w\s,&/\-+]+) skills",
            r"strong ([\w\s,&/\-+]+) skills",
            r"excellent ([\w\s,&/\-+]+) skills",
            r"advanced ([\w\s,&/\-+]+) skills",
            r"proven ([\w\s,&/\-+]+) skills",
            r"expert in ([\w\s,&/\-+]+)",
            # Database and technical specific patterns
            r"(database management systems?)",
            r"(relational databases?)",
            r"(data modeling)",
            r"(version control)",
            r"(database design)",
            r"(systems? database management)",
            r"(database administration)",
            r"(data(?:base)? security)",
            r"working with ([\w\s,&/\-+]+) databases",
            r"managing ([\w\s,&/\-+]+) systems",
            r"designing ([\w\s,&/\-+]+) solutions"
        ]
        
        # Compile patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.skill_indicators]
        
        # Skill adjective markers - adjectives that often precede skills
        self.skill_adjectives = {
            "strong", "excellent", "advanced", "proven", "expert", "proficient", 
            "skilled", "experienced", "knowledgeable", "capable", "effective",
            "outstanding", "exceptional", "superior", "solid", "comprehensive"
        }
        
        # Nouns/phrases often referred to as skills (to use when parsing sentences)
        self.skill_noun_indicators = {
            "skills", "abilities", "competencies", "expertise", "knowledge", 
            "proficiency", "capabilities", "qualification", "experience", 
            "background", "strength", "talent", "aptitude", "specialty", 
            "foundation", "foundations", "basics", "fundamentals"
        }
        
        # Technical compound terms that should be kept together
        self.technical_compounds = [
            "database management systems", "systems database management", 
            "relational databases", "data modeling", "version control",
            "entity relationship diagrams", "data normalization",
            "database design", "database administration", "database security",
            "database optimization", "performance tuning", "query optimization"
        ]
    
    def extract_skills_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract skills from text, including descriptive sentences
        
        Args:
            text (str): Text to extract skills from
            
        Returns:
            list: List of extracted skill dictionaries
        """
        extracted_skills = []
        
        # Clean the text
        text = text.strip()
        if not text:
            return extracted_skills
        
        # Extract using pattern matching
        pattern_skills = self._extract_with_patterns(text)
        extracted_skills.extend(pattern_skills)
        
        # Extract using NLP-based analysis
        nlp_skills = self._extract_with_nlp(text)
        extracted_skills.extend(nlp_skills)
        
        # Deduplicate skills
        deduplicated_skills = self._deduplicate_skills(extracted_skills)
        
        return deduplicated_skills
    
    def _extract_with_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract skills using regex patterns that identify skill phrases
        
        Args:
            text (str): Text to extract skills from
            
        Returns:
            list: List of extracted skill dictionaries
        """
        extracted_skills = []
        
        # Break text into lines/sentences for better context
        lines = re.split(r'[\.\n]', text)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Apply each pattern to the line
            for i, pattern in enumerate(self.compiled_patterns):
                matches = pattern.findall(line)
                
                for match in matches:
                    # Clean the match
                    if isinstance(match, tuple):
                        match = match[0]  # Extract from capture group
                    
                    skill_text = match.strip()
                    
                    # Skip if empty
                    if not skill_text:
                        continue
                    
                    # For pattern matches, check for multiple skills (comma/and separated)
                    if any(separator in skill_text for separator in [',', ' and ', ';']):
                        # Split by common separators
                        for splitter in [',', ' and ', ';']:
                            if splitter in skill_text:
                                parts = [p.strip() for p in skill_text.split(splitter)]
                                for part in parts:
                                    if part:
                                        self._process_potential_skill(part, line, extracted_skills)
                    else:
                        # Process as a single skill
                        self._process_potential_skill(skill_text, line, extracted_skills)
        
        return extracted_skills
    
    def _extract_with_nlp(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract skills using NLP analysis of the text
        
        Args:
            text (str): Text to extract skills from
            
        Returns:
            list: List of extracted skill dictionaries
        """
        extracted_skills = []
        
        # Process with spaCy
        doc = nlp(text)
        
        # Extract skills from each sentence
        for sent in doc.sents:
            # Look for skill-indicating structures
            self._analyze_sentence_structure(sent, extracted_skills)
            
            # Extract noun phrases that might be skills
            for chunk in sent.noun_chunks:
                # Skip very short chunks
                if len(chunk.text.split()) < 2:
                    continue
                
                # Check if this might be a skill phrase
                self._process_potential_skill(chunk.text, sent.text, extracted_skills)
        
        return extracted_skills
    
    def _analyze_sentence_structure(self, sent, extracted_skills: List[Dict[str, Any]]):
        """
        Analyze sentence structure to identify skills based on dependencies
        
        Args:
            sent: The spaCy sentence object
            extracted_skills: List to append extracted skills to
        """
        # Check for skill description patterns like "Skilled in X" or "Expert in X"
        # These often follow a structure where a skill is the object of a preposition
        for token in sent:
            # Look for prepositions that might introduce skills
            if token.dep_ == "prep" and token.text.lower() in ["in", "with"]:
                # The skill often follows the preposition
                skill_tokens = []
                for child in token.children:
                    if child.dep_ in ["pobj", "dobj"]:
                        # Get the full phrase including any children
                        phrase = self._get_full_phrase(child)
                        self._process_potential_skill(phrase, sent.text, extracted_skills)
            
            # Look for adjectives that often describe skills
            if token.pos_ == "ADJ" and token.text.lower() in self.skill_adjectives:
                for child in token.children:
                    if child.dep_ == "conj":
                        phrase = self._get_full_phrase(child)
                        self._process_potential_skill(phrase, sent.text, extracted_skills)
                
                # Also check if the adjective is modifying a noun that could be a skill
                if token.head.pos_ == "NOUN":
                    phrase = self._get_full_phrase(token.head)
                    self._process_potential_skill(phrase, sent.text, extracted_skills)
    
    def _get_full_phrase(self, token) -> str:
        """
        Get the full phrase starting from a token, including its children
        
        Args:
            token: The spaCy token
            
        Returns:
            str: The full phrase
        """
        words = [token.text]
        for child in token.children:
            # Only include certain dependency types to avoid getting too much
            if child.dep_ in ["amod", "compound", "nmod", "advmod", "conj", "cc", "prep", "pobj"]:
                # Recursively get child phrases
                child_phrase = self._get_full_phrase(child)
                words.append(child_phrase)
        
        # Join all words, but handle order properly
        return " ".join(words)
    
    def _process_potential_skill(self, skill_text: str, context: str, extracted_skills: List[Dict[str, Any]]):
        """
        Process a potential skill, validate it, and add to extracted skills if valid
        
        Args:
            skill_text (str): Potential skill text
            context (str): Context the skill was found in
            extracted_skills (list): List to add the skill to if valid
        """
        # Skip if too short
        if len(skill_text) < 3:
            return
        
        # Skip common non-skill words
        if skill_text.lower() in self.skill_noun_indicators:
            return
        
        # Clean the skill text
        clean_skill = self._clean_skill_text(skill_text)
        
        # Skip if cleaning made it too short
        if len(clean_skill) < 3:
            return
        
        # Check for compound technical terms that should be kept together
        for compound in self.technical_compounds:
            if compound in clean_skill.lower():
                # Found a technical compound term
                extracted_skills.append({
                    "name": compound.title(),  # Convert to title case
                    "confidence_score": 0.85,  # High confidence for compound terms
                    "source": "sentence_extraction",
                    "context": context,
                    "is_technical": True  # Technical compound terms are always technical
                })
                return
        
        # Try to find in skill database
        if self.skill_db.is_known_skill(clean_skill):
            # Use canonical name from database
            canonical_name = self.skill_db.get_canonical_name(clean_skill)
            category = self.skill_db.get_skill_category(canonical_name)
            
            # Add to extracted skills
            extracted_skills.append({
                "name": canonical_name,
                "confidence_score": 0.9,  # High confidence for database match
                "source": "sentence_extraction",
                "context": context,
                "is_technical": (category == "technical")
            })
        elif len(clean_skill.split()) <= 3:
            # For short phrases not in database, still consider them
            # but with lower confidence
            extracted_skills.append({
                "name": clean_skill,
                "confidence_score": 0.6,  # Lower confidence for non-database match
                "source": "sentence_extraction",
                "context": context,
                "is_technical": self._guess_if_technical(clean_skill, context)
            })
    
    def _clean_skill_text(self, text: str) -> str:
        """
        Clean skill text by removing unnecessary parts
        
        Args:
            text (str): Skill text to clean
            
        Returns:
            str: Cleaned skill text
        """
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
    
    def _guess_if_technical(self, skill_name: str, context: str) -> bool:
        """
        Make an educated guess if a skill is technical based on context
        
        Args:
            skill_name (str): The skill name
            context (str): The context the skill was found in
            
        Returns:
            bool: True if likely technical, False otherwise
        """
        # Check for technical-sounding terms in the skill name
        technical_indicators = ["software", "programming", "development", "system", 
                              "analysis", "database", "design", "implementation", 
                              "architecture", "network", "security", "data", "code",
                              "application", "platform", "framework", "language",
                              "algorithm", "automation", "engineering", "technical"]
        
        for indicator in technical_indicators:
            if indicator in skill_name.lower() or indicator in context.lower():
                return True
        
        # Default to soft skill
        return False
    
    def _deduplicate_skills(self, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate skills by name and retain the one with highest confidence
        
        Args:
            skills (list): List of skill dictionaries
            
        Returns:
            list: Deduplicated list of skill dictionaries
        """
        skill_map = {}
        
        for skill in skills:
            skill_name = skill["name"]
            confidence = skill["confidence_score"]
            
            if skill_name not in skill_map or confidence > skill_map[skill_name]["confidence_score"]:
                skill_map[skill_name] = skill
                
        return list(skill_map.values()) 