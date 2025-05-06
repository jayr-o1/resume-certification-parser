#!/usr/bin/env python3
"""
Test script specifically for database and technical skills extraction
"""

import os
import logging
from processors.sentence_skill_extractor import SentenceSkillExtractor
from processors.skill_validator import SkillValidator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_db_skills')

def test_db_skills_extraction():
    """Test extraction of database and technical skills"""
    # Get the path to the skills database
    skills_db_path = os.path.join(os.path.dirname(__file__), 'data', 'skills_database.json')
    
    # Initialize the extractor and validator
    extractor = SentenceSkillExtractor(skills_db_path)
    validator = SkillValidator(skills_db_path)
    
    # Example text with database and technical skills
    test_text = """
    Extensive experience in Database Management Systems with a focus on SQL Server and Oracle.
    Expert in designing and implementing Relational Databases for enterprise applications.
    Proficient in Data Modeling techniques including ER Diagrams and normalization.
    Strong understanding of Database Security principles and practices.
    Skilled in Version Control systems like Git and SVN.
    Experience with Systems Database Management in cloud environments.
    Implemented and maintained database optimization strategies and Performance Tuning.
    Knowledge of ETL processes and Data Warehousing concepts.
    """
    
    # Extract skills from the text
    extracted_skills = extractor.extract_skills_from_text(test_text)
    
    # Validate the extracted skills
    validated_skills = validator.validate_skills(extracted_skills)
    
    # Print results
    print("\nExtracted Database and Technical Skills:")
    print("---------------------------------------")
    for skill in sorted(extracted_skills, key=lambda s: s["name"]):
        confidence = skill.get("confidence_score", 0.0)
        print(f"- {skill['name']} (Confidence: {confidence:.2f})")
    
    print("\nAfter Validation:")
    print("----------------")
    for skill in sorted(validated_skills, key=lambda s: s["name"]):
        confidence = skill.get("confidence_score", 0.0)
        print(f"- {skill['name']} (Confidence: {confidence:.2f})")
    
    # Test specific problematic skills directly
    problem_skills = [
        {"name": "Database Management Systems", "confidence_score": 0.8, "is_technical": True, "is_backed": False},
        {"name": "Systems Database Management", "confidence_score": 0.8, "is_technical": True, "is_backed": False},
        {"name": "Relational Databases", "confidence_score": 0.8, "is_technical": True, "is_backed": False},
        {"name": "Data Modeling", "confidence_score": 0.8, "is_technical": True, "is_backed": False},
        {"name": "Version Control", "confidence_score": 0.8, "is_technical": True, "is_backed": False}
    ]
    
    # Validate these skills directly
    directly_validated = validator.validate_skills(problem_skills)
    
    print("\nDirect Validation of Problematic Skills:")
    print("--------------------------------------")
    valid_names = [skill["name"] for skill in directly_validated]
    
    for skill in problem_skills:
        if skill["name"] in valid_names:
            status = "VALID"
        else:
            status = "FILTERED OUT"
        print(f"- {skill['name']}: {status}")

if __name__ == "__main__":
    test_db_skills_extraction() 