#!/usr/bin/env python3
"""
Process Example Files

This script processes all files in the examples directory and generates
consolidated results with skills and proficiency levels.
"""

import os
import sys
import json
import logging
from pathlib import Path

from extractors import PDFExtractor, ImageExtractor, StructuredFormatConverter
from processors import SkillExtractor, CertificationExtractor, ProficiencyCalculator
from models import Skill, SkillRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('example_processor')

def process_pdf(file_path):
    """Process a PDF file and extract text with layout information"""
    logger.info(f"Processing PDF: {file_path}")
    extractor = PDFExtractor()
    layout_data = extractor.extract_with_layout(file_path)
    return layout_data

def process_image(file_path):
    """Process an image file and extract text"""
    logger.info(f"Processing image: {file_path}")
    extractor = ImageExtractor()  # No tesseract path specified, using default
    extracted_text = extractor.extract(file_path)
    return {"text": extracted_text, "layout": None}

def extract_skills_and_certifications(text_data):
    """Extract skills and certifications from text data"""
    # Create extractors
    skill_extractor = SkillExtractor()
    cert_extractor = CertificationExtractor()
    proficiency_calculator = ProficiencyCalculator()
    
    # Create skill repository
    skill_repo = SkillRepository()
    
    # Use structured format converter for better results
    converter = StructuredFormatConverter()
    structured_doc = converter.convert(text_data)
    
    # Extract skills
    extracted_skills, sections_with_skills = skill_extractor.extract_skills(structured_doc)
    
    # Extract certifications
    certifications = cert_extractor.extract_certifications(structured_doc)
    
    # Link skills to certifications
    linked_skills = cert_extractor.link_skills_to_certifications(extracted_skills, certifications)
    
    # Calculate proficiency levels
    for skill_data in linked_skills:
        skill = Skill(
            name=skill_data["name"],
            confidence_score=skill_data["confidence_score"],
            source=skill_data.get("source", "unknown")
        )
        
        # Set backed status if available
        if "is_backed" in skill_data and skill_data["is_backed"]:
            skill.is_backed = True
            skill.backing_certificate = skill_data.get("backing_certificate", "")
        
        # Calculate proficiency
        if "context" in skill_data:
            proficiency = proficiency_calculator.calculate_proficiency(skill_data["name"], skill_data["context"])
            skill.proficiency = proficiency
        
        skill_repo.add_skill(skill)
    
    return skill_repo, certifications

def main():
    """Main entry point"""
    examples_dir = Path("examples")
    
    if not examples_dir.exists() or not examples_dir.is_dir():
        logger.error(f"Examples directory not found: {examples_dir}")
        return 1
    
    # Process all files in the examples directory
    all_results = {
        "skills": [],
        "certifications": []
    }
    
    for file_path in examples_dir.glob("*"):
        if file_path.is_file():
            logger.info(f"Processing file: {file_path}")
            
            try:
                # Process based on file type
                file_suffix = file_path.suffix.lower()
                if file_suffix == ".pdf":
                    text_data = process_pdf(file_path)
                elif file_suffix in [".png", ".jpg", ".jpeg"]:
                    text_data = process_image(file_path)
                else:
                    logger.warning(f"Unsupported file type: {file_path}")
                    continue
                
                # Extract skills and certifications
                skill_repo, certifications = extract_skills_and_certifications(text_data)
                
                # Add to results
                for skill in skill_repo.get_all_skills():
                    all_results["skills"].append({
                        "name": skill.name,
                        "proficiency": skill.proficiency,
                        "is_backed": skill.is_backed,
                        "backing_certificate": skill.backing_certificate,
                        "confidence_score": skill.confidence_score,
                        "source": skill.source,
                        "file": str(file_path)
                    })
                
                for cert in certifications:
                    all_results["certifications"].append({
                        "name": cert["name"],
                        "issuer": cert.get("issuer", "Unknown"),
                        "date": cert.get("date", "Unknown"),
                        "confidence": cert["confidence"],
                        "file": str(file_path)
                    })
                
                # Display results for this file
                print(f"\nSkills extracted from {file_path.name}:")
                all_skills = skill_repo.get_all_skills()
                top_skills = sorted(all_skills, key=lambda x: x.confidence_score, reverse=True)[:10]
                
                for skill in top_skills:
                    print(f"- {skill.name}: {skill.proficiency or 'Unknown'} - {skill.confidence_score:.2f} confidence")
                
                print(f"Total skills: {len(all_skills)}")
                print(f"Backed skills: {len(skill_repo.get_backed_skills())}")
                print(f"Unbacked skills: {len(skill_repo.get_unbacked_skills())}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
    
    # Save consolidated results
    output_path = "consolidated_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=4)
    
    logger.info(f"Consolidated results saved to {output_path}")
    
    # Display summary
    print("\n===== PROCESSING SUMMARY =====")
    print(f"Total files processed: {len(set(skill['file'] for skill in all_results['skills']))}")
    print(f"Total unique skills extracted: {len(set(skill['name'] for skill in all_results['skills']))}")
    print(f"Total certifications detected: {len(all_results['certifications'])}")
    
    # Show top skills overall
    print("\nTop skills overall:")
    skill_counts = {}
    for skill in all_results["skills"]:
        if skill["name"] not in skill_counts:
            skill_counts[skill["name"]] = {
                "count": 0,
                "total_confidence": 0,
                "proficiency": skill["proficiency"],
                "is_backed": skill["is_backed"]
            }
        skill_counts[skill["name"]]["count"] += 1
        skill_counts[skill["name"]]["total_confidence"] += skill["confidence_score"]
    
    top_skills = sorted(
        [(name, data) for name, data in skill_counts.items()],
        key=lambda x: (x[1]["count"], x[1]["total_confidence"]),
        reverse=True
    )[:15]
    
    for skill_name, data in top_skills:
        avg_confidence = data["total_confidence"] / data["count"]
        backed_status = "✓" if data["is_backed"] else "✗"
        print(f"- {skill_name}: {data['proficiency'] or 'Unknown'} proficiency, {backed_status} backed, {avg_confidence:.2f} confidence")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 