#!/usr/bin/env python3
"""
Test Industry-Specific Skill Extraction

This script tests the industry detection and industry-specific skill extraction
functionality to ensure it's working correctly.
"""

import os
import sys
import logging
import json
from extract_and_process import DocumentProcessor, SkillProcessor, ProficiencyCalculator, detect_industry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_industry_detection(resume_path):
    """Test industry detection on a resume"""
    # Initialize document processor
    document_processor = DocumentProcessor()
    
    # Extract text from resume
    resume_text = document_processor.process_file(resume_path)
    if not resume_text:
        logger.error(f"Failed to extract text from {resume_path}")
        return False
    
    # Detect industry
    detected_industry, industry_scores = detect_industry(resume_text)
    
    logger.info(f"Detected industry: {detected_industry}")
    logger.info("Industry scores:")
    for industry, score in sorted(industry_scores.items(), key=lambda x: x[1], reverse=True)[:5]:
        if score > 0.01:
            logger.info(f"  {industry}: {score:.2f}")
    
    return detected_industry, industry_scores

def test_industry_specific_extraction(resume_path):
    """Test industry-specific skill extraction"""
    # Initialize processors
    document_processor = DocumentProcessor()
    skill_processor = SkillProcessor()
    
    # Extract text from resume
    resume_text = document_processor.process_file(resume_path)
    if not resume_text:
        logger.error(f"Failed to extract text from {resume_path}")
        return False
    
    # Detect industry
    detected_industry, _ = detect_industry(resume_text)
    logger.info(f"Detected industry: {detected_industry}")
    
    # Extract skills using generic approach (no industry context)
    generic_skills = skill_processor.extract_skills(resume_text)
    
    # Update processor for industry-specific extraction
    if hasattr(skill_processor, 'update_for_industry'):
        skill_processor.update_for_industry(detected_industry)
    
    # Extract skills using industry context
    industry_specific_skills = skill_processor.extract_skills(resume_text)
    
    # Compare results
    logger.info(f"Generic extraction found {len(generic_skills)} skills")
    logger.info(f"Industry-specific extraction found {len(industry_specific_skills)} skills")
    
    # Find skills unique to industry-specific extraction
    generic_skill_names = {skill["name"] for skill in generic_skills}
    industry_specific_skill_names = {skill["name"] for skill in industry_specific_skills}
    
    unique_to_industry = industry_specific_skill_names - generic_skill_names
    
    if unique_to_industry:
        logger.info("Skills unique to industry-specific extraction:")
        for skill_name in sorted(unique_to_industry):
            logger.info(f"  {skill_name}")
    
    return {
        "generic_skills": generic_skills,
        "industry_specific_skills": industry_specific_skills,
        "unique_to_industry": list(unique_to_industry)
    }

def test_proficiency_calculation(resume_path):
    """Test industry-specific proficiency calculation"""
    # Initialize processors
    document_processor = DocumentProcessor()
    skill_processor = SkillProcessor()
    
    # Extract text from resume
    resume_text = document_processor.process_file(resume_path)
    if not resume_text:
        logger.error(f"Failed to extract text from {resume_path}")
        return False
    
    # Detect industry
    detected_industry, _ = detect_industry(resume_text)
    
    # Initialize proficiency calculators - one generic, one industry-specific
    generic_calculator = ProficiencyCalculator(skill_processor.technical_skills)
    industry_calculator = ProficiencyCalculator(skill_processor.technical_skills, industry=detected_industry)
    
    # Extract skills
    skills = skill_processor.extract_skills(resume_text)
    
    # Compare proficiency calculations
    results = []
    
    for skill in skills[:10]:  # Test on first 10 skills
        # Get context for the skill
        context = skill.get("context", "")
        
        # Calculate proficiency using generic calculator
        generic_proficiency, generic_confidence = generic_calculator.calculate_proficiency(
            skill["name"], context)
        
        # Calculate proficiency using industry-specific calculator
        industry_proficiency, industry_confidence = industry_calculator.calculate_proficiency(
            skill["name"], context)
        
        results.append({
            "skill": skill["name"],
            "generic": {
                "proficiency": generic_proficiency,
                "confidence": generic_confidence
            },
            "industry_specific": {
                "proficiency": industry_proficiency,
                "confidence": industry_confidence
            },
            "difference": industry_confidence - generic_confidence
        })
        
        logger.info(f"Skill: {skill['name']}")
        logger.info(f"  Generic: {generic_proficiency} (Confidence: {generic_confidence:.2f})")
        logger.info(f"  Industry: {industry_proficiency} (Confidence: {industry_confidence:.2f})")
        logger.info(f"  Confidence Difference: {industry_confidence - generic_confidence:.2f}")
    
    return results

def find_resume_files():
    """Find resume files in the examples directory"""
    resume_files = []
    examples_dir = "examples"
    
    if os.path.exists(examples_dir):
        for filename in os.listdir(examples_dir):
            if filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                file_path = os.path.join(examples_dir, filename)
                resume_files.append(file_path)
    
    return resume_files

def main():
    """Main function"""
    # Find resume files
    resume_files = find_resume_files()
    
    if not resume_files:
        logger.error("No resume files found in the examples directory")
        return
    
    # Create results directory
    results_dir = "test_results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Test on each resume
    for resume_path in resume_files:
        logger.info(f"\n\nTesting with resume: {resume_path}")
        
        # Test industry detection
        industry, scores = test_industry_detection(resume_path)
        
        # Test industry-specific extraction
        extraction_results = test_industry_specific_extraction(resume_path)
        
        # Test proficiency calculation
        proficiency_results = test_proficiency_calculation(resume_path)
        
        # Save results
        resume_name = os.path.basename(resume_path).rsplit('.', 1)[0]
        results_file = os.path.join(results_dir, f"{resume_name}_results.json")
        
        results = {
            "resume": resume_path,
            "industry": industry,
            "industry_scores": {k: round(v, 2) for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5] if v > 0.01},
            "extraction_results": extraction_results,
            "proficiency_results": proficiency_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")

if __name__ == "__main__":
    main() 