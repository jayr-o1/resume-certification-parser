#!/usr/bin/env python3
"""
Skill Proficiency Summarizer

This script takes the output from our skill extraction process and creates
a clean, human-readable summary of the skills detected in a resume and 
their backing by certifications.
"""

import json
import sys
import os
import argparse

PROFICIENCY_DESCRIPTIONS = {
    "Beginner": "Basic knowledge and limited practical experience",
    "Intermediate": "Working knowledge with practical application experience",
    "Advanced": "Deep knowledge with significant project experience",
    "Expert": "Comprehensive mastery and leadership in the subject"
}

def load_skills(json_file):
    """Load skills data from a JSON file"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading skills data: {str(e)}")
        return None

def generate_summary(skills_data, output_file=None):
    """Generate a human-readable summary of skills"""
    if not skills_data:
        print("No skills data available")
        return
    
    # Organize skills by proficiency level
    skills_by_level = {level: [] for level in ["Expert", "Advanced", "Intermediate", "Beginner"]}
    
    # Count backed vs unbacked skills
    backed_count = 0
    total_skills = len(skills_data.get("skills", []))
    
    for skill in skills_data.get("skills", []):
        proficiency = skill.get("proficiency", "Beginner")
        skills_by_level[proficiency].append(skill)
        if skill.get("is_backed", False):
            backed_count += 1
    
    # Generate summary text
    summary = []
    summary.append("# SKILL PROFICIENCY SUMMARY\n")
    
    # Resume info
    summary.append(f"## Resume: {skills_data.get('file', 'Unknown')}\n")
    
    # Industry info
    if "industry" in skills_data and skills_data["industry"] != "general":
        summary.append(f"## Detected Industry: {skills_data['industry'].title()}\n")
        
        # Add top industry scores if available
        if "industry_scores" in skills_data and skills_data["industry_scores"]:
            summary.append("### Industry Confidence Scores\n")
            for industry, score in skills_data["industry_scores"].items():
                summary.append(f"- {industry.title()}: {score:.2f}\n")
            summary.append("\n")
    
    # Certification info
    cert_count = len(skills_data.get("certifications", []))
    if cert_count > 0:
        summary.append(f"## Certifications: {cert_count}\n")
        for cert in skills_data.get("certifications", []):
            summary.append(f"- {cert}\n")
    
    # Skills overview
    summary.append(f"\n## Skills Overview\n")
    summary.append(f"- Total Skills: {total_skills}\n")
    summary.append(f"- Backed by Certifications: {backed_count} ({(backed_count/total_skills*100):.1f}%)\n")
    
    # Skills by proficiency
    summary.append("\n## Skills by Proficiency\n")
    for level in ["Expert", "Advanced", "Intermediate", "Beginner"]:
        level_skills = skills_by_level[level]
        if level_skills:
            summary.append(f"\n### {level} ({len(level_skills)})\n")
            summary.append(f"_{PROFICIENCY_DESCRIPTIONS[level]}_\n\n")
            
            # Group skills into technical and soft skills
            technical_skills = [s for s in level_skills if s.get("is_technical", True)]
            soft_skills = [s for s in level_skills if not s.get("is_technical", True)]
            
            if technical_skills:
                summary.append("**Technical Skills:**\n")
                for skill in technical_skills:
                    backed_marker = "X" if skill.get("is_backed", False) else " "
                    summary.append(f"- [{backed_marker}] {skill['name']} (Confidence: {skill['confidence']:.2f})\n")
            
            if soft_skills:
                summary.append("\n**Soft Skills:**\n")
                for skill in soft_skills:
                    backed_marker = "X" if skill.get("is_backed", False) else " "
                    summary.append(f"- [{backed_marker}] {skill['name']} (Confidence: {skill['confidence']:.2f})\n")
    
    # Add industry-specific section if industry is detected
    if "industry" in skills_data and skills_data["industry"] != "general":
        industry = skills_data["industry"]
        industry_specific_skills = []
        
        # Define industry-specific skill keywords
        industry_skill_keywords = {
            "technology": ["programming", "development", "software", "database", "cloud", "DevOps"],
            "healthcare": ["patient", "medical", "clinical", "health", "diagnosis", "treatment"],
            "finance": ["financial", "accounting", "banking", "investment", "budget", "analysis"],
            "education": ["teaching", "curriculum", "instruction", "assessment", "learning"],
            "legal": ["legal", "law", "contracts", "compliance", "regulation"],
            "marketing": ["marketing", "brand", "digital", "content", "campaign"],
            "sales": ["sales", "account", "business development", "client", "revenue"]
        }
        
        # Find industry-specific skills
        if industry in industry_skill_keywords:
            keywords = industry_skill_keywords[industry]
            for skill in skills_data.get("skills", []):
                skill_name = skill["name"].lower()
                if any(keyword.lower() in skill_name for keyword in keywords):
                    industry_specific_skills.append(skill)
        
        # Add industry-specific skills section if any found
        if industry_specific_skills:
            summary.append(f"\n## {industry.title()} Industry Skills\n")
            for skill in sorted(industry_specific_skills, key=lambda x: x["name"]):
                proficiency = skill.get("proficiency", "Beginner")
                backed_marker = "X" if skill.get("is_backed", False) else " "
                summary.append(f"- [{backed_marker}] {skill['name']} ({proficiency}, Confidence: {skill['confidence']:.2f})\n")
    
    # Certifications legend
    summary.append("\n## Legend\n")
    summary.append("- [X] Skill backed by certification\n")
    summary.append("- [ ] Skill not backed by certification\n")
    
    # Join all parts together
    summary_text = "".join(summary)
    
    # Output summary
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            print(f"Summary saved to {output_file}")
        except Exception as e:
            print(f"Error writing summary to file: {str(e)}")
            print(summary_text)
    else:
        print(summary_text)
    
    return summary_text

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Summarize skills data into a human-readable format.'
    )
    
    parser.add_argument('--input', '-i', required=True,
                      help='Path to skills JSON file')
    parser.add_argument('--output', '-o',
                      help='Path to output summary file (markdown format)')
    
    args = parser.parse_args()
    
    # Load skills data
    skills_data = load_skills(args.input)
    
    # Generate summary
    if skills_data:
        generate_summary(skills_data, args.output)

if __name__ == "__main__":
    main() 