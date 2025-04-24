import re
import nltk
from nltk.tokenize import sent_tokenize
from models.skill import Skill

class ProficiencyCalculator:
    """
    Calculates proficiency levels for extracted skills
    """
    
    def __init__(self):
        """Initialize the ProficiencyCalculator"""
        # Ensure NLTK data is downloaded
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            
        # Proficiency level indicators
        self.proficiency_indicators = {
            "Beginner": [
                "basic knowledge", "fundamental", "introductory", "novice", 
                "entry-level", "beginner", "basic understanding", "elementary",
                "limited experience", "newly acquired", "recently learned"
            ],
            "Intermediate": [
                "intermediate", "competent", "proficient", "skilled", "capable",
                "working knowledge", "moderate experience", "practical knowledge",
                "comfortable with", "familiar with", "solid understanding",
                "hands-on experience", "applied knowledge"
            ],
            "Advanced": [
                "advanced", "extensive experience", "in-depth knowledge", 
                "highly skilled", "strong background", "deep understanding",
                "significant experience", "expert-level", "mastery", "expertise",
                "specialized knowledge", "thoroughly familiar", "considerable experience"
            ],
            "Expert": [
                "expert", "mastery of", "authority on", "specialized", "guru",
                "leading", "top-tier", "exceptional", "world-class", "superior",
                "renowned", "distinguished", "preeminent", "outstanding",
                "certified expert", "recognized expert", "industry-leading"
            ]
        }
        
        # Words indicating experience duration
        self.experience_indicators = {
            r"(\d+)\s*(?:\+)?\s*years?\s*(?:of)?\s*experience": {
                (0, 2): "Beginner",
                (2, 4): "Intermediate",
                (4, 8): "Advanced",
                (8, float('inf')): "Expert"
            },
            r"(\d+)\s*(?:\+)?\s*years?\s*working with": {
                (0, 2): "Beginner",
                (2, 4): "Intermediate",
                (4, 8): "Advanced",
                (8, float('inf')): "Expert"
            }
        }
        
    def calculate_proficiency(self, skill_name, text):
        """
        Calculate proficiency level for a skill based on surrounding text
        
        Args:
            skill_name (str): The name of the skill
            text (str): The text containing the skill
            
        Returns:
            tuple: (proficiency level, confidence score)
        """
        if not skill_name or not text:
            return (None, 0.0)
            
        # Default values
        proficiency_level = None
        confidence_score = 0.0
        
        # Find sentences containing the skill
        relevant_sentences = self._find_relevant_sentences(skill_name, text)
        
        if not relevant_sentences:
            return (None, 0.0)
            
        # Check for direct proficiency indicators
        direct_proficiency, direct_confidence = self._check_direct_proficiency_indicators(skill_name, relevant_sentences)
        
        # Check for experience duration indicators
        experience_proficiency, experience_confidence = self._check_experience_indicators(skill_name, relevant_sentences)
        
        # Calculate final proficiency and confidence
        if direct_confidence > experience_confidence:
            proficiency_level = direct_proficiency
            confidence_score = direct_confidence
        else:
            proficiency_level = experience_proficiency
            confidence_score = experience_confidence
            
        return (proficiency_level, confidence_score)
        
    def _find_relevant_sentences(self, skill_name, text):
        """
        Find sentences in the text that mention the skill
        
        Args:
            skill_name (str): The name of the skill
            text (str): The text to search in
            
        Returns:
            list: List of sentences containing the skill
        """
        relevant_sentences = []
        sentences = sent_tokenize(text)
        
        skill_pattern = r'\b' + re.escape(skill_name) + r'\b'
        
        for sentence in sentences:
            if re.search(skill_pattern, sentence, re.IGNORECASE):
                relevant_sentences.append(sentence)
                
                # Also include adjacent sentences for context
                sentence_index = sentences.index(sentence)
                
                if sentence_index > 0:
                    relevant_sentences.append(sentences[sentence_index - 1])
                    
                if sentence_index < len(sentences) - 1:
                    relevant_sentences.append(sentences[sentence_index + 1])
                    
        return list(set(relevant_sentences))  # Remove duplicates
        
    def _check_direct_proficiency_indicators(self, skill_name, sentences):
        """
        Check for direct proficiency indicators in sentences
        
        Args:
            skill_name (str): The name of the skill
            sentences (list): List of sentences to check
            
        Returns:
            tuple: (proficiency level, confidence score)
        """
        proficiency_scores = {level: 0 for level in self.proficiency_indicators}
        
        for sentence in sentences:
            lower_sentence = sentence.lower()
            
            # Check each proficiency level's indicators
            for level, indicators in self.proficiency_indicators.items():
                for indicator in indicators:
                    # Check if indicator is in the sentence
                    if indicator.lower() in lower_sentence:
                        # Check if indicator is close to skill name
                        if self._is_close_to_skill(skill_name, indicator, lower_sentence):
                            proficiency_scores[level] += 1
                            
        # Determine the most likely proficiency level
        max_score = 0
        proficiency_level = None
        
        for level, score in proficiency_scores.items():
            if score > max_score:
                max_score = score
                proficiency_level = level
                
        # Calculate confidence based on how many indicators were found
        confidence = min(max_score * 0.2, 0.8) if max_score > 0 else 0.0
        
        return (proficiency_level, confidence)
        
    def _check_experience_indicators(self, skill_name, sentences):
        """
        Check for experience duration indicators in sentences
        
        Args:
            skill_name (str): The name of the skill
            sentences (list): List of sentences to check
            
        Returns:
            tuple: (proficiency level, confidence score)
        """
        for sentence in sentences:
            lower_sentence = sentence.lower()
            
            # Check if sentence mentions both the skill and some experience
            if skill_name.lower() in lower_sentence and ('experience' in lower_sentence or 'working with' in lower_sentence):
                # Check each experience pattern
                for pattern, level_map in self.experience_indicators.items():
                    matches = re.finditer(pattern, lower_sentence)
                    
                    for match in matches:
                        years = int(match.group(1))
                        
                        # Determine proficiency level based on years of experience
                        for (min_years, max_years), level in level_map.items():
                            if min_years <= years < max_years:
                                # Higher confidence for specific year mentions
                                return (level, 0.7)
                                
        return (None, 0.0)
        
    def _is_close_to_skill(self, skill_name, indicator, sentence):
        """
        Check if an indicator is close to a skill name in a sentence
        
        Args:
            skill_name (str): The name of the skill
            indicator (str): The proficiency indicator
            sentence (str): The sentence to check
            
        Returns:
            bool: True if the indicator is close to the skill name
        """
        skill_pos = sentence.find(skill_name.lower())
        indicator_pos = sentence.find(indicator.lower())
        
        if skill_pos == -1 or indicator_pos == -1:
            return False
            
        # Consider them close if they are within 80 characters of each other
        return abs(skill_pos - indicator_pos) < 80
        
    def calculate_proficiencies_for_skills(self, skills, text):
        """
        Calculate proficiency levels for a list of skills
        
        Args:
            skills (list): List of Skill objects
            text (str): The text to analyze
            
        Returns:
            list: List of updated Skill objects with proficiency levels
        """
        updated_skills = []
        
        for skill in skills:
            proficiency, confidence = self.calculate_proficiency(skill.name, text)
            
            if proficiency:
                skill.proficiency = proficiency
                
                # Adjust confidence if it's higher than the current one
                if confidence > skill.confidence_score:
                    skill.adjust_confidence(confidence)
            else:
                # If no specific proficiency found, set a default based on confidence score
                if skill.confidence_score > 0.7:
                    skill.proficiency = "Intermediate"
                elif skill.confidence_score > 0.5:
                    skill.proficiency = "Beginner"
                elif skill.is_backed:
                    # If the skill is backed by a certification, at least Intermediate
                    skill.proficiency = "Intermediate"
                else:
                    skill.proficiency = "Beginner"
                    
            updated_skills.append(skill)
            
        return updated_skills 