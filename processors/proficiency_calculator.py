import re
import logging
import math
import nltk  # Add explicit import for nltk
from collections import defaultdict
from nltk.tokenize import sent_tokenize
from models.skill import Skill

logger = logging.getLogger('proficiency_calculator')

class ProficiencyCalculator:
    """
    Calculate proficiency levels for skills based on academic research on skill acquisition
    and professional development frameworks.
    """
    
    def __init__(self):
        """Initialize the proficiency calculator with research-based indicators"""
        # Ensure NLTK data is downloaded
        try:
            nltk.data.find('tokenizers/punkt')
        except (LookupError, ImportError):
            try:
                nltk.download('punkt')
            except:
                logger.warning("NLTK download failed, continuing without sentence tokenization")
            
        # Proficiency levels based on Dreyfus & Dreyfus Model (1980, 1986)
        # and Bloom's Taxonomy of Educational Objectives (1956, revised 2001)
        self.proficiency_levels = [
            "Beginner",        # Novice level - rule-based behavior, limited situational perception
            "Intermediate",    # Advanced beginner - situational perception still limited
            "Advanced",        # Competent - sees actions as part of broader goals
            "Expert"           # Proficient/Expert - intuitive grasp of situations, analytical approaches
        ]
        
        # Keywords indicating different proficiency levels (based on research by Chi et al., 2014;
        # Ericsson et al., 1993; Simon & Chase, 1973 on expertise development)
        self.proficiency_indicators = {
            # Beginner level keywords (rule-following, assisted work)
            "Beginner": [
                "basic", "familiar", "learning", "entry-level", "fundamental", "coursework", 
                "introduction", "beginner", "novice", "studied", "exposure to", "classroom",
                "training", "guided", "assisted", "supervised", "academic", "course", "101",
                "recently", "new to"
            ],
            
            # Intermediate level keywords (independent work, practical experience)
            "Intermediate": [
                "applied", "practical", "experience", "implemented", "developed", "built",
                "created", "designed", "intermediate", "proficient", "competent", "functional",
                "working knowledge", "solid understanding", "hands-on", "1-3 years", "participated in",
                "contributed to", "team member", "handled", "responsible for", "managed", "maintained"
            ],
            
            # Advanced level keywords (mastery, leadership, complex problem solving)
            "Advanced": [
                "advanced", "extensive", "expert", "specialized", "in-depth", "thorough",
                "comprehensive", "mastery", "proficiency", "seasoned", "strong", "3-5 years",
                "led", "orchestrated", "architected", "complex", "mentor", "trained others",
                "significant", "major", "key contributor", "senior", "optimization", "innovative",
                "solutions"
            ],
            
            # Expert level keywords (thought leadership, innovation, strategic impact)
            "Expert": [
                "expert", "authority", "specialist", "thought leader", "5+ years", "deep expertise",
                "recognized", "acclaimed", "pioneered", "strategic", "outstanding", "exceptional",
                "cutting-edge", "industry leader", "speaker", "published", "researcher", "invented",
                "patent", "revolutionized", "transformed", "principal", "consultant", "advisor"
            ]
        }
        
        # Term complexity indicators based on Cognitive Complexity Framework (Bloom et al.)
        self.cognitive_indicators = {
            "Beginner": [
                "understand", "define", "describe", "identify", "list", "recognize", "recall",
                "memorize", "observe", "know", "label", "follow", "assist", "watch"
            ],
            
            "Intermediate": [
                "apply", "implement", "use", "demonstrate", "operate", "solve", "calculate",
                "illustrate", "modify", "perform", "prepare", "produce", "translate"
            ],
            
            "Advanced": [
                "analyze", "compare", "contrast", "differentiate", "examine", "test", "investigate",
                "categorize", "critique", "diagnose", "integrate", "organize", "plan", "design"
            ],
            
            "Expert": [
                "evaluate", "assess", "appraise", "conclude", "convince", "judge", "recommend",
                "create", "develop", "invent", "construct", "formulate", "author", "innovate",
                "theorize", "synthesize", "generate", "predict", "propose", "devise"
            ]
        }
        
        # Duration indicators based on research on skill acquisition times
        # (Ericsson's 10,000 hour rule, Simon & Chase chess expertise studies)
        self.duration_indicators = {
            "Beginner": [
                r"(?<!\d)(\d{1,2})\s*(?:day|week|month)s?",
                r"less than (?:a|one|1)\s*year",
                r"recently",
                r"(?<!\d)1\s*year"
            ],
            
            "Intermediate": [
                r"(?<!\d)([1-3])\s*years?",
                r"(?:a|one|1)\s*year",
                r"couple\s*(?:of)?\s*years"
            ],
            
            "Advanced": [
                r"(?<!\d)([3-5])\s*years?",
                r"several\s*years",
                r"extensive experience"
            ],
            
            "Expert": [
                r"(?<!\d)([5-9]|1\d+)\s*years?",
                r"(?<!\d)\d{2,}\s*years?",
                r"over (?:a|one)?\s*decade",
                r"decades of",
                r"(?:long|extensive)\s*(?:career|history|background)"
            ]
        }
        
        # Project scale indicators based on project complexity research (Xia & Lee, 2005)
        self.project_scale_indicators = {
            "Beginner": [
                "small", "minor", "simple", "basic", "single", "individual", "personal"
            ],
            
            "Intermediate": [
                "moderate", "team", "project", "component", "module", "feature"
            ],
            
            "Advanced": [
                "large", "complex", "significant", "major", "system", "platform", "product",
                "enterprise", "organization", "department"
            ],
            
            "Expert": [
                "enterprise-wide", "cross-organizational", "industry", "global", "international",
                "multi-system", "critical", "strategic", "nationwide", "worldwide"
            ]
        }
        
        # Responsibility level indicators (based on Jaques' Levels of Work complexity)
        self.responsibility_indicators = {
            "Beginner": [
                "assisted", "helped", "supported", "followed", "performed", "conducted",
                "observed", "shadowed", "participated"
            ],
            
            "Intermediate": [
                "contributed", "implemented", "executed", "handled", "coordinated", "developed",
                "managed", "responsible for"
            ],
            
            "Advanced": [
                "led", "designed", "architected", "directed", "orchestrated", "supervised",
                "guided", "oversaw", "mentored", "headed", "spearheaded"
            ],
            
            "Expert": [
                "chief", "principal", "head", "executive", "founder", "creator", "pioneered",
                "established", "strategized", "transformed", "revolutionized", "keynote"
            ]
        }
        
        # Certification level indicators
        self.certification_indicators = {
            "Beginner": [
                "fundamentals", "foundations", "associate", "entry", "basic", "introduction"
            ],
            
            "Intermediate": [
                "practitioner", "professional", "regular", "standard", "applied", "certified"
            ],
            
            "Advanced": [
                "advanced", "expert", "senior", "specialist", "professional", "architect"
            ],
            
            "Expert": [
                "master", "distinguished", "elite", "principal", "fellow", "authority",
                "subject matter expert", "distinguished"
            ]
        }
        
        # Weights for different types of evidence
        # Based on research by Schmidt & Hunter (1998) on the validity of different selection methods
        self.evidence_weights = {
            "duration": 0.25,        # Schmidt & Hunter found work experience duration has 0.18 validity
            "keywords": 0.15,        # General term matches 
            "cognitive": 0.20,       # Cognitive complexity has higher validity
            "projects": 0.20,        # Project work has 0.35 validity in Schmidt & Hunter
            "responsibility": 0.25,  # Level of responsibility/work samples have 0.54 validity
            "certification": 0.10    # Certifications/training has 0.10 validity
        }
        
        # Source literature for the proficiency assessment methodology
        self.literature_sources = [
            {
                "title": "The Cambridge Handbook of Expertise and Expert Performance",
                "authors": "Ericsson, K. A., Hoffman, R. R., Kozbelt, A., & Williams, A. M. (Eds.)",
                "year": 2018,
                "publisher": "Cambridge University Press",
                "citation": "Establishes the 'deliberate practice' framework and outlines how expertise develops across domains."
            },
            {
                "title": "Mind over Machine: The Power of Human Intuition and Expertise in the Era of the Computer",
                "authors": "Dreyfus, H. L., & Dreyfus, S. E.",
                "year": 1986,
                "publisher": "The Free Press",
                "citation": "Proposed the influential five-stage model of skill acquisition from novice to expert."
            },
            {
                "title": "A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives",
                "authors": "Anderson, L. W., Krathwohl, D. R., & Bloom, B. S.",
                "year": 2001,
                "publisher": "Longman",
                "citation": "Presents the revised Bloom's taxonomy, showing progression from knowledge to creation."
            },
            {
                "title": "The validity and utility of selection methods in personnel psychology: Practical and theoretical implications of 85 years of research findings",
                "authors": "Schmidt, F. L., & Hunter, J. E.",
                "year": 1998,
                "journal": "Psychological Bulletin, 124(2), 262-274",
                "citation": "Meta-analysis showing the predictive validity of different assessment methods for job performance."
            },
            {
                "title": "The Role of Deliberate Practice in the Acquisition of Expert Performance",
                "authors": "Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C.",
                "year": 1993,
                "journal": "Psychological Review, 100(3), 363-406",
                "citation": "Pioneering study on the role of deliberate practice in developing expertise."
            },
            {
                "title": "Acquisition of chess skill",
                "authors": "Simon, H. A., & Chase, W. G.",
                "year": 1973,
                "journal": "American Scientist, 61(4), 394-403",
                "citation": "Classic study on expertise development through structured knowledge in chess."
            }
        ]
        
    def calculate_proficiency(self, skill_name, context):
        """
        Calculate proficiency level for a skill based on the context in which it appears.
        
        Args:
            skill_name (str): The name of the skill
            context (str): The context in which the skill appears
            
        Returns:
            tuple: (proficiency_level, confidence_score)
        """
        if not context:
            return None, 0.0
            
        context = context.lower()
        skill_name = skill_name.lower()
        
        # Evidence collection based on different types of indicators
        evidence = {
            "duration": self._extract_duration_evidence(context),
            "keywords": self._extract_keyword_evidence(context),
            "cognitive": self._extract_cognitive_evidence(context),
            "projects": self._extract_project_evidence(context),
            "responsibility": self._extract_responsibility_evidence(context),
            "certification": self._extract_certification_evidence(context, skill_name)
        }
        
        # Calculate weighted scores for each proficiency level
        level_scores = defaultdict(float)
        
        for evidence_type, evidence_data in evidence.items():
            weight = self.evidence_weights.get(evidence_type, 0.1)
            
            for level, score in evidence_data.items():
                level_scores[level] += score * weight
        
        # Handle case with no evidence
        if not level_scores:
            return None, 0.0
            
        # Find the proficiency level with the highest score
        total_score = sum(level_scores.values())
        if total_score == 0:
            return None, 0.0
            
        # Normalize the scores
        normalized_scores = {level: score/total_score for level, score in level_scores.items()}
        
        # Find the level with the highest normalized score
        best_level = max(normalized_scores.items(), key=lambda x: x[1])
        proficiency_level = best_level[0]
        confidence = best_level[1]
        
        return proficiency_level, confidence
    
    def _extract_duration_evidence(self, context):
        """Extract evidence related to duration of experience"""
        evidence = defaultdict(float)
        
        for level, patterns in self.duration_indicators.items():
            for pattern in patterns:
                matches = re.findall(pattern, context, re.IGNORECASE)
                if matches:
                    # If we find numeric matches, use them to strengthen the evidence
                    for match in matches:
                        if isinstance(match, tuple) and len(match) > 0 and match[0].isdigit():
                            # Extract the numeric value
                            value = int(match[0])
                            evidence[level] += value * 0.1  # More years = stronger evidence
                        else:
                            evidence[level] += 1.0
        
        return evidence
    
    def _extract_keyword_evidence(self, context):
        """Extract evidence related to general proficiency keywords"""
        evidence = defaultdict(float)
        
        words = re.findall(r'\b\w+\b', context.lower())
        words_set = set(words)
        
        for level, keywords in self.proficiency_indicators.items():
            for keyword in keywords:
                if keyword.lower() in context.lower():
                    # For multi-word indicators, give more weight
                    if len(keyword.split()) > 1:
                        evidence[level] += 1.5
                    else:
                        evidence[level] += 1.0
        
        return evidence
    
    def _extract_cognitive_evidence(self, context):
        """Extract evidence related to cognitive complexity"""
        evidence = defaultdict(float)
        
        for level, verbs in self.cognitive_indicators.items():
            for verb in verbs:
                # Look for these verbs as full words
                matches = re.findall(r'\b' + re.escape(verb) + r'\b', context.lower())
                # Give stronger weight to cognitive indicators
                evidence[level] += len(matches) * 1.2
        
        return evidence
    
    def _extract_project_evidence(self, context):
        """Extract evidence related to project scale"""
        evidence = defaultdict(float)
        
        for level, indicators in self.project_scale_indicators.items():
            for indicator in indicators:
                matches = re.findall(r'\b' + re.escape(indicator) + r'\b', context.lower())
                evidence[level] += len(matches) * 1.0
        
        return evidence
    
    def _extract_responsibility_evidence(self, context):
        """Extract evidence related to level of responsibility"""
        evidence = defaultdict(float)
        
        for level, indicators in self.responsibility_indicators.items():
            for indicator in indicators:
                matches = re.findall(r'\b' + re.escape(indicator) + r'\b', context.lower())
                # Responsibility has high validity, so give it more weight
                evidence[level] += len(matches) * 1.3
        
        return evidence
    
    def _extract_certification_evidence(self, context, skill_name):
        """Extract evidence related to certifications"""
        evidence = defaultdict(float)
        
        # Check if the context indicates certification in this skill
        contains_cert = any(term in context.lower() for term in [
            "certification", "certificate", "certified", "credential", "qualification", 
            "diploma", "degree", "license"
        ])
        
        if contains_cert and skill_name in context.lower():
            # If certification is mentioned with the skill, check the level
            for level, indicators in self.certification_indicators.items():
                for indicator in indicators:
                    if indicator.lower() in context.lower():
                        evidence[level] += 1.0
                        
            # If no specific level is detected but certification exists, default to intermediate
            if sum(evidence.values()) == 0:
                evidence["Intermediate"] += 0.8
        
        return evidence
    
    def get_literature_sources(self):
        """Return the literature sources used for proficiency assessment methodology"""
        return self.literature_sources
    
    def explain_proficiency_assessment(self, skill_name, context, proficiency_level, confidence):
        """
        Provide an explanation of the proficiency assessment with literature references.
        
        Args:
            skill_name (str): The name of the skill
            context (str): The context in which the skill appears
            proficiency_level (str): The assessed proficiency level
            confidence (float): Confidence score for the assessment
            
        Returns:
            dict: Explanation of the assessment with literature backing
        """
        explanation = {
            "skill": skill_name,
            "proficiency_level": proficiency_level,
            "confidence_score": confidence,
            "assessment_framework": "Multi-dimensional expertise assessment based on the Dreyfus & Dreyfus (1986) model of skill acquisition and Bloom's Taxonomy (2001)",
            "key_indicators": [],
            "literature_foundation": []
        }
        
        # Extract key indicators that contributed to this assessment
        evidence = {
            "duration": self._extract_duration_evidence(context),
            "keywords": self._extract_keyword_evidence(context),
            "cognitive": self._extract_cognitive_evidence(context),
            "projects": self._extract_project_evidence(context),
            "responsibility": self._extract_responsibility_evidence(context),
            "certification": self._extract_certification_evidence(context, skill_name)
        }
        
        # Identify top indicators for this proficiency level
        if proficiency_level:
            for evidence_type, scores in evidence.items():
                if proficiency_level in scores and scores[proficiency_level] > 0:
                    if evidence_type == "duration":
                        explanation["key_indicators"].append({
                            "type": "Experience Duration",
                            "assessment": f"Duration indicators suggest {proficiency_level.lower()} level experience",
                            "research_basis": "Based on Ericsson et al.'s (1993) deliberate practice research"
                        })
                    elif evidence_type == "keywords":
                        explanation["key_indicators"].append({
                            "type": "Proficiency Terms",
                            "assessment": f"Language used indicates {proficiency_level.lower()} level knowledge",
                            "research_basis": "Based on Chi et al.'s (2014) expertise discourse analysis"
                        })
                    elif evidence_type == "cognitive":
                        explanation["key_indicators"].append({
                            "type": "Cognitive Complexity",
                            "assessment": f"Demonstrates {proficiency_level.lower()} level cognitive engagement",
                            "research_basis": "Based on Anderson & Krathwohl's revised Bloom's Taxonomy (2001)"
                        })
                    elif evidence_type == "projects":
                        explanation["key_indicators"].append({
                            "type": "Project Scope",
                            "assessment": f"Project scale indicates {proficiency_level.lower()} level application",
                            "research_basis": "Based on Xia & Lee's (2005) project complexity framework"
                        })
                    elif evidence_type == "responsibility":
                        explanation["key_indicators"].append({
                            "type": "Role Responsibility",
                            "assessment": f"Responsibility level matches {proficiency_level.lower()} expertise",
                            "research_basis": "Based on Jaques' Stratified Systems Theory of levels of work"
                        })
                    elif evidence_type == "certification":
                        explanation["key_indicators"].append({
                            "type": "Certifications",
                            "assessment": f"Certification suggests {proficiency_level.lower()} level competence",
                            "research_basis": "Based on Schmidt & Hunter's (1998) validity of credentials"
                        })
        
        # Add most relevant literature references
        if proficiency_level == "Beginner":
            explanation["literature_foundation"] = [
                self.literature_sources[1],  # Dreyfus model
                self.literature_sources[2]   # Bloom's taxonomy
            ]
        elif proficiency_level == "Intermediate":
            explanation["literature_foundation"] = [
                self.literature_sources[5],  # Simon & Chase
                self.literature_sources[3]   # Schmidt & Hunter
            ]
        elif proficiency_level == "Advanced":
            explanation["literature_foundation"] = [
                self.literature_sources[4],  # Ericsson
                self.literature_sources[1]   # Dreyfus model
            ]
        elif proficiency_level == "Expert":
            explanation["literature_foundation"] = [
                self.literature_sources[0],  # Cambridge handbook
                self.literature_sources[4]   # Ericsson
            ]
        else:
            # Default references
            explanation["literature_foundation"] = [
                self.literature_sources[0],
                self.literature_sources[1]
            ]
            
        return explanation

    def calculate_proficiencies_for_skills(self, skills, text):
        """
        Calculate proficiency levels for a list of skills
        
        Args:
            skills (list): List of Skill objects
            text (str): The text to analyze
            
        Returns:
            list: List of updated Skill objects with proficiency levels
        """
        updated_skills = []
        
        for skill in skills:
            proficiency, confidence = self.calculate_proficiency(skill.name, text)
            
            if proficiency:
                skill.proficiency = proficiency
                
                # Adjust confidence if it's higher than the current one
                if confidence > skill.confidence_score:
                    skill.adjust_confidence(confidence)
            else:
                # If no specific proficiency found, set a default based on confidence score
                if skill.confidence_score > 0.7:
                    skill.proficiency = "Intermediate"
                elif skill.confidence_score > 0.5:
                    skill.proficiency = "Beginner"
                elif skill.is_backed:
                    # If the skill is backed by a certification, at least Intermediate
                    skill.proficiency = "Intermediate"
                else:
                    skill.proficiency = "Beginner"
                    
            updated_skills.append(skill)
            
        return updated_skills 