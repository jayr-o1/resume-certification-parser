#!/usr/bin/env python3
"""
Test script for the SentenceSkillExtractor module
"""

import os
import logging
from processors.sentence_skill_extractor import SentenceSkillExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_sentence_extractor')

def test_sentence_extraction():
    """Test the sentence-based skill extractor functionality"""
    # Get the path to the skills database
    skills_db_path = os.path.join(os.path.dirname(__file__), 'data', 'skills_database.json')
    
    # Initialize the extractor
    extractor = SentenceSkillExtractor(skills_db_path)
    
    # Example text with skills embedded in sentences
    test_text = """
    Extensive experience in conducting field work for insurance sales and lending collection.
    Expert in clear, persuasive communication and effective client engagement.
    Proven ability to build rapport and maintain positive relationships with diverse populations.
    Skilled in meticulous data collection and accurate record-keeping.
    Strong analytical skills to resolve issues and adapt to changing situations.
    Efficient in managing schedules and meeting deadlines in fast-paced environments.
    Proficient in Microsoft Office Suite, including Excel, Word, and PowerPoint.
    Experience with various CRM platforms and database management systems.
    Trained in conflict resolution and effective negotiation techniques.
    """
    
    # Extract skills from the text
    extracted_skills = extractor.extract_skills_from_text(test_text)
    
    # Print results
    print("\nExtracted Skills from Text:")
    print("--------------------------")
    for skill in sorted(extracted_skills, key=lambda s: s["name"]):
        confidence = skill.get("confidence_score", 0.0)
        technical = "Technical" if skill.get("is_technical", False) else "Soft"
        
        print(f"- {skill['name']} ({technical}, Confidence: {confidence:.2f})")
        print(f"  Context: '{skill['context']}'")
        print()
    
    # Try with different examples
    additional_examples = [
        "Leveraged Python and SQL to analyze large datasets and create automated reporting dashboards.",
        "Implemented agile methodologies to improve project delivery timelines by 30%.",
        "Collaborated with cross-functional teams to deliver complex software solutions.",
        "Strong understanding of financial markets and investment strategies.",
        "Experienced in both front-end and back-end web development using modern frameworks."
    ]
    
    print("\nProcessing Additional Examples:")
    print("------------------------------")
    for i, example in enumerate(additional_examples):
        print(f"\nExample {i+1}: {example}")
        skills = extractor.extract_skills_from_text(example)
        for skill in skills:
            confidence = skill.get("confidence_score", 0.0)
            technical = "Technical" if skill.get("is_technical", False) else "Soft"
            print(f"- {skill['name']} ({technical}, Confidence: {confidence:.2f})")

if __name__ == "__main__":
    test_sentence_extraction() 