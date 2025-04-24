#!/usr/bin/env python3
"""
Skill Extractor for Images and PDFs

This application extracts skills from resume and certification documents,
categorizes them as backed or unbacked, and assigns proficiency levels.

The application uses structured document conversion to preserve document layout
and improve extraction accuracy with well-formatted documents. This structured
approach enables better identification of document sections and more accurate
skill and certification extraction.
"""

import os
import argparse
import json
import logging
import sys
import glob
import datetime
import re

from extractors import PDFExtractor, ImageExtractor, StructuredFormatConverter
from processors import SkillExtractor, CertificationExtractor, ProficiencyCalculator
from models import Skill, SkillRepository
from utils import get_file_type, is_supported_file, get_output_path, validate_file_naming, sort_files_by_type, get_supported_files_in_directory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('skill_extractor')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract skills from resumes and certification documents.'
    )
    
    parser.add_argument('--input', '-i',
                        help='Path to the input file (PDF or image) or directory')
    parser.add_argument('--output', '-o',
                        help='Path to the output file (JSON)')
    parser.add_argument('--skills-db', '-s',
                        help='Path to custom skills database JSON file')
    parser.add_argument('--cert-db', '-c',
                        help='Path to custom certifications database JSON file')
    parser.add_argument('--tesseract-path', '-t',
                        help='Path to Tesseract OCR executable')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--update-db', '-u', action='store_true',
                        help='Update skill/certification database with newly extracted entries')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Force processing even if file naming convention is not followed')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='Process all files in the input directory')
    parser.add_argument('--use-structured-format', '-sf', action='store_false', dest='disable_structured_format',
                        help='Disable structured format converter (enabled by default)')
    
    args = parser.parse_args()
    
    # Default to examples directory if no input is provided
    if not args.input:
        args.input = "examples"
        args.batch = True
    
    # Structured format is enabled by default
    args.use_structured_format = not args.disable_structured_format
        
    return args

def process_file(file_path, args):
    """
    Process a file to extract skills and certifications
    
    Args:
        file_path (str): Path to the file
        args (Namespace): Command line arguments
        
    Returns:
        tuple: (SkillRepository, extracted_text, certifications)
    """
    # Determine file type
    file_type = get_file_type(file_path)
    
    if not file_type:
        logger.error(f"Unsupported file type: {file_path}")
        return None, None, None
        
    # Extract text based on file type
    logger.info(f"Processing {file_type} file: {file_path}")
    
    try:
        # Check if we should use the structured format converter
        if args.use_structured_format:
            # Use the structured format converter
            logger.info("Using structured format converter")
            converter = StructuredFormatConverter(args.tesseract_path)
            structured_doc = converter.convert(file_path)
            
            if not structured_doc or not structured_doc.get("raw_text"):
                logger.error(f"Failed to convert document to structured format: {file_path}")
                return None, None, None
                
            logger.info(f"Successfully converted document to structured format")
            
            if args.verbose:
                doc_type = structured_doc.get("document_type", "unknown")
                section_count = len(structured_doc.get("sections", {}))
                logger.info(f"Document type: {doc_type}")
                logger.info(f"Extracted {section_count} sections")
                logger.info(f"Raw text preview: {structured_doc['raw_text'][:200]}...")
                
            # Process the structured document
            return process_structured_doc(structured_doc, args)
        else:
            # Use traditional extraction methods
            extracted_text = ""
            layout_info = None
            
            if file_type == 'pdf':
                extractor = PDFExtractor()
                # Use the new layout-preserving extraction
                if args.verbose:
                    logger.info("Using enhanced PDF extraction with layout preservation")
                layout_data = extractor.extract_with_layout(file_path)
                extracted_text = layout_data["text"]
                layout_info = layout_data
            elif file_type == 'image':
                extractor = ImageExtractor(args.tesseract_path)
                extracted_text = extractor.extract(file_path)
                
            if not extracted_text:
                logger.error(f"Failed to extract text from {file_path}")
                return None, None, None
                
            logger.info(f"Successfully extracted text from {file_path}")
            
            if args.verbose:
                logger.info(f"Extracted text preview: {extracted_text[:200]}...")
                
            # Process the extracted text
            skill_repo, certifications = process_text(extracted_text, args, layout_info)
            
            return skill_repo, extracted_text, certifications
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return None, None, None

def process_structured_doc(structured_doc, args):
    """
    Process a structured document to extract skills and certifications
    
    Args:
        structured_doc (dict): Structured document representation
        args (Namespace): Command line arguments
        
    Returns:
        tuple: (SkillRepository, extracted_text, extracted_certifications)
    """
    # Create extractors
    skill_extractor = SkillExtractor(args.skills_db)
    cert_extractor = CertificationExtractor(args.cert_db)
    proficiency_calculator = ProficiencyCalculator()
    
    # Create skill repository
    skill_repo = SkillRepository()
    
    # Extract skills
    logger.info("Extracting skills from structured document...")
    
    # Use structured document for extraction
    extracted_text = structured_doc.get("raw_text", "")
    extracted_skills, sections_with_skills = skill_extractor.extract_skills(structured_doc)
    
    if args.verbose:
        logger.info(f"Extracted {len(extracted_skills)} raw skills")
        for section, skills in sections_with_skills.items():
            logger.info(f"  - {section}: {len(skills)} skills")
    
    # Extract certifications
    logger.info("Extracting certifications from structured document...")
    certifications = cert_extractor.extract_certifications(structured_doc)
    
    if args.verbose:
        logger.info(f"Extracted {len(certifications)} certifications")
        for cert in certifications:
            logger.info(f"  - {cert['name']} (Confidence: {cert['confidence']:.2f}, Source: {cert.get('source', 'unknown')})")
    
    # Link skills to certifications
    logger.info("Linking skills to certifications...")
    linked_skills = cert_extractor.link_skills_to_certifications(extracted_skills, certifications)
    
    # Calculate proficiency levels
    logger.info("Calculating proficiency levels...")
    final_skills = []
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
        
        final_skills.append(skill)
        skill_repo.add_skill(skill)
    
    # Update the database if requested
    if args.update_db:
        update_databases(final_skills, certifications, args)
    
    # Summary
    backed_skills = skill_repo.get_backed_skills()
    unbacked_skills = skill_repo.get_unbacked_skills()
    
    logger.info(f"Processed {len(final_skills)} skills total")
    logger.info(f"Backed skills: {len(backed_skills)}")
    logger.info(f"Unbacked skills: {len(unbacked_skills)}")
    
    return skill_repo, extracted_text, certifications

def process_text(text, args, layout_info=None):
    """
    Process extracted text to identify skills and certifications
    
    Args:
        text (str): Extracted text
        args (Namespace): Command line arguments
        layout_info (dict): Layout information extracted from the file
        
    Returns:
        tuple: (SkillRepository, list of certifications)
    """
    # Create extractors and processors
    skill_extractor = SkillExtractor(args.skills_db)
    cert_extractor = CertificationExtractor(args.cert_db)
    proficiency_calculator = ProficiencyCalculator()
    
    # Create skill repository
    skill_repo = SkillRepository()
    
    # Extract skills
    logger.info("Extracting skills...")
    
    # If we have layout information, use it for better skill extraction
    if layout_info:
        skills = skill_extractor.extract_skills(text, layout_info=layout_info)
    else:
        skills = skill_extractor.extract_skills(text)
    
    if args.verbose:
        logger.info(f"Extracted {len(skills)} raw skills")
        
    # Extract certifications
    logger.info("Extracting certifications...")
    
    # If we have layout information, use it for better certification extraction
    if layout_info:
        certifications = cert_extractor.extract_certifications(text, layout_info=layout_info)
    else:
        certifications = cert_extractor.extract_certifications(text)
    
    if args.verbose:
        logger.info(f"Extracted {len(certifications)} certifications")
        for cert in certifications:
            logger.info(f"  - {cert['name']} (Confidence: {cert['confidence']:.2f}, Source: {cert.get('source', 'unknown')})")
        
    # Link skills to certifications
    logger.info("Linking skills to certifications...")
    linked_skills = cert_extractor.link_skills_to_certifications(skills, certifications)
    
    # Calculate proficiency levels
    logger.info("Calculating proficiency levels...")
    final_skills = proficiency_calculator.calculate_proficiencies_for_skills(linked_skills, text)
    
    # Add skills to repository
    for skill in final_skills:
        skill_repo.add_skill(skill)
        
    # Update the database if requested
    if args.update_db:
        update_databases(final_skills, certifications, args)
        
    # Summary
    backed_skills = skill_repo.get_backed_skills()
    unbacked_skills = skill_repo.get_unbacked_skills()
    
    logger.info(f"Processed {len(final_skills)} skills total")
    logger.info(f"Backed skills: {len(backed_skills)}")
    logger.info(f"Unbacked skills: {len(unbacked_skills)}")
    
    return skill_repo, certifications

def update_databases(skills, certifications, args):
    """
    Update skills and certifications databases with newly extracted items
    
    Args:
        skills (list): List of extracted Skill objects
        certifications (list): List of extracted certification dictionaries
        args (Namespace): Command line arguments
    """
    # Update skills database
    if args.skills_db and os.path.exists(args.skills_db):
        try:
            with open(args.skills_db, 'r') as f:
                skills_data = json.load(f)
                
            # Extract high-confidence skills
            high_conf_skills = [s.name for s in skills if s.confidence_score > 0.7]
            
            # Add technical skills to the database
            for skill_name in high_conf_skills:
                if "technical_skills" in skills_data and skill_name not in skills_data["technical_skills"]:
                    logger.info(f"Adding skill to database: {skill_name}")
                    skills_data["technical_skills"].append(skill_name)
                    
            # Save updated database
            with open(args.skills_db, 'w') as f:
                json.dump(skills_data, f, indent=4)
                
            logger.info(f"Updated skills database at {args.skills_db}")
            
        except Exception as e:
            logger.error(f"Error updating skills database: {str(e)}")
            
    # Update certifications database
    if args.cert_db and os.path.exists(args.cert_db):
        try:
            with open(args.cert_db, 'r') as f:
                cert_data = json.load(f)
                
            # Extract high-confidence certifications
            high_conf_certs = [c['name'] for c in certifications if c['confidence'] > 0.7]
            
            # Add certifications to the database
            if "certifications" in cert_data:
                for cert_name in high_conf_certs:
                    if cert_name not in cert_data["certifications"]:
                        logger.info(f"Adding certification to database: {cert_name}")
                        cert_data["certifications"].append(cert_name)
                        
                # Save updated database
                with open(args.cert_db, 'w') as f:
                    json.dump(cert_data, f, indent=4)
                    
                logger.info(f"Updated certifications database at {args.cert_db}")
                
        except Exception as e:
            logger.error(f"Error updating certifications database: {str(e)}")
    
def save_batch_results(all_results, output_path=None):
    """
    Save comprehensive batch processing results to a single JSON file
    
    Args:
        all_results (dict): Combined results from all processed files
        output_path (str, optional): Path to save the results
        
    Returns:
        str: Path to the saved file
    """
    if not output_path:
        output_path = "batch_results.json"
        
    # Create a structured output format
    output_data = {
        "processed_date": datetime.datetime.now().isoformat(),
        "total_files_processed": {
            "resumes": len(all_results['resumes']),
            "certifications": len(all_results['certifications']),
            "unknown": len(all_results['unknown'])
        },
        "resume_skills": {},
        "certification_skills": {},
        "unknown_file_skills": {},
        "extracted_raw_text": {}
    }
    
    # Add resume skills
    for filename, results in all_results['resumes'].items():
        skills_data = []
        for skill in results['all_skills']:
            skills_data.append({
                "name": skill.name,
                "proficiency": skill.proficiency,
                "is_backed": skill.is_backed,
                "confidence_score": skill.confidence_score,
                "backing_certificate": skill.backing_certificate,
                "source": skill.source
            })
            
        output_data["resume_skills"][filename] = {
            "skills": skills_data,
            "total_skills": len(results['all_skills']),
            "backed_skills": len(results['backed_skills']),
            "unbacked_skills": len(results['unbacked_skills']),
            "skills_by_source": {source: [s.name for s in skills] for source, skills in results['skills_by_source'].items()},
            "individual_output_path": results['output_path']
        }
        
        # Extract certifications from the resume if available
        if hasattr(results, 'certifications') and results.certifications:
            output_data["resume_skills"][filename]["certifications"] = results.certifications
        
        # Store the raw text from the file if available for debugging
        if hasattr(results, 'raw_text') and results.raw_text:
            output_data["extracted_raw_text"][filename] = results.raw_text
    
    # Add certification skills
    for filename, results in all_results['certifications'].items():
        skills_data = []
        for skill in results['all_skills']:
            skills_data.append({
                "name": skill.name,
                "proficiency": skill.proficiency,
                "is_backed": skill.is_backed,
                "confidence_score": skill.confidence_score,
                "backing_certificate": skill.backing_certificate,
                "source": skill.source
            })
            
        output_data["certification_skills"][filename] = {
            "skills": skills_data,
            "total_skills": len(results['all_skills']),
            "backed_skills": len(results['backed_skills']),
            "unbacked_skills": len(results['unbacked_skills']),
            "skills_by_source": {source: [s.name for s in skills] for source, skills in results['skills_by_source'].items()},
            "individual_output_path": results['output_path']
        }
        
        # Extract certifications from the certificate if available
        if hasattr(results, 'certifications') and results.certifications:
            output_data["certification_skills"][filename]["certifications"] = results.certifications
        
        # Store the raw text from the file if available for debugging
        if hasattr(results, 'raw_text') and results.raw_text:
            output_data["extracted_raw_text"][filename] = results.raw_text
    
    # Add unknown file skills if processed
    for filename, results in all_results['unknown'].items():
        skills_data = []
        for skill in results['all_skills']:
            skills_data.append({
                "name": skill.name,
                "proficiency": skill.proficiency,
                "is_backed": skill.is_backed,
                "confidence_score": skill.confidence_score,
                "backing_certificate": skill.backing_certificate,
                "source": skill.source
            })
            
        output_data["unknown_file_skills"][filename] = {
            "skills": skills_data,
            "total_skills": len(results['all_skills']),
            "backed_skills": len(results['backed_skills']),
            "unbacked_skills": len(results['unbacked_skills']),
            "skills_by_source": {source: [s.name for s in skills] for source, skills in results['skills_by_source'].items()},
            "individual_output_path": results['output_path']
        }
        
        # Extract certifications from the file if available
        if hasattr(results, 'certifications') and results.certifications:
            output_data["unknown_file_skills"][filename]["certifications"] = results.certifications
        
        # Store the raw text from the file if available for debugging
        if hasattr(results, 'raw_text') and results.raw_text:
            output_data["extracted_raw_text"][filename] = results.raw_text
    
    # Save the comprehensive results
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=4)
        
    logger.info(f"Saved comprehensive batch results to {output_path}")
    return output_path

def save_extracted_text(all_results, output_path=None):
    """
    Save all extracted raw text to a JSON file
    
    Args:
        all_results (dict): Combined results from all processed files
        output_path (str, optional): Path to save the results
        
    Returns:
        str: Path to the saved file
    """
    if not output_path:
        output_path = "extracted_text.json"
        
    # Create a structured output format
    output_data = {
        "processed_date": datetime.datetime.now().isoformat(),
        "resume_text": {},
        "certification_text": {},
        "unknown_text": {}
    }
    
    # Add resume text
    for filename, results in all_results['resumes'].items():
        if 'raw_text' in results and results['raw_text']:
            # Convert certifications to serializable dictionaries
            cert_list = []
            if 'certifications' in results and results['certifications']:
                for cert in results['certifications']:
                    cert_list.append({
                        "name": cert.get('name', ''),
                        "confidence": cert.get('confidence', 0.0),
                        "source": cert.get('source', 'unknown')
                    })
                    
            output_data["resume_text"][filename] = {
                "text": results['raw_text'],
                "certifications": cert_list
            }
    
    # Add certification text
    for filename, results in all_results['certifications'].items():
        if 'raw_text' in results and results['raw_text']:
            # Extract skills from the text if the filename contains skill-related keywords
            skills = []
            if 'sql' in filename.lower():
                skills.append('SQL')
            if 'python' in filename.lower():
                skills.append('Python')
                
            # Convert certifications to serializable dictionaries
            cert_list = []
            if 'certifications' in results and results['certifications']:
                for cert in results['certifications']:
                    cert_list.append({
                        "name": cert.get('name', ''),
                        "confidence": cert.get('confidence', 0.0),
                        "source": cert.get('source', 'unknown')
                    })
                    
            output_data["certification_text"][filename] = {
                "text": results['raw_text'],
                "certifications": cert_list,
                "inferred_skills": skills
            }
    
    # Add unknown text
    for filename, results in all_results['unknown'].items():
        if 'raw_text' in results and results['raw_text']:
            # Convert certifications to serializable dictionaries
            cert_list = []
            if 'certifications' in results and results['certifications']:
                for cert in results['certifications']:
                    cert_list.append({
                        "name": cert.get('name', ''),
                        "confidence": cert.get('confidence', 0.0),
                        "source": cert.get('source', 'unknown')
                    })
                    
            output_data["unknown_text"][filename] = {
                "text": results['raw_text'],
                "certifications": cert_list
            }
    
    # Save the extracted text
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=4)
        
    logger.info(f"Saved extracted text to {output_path}")
    return output_path

def create_consolidated_profile(all_results, output_path=None):
    """
    Create a consolidated skills profile for an individual by combining results from all files
    
    Args:
        all_results (dict): Combined results from all processed files
        output_path (str, optional): Path to save the consolidated profile
        
    Returns:
        str: Path to the saved file
    """
    if not output_path:
        output_path = "consolidated_profile.json"
    
    # Extract the person's name from file names
    person_name = None
    for filename in all_results['resumes'].keys():
        # Extract name from filename (e.g., "John Smith Resume.pdf" -> "John Smith")
        name_match = re.search(r'(.+?)\s+Resume', filename, re.IGNORECASE)
        if name_match:
            person_name = name_match.group(1)
            break
    
    if not person_name:
        for filename in all_results['certifications'].keys():
            # Extract name from filename (e.g., "John Smith Certificate.pdf" -> "John Smith")
            name_match = re.search(r'(.+?)\s+(Certificate|Certification)', filename, re.IGNORECASE)
            if name_match:
                person_name = name_match.group(1)
                break
    
    if not person_name:
        person_name = "Unknown"
    
    # Create a consolidated profile
    profile = {
        "name": person_name,
        "processed_date": datetime.datetime.now().isoformat(),
        "skills": [],
        "certifications": [],
        "skill_proficiency": {}
    }
    
    # Collect all skills from resumes
    for filename, results in all_results['resumes'].items():
        for skill in results['all_skills']:
            skill_info = {
                "name": skill.name,
                "proficiency": skill.proficiency,
                "is_backed": skill.is_backed,
                "confidence_score": skill.confidence_score,
                "source": skill.source,
                "from_file": filename
            }
            
            # Only add if not already in the list
            if not any(s['name'] == skill.name for s in profile['skills']):
                profile['skills'].append(skill_info)
                
            # Add to proficiency map
            if skill.proficiency:
                profile['skill_proficiency'][skill.name] = skill.proficiency
    
    # Collect inferred skills from certifications
    for filename, results in all_results['certifications'].items():
        # Check filename for skill keywords
        inferred_skills = []
        if 'sql' in filename.lower():
            inferred_skills.append('SQL')
        if 'python' in filename.lower():
            inferred_skills.append('Python')
            
        for skill_name in inferred_skills:
            # Only add if not already in the list
            if not any(s['name'] == skill_name for s in profile['skills']):
                skill_info = {
                    "name": skill_name,
                    "proficiency": "Certified",  # Assume certification implies proficiency
                    "is_backed": True,
                    "confidence_score": 0.9,  # High confidence since it's from certification filename
                    "source": f"Certification: {filename}",
                    "from_file": filename
                }
                profile['skills'].append(skill_info)
                
                # Add to proficiency map
                profile['skill_proficiency'][skill_name] = "Certified"
    
    # Collect all certifications from certification files
    for filename, results in all_results['certifications'].items():
        extracted_text = results.get('raw_text', '')
        
        # Try to extract certification name from the text
        cert_text = None
        
        # Look for "Course in X Training" pattern
        course_match = re.search(r'Course in\s+(.+?)\s+Training', extracted_text, re.IGNORECASE)
        if course_match:
            cert_text = f"{course_match.group(1)} Training Certificate"
        else:
            # Use the filename as a fallback
            cert_text = f"{filename.replace('.png', '').replace('.pdf', '')}"
        
        # Add certification to the list
        certification = {
            "name": cert_text,
            "confidence": 0.9,  # High confidence since it's a dedicated certification file
            "source": filename,
            "date_extracted": datetime.datetime.now().isoformat()
        }
        
        # Only add if not already in the list
        if not any(c['name'] == cert_text for c in profile['certifications']):
            profile['certifications'].append(certification)
    
    # Sort skills by confidence score
    profile['skills'] = sorted(profile['skills'], key=lambda x: x['confidence_score'], reverse=True)
    
    # Save the consolidated profile
    with open(output_path, 'w') as f:
        json.dump(profile, f, indent=4)
    
    logger.info(f"Saved consolidated profile to {output_path}")
    return output_path

def process_directory(directory_path, args):
    """
    Process all supported files in a directory, processing resumes first then certifications
    
    Args:
        directory_path (str): Path to the directory containing files to process
        args (Namespace): Command line arguments
        
    Returns:
        dict: Combined results from all processed files
    """
    # Find all supported files in the directory
    all_files = get_supported_files_in_directory(directory_path)
    
    if not all_files:
        logger.error(f"No supported files found in {directory_path}")
        return None
    
    logger.info(f"Found {len(all_files)} supported files in {directory_path}")
    
    # Separate files into resumes and certifications based on naming convention
    resume_files, certification_files, unknown_files = sort_files_by_type(all_files)
    
    logger.info(f"Categorized files: {len(resume_files)} resumes, {len(certification_files)} certifications, {len(unknown_files)} unknown")
    
    # Process files in hierarchical order: resumes first, then certifications
    all_results = {
        'resumes': {},
        'certifications': {},
        'unknown': {}
    }
    
    # Process resume files
    logger.info("Processing resume files...")
    for file_path in resume_files:
        logger.info(f"Processing resume: {os.path.basename(file_path)}")
        skill_repo, extracted_text, certifications = process_file(file_path, args)
        if skill_repo:
            output_path = args.output if args.output else get_output_path(file_path)
            skill_repo.save_to_file(output_path)
            result_data = {
                'all_skills': skill_repo.get_all_skills(),
                'backed_skills': skill_repo.get_backed_skills(),
                'unbacked_skills': skill_repo.get_unbacked_skills(),
                'skills_by_source': skill_repo.get_skills_by_source(),
                'output_path': output_path,
                'raw_text': extracted_text,
                'certifications': certifications
            }
            all_results['resumes'][os.path.basename(file_path)] = result_data
    
    # Process certification files
    logger.info("Processing certification files...")
    for file_path in certification_files:
        logger.info(f"Processing certification: {os.path.basename(file_path)}")
        skill_repo, extracted_text, certifications = process_file(file_path, args)
        if skill_repo:
            output_path = args.output if args.output else get_output_path(file_path)
            skill_repo.save_to_file(output_path)
            result_data = {
                'all_skills': skill_repo.get_all_skills(),
                'backed_skills': skill_repo.get_backed_skills(),
                'unbacked_skills': skill_repo.get_unbacked_skills(),
                'skills_by_source': skill_repo.get_skills_by_source(),
                'output_path': output_path,
                'raw_text': extracted_text,
                'certifications': certifications
            }
            all_results['certifications'][os.path.basename(file_path)] = result_data
    
    # Process unknown files if force flag is set
    if args.force and unknown_files:
        logger.info("Processing files with unknown naming convention (--force enabled)...")
        for file_path in unknown_files:
            logger.info(f"Processing file: {os.path.basename(file_path)}")
            skill_repo, extracted_text, certifications = process_file(file_path, args)
            if skill_repo:
                output_path = args.output if args.output else get_output_path(file_path)
                skill_repo.save_to_file(output_path)
                result_data = {
                    'all_skills': skill_repo.get_all_skills(),
                    'backed_skills': skill_repo.get_backed_skills(),
                    'unbacked_skills': skill_repo.get_unbacked_skills(),
                    'skills_by_source': skill_repo.get_skills_by_source(),
                    'output_path': output_path,
                    'raw_text': extracted_text,
                    'certifications': certifications
                }
                all_results['unknown'][os.path.basename(file_path)] = result_data
    
    # Display summary of results
    display_batch_results(all_results)
    
    # Save comprehensive results
    save_batch_results(all_results, args.output if args.output else "batch_results.json")
    
    # Save extracted text
    save_extracted_text(all_results, "extracted_text.json")
    
    # Create consolidated profile
    create_consolidated_profile(all_results, "consolidated_profile.json")
    
    return all_results

def display_batch_results(all_results):
    """
    Display summary of batch processing results
    
    Args:
        all_results (dict): Combined results from all processed files
    """
    print("\n===== BATCH PROCESSING SUMMARY =====")
    
    # Resume results
    if all_results['resumes']:
        print("\n== RESUME SKILLS ==")
        for filename, results in all_results['resumes'].items():
            print(f"\nFile: {filename}")
            all_skills = results['all_skills']
            top_skills = sorted(all_skills, key=lambda x: x.confidence_score, reverse=True)[:10]
            
            print("Top skills extracted:")
            for skill in top_skills:
                print(f"- {skill.name}: {skill.proficiency or 'Unknown'} - {skill.confidence_score:.2f} confidence")
            
            print(f"Total skills: {len(all_skills)}")
            print(f"Backed skills: {len(results['backed_skills'])}")
            print(f"Unbacked skills: {len(results['unbacked_skills'])}")
            print(f"Results saved to: {results['output_path']}")
    
    # Certification results
    if all_results['certifications']:
        print("\n== CERTIFICATION SKILLS ==")
        for filename, results in all_results['certifications'].items():
            print(f"\nFile: {filename}")
            all_skills = results['all_skills']
            top_skills = sorted(all_skills, key=lambda x: x.confidence_score, reverse=True)[:10]
            
            print("Top skills extracted:")
            for skill in top_skills:
                print(f"- {skill.name}: {skill.proficiency or 'Unknown'} - {skill.confidence_score:.2f} confidence")
            
            print(f"Total skills: {len(all_skills)}")
            print(f"Backed skills: {len(results['backed_skills'])}")
            print(f"Unbacked skills: {len(results['unbacked_skills'])}")
            print(f"Results saved to: {results['output_path']}")
    
    # Unknown file results
    if all_results['unknown']:
        print("\n== UNKNOWN FILE TYPE SKILLS ==")
        for filename, results in all_results['unknown'].items():
            print(f"\nFile: {filename}")
            all_skills = results['all_skills']
            top_skills = sorted(all_skills, key=lambda x: x.confidence_score, reverse=True)[:10]
            
            print("Top skills extracted:")
            for skill in top_skills:
                print(f"- {skill.name}: {skill.proficiency or 'Unknown'} - {skill.confidence_score:.2f} confidence")
            
            print(f"Total skills: {len(all_skills)}")
            print(f"Backed skills: {len(results['backed_skills'])}")
            print(f"Unbacked skills: {len(results['unbacked_skills'])}")
            print(f"Results saved to: {results['output_path']}")

def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Display information about the structured format converter
    if args.use_structured_format:
        logger.info("Structured Format Converter is enabled (default)")
        logger.info("Document sections will be automatically identified and labeled")
        logger.info("This mode is optimal for well-formatted resumes and certification documents")
    else:
        logger.info("Structured Format Converter is disabled")
        logger.info("Using basic text extraction without document structure preservation")
    
    # Check if running in batch mode
    if args.batch or os.path.isdir(args.input):
        # Process all files in the directory
        input_dir = args.input
        if not os.path.exists(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            return 1
            
        logger.info(f"Processing all supported files in directory: {input_dir}")
        results = process_directory(input_dir, args)
        
        if not results:
            logger.error("Batch processing failed")
            return 1
            
        return 0
    else:
        # Process a single file
        input_file = args.input
        
        # Check if input file exists
        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            return 1
            
        # Check if file is supported
        if not is_supported_file(input_file):
            logger.error(f"Unsupported file type: {input_file}")
            return 1
        
        # Validate file naming convention
        is_valid_name, file_type = validate_file_naming(input_file)
        if not is_valid_name and not args.force:
            logger.error(f"Invalid file naming convention for {input_file}")
            logger.error("File name should contain 'resume' for resume files or 'certification'/'certificate' for certification files.")
            logger.error("Use --force or -f flag to process the file anyway.")
            return 1
        
        if is_valid_name and args.verbose:
            logger.info(f"Detected file type based on naming: {file_type}")
            
        # Get output path
        output_path = args.output if args.output else get_output_path(input_file)
        
        # Process file
        skill_repo, extracted_text, certifications = process_file(input_file, args)
        
        if not skill_repo:
            logger.error("Failed to process file")
            return 1
            
        # Save results
        logger.info(f"Saving results to {output_path}")
        
        if skill_repo.save_to_file(output_path):
            logger.info("Successfully saved results")
            
            # Display the top skills by confidence
            all_skills = skill_repo.get_all_skills()
            top_skills = sorted(all_skills, key=lambda x: x.confidence_score, reverse=True)[:10]
            
            print("\nTop skills extracted:")
            for skill in top_skills:
                print(f"- {skill}")
                
            # Display skills by source/section
            skills_by_source = skill_repo.get_skills_by_source()
            
            print("\nSkills grouped by source:")
            for source, skills in skills_by_source.items():
                print(f"\n{source}:")
                for skill in skills:
                    print(f"- {skill.name}: {skill.proficiency or 'Unknown'} - {skill.confidence_score:.2f} confidence")
                
            # Display certifications if any
            if certifications:
                print("\nCertifications detected:")
                for cert in certifications:
                    print(f"- {cert['name']} (Confidence: {cert['confidence']:.2f}, Source: {cert.get('source', 'unknown')})")
                
            return 0
        else:
            logger.error("Failed to save results")
            return 1
            
if __name__ == "__main__":
    sys.exit(main()) 