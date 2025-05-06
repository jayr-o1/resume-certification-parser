#!/usr/bin/env python3
"""
Test script for the SkillValidator module
"""

import os
import logging
import json
from processors.skill_validator import SkillValidator
from utils.skill_database import SkillDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_skill_validator')

def test_validator():
    """Test the skill validator functionality"""
    # Get the path to the skills database
    skills_db_path = os.path.join(os.path.dirname(__file__), 'data', 'skills_database.json')
    
    # Initialize the validator
    validator = SkillValidator(skills_db_path)
    
    # Example skills to test - mix of valid and invalid
    test_skills = [
        {"name": "Python", "confidence": 0.7, "is_technical": True, "is_backed": False},
        {"name": "Java", "confidence": 0.6, "is_technical": True, "is_backed": False},
        {"name": "Collaborated With Peers For Departmental Planning", "confidence": 0.5, "is_technical": False, "is_backed": False},
        {"name": "Curriculum Enhancements", "confidence": 0.5, "is_technical": False, "is_backed": False},
        {"name": "Key Skills", "confidence": 0.5, "is_technical": False, "is_backed": False},
        {"name": "Technologies Into Course Delivery", "confidence": 0.6, "is_technical": False, "is_backed": False},
        {"name": "SQL", "confidence": 0.6, "is_technical": True, "is_backed": False},
        {"name": "Project Management", "confidence": 0.65, "is_technical": False, "is_backed": False},
        {"name": "Curriculum Development", "confidence": 0.7, "is_technical": False, "is_backed": False},
        {"name": "programming with python", "confidence": 0.5, "is_technical": True, "is_backed": False}
    ]
    
    # Validate the skills
    validated_skills = validator.validate_skills(test_skills)
    
    # Display results
    logger.info(f"Original skills: {len(test_skills)}")
    logger.info(f"Validated skills: {len(validated_skills)}")
    
    print("\nSkills that passed validation:")
    for skill in validated_skills:
        print(f"- {skill['name']} (Confidence: {skill['confidence']}, Technical: {skill['is_technical']})")
    
    print("\nSkills that were filtered out:")
    validated_names = [skill["name"] for skill in validated_skills]
    for skill in test_skills:
        if skill["name"] not in validated_names and skill["name"].lower() != validator.clean_skill_name(skill["name"]).lower():
            print(f"- {skill['name']}")
    
    # Test the skill database directly
    skill_db = SkillDatabase(skills_db_path)
    
    print("\nSkill database info:")
    print(f"Total skills: {len(skill_db.all_skills)}")
    print(f"Technical skills: {len(skill_db.technical_skills)}")
    print(f"Soft skills: {len(skill_db.soft_skills)}")
    print(f"Domain-specific skills: {sum(len(skills) for skills in skill_db.domain_skills.values())}")
    
    # Test known skills
    test_terms = ["python", "java", "project management", "curriculum development", 
                 "collaborated with peers", "javascript", "react"]
    
    print("\nTesting skill lookup:")
    for term in test_terms:
        is_known = skill_db.is_known_skill(term)
        canonical = skill_db.get_canonical_name(term) if is_known else "Unknown"
        category = skill_db.get_skill_category(term) if is_known else "Unknown"
        print(f"- {term}: Known={is_known}, Canonical={canonical}, Category={category}")

if __name__ == "__main__":
    test_validator() 