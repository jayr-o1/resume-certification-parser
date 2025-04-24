#!/usr/bin/env python3
"""
Extract, Convert, and Process Files

This script:
1. Extracts text from PDF and image files
2. Converts them to text files
3. Processes the text files to identify skills and calculate proficiency
"""

import os
import sys
import json
import logging
import re
from pathlib import Path

from extractors import PDFExtractor, ImageExtractor
from processors import SkillExtractor, CertificationExtractor, ProficiencyCalculator
from models import Skill, SkillRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('extract_processor')

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file"""
    logger.info(f"Extracting text from PDF: {file_path}")
    extractor = PDFExtractor()
    text_data = extractor.extract(file_path)
    return text_data

def extract_text_from_image(file_path):
    """Extract text from an image file"""
    logger.info(f"Extracting text from image: {file_path}")
    extractor = ImageExtractor()
    text_data = extractor.extract(file_path)
    return text_data

def save_as_text_file(text, output_path):
    """Save text to a file"""
    logger.info(f"Saving text to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(text)
    return output_path

def process_text_file(text_file_path):
    """Process a text file to extract skills and certifications"""
    logger.info(f"Processing text file: {text_file_path}")
    
    # Read the text file
    with open(text_file_path, 'r', encoding='utf-8') as file:
        text_content = file.read()
    
    # Create extractors
    skill_extractor = SkillExtractor()
    cert_extractor = CertificationExtractor()
    proficiency_calculator = ProficiencyCalculator()
    
    # Create skill repository
    skill_repo = SkillRepository()
    
    # Create a simple structured document from the text
    structured_doc = {
        "document_type": "unknown",
        "raw_text": text_content,
        "sections": {
            "content": [text_content]
        }
    }
    
    # Determine document type based on filename
    file_name = Path(text_file_path).stem.lower()
    if "resume" in file_name:
        structured_doc["document_type"] = "resume"
        structured_doc["sections"]["experience"] = [text_content]
        structured_doc["sections"]["skills"] = [text_content]
    elif "certificate" in file_name or "certification" in file_name:
        structured_doc["document_type"] = "certification"
        structured_doc["sections"]["certifications"] = [text_content]
    
    # Process the structured document
    extracted_skills, sections_with_skills = skill_extractor.extract_skills(structured_doc)
    
    # Extract certifications - use the structured document based extraction
    certifications = cert_extractor.extract_certifications(structured_doc)
    
    # Create a manual list of certifications based on the filename
    if "certificate" in file_name or "certification" in file_name:
        # Extract the type of certification from the filename
        cert_type = None
        if "sql" in file_name.lower():
            cert_type = "SQL"
        elif "python" in file_name.lower():
            cert_type = "Python"
            
        if cert_type:
            # Add a manual certification entry if we can identify the type
            certifications.append({
                "name": f"{cert_type} Certificate",
                "issuer": "Training Provider",
                "date": "Unknown",
                "confidence": 0.95
            })
    
    # Manually link skills to certifications without using the problematic method
    linked_skills = []
    for skill in extracted_skills:
        skill_linked = False
        skill_name = skill["name"].lower()
        
        for cert in certifications:
            cert_name = cert["name"].lower()
            # Simple check if skill name appears in certification name
            if skill_name in cert_name or any(kw in cert_name for kw in skill_name.split()):
                skill["is_backed"] = True
                skill["backing_certificate"] = cert["name"]
                skill_linked = True
                break
        
        if not skill_linked:
            skill["is_backed"] = False
            skill["backing_certificate"] = ""
            
        linked_skills.append(skill)
    
    # Add skills from certificate names that might not be in the extracted skills
    for cert in certifications:
        cert_name = cert["name"].lower()
        # Look for common skills in certification names
        for skill_name in ["python", "sql", "javascript", "java", "c++", "c#", "cloud", "aws", "azure", "docker"]:
            if skill_name in cert_name and not any(s["name"].lower() == skill_name for s in linked_skills):
                # Add this skill
                skill_data = {
                    "name": skill_name.capitalize(),
                    "confidence_score": 0.9,
                    "source": "certification_name",
                    "is_backed": True,
                    "backing_certificate": cert["name"],
                    "context": f"Found in certification: {cert['name']}"
                }
                linked_skills.append(skill_data)
    
    # Storage for proficiency assessment explanations
    proficiency_explanations = []
    
    # Calculate proficiency levels with enhanced context
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
        
        # Extract context for proficiency assessment
        context = ""
        if "context" in skill_data:
            context = skill_data["context"]
        else:
            # Find all mentions of this skill in the text
            skill_pattern = re.compile(r'(?i)(?:^|\W)' + re.escape(skill_data["name"].lower()) + r'(?:$|\W)')
            matches = skill_pattern.finditer(text_content.lower())
            
            # Collect context around each mention (50 chars before and after)
            for match in matches:
                start = max(0, match.start() - 100)
                end = min(len(text_content), match.end() + 100)
                context += text_content[start:end] + " "
        
        # Calculate proficiency with research-based approach
        proficiency_level, confidence = proficiency_calculator.calculate_proficiency(skill_data["name"], context)
        
        # Get literature-backed explanation for this assessment
        explanation = proficiency_calculator.explain_proficiency_assessment(
            skill_data["name"], context, proficiency_level, confidence
        )
        proficiency_explanations.append(explanation)
        
        # Set the proficiency
        if proficiency_level:
            skill.proficiency = proficiency_level
        else:
            # Set default proficiency levels
            if skill.is_backed:
                skill.proficiency = "Intermediate"
            else:
                skill.proficiency = "Beginner"
        
        skill_repo.add_skill(skill)
    
    return skill_repo, certifications, proficiency_explanations

def extract_and_convert(input_path, output_dir="extracted_texts"):
    """Extract text from a file and save it as a text file"""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    input_path = Path(input_path)
    
    if not input_path.exists():
        logger.error(f"Input file does not exist: {input_path}")
        return None
    
    # Determine file type and extract text
    file_suffix = input_path.suffix.lower()
    text = None
    
    try:
        if file_suffix == ".pdf":
            text = extract_text_from_pdf(str(input_path))
        elif file_suffix in [".png", ".jpg", ".jpeg"]:
            text = extract_text_from_image(str(input_path))
        else:
            logger.warning(f"Unsupported file type: {input_path}")
            return None
        
        if not text:
            logger.error(f"Failed to extract text from: {input_path}")
            return None
        
        # Save as text file
        output_file = Path(output_dir) / f"{input_path.stem}.txt"
        save_as_text_file(text, str(output_file))
        
        return str(output_file)
    
    except Exception as e:
        logger.error(f"Error extracting text from {input_path}: {str(e)}")
        return None

def main():
    """Main entry point"""
    # Determine input files
    if len(sys.argv) > 1:
        input_paths = sys.argv[1:]
    else:
        # Use examples directory if no input is provided
        examples_dir = Path("examples")
        if not examples_dir.exists() or not examples_dir.is_dir():
            logger.error(f"Examples directory not found: {examples_dir}")
            return 1
        
        input_paths = [str(path) for path in examples_dir.glob("*") if path.is_file()]
    
    logger.info(f"Found {len(input_paths)} files to process")
    
    # Extract and convert to text files
    text_files = []
    for input_path in input_paths:
        text_file = extract_and_convert(input_path)
        if text_file:
            text_files.append(text_file)
    
    logger.info(f"Successfully extracted {len(text_files)} text files")
    
    # Process text files
    all_results = {
        "skills": [],
        "certifications": [],
        "proficiency_explanations": []  # Add storage for explanations
    }
    
    for text_file in text_files:
        try:
            # Process text file
            skill_repo, certifications, proficiency_explanations = process_text_file(text_file)
            
            # Add to results
            for skill in skill_repo.get_all_skills():
                all_results["skills"].append({
                    "name": skill.name,
                    "proficiency": skill.proficiency,
                    "is_backed": skill.is_backed,
                    "backing_certificate": skill.backing_certificate,
                    "confidence_score": skill.confidence_score,
                    "source": skill.source,
                    "file": text_file
                })
            
            for cert in certifications:
                all_results["certifications"].append({
                    "name": cert["name"],
                    "issuer": cert.get("issuer", "Unknown"),
                    "date": cert.get("date", "Unknown"),
                    "confidence": cert["confidence"],
                    "file": text_file
                })
                
            # Add proficiency explanations
            all_results["proficiency_explanations"].extend(proficiency_explanations)
            
            # Display results for this file
            print(f"\nSkills extracted from {Path(text_file).name}:")
            all_skills = skill_repo.get_all_skills()
            top_skills = sorted(all_skills, key=lambda x: x.confidence_score, reverse=True)[:10]
            
            for skill in top_skills:
                print(f"- {skill.name}: {skill.proficiency or 'Unknown'} - {skill.confidence_score:.2f} confidence")
            
            print(f"Total skills: {len(all_skills)}")
            print(f"Backed skills: {len(skill_repo.get_backed_skills())}")
            print(f"Unbacked skills: {len(skill_repo.get_unbacked_skills())}")
            
        except Exception as e:
            logger.error(f"Error processing {text_file}: {str(e)}")
    
    # Save consolidated results
    output_path = "consolidated_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=4)
    
    logger.info(f"Consolidated results saved to {output_path}")
    
    # Generate a research-backed proficiency assessment report
    generate_proficiency_report(all_results)
    
    # Display summary
    print("\n===== PROCESSING SUMMARY =====")
    print(f"Total files processed: {len(text_files)}")
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
        proficiency = data["proficiency"] if isinstance(data["proficiency"], str) else "Unknown"
        print(f"- {skill_name}: {proficiency} proficiency, {backed_status} backed, {avg_confidence:.2f} confidence")
    
    return 0

def generate_proficiency_report(results):
    """
    Generate a research-backed proficiency assessment report
    
    Args:
        results (dict): Consolidated results from processing
    """
    # Get the literature sources from the proficiency calculator
    proficiency_calculator = ProficiencyCalculator()
    literature_sources = proficiency_calculator.get_literature_sources()
    
    report = {
        "title": "Skill Proficiency Assessment Report with Research Backing",
        "skills_summary": [],
        "research_methodology": {
            "description": "This assessment uses a multi-dimensional approach to evaluate skill proficiency based on established academic research in expertise development and skill acquisition. The framework combines multiple evidence types weighted according to their predictive validity as established in the literature.",
            "key_frameworks": [
                "Dreyfus & Dreyfus (1986) Five-Stage Model of Skill Acquisition",
                "Bloom's Taxonomy of Educational Objectives (revised 2001)",
                "Ericsson's Deliberate Practice Framework (1993)",
                "Schmidt & Hunter's Validity of Assessment Methods (1998)"
            ],
            "literature_sources": literature_sources
        }
    }
    
    # Organize skills by proficiency level
    skills_by_level = {
        "Beginner": [],
        "Intermediate": [],
        "Advanced": [],
        "Expert": []
    }
    
    for skill in results["skills"]:
        proficiency = skill["proficiency"]
        if isinstance(proficiency, str) and proficiency in skills_by_level:
            skills_by_level[proficiency].append(skill)
    
    # Add skill summaries by proficiency level
    for level, skills in skills_by_level.items():
        if skills:
            skill_entries = []
            for skill in skills:
                # Find corresponding explanation if available
                explanation = next((exp for exp in results.get("proficiency_explanations", []) 
                                  if exp.get("skill") == skill["name"] and exp.get("proficiency_level") == level), None)
                
                entry = {
                    "name": skill["name"],
                    "confidence_score": skill["confidence_score"],
                    "backed_by_certification": skill["is_backed"],
                    "source": skill["source"],
                    "file": skill["file"]
                }
                
                if explanation:
                    entry["assessment_indicators"] = explanation.get("key_indicators", [])
                    entry["research_foundation"] = explanation.get("literature_foundation", [])
                
                skill_entries.append(entry)
            
            report["skills_summary"].append({
                "proficiency_level": level,
                "description": get_proficiency_level_description(level),
                "skills": skill_entries
            })
    
    # Save the report
    report_path = "proficiency_assessment_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
    
    logger.info(f"Proficiency assessment report saved to {report_path}")

def get_proficiency_level_description(level):
    """
    Get a research-backed description of a proficiency level
    
    Args:
        level (str): The proficiency level
        
    Returns:
        str: Description of the proficiency level
    """
    descriptions = {
        "Beginner": "Exhibits rule-based behavior with limited contextual perception. Individuals at this level typically work with structured guidelines and require supervision. Based on Dreyfus & Dreyfus (1986) 'novice' stage, characterized by rigid adherence to taught rules and little situational perception.",
        
        "Intermediate": "Shows situational perception and can work independently on routine tasks. Individuals at this level understand the context of their work but may still approach problem-solving in a limited, procedural way. Based on the 'advanced beginner' stage in the Dreyfus model, where guidelines for actions are based on attributes and aspects that require prior experience.",
        
        "Advanced": "Demonstrates conceptual understanding and sees actions as part of larger goals. Individuals at this level can handle complex situations through deliberate planning and have the ability to adapt approaches based on the specific context. Based on the 'competent' stage in expertise development research, characterized by conscious deliberate planning.",
        
        "Expert": "Shows intuitive grasp of situations and works from deep understanding rather than rules. Individuals at this level have a highly developed situational awareness and can take a holistic view of complex problems. This reflects the highest stages of the Dreyfus model ('proficient' and 'expert'), where behavior is fluid, intuitive, and adaptive."
    }
    
    return descriptions.get(level, "No description available")

if __name__ == "__main__":
    sys.exit(main()) 