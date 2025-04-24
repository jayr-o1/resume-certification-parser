#!/usr/bin/env python3
"""
Example script to demonstrate how to use the resume and certification parser.
"""

import os
import json
from extract_and_process import DocumentProcessor, SkillProcessor, ProficiencyCalculator

def main():
    """
    Process example resume and certification files and display the results.
    """
    print("Resume and Certification Parser Example")
    print("--------------------------------------")
    
    # Initialize processors
    document_processor = DocumentProcessor()
    skill_processor = SkillProcessor()
    proficiency_calculator = ProficiencyCalculator()
    
    # Sample files - replace with your own file paths
    examples_dir = "examples"
    
    # Check if the examples directory exists
    if not os.path.exists(examples_dir):
        print(f"Examples directory '{examples_dir}' not found. Creating it...")
        os.makedirs(examples_dir)
        print(f"Please place PDF/PNG files in the '{examples_dir}' directory and run this script again.")
        return
    
    # Get all PDF and image files in the examples directory
    files = []
    for ext in ['.pdf', '.png', '.jpg', '.jpeg']:
        for file in os.listdir(examples_dir):
            if file.lower().endswith(ext):
                files.append(os.path.join(examples_dir, file))
    
    if not files:
        print(f"No PDF or image files found in '{examples_dir}' directory.")
        print("Please add some resume and certification files and try again.")
        return
    
    print(f"Found {len(files)} files to process.")
    
    # Process each file
    all_results = {}
    
    for file_path in files:
        print(f"\nProcessing: {os.path.basename(file_path)}")
        
        # Extract text from the document
        extracted_text = document_processor.process_file(file_path)
        
        if not extracted_text:
            print(f"Failed to extract text from {file_path}")
            continue
        
        print(f"Successfully extracted {len(extracted_text)} characters of text.")
        
        # Extract skills from the text
        extracted_skills = skill_processor.extract_skills(extracted_text)
        print(f"Extracted {len(extracted_skills)} skills.")
        
        # Calculate proficiency levels for each skill
        processed_skills = []
        
        for skill in extracted_skills:
            proficiency_level, confidence = proficiency_calculator.calculate_proficiency(
                skill["name"], 
                skill["context"],
                certification_text=extracted_text if "certification" in file_path.lower() else None
            )
            
            # Add proficiency information to the skill
            skill_with_proficiency = {
                "name": skill["name"],
                "proficiency": proficiency_level,
                "confidence": confidence,
                "is_technical": skill.get("is_technical", True)
            }
            
            processed_skills.append(skill_with_proficiency)
            
            # Display the skill and its proficiency
            print(f"  - {skill['name']}: {proficiency_level} (Confidence: {confidence:.2f})")
        
        # Sort skills by name
        processed_skills.sort(key=lambda x: x["name"])
        
        # Add to results
        all_results[os.path.basename(file_path)] = {
            "file": os.path.basename(file_path),
            "skills": processed_skills,
            "text_length": len(extracted_text)
        }
    
    # Save the results to a JSON file
    output_file = "parsed_skills.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main() 