#!/usr/bin/env python3
"""
Test script for the resume parsing API

This script sends a sample resume to the API and prints the response
"""

import requests
import os
import glob
import json

def test_api():
    """Test the API with a sample resume"""
    # Find example files
    examples_dir = "examples"
    if not os.path.exists(examples_dir):
        print(f"Error: Examples directory {examples_dir} not found")
        return
    
    # Look for resume and certification files
    resume_files = []
    cert_files = []
    
    for file_path in glob.glob(os.path.join(examples_dir, "*")):
        if "resume" in file_path.lower():
            resume_files.append(file_path)
        elif "cert" in file_path.lower():
            cert_files.append(file_path)
    
    if not resume_files:
        print("Error: No resume files found in examples directory")
        return
        
    # Prepare files for upload
    files = []
    for file_path in resume_files + cert_files:
        files.append(("files", (os.path.basename(file_path), open(file_path, "rb"))))
    
    # Make the API request
    print(f"Sending {len(files)} files to API...")
    response = requests.post("http://localhost:5000/api/extract", files=files)
    
    # Close file handles
    for _, file_obj in files:
        file_obj[1].close()
    
    # Check the response
    if response.status_code == 200:
        result = response.json()
        print(f"API request successful")
        print(f"Session ID: {result.get('session_id')}")
        
        # Display industry information
        skill_data = result.get("result", {})
        industry = skill_data.get("industry", "unknown")
        print(f"Detected industry: {industry}")
        
        # Display industry scores
        industry_scores = skill_data.get("industry_scores", {})
        if industry_scores:
            print("Industry confidence scores:")
            for ind, score in industry_scores.items():
                print(f"  - {ind}: {score}")
        
        # Display skills
        skills = skill_data.get("skills", [])
        print(f"Extracted {len(skills)} skills")
        
        # Print skill summary by proficiency
        skills_by_level = {}
        for skill in skills:
            level = skill.get("proficiency", "Unknown")
            if level not in skills_by_level:
                skills_by_level[level] = []
            skills_by_level[level].append(skill)
        
        for level, level_skills in skills_by_level.items():
            print(f"\n{level} skills ({len(level_skills)}):")
            for skill in level_skills:
                backed = "✓" if skill.get("is_backed", False) else " "
                print(f"  [{backed}] {skill['name']} (Confidence: {skill['confidence']:.2f})")
        
        # Save raw response for inspection
        with open("api_response.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\nFull response saved to api_response.json")
        
    else:
        print(f"API request failed with status code {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_api() 