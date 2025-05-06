#!/usr/bin/env python3
"""
Skills Extractor for Resumes and Certifications

This script processes resume and certification files (PDF and images),
extracts skills, and identifies which skills are backed by certifications.
It calculates proficiency levels for each skill with higher confidence
for skills that are backed by certifications.
"""

import os
import sys
import json
import argparse
import logging
import glob
import re
from extract_and_process import DocumentProcessor, SkillProcessor, ProficiencyCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('skills_extractor')

def extract_skills(input_path, output_path=None, tesseract_path=None):
    """
    Extract skills from resumes and certifications, with backed skills getting
    higher proficiency scores.
    
    Args:
        input_path (str): Path to input directory with resume and certification files
        output_path (str, optional): Path to output JSON file
        tesseract_path (str, optional): Path to Tesseract OCR executable
    """
    # Initialize processors
    document_processor = DocumentProcessor(tesseract_path)
    skill_processor = SkillProcessor()
    proficiency_calculator = ProficiencyCalculator(skill_processor.technical_skills)
    
    # Default output path if not provided
    if not output_path:
        output_path = "skills_with_proficiency.json"
    
    # Check if input path exists
    if not os.path.exists(input_path):
        logger.error(f"Input path does not exist: {input_path}")
        return False
    
    # If input is a directory, process all files
    if os.path.isdir(input_path):
        # Find all PDF and image files
        file_patterns = ['*.pdf', '*.png', '*.jpg', '*.jpeg']
        files = []
        for pattern in file_patterns:
            files.extend(glob.glob(os.path.join(input_path, pattern)))
        
        if not files:
            logger.error(f"No supported files found in directory: {input_path}")
            return False
        
        # Categorize files
        resume_files = [f for f in files if document_processor.is_resume(f)]
        cert_files = [f for f in files if document_processor.is_certification(f)]
        
        logger.info(f"Found {len(resume_files)} resume files and {len(cert_files)} certification files")
        
        # Process certification files first to get skills
        cert_skills = []
        cert_texts = {}
        
        for file_path in cert_files:
            logger.info(f"Processing certification: {os.path.basename(file_path)}")
            
            # Extract text
            extracted_text = document_processor.process_file(file_path)
            
            if not extracted_text:
                logger.warning(f"Failed to extract text from {file_path}")
                continue
            
            # Store certification text for context
            cert_texts[file_path] = extracted_text
            
            # Extract skills
            file_skills = skill_processor.extract_skills(extracted_text)
            logger.info(f"Extracted {len(file_skills)} skills from certification")
            cert_skills.extend(file_skills)
        
        # Now process resume files
        all_skills = []
        resume_file = None
        
        for file_path in resume_files:
            logger.info(f"Processing resume: {os.path.basename(file_path)}")
            resume_file = os.path.basename(file_path)
            
            # Extract text
            extracted_text = document_processor.process_file(file_path)
            
            if not extracted_text:
                logger.warning(f"Failed to extract text from {file_path}")
                continue
            
            # Extract skills
            resume_skills = skill_processor.extract_skills(extracted_text)
            logger.info(f"Extracted {len(resume_skills)} skills from resume")
            
            # Mark backed skills
            backed_skills = skill_processor.mark_backed_skills(resume_skills, cert_skills)
            
            # Count backed skills
            backed_count = sum(1 for skill in backed_skills if skill.get("is_backed", False))
            logger.info(f"Marked {backed_count} skills as backed by certifications")
            
            # Process skills with proficiency levels
            processed_skills = []
            
            for skill in backed_skills:
                # Verify that the skill is actually mentioned in the text
                skill_name = skill["name"]
                explicit_mention = re.search(r'\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE)
                
                if not explicit_mention:
                    logger.warning(f"Skipping skill {skill_name} - not explicitly mentioned in text")
                    continue
                    
                # Special validation for potentially ambiguous skills
                if skill_name in ["C++", "R"]:
                    # More strict verification for programming languages
                    programming_context = any([
                        re.search(r'programming.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                        re.search(r'languages.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                        re.search(r'skills.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                        re.search(r'technologies.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE),
                        re.search(r'proficient.*\b' + re.escape(skill_name) + r'\b', extracted_text, re.IGNORECASE)
                    ])
                    
                    if not programming_context:
                        logger.warning(f"Skipping ambiguous skill {skill_name} - not in proper context")
                        continue
                    
                # Get certification text for this skill if available
                cert_text = ""
                for cert_file, text in cert_texts.items():
                    if skill["name"].lower() in text.lower():
                        cert_text += text + " "
                
                # Calculate proficiency
                proficiency_level, confidence = proficiency_calculator.calculate_proficiency(
                    skill["name"], 
                    skill["context"],
                    certification_text=cert_text if cert_text else None,
                    is_backed=skill.get("is_backed", False)
                )
                
                # Add processed skill
                processed_skills.append({
                    "name": skill["name"],
                    "proficiency": proficiency_level,
                    "confidence": confidence,
                    "is_technical": skill.get("is_technical", True),
                    "is_backed": skill.get("is_backed", False)
                })
            
            # Sort skills by name
            processed_skills.sort(key=lambda x: x["name"])
            all_skills.extend(processed_skills)
        
        # Get unique list of certification names
        certification_names = list(set(os.path.basename(f) for f in cert_files))
        
        # Save results
        if resume_file:
            results = {
                "file": resume_file,
                "skills": all_skills,
                "certifications": certification_names
            }
            
            try:
                with open(output_path, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results saved to {output_path}")
                return True
            except Exception as e:
                logger.error(f"Error saving results: {str(e)}")
                return False
        else:
            logger.error("No resume file was processed")
            return False
    
    # If input is a single file
    elif os.path.isfile(input_path):
        logger.error("Please provide a directory containing both resume and certification files")
        return False
    
    return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Extract skills from resumes and certifications, identifying backed skills.'
    )
    
    parser.add_argument('--input', '-i', required=True,
                      help='Path to directory containing resume and certification files')
    parser.add_argument('--output', '-o',
                      help='Path to output JSON file')
    parser.add_argument('--tesseract-path', '-t',
                      help='Path to Tesseract OCR executable')
    
    args = parser.parse_args()
    
    # Process files
    extract_skills(args.input, args.output, args.tesseract_path)


if __name__ == "__main__":
    main() 