#!/usr/bin/env python3
"""
Resume Analyzer - Main Entry Point

This script is the main entry point for the resume and certification skill extraction system.
It analyzes resumes and certification files to extract skills, determine which skills are 
backed by certifications, calculate proficiency levels, and produce a human-readable summary.

Usage:
    python resume_analyzer.py --input examples/ --output results/
"""

import os
import sys
import argparse
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('resume_analyzer')

def analyze_resume(input_dir, output_dir=None, tesseract_path=None):
    """
    Analyze resume and certification files, extract skills, and create a summary.
    
    Args:
        input_dir (str): Directory containing resume and certification files
        output_dir (str, optional): Directory to save output files
        tesseract_path (str, optional): Path to Tesseract OCR executable
    
    Returns:
        bool: True if analysis was successful, False otherwise
    """
    # Create output directory if it doesn't exist
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = "."
    
    # Set file paths
    skills_json = os.path.join(output_dir, "skills.json")
    skills_summary = os.path.join(output_dir, "skills_summary.md")
    
    # Step 1: Extract skills from resume and certification files
    logger.info("Step 1: Extracting skills from resume and certification files...")
    
    extract_cmd = [sys.executable, "skills_extractor.py", "--input", input_dir, "--output", skills_json]
    if tesseract_path:
        extract_cmd.extend(["--tesseract-path", tesseract_path])
    
    try:
        subprocess.run(extract_cmd, check=True)
        logger.info(f"Skills data saved to {skills_json}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting skills: {str(e)}")
        return False
    
    # Step 2: Generate human-readable summary
    logger.info("Step 2: Generating human-readable summary...")
    
    try:
        subprocess.run([sys.executable, "summarize_skills.py", "--input", skills_json, "--output", skills_summary], check=True)
        logger.info(f"Skills summary saved to {skills_summary}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating summary: {str(e)}")
        return False
    
    logger.info("Analysis complete!")
    logger.info(f"- JSON data: {skills_json}")
    logger.info(f"- Summary: {skills_summary}")
    
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Analyze resumes and certifications to extract skills and proficiency levels.'
    )
    
    parser.add_argument('--input', '-i', required=True,
                      help='Directory containing resume and certification files')
    parser.add_argument('--output', '-o',
                      help='Directory to save output files')
    parser.add_argument('--tesseract-path', '-t',
                      help='Path to Tesseract OCR executable')
    
    args = parser.parse_args()
    
    # Run analysis
    analyze_resume(args.input, args.output, args.tesseract_path)

if __name__ == "__main__":
    main() 