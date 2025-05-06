"""
Skill Database Utility

Provides access to a comprehensive database of professional skills, 
categorized by domain (technical, soft skills, domain-specific).
"""

import os
import json
import logging
from typing import List, Dict, Any, Set, Optional

logger = logging.getLogger('skill_database')

class SkillDatabase:
    """Maintains a database of known and validated professional skills"""
    
    def __init__(self, custom_db_path: Optional[str] = None):
        """
        Initialize the skill database
        
        Args:
            custom_db_path (str, optional): Path to a custom skills database JSON file
        """
        self.skills_data = self._load_skills_data(custom_db_path)
        self.technical_skills = set(self.skills_data.get("technical_skills", []))
        self.soft_skills = set(self.skills_data.get("soft_skills", []))
        self.domain_skills = {}
        
        # Load domain-specific skills
        for key, skills in self.skills_data.items():
            if key.endswith('_skills') and key not in ["technical_skills", "soft_skills"]:
                domain = key.replace('_skills', '')
                self.domain_skills[domain] = set(skills)
                
        # Create a set of all skills for quick lookups
        self.all_skills = self.technical_skills.union(self.soft_skills)
        for domain_skills in self.domain_skills.values():
            self.all_skills = self.all_skills.union(domain_skills)
            
        # Create case-insensitive lookup
        self.skill_lookup = {skill.lower(): skill for skill in self.all_skills}
        
        logger.info(f"Initialized skill database with {len(self.all_skills)} skills")
    
    def _load_skills_data(self, custom_db_path: Optional[str]) -> Dict[str, List[str]]:
        """
        Load skills data from a custom JSON file or use the default database
        
        Args:
            custom_db_path (str, optional): Path to a custom skills database JSON file
            
        Returns:
            dict: Skills data with categories and lists of skills
        """
        # Define the comprehensive built-in skill database
        default_db = {
            "technical_skills": [
                # Programming Languages
                "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Ruby", "PHP", 
                "Swift", "Kotlin", "Go", "Rust", "COBOL", "Fortran", "R", "Scala", "Perl",
                "Objective-C", "Groovy", "Dart", "Lua", "Haskell", "Clojure", "Erlang", "F#",
                
                # Web Development
                "HTML", "CSS", "SASS", "LESS", "Bootstrap", "Tailwind CSS", "Material UI",
                "React", "Angular", "Vue.js", "Svelte", "jQuery", "Redux", "Next.js", "Gatsby",
                "Node.js", "Express", "Django", "Flask", "Ruby on Rails", "Spring", "ASP.NET",
                "Laravel", "CodeIgniter", "Symfony", "Wordpress", "Drupal", "Magento", "Shopify",
                
                # Data Science & Machine Learning
                "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy", "SciPy",
                "MATLAB", "Jupyter", "Matplotlib", "Seaborn", "Tableau", "Power BI", "Alteryx",
                "SPSS", "SAS", "R Studio", "Databricks", "Dataiku", "H2O",
                
                # Cloud & DevOps
                "AWS", "Azure", "Google Cloud", "IBM Cloud", "Oracle Cloud", "DigitalOcean",
                "Docker", "Kubernetes", "Jenkins", "Travis CI", "CircleCI", "GitHub Actions",
                "Terraform", "Ansible", "Puppet", "Chef", "Vagrant", "Prometheus", "Grafana",
                
                # Databases
                "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite", "Oracle", 
                "Microsoft SQL Server", "Cassandra", "Couchbase", "Elasticsearch", "Firebase",
                "DynamoDB", "MariaDB", "Neo4j", "GraphQL", "T-SQL", "PL/SQL", "ER Diagrams",
                
                # Mobile Development
                "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic", "Cordova",
                "SwiftUI", "UIKit", "Kotlin Multiplatform", "App Store Connect", "Google Play Console",
                
                # Version Control & Collaboration
                "Git", "GitHub", "GitLab", "Bitbucket", "SVN", "Mercurial", "JIRA",
                "Confluence", "Trello", "Asana", "Notion", "Slack", "Microsoft Teams",
                
                # Design & Creative
                "Photoshop", "Illustrator", "InDesign", "Figma", "Sketch", "Adobe XD",
                "After Effects", "Premiere Pro", "Blender", "AutoCAD", "Revit", "SketchUp",
                
                # Other Technical Skills
                "Excel", "VBA", "PowerPoint", "Word", "Outlook", "SharePoint", "Power Automate",
                "PowerApps", "Access", "Salesforce", "SAP", "QuickBooks", "Visio"
            ],
            
            "soft_skills": [
                # Communication
                "Communication", "Public Speaking", "Presentation", "Writing", "Technical Writing",
                "Active Listening", "Negotiation", "Persuasion", "Storytelling", "Facilitation",
                
                # Leadership & Management
                "Leadership", "Team Management", "Project Management", "Strategic Planning",
                "Delegation", "Coaching", "Mentoring", "Decision Making", "Change Management",
                "Performance Management", "Risk Management", "Conflict Resolution",
                
                # Interpersonal Skills
                "Teamwork", "Collaboration", "Emotional Intelligence", "Empathy", "Interpersonal Skills",
                "Relationship Building", "Cultural Awareness", "Diplomacy", "Customer Service",
                
                # Problem Solving
                "Problem Solving", "Critical Thinking", "Analytical Thinking", "Research",
                "Troubleshooting", "Creativity", "Innovation", "Design Thinking",
                
                # Organization
                "Time Management", "Organization", "Multitasking", "Prioritization",
                "Attention to Detail", "Planning", "Goal Setting", "Process Improvement",
                
                # Adaptability
                "Adaptability", "Flexibility", "Learning Agility", "Resilience", "Stress Management"
            ],
            
            "healthcare_skills": [
                "Patient Care", "Medical Terminology", "Electronic Health Records (EHR)",
                "Clinical Documentation", "HIPAA Compliance", "Medical Coding", "Vital Signs",
                "Infection Control", "Medication Administration", "Clinical Assessment",
                "Patient Education", "Care Coordination", "CPR", "First Aid", "Phlebotomy",
                "Telehealth", "Epic", "Cerner", "MEDITECH", "Allscripts"
            ],
            
            "finance_skills": [
                "Financial Analysis", "Financial Modeling", "Forecasting", "Budgeting",
                "Accounting", "Bookkeeping", "Financial Reporting", "Audit", "Tax Preparation",
                "Risk Assessment", "Compliance", "Banking", "Investment Management",
                "Portfolio Management", "Asset Management", "Bloomberg Terminal",
                "QuickBooks", "SAP Finance", "Oracle Financials", "NetSuite"
            ],
            
            "education_skills": [
                "Curriculum Development", "Instructional Design", "Lesson Planning",
                "Student Assessment", "Classroom Management", "Educational Technology",
                "Differentiated Instruction", "Special Education", "eLearning", "LMS",
                "Blackboard", "Canvas", "Moodle", "Google Classroom", "Student Engagement",
                "Educational Psychology", "Pedagogy", "IEP Development", "FERPA"
            ],
            
            "legal_skills": [
                "Legal Research", "Legal Writing", "Case Management", "Contract Drafting",
                "Contract Review", "Compliance", "Litigation", "Negotiation", "Due Diligence",
                "eDiscovery", "Westlaw", "LexisNexis", "Legal Ethics", "Client Counseling",
                "Regulatory Compliance", "Legal Analysis", "Intellectual Property"
            ],
            
            "marketing_skills": [
                "Digital Marketing", "Social Media Marketing", "SEO", "SEM", "Content Marketing",
                "Email Marketing", "Google Analytics", "Google Ads", "Facebook Ads", "Instagram Marketing",
                "LinkedIn Marketing", "Twitter Marketing", "TikTok Marketing", "Brand Management",
                "Market Research", "Competitor Analysis", "Customer Segmentation", "CRM",
                "HubSpot", "Salesforce Marketing Cloud", "Marketo", "MailChimp", "Hootsuite"
            ],
            
            "sales_skills": [
                "Lead Generation", "Prospecting", "Sales Funnel Management", "Closing Techniques",
                "Relationship Building", "Consultative Selling", "Solution Selling", "B2B Sales",
                "B2C Sales", "Enterprise Sales", "Upselling", "Cross-selling", "Customer Retention",
                "Account Management", "CRM", "Salesforce", "HubSpot CRM", "Pipedrive", "Sales Analytics"
            ]
        }
        
        # Try to load custom database if provided
        if custom_db_path and os.path.exists(custom_db_path):
            try:
                with open(custom_db_path, 'r') as f:
                    loaded_db = json.load(f)
                    logger.info(f"Loaded custom skill database from {custom_db_path}")
                    return loaded_db
            except Exception as e:
                logger.error(f"Error loading custom skill database: {str(e)}")
        
        # Return default database
        logger.info("Using default skill database")
        return default_db
    
    def is_known_skill(self, skill_name: str) -> bool:
        """
        Check if a skill name matches a known skill in the database
        
        Args:
            skill_name (str): Skill name to check
            
        Returns:
            bool: True if it's a known skill, False otherwise
        """
        return skill_name.lower() in self.skill_lookup
    
    def get_canonical_name(self, skill_name: str) -> str:
        """
        Get the canonical (properly capitalized) name of a skill
        
        Args:
            skill_name (str): Skill name to normalize
            
        Returns:
            str: Canonical skill name or the original if not found
        """
        return self.skill_lookup.get(skill_name.lower(), skill_name)
    
    def get_skill_category(self, skill_name: str) -> str:
        """
        Get the category a skill belongs to
        
        Args:
            skill_name (str): Skill name to check
            
        Returns:
            str: Category name ('technical', 'soft', domain name, or 'unknown')
        """
        canonical = self.get_canonical_name(skill_name)
        
        if canonical in self.technical_skills:
            return "technical"
        elif canonical in self.soft_skills:
            return "soft"
        else:
            # Check domain skills
            for domain, skills in self.domain_skills.items():
                if canonical in skills:
                    return domain
        
        return "unknown"
    
    def get_related_skills(self, skill_name: str, limit: int = 5) -> List[str]:
        """
        Get related skills for a given skill
        
        Args:
            skill_name (str): Skill to find related skills for
            limit (int): Maximum number of related skills to return
            
        Returns:
            list: List of related skills
        """
        canonical = self.get_canonical_name(skill_name)
        category = self.get_skill_category(canonical)
        
        related = []
        
        if category == "technical":
            # For technical skills, return other skills in the same tech stack
            tech_stacks = {
                "web_frontend": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "Angular", "Vue.js"],
                "web_backend": ["Node.js", "Express", "Django", "Flask", "Ruby on Rails", "Spring"],
                "data_science": ["Python", "R", "TensorFlow", "PyTorch", "Pandas", "NumPy"],
                "database": ["SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Oracle"],
                "cloud": ["AWS", "Azure", "Google Cloud", "Docker", "Kubernetes"],
                "mobile": ["Android", "iOS", "React Native", "Flutter", "Swift", "Kotlin"]
            }
            
            # Find which stack the skill belongs to
            for stack, stack_skills in tech_stacks.items():
                if canonical in stack_skills:
                    # Return other skills in the same stack
                    related = [skill for skill in stack_skills if skill != canonical]
                    break
        
        # If we don't have related skills yet, get skills from the same category
        if not related:
            if category == "technical":
                pool = self.technical_skills
            elif category == "soft":
                pool = self.soft_skills
            elif category in self.domain_skills:
                pool = self.domain_skills[category]
            else:
                pool = set()
            
            # Filter out the current skill and convert to list
            related = [skill for skill in pool if skill != canonical]
        
        # Limit the number of related skills
        return related[:limit] 