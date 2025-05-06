import re
import logging
from typing import List, Dict, Any, Optional
from utils.skill_database import SkillDatabase

logger = logging.getLogger('skill_validator')

class SkillValidator:
    """
    Validates and cleans extracted skills to remove non-skills and improve accuracy
    """
    
    def __init__(self, custom_db_path: Optional[str] = None):
        """
        Initialize the skill validator
        
        Args:
            custom_db_path (str, optional): Path to custom skills database
        """
        # Initialize skill database for validation
        self.skill_db = SkillDatabase(custom_db_path)
        
        # List of common non-skill phrases that should be filtered out
        self.invalid_skills = [
            # Section headers
            "key skills", "core skills", "technical skills", "professional skills",
            "soft skills", "hard skills", "primary skills", "skills include", "skills",
            "qualifications", "competencies", "expertise", "experience", "education",
            "certification", "professional summary", "summary",
            
            # Action phrases
            "collaborated with", "curriculum enhancements", "technologies into",
            "integrated", "developed", "implemented", "managed", "created",
            "enhanced", "improved", "directed", "supervised", "assisted", 
            "helped", "supported", "delivered", "provided", "utilized", "demonstrated",
            
            # Parts of phrases
            "key", "core", "technical", "professional", "soft", "hard", "primary",
            "proficient in", "experience with", "expertise in", "knowledge of",
            "familiar with", "worked with", "used", "foundation", "foundations",
            
            # Resume section names
            "work experience", "education", "professional experience", "employment",
            "job history", "career", "achievements", "accomplishments"
        ]
        
        # Compile regex patterns for invalid skills
        self.invalid_patterns = [
            # Phrases that start with action verbs or contain verb phrases
            r"^(collaborated|developed|implemented|managed|created|enhanced|improved|integrated|directed|supervised|assisted|helped|supported)\b",
            r"\b(using|utilizing|applying|implementing|developing|creating|enhancing|improving)\b",
            
            # Phrases that are clearly incomplete fragments
            r"^(into|for|with|to|by|from)\b",
            r"(into|for|with|to|by|from)$",
            
            # Phrases that are likely parts of bullet points
            r"^[•\-\*]\s*",
            
            # Capitalized phrases that are likely titles or headers
            r"^[A-Z][a-z]*([\s-][A-Z][a-z]*)+$"
        ]
        
        # Compile the patterns
        self.compiled_patterns = [re.compile(pattern) for pattern in self.invalid_patterns]
        
    def validate_skills(self, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean extracted skills
        
        Args:
            skills (list): List of extracted skill dictionaries
            
        Returns:
            list: Validated and cleaned skills
        """
        validated_skills = []
        
        for skill in skills:
            skill_name = skill["name"]
            
            # Skip skills that match invalid patterns
            if self._is_invalid_skill(skill_name):
                logger.info(f"Filtered out invalid skill: '{skill_name}'")
                continue
            
            # Clean the skill name
            cleaned_name = self.clean_skill_name(skill_name)
            
            # Try to find the canonical name in the database
            if self.skill_db.is_known_skill(cleaned_name):
                canonical_name = self.skill_db.get_canonical_name(cleaned_name)
                # Use the canonical name from the database
                skill["name"] = canonical_name
                
                # Set is_technical based on skill category
                category = self.skill_db.get_skill_category(canonical_name)
                skill["is_technical"] = (category == "technical")
                
                # If confidence is low, boost it for known skills
                if skill.get("confidence", 0) < 0.5:
                    skill["confidence"] = 0.5
                
                validated_skills.append(skill)
            elif len(cleaned_name.split()) <= 2:
                # For short names (1-2 words) that aren't in the database
                # still accept them if they pass other validation
                
                # If the name was cleaned, update it
                if cleaned_name != skill_name:
                    skill["name"] = cleaned_name
                
                validated_skills.append(skill)
            else:
                # Longer phrases that aren't in the database are likely not skills
                logger.info(f"Filtered out unknown multi-word skill: '{skill_name}'")
                continue
                
        return validated_skills
        
    def _is_invalid_skill(self, skill_name: str) -> bool:
        """
        Check if a skill name should be considered invalid
        
        Args:
            skill_name (str): The skill name to check
            
        Returns:
            bool: True if the skill is invalid, False otherwise
        """
        # Convert to lowercase for comparison
        name_lower = skill_name.lower()
        
        # Special exception for known technical terms - always allow these
        technical_exceptions = [
            "database management", "database systems", "database management systems", 
            "systems database management", "relational databases", "data modeling", 
            "version control", "data analysis", "data mining", "machine learning",
            "artificial intelligence", "natural language processing", "computer vision",
            "cloud computing", "distributed systems", "operating systems", "networking",
            "cyber security", "information security", "web development", "mobile development",
            "software engineering", "devops", "continuous integration", "continuous deployment"
        ]
        
        if any(exception in name_lower for exception in technical_exceptions):
            return False
        
        # Check against the list of invalid skills
        for invalid_skill in self.invalid_skills:
            if invalid_skill in name_lower:
                return True
                
        # Check against regex patterns
        for pattern in self.compiled_patterns:
            if pattern.search(skill_name):
                return True
                
        # Check length and word count
        words = name_lower.split()
        if len(words) > 4:  # Too many words is likely a phrase, not a skill
            return True
            
        # Check for sentence-like structures
        sentence_indicators = [". ", "! ", "? ", ": ", "; ", " and ", " or ", " but ", " because ", " when ", " while "]
        if any(indicator in name_lower for indicator in sentence_indicators):
            return True
            
        return False
        
    def clean_skill_name(self, skill_name: str) -> str:
        """
        Clean a skill name by removing unnecessary prefixes/suffixes
        
        Args:
            skill_name (str): The skill name to clean
            
        Returns:
            str: Cleaned skill name
        """
        # Remove common prefixes like "proficient in", "experience with", etc.
        prefixes = ["proficient in ", "experience with ", "expertise in ", "knowledge of ", "skilled in ", 
                   "familiar with ", "worked with ", "used ", "using "]
        
        cleaned_name = skill_name
        for prefix in prefixes:
            if cleaned_name.lower().startswith(prefix):
                cleaned_name = cleaned_name[len(prefix):]
                
        # Remove trailing punctuation and whitespace
        cleaned_name = cleaned_name.strip(" .,;:-")
        
        # Capitalize first letter of each word for consistency
        cleaned_name = ' '.join(word.capitalize() for word in cleaned_name.split())
        
        return cleaned_name 