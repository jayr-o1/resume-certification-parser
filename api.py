#!/usr/bin/env python3
"""
Resume Analyzer API

This script provides a REST API for the resume skill extraction system.
It allows users to upload multiple resume and certification files via
HTTP requests and returns the extracted skills with proficiency levels.
"""

import os
import json
import shutil
import tempfile
import uuid
import re
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging
from extract_and_process import DocumentProcessor, SkillProcessor, ProficiencyCalculator
from processors.skill_validator import SkillValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('resume_api')

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for all routes
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'api_results'

# Create upload and results folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the HTML interface"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Service is running'})

@app.route('/api/extract', methods=['POST'])
def extract_skills():
    """
    Extract skills from uploaded files
    
    Expects multipart/form-data with files under the 'files' key
    """
    # Check if files are present in the request
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    # Check if files are empty
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected files'}), 400
    
    # Create a unique session ID for this request
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    results_dir = os.path.join(app.config['RESULTS_FOLDER'], session_id)
    
    os.makedirs(session_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    # Save uploaded files
    saved_files = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(session_dir, filename)
            file.save(file_path)
            saved_files.append(file_path)
    
    if not saved_files:
        return jsonify({'error': 'No valid files uploaded'}), 400
    
    logger.info(f"Processing {len(saved_files)} files for session {session_id}")
    
    try:
        # Process files
        result = process_files(saved_files, results_dir)
        
        # Return result
        return jsonify({
            'session_id': session_id,
            'message': f'Successfully processed {len(saved_files)} files',
            'result': result,
            'result_urls': {
                'json': f'/api/results/{session_id}/skills.json',
                'markdown': f'/api/results/{session_id}/skills_summary.md'
            }
        })
    
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        return jsonify({'error': f'Error processing files: {str(e)}'}), 500

@app.route('/api/results/<session_id>/<filename>', methods=['GET'])
def get_result_file(session_id, filename):
    """
    Get a result file from a processing session
    """
    # Validate filename
    if filename not in ['skills.json', 'skills_summary.md']:
        return jsonify({'error': 'Invalid filename'}), 400
    
    # Check if the result exists
    file_path = os.path.join(app.config['RESULTS_FOLDER'], session_id, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Result not found'}), 404
    
    # Return the file
    content_type = 'application/json' if filename.endswith('.json') else 'text/markdown'
    return send_file(file_path, mimetype=content_type)

def process_files(file_paths, output_dir):
    """
    Process files and extract skills
    
    Args:
        file_paths (list): List of file paths to process
        output_dir (str): Directory to save output files
        
    Returns:
        dict: Processing result
    """
    # Initialize processors
    document_processor = DocumentProcessor()
    skill_processor = SkillProcessor()
    proficiency_calculator = ProficiencyCalculator(skill_processor.technical_skills)
    
    # Initialize skill validator with custom database if available
    custom_db_path = os.path.join(os.path.dirname(__file__), 'data', 'skills_database.json')
    if not os.path.exists(custom_db_path):
        custom_db_path = None
    skill_validator = SkillValidator(custom_db_path)  # Initialize the skill validator with db path
    
    # Initialize result containers
    all_skills = []
    cert_skills = []
    cert_texts = {}
    resume_skills = []
    resume_file = None
    detected_industry = "general"
    industry_scores = {}
    
    # Categorize files
    resume_files = [f for f in file_paths if document_processor.is_resume(f)]
    cert_files = [f for f in file_paths if document_processor.is_certification(f)]
    other_files = [f for f in file_paths if f not in resume_files and f not in cert_files]
    
    logger.info(f"Found {len(resume_files)} resume files, {len(cert_files)} certification files, and {len(other_files)} other files")
    
    # Process certification files first
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
    
    # Process resume files
    for file_path in resume_files:
        logger.info(f"Processing resume: {os.path.basename(file_path)}")
        resume_file = os.path.basename(file_path)
        
        # Extract text
        extracted_text = document_processor.process_file(file_path)
        
        if not extracted_text:
            logger.warning(f"Failed to extract text from {file_path}")
            continue
        
        # Detect industry for targeted skill extraction
        from extract_and_process import detect_industry
        detected_industry, industry_scores = detect_industry(extracted_text)
        logger.info(f"Detected industry: {detected_industry}")
        
        # Update processors for industry-specific extraction
        if hasattr(skill_processor, 'update_for_industry'):
            skill_processor.update_for_industry(detected_industry)
        
        if hasattr(proficiency_calculator, 'update_for_industry'):
            proficiency_calculator.update_for_industry(detected_industry)
        
        # Extract skills with industry context
        file_skills = skill_processor.extract_skills(extracted_text)
        logger.info(f"Extracted {len(file_skills)} skills from resume (industry: {detected_industry})")
        
        # Mark backed skills
        backed_skills = skill_processor.mark_backed_skills(file_skills, cert_skills)
        resume_skills.extend(backed_skills)
    
    # Process other files as resumes if no resume files found
    if not resume_skills and other_files:
        logger.info("No resume files found, treating other files as resumes")
        for file_path in other_files:
            logger.info(f"Processing file as resume: {os.path.basename(file_path)}")
            resume_file = os.path.basename(file_path)
            
            # Extract text
            extracted_text = document_processor.process_file(file_path)
            
            if not extracted_text:
                logger.warning(f"Failed to extract text from {file_path}")
                continue
            
            # Extract skills
            file_skills = skill_processor.extract_skills(extracted_text)
            logger.info(f"Extracted {len(file_skills)} skills")
            
            # Mark backed skills if cert skills exist
            if cert_skills:
                file_skills = skill_processor.mark_backed_skills(file_skills, cert_skills)
            
            resume_skills.extend(file_skills)
    
    # Calculate proficiency for all skills
    processed_skills = []
    for skill in resume_skills:
        # Get certification text for this skill if available
        cert_text = ""
        for cert_file, text in cert_texts.items():
            if skill["name"].lower() in text.lower():
                cert_text += text + " "
        
        # Extra validation - ensure skill is actually mentioned in the original text
        # Extract text from resumes
        resume_text = ""
        for file_path in resume_files:
            resume_text += document_processor.process_file(file_path) + " "
            
        # Initialize specialized skill flags
        is_database_skill = skill["name"] in ["MySQL", "PostgreSQL", "Oracle", "Microsoft SQL Server", 
                                            "SQL", "PL/SQL", "T-SQL", "ER Diagrams", "Normalization", 
                                            "Schema Design", "ETL Processes", "Star Schema"]
        
        is_teaching_skill = skill["name"] in ["Curriculum Development", "Student-Centered Learning",
                                            "Classroom Teaching", "Online Teaching", "Assessment & Evaluation",
                                            "Instructional Design"]
                                            
        # For multi-word skills, check for different patterns
        if " " in skill["name"]:
            words = skill["name"].split()
            # Try different combinations for multi-word skills
            explicit_skill_pattern = any([
                re.search(r'\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE),  # Exact match
                re.search(r'\b' + re.escape(words[0]) + r'.*?' + re.escape(words[-1]) + r'\b', resume_text, re.IGNORECASE),  # First and last word
                re.search(r'\b' + re.escape(" ".join(words[:2])) + r'\b', resume_text, re.IGNORECASE) if len(words) > 2 else False,  # First two words
                all(re.search(r'\b' + re.escape(word) + r'\b', resume_text, re.IGNORECASE) for word in words)  # All words separately
            ])
        else:
            # Single word skills
            explicit_skill_pattern = re.search(r'\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE)
            
        # Skip if skill is not mentioned in any form and not in a specialized domain section
        if not explicit_skill_pattern:
            # Check if it's in a specialized domain - if so, be more lenient
            if is_database_skill:
                db_section_match = re.search(r'database|data|sql|query', resume_text, re.IGNORECASE)
                if not db_section_match:
                    logger.warning(f"Skipping database skill {skill['name']} - not explicitly mentioned in resume")
                    continue
            elif is_teaching_skill:
                teaching_section_match = re.search(r'teaching|education|instruction|curriculum', resume_text, re.IGNORECASE)
                if not teaching_section_match:
                    logger.warning(f"Skipping teaching skill {skill['name']} - not explicitly mentioned in resume")
                    continue
            else:
                logger.warning(f"Skipping skill {skill['name']} - not explicitly mentioned in resume")
                continue
            
        # Special handling for potentially problematic skills
        if skill["name"] in ["C++", "R"]:
            # More strict verification - ensure it's in a skills or programming context
            programming_context = any([
                re.search(r'programming.*\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE),
                re.search(r'languages.*\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE),
                re.search(r'skills.*\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE),
                re.search(r'technologies.*\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE),
                re.search(r'proficient.*\b' + re.escape(skill["name"]) + r'\b', resume_text, re.IGNORECASE)
            ])
            
            if not programming_context:
                logger.warning(f"Skipping ambiguous skill {skill['name']} - not in programming context")
                continue
        
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
    
    # Post-process extracted skills to validate and remove non-skills
    validated_skills = skill_validator.validate_skills(processed_skills)
    logger.info(f"Validated skills: {len(validated_skills)} out of {len(processed_skills)} original skills")
    
    # Sort validated skills by name
    validated_skills.sort(key=lambda x: x["name"])
    
    # Get certification names
    certification_names = [os.path.basename(f) for f in cert_files]
    
    # Create result object
    result = {
        "file": resume_file or "unknown",
        "skills": validated_skills,  # Use validated skills instead of all processed skills
        "certifications": certification_names,
        "industry": detected_industry,
        "industry_scores": {k: round(v, 2) for k, v in sorted(industry_scores.items(), key=lambda x: x[1], reverse=True)[:3] if v > 0.05}
    }
    
    # Save results to files
    with open(os.path.join(output_dir, "skills.json"), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    # Create markdown summary
    from summarize_skills import generate_summary
    generate_summary(result, os.path.join(output_dir, "skills_summary.md"))
    
    return result

# Clean up old sessions
def cleanup_old_sessions(max_age_hours=24):
    """Clean up old sessions"""
    import time
    from datetime import datetime, timedelta
    
    now = time.time()
    cutoff_time = now - (max_age_hours * 60 * 60)
    
    # Clean up uploads directory
    for session_id in os.listdir(app.config['UPLOAD_FOLDER']):
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        if os.path.isdir(session_dir):
            # Check directory modification time
            if os.path.getmtime(session_dir) < cutoff_time:
                logger.info(f"Cleaning up old upload session: {session_id}")
                shutil.rmtree(session_dir, ignore_errors=True)
    
    # Clean up results directory
    for session_id in os.listdir(app.config['RESULTS_FOLDER']):
        results_dir = os.path.join(app.config['RESULTS_FOLDER'], session_id)
        if os.path.isdir(results_dir):
            # Check directory modification time
            if os.path.getmtime(results_dir) < cutoff_time:
                logger.info(f"Cleaning up old results session: {session_id}")
                shutil.rmtree(results_dir, ignore_errors=True)

if __name__ == '__main__':
    # Run cleanup job every hour in a background thread
    import threading
    import time
    
    def cleanup_job():
        while True:
            try:
                cleanup_old_sessions()
            except Exception as e:
                logger.error(f"Error in cleanup job: {str(e)}")
            time.sleep(3600)  # Sleep for 1 hour
    
    cleanup_thread = threading.Thread(target=cleanup_job)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port) 