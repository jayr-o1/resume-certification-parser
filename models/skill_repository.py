import json
import os
from .skill import Skill

class SkillRepository:
    """
    Repository for managing skills
    """
    
    def __init__(self):
        """Initialize an empty skill repository"""
        self.skills = {}  # Dictionary to store skills by name
        
    def add_skill(self, skill):
        """
        Add a skill to the repository
        
        Args:
            skill (Skill): The skill to add
            
        Returns:
            bool: True if added, False if updated
        """
        is_new = skill.name not in self.skills
        
        if is_new:
            self.skills[skill.name] = skill
        else:
            # If skill already exists, update confidence score and other attributes
            existing_skill = self.skills[skill.name]
            
            # If the new skill has better confidence or is backed, update the existing one
            if (skill.is_backed and not existing_skill.is_backed) or \
               (skill.confidence_score > existing_skill.confidence_score):
                existing_skill.proficiency = skill.proficiency
                existing_skill.is_backed = skill.is_backed
                existing_skill.confidence_score = skill.confidence_score
                existing_skill.backing_certificate = skill.backing_certificate
                existing_skill.source = skill.source  # Update source information
                
        return is_new
        
    def get_skill(self, skill_name):
        """
        Get a skill by name
        
        Args:
            skill_name (str): The name of the skill
            
        Returns:
            Skill or None: The skill if found, None otherwise
        """
        return self.skills.get(skill_name)
        
    def get_all_skills(self):
        """
        Get all skills in the repository
        
        Returns:
            list: List of all skills
        """
        return list(self.skills.values())
        
    def get_backed_skills(self):
        """
        Get all backed skills
        
        Returns:
            list: List of backed skills
        """
        return [skill for skill in self.skills.values() if skill.is_backed]
        
    def get_unbacked_skills(self):
        """
        Get all unbacked skills
        
        Returns:
            list: List of unbacked skills
        """
        return [skill for skill in self.skills.values() if not skill.is_backed]
    
    def get_skills_by_source(self):
        """
        Get skills grouped by their source
        
        Returns:
            dict: Dictionary with sources as keys and lists of skills as values
        """
        skills_by_source = {}
        
        for skill in self.skills.values():
            source = skill.source or "Unknown"
            if source not in skills_by_source:
                skills_by_source[source] = []
            skills_by_source[source].append(skill)
            
        # Sort skills by confidence score within each source
        for source in skills_by_source:
            skills_by_source[source].sort(key=lambda s: s.confidence_score, reverse=True)
            
        return skills_by_source
    
    def get_skills_from_section(self, section_name):
        """
        Get skills from a specific section
        
        Args:
            section_name (str): The name of the section (e.g., "Skills section", "Experience section")
            
        Returns:
            list: List of skills from the specified section
        """
        return [skill for skill in self.skills.values() 
                if skill.source and section_name.lower() in skill.source.lower()]
        
    def save_to_file(self, file_path):
        """
        Save skills to a JSON file
        
        Args:
            file_path (str): Path to the output JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            skills_data = {
                'skills': [skill.to_dict() for skill in self.skills.values()]
            }
            
            with open(file_path, 'w') as f:
                json.dump(skills_data, f, indent=4)
                
            return True
            
        except Exception as e:
            print(f"Error saving skills to file: {str(e)}")
            return False
            
    def load_from_file(self, file_path):
        """
        Load skills from a JSON file
        
        Args:
            file_path (str): Path to the JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(file_path):
            return False
            
        try:
            with open(file_path, 'r') as f:
                skills_data = json.load(f)
                
            self.skills = {}
            
            for skill_dict in skills_data.get('skills', []):
                skill = Skill(
                    name=skill_dict['name'],
                    proficiency=skill_dict.get('proficiency'),
                    is_backed=skill_dict.get('is_backed', False),
                    confidence_score=skill_dict.get('confidence_score', 0.0),
                    backing_certificate=skill_dict.get('backing_certificate'),
                    source=skill_dict.get('source')
                )
                self.skills[skill.name] = skill
                
            return True
            
        except Exception as e:
            print(f"Error loading skills from file: {str(e)}")
            return False 