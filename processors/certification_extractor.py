import json
import re
import os
import logging
from datetime import datetime
import spacy

try:
    # Try loading the language model for NER
    nlp = spacy.load("en_core_web_md")
except OSError:
    # Fall back to a simpler model if the larger one isn't available
    nlp = spacy.load("en_core_web_sm")
    
logger = logging.getLogger('certification_extractor')

class CertificationExtractor:
    """
    Certification extractor that works with structured document formats
    for more accurate certification identification
    """
    
    def __init__(self, certifications_db_path=None):
        """
        Initialize the certification extractor
        
        Args:
            certifications_db_path (str, optional): Path to custom certifications database JSON file
        """
        self.cert_data = self._load_cert_data(certifications_db_path)
        self.known_certifications = self.cert_data.get("certifications", [])
        self.certification_providers = self.cert_data.get("providers", [])
        
        # Common certification patterns and variations
        self.cert_patterns = self._compile_cert_patterns()
        self.skill_to_cert_map = self._build_skill_cert_map()
        
    def _load_cert_data(self, certifications_db_path):
        """
        Load certification data from a JSON file
        
        Args:
            certifications_db_path (str, optional): Path to certifications database JSON file
            
        Returns:
            dict: Certification data
        """
        default_db = {
            "certifications": [
                "AWS Certified Solutions Architect",
                "AWS Certified Developer",
                "AWS Certified SysOps Administrator",
                "Microsoft Certified: Azure Administrator",
                "Microsoft Certified: Azure Developer",
                "Microsoft Certified: Azure Solutions Architect",
                "Google Cloud Professional Cloud Architect",
                "Google Cloud Professional Data Engineer",
                "Cisco Certified Network Associate (CCNA)",
                "Cisco Certified Network Professional (CCNP)",
                "CompTIA A+",
                "CompTIA Network+",
                "CompTIA Security+",
                "Certified Information Systems Security Professional (CISSP)",
                "Project Management Professional (PMP)",
                "Certified ScrumMaster (CSM)",
                "Professional Scrum Master (PSM)",
                "Oracle Certified Associate (OCA)",
                "Oracle Certified Professional (OCP)",
                "MySQL Certified Developer",
                "MongoDB Certified Developer",
                "Certified Kubernetes Administrator (CKA)",
                "Certified Kubernetes Application Developer (CKAD)",
                "Certified Ethical Hacker (CEH)",
                "Offensive Security Certified Professional (OSCP)",
                "Salesforce Certified Administrator",
                "Salesforce Certified Developer",
                "Certified Information Security Manager (CISM)",
                "ITIL Foundation",
                "TOGAF Certified"
            ],
            "providers": [
                "AWS",
                "Microsoft",
                "Google Cloud",
                "Cisco",
                "CompTIA",
                "PMI",
                "Scrum Alliance",
                "Scrum.org",
                "Oracle",
                "MySQL",
                "MongoDB",
                "Linux Foundation",
                "EC-Council",
                "Offensive Security",
                "Salesforce",
                "ISACA",
                "Axelos",
                "The Open Group"
            ]
        }
        
        if not certifications_db_path or not os.path.exists(certifications_db_path):
            logger.warning("Certifications database not provided or not found. Using default certifications list.")
            return default_db
            
        try:
            with open(certifications_db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading certifications database: {str(e)}")
            return default_db
            
    def _compile_cert_patterns(self):
        """
        Compile patterns for certification detection
        
        Returns:
            list: List of compiled patterns
        """
        patterns = []
        
        # Pattern for certification statements
        patterns.append(re.compile(r'(certified|certificate|certification|qualified|diploma)\s+(?:in|for|as)?\s+([^.,:;]+)', re.IGNORECASE))
        
        # Pattern for provider-specific certifications
        for provider in self.certification_providers:
            patterns.append(re.compile(fr'{re.escape(provider)}\s+(certified|certificate|certification)\s+([^.,:;]+)', re.IGNORECASE))
            patterns.append(re.compile(fr'{re.escape(provider)}[:\s]+([^.,:;]+)\s+(certified|certificate|certification)', re.IGNORECASE))
        
        # Pattern for certificate numbers/IDs
        patterns.append(re.compile(r'(certificate|certification|credential)\s+(id|number)[:\s]*([A-Za-z0-9\-]+)', re.IGNORECASE))
        
        # Pattern for issue dates
        patterns.append(re.compile(r'(issued|issued on|date issued|issue date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})', re.IGNORECASE))
        
        return patterns
        
    def _build_skill_cert_map(self):
        """
        Build a mapping of skills to related certifications
        
        Returns:
            dict: Mapping of skills to certifications
        """
        skill_cert_map = {
            "aws": ["AWS Certified", "Amazon Web Services"],
            "azure": ["Microsoft Certified: Azure", "Azure"],
            "google cloud": ["Google Cloud Professional", "GCP"],
            "python": ["Python Developer", "Python Programming"],
            "java": ["Java Developer", "Java Certified", "Oracle Certified"],
            "javascript": ["JavaScript Developer", "Web Development"],
            "sql": ["SQL Developer", "Database", "Oracle", "MySQL", "PostgreSQL"],
            "security": ["Security+", "CISSP", "CEH", "Cybersecurity"],
            "networking": ["CCNA", "CCNP", "Network+"],
            "scrum": ["ScrumMaster", "Agile", "Scrum"],
            "kubernetes": ["CKA", "CKAD", "Kubernetes"],
            "docker": ["Docker", "Container", "Kubernetes"],
            "devops": ["DevOps", "CI/CD", "Jenkins", "GitLab"]
        }
        
        return skill_cert_map
        
    def extract_certifications(self, structured_doc):
        """
        Extract certifications from a structured document
        
        Args:
            structured_doc (dict): Structured document representation
            
        Returns:
            list: List of extracted certifications
        """
        extracted_certs = []
        
        # Process based on document type
        doc_type = structured_doc.get("document_type", "unknown")
        
        # Certification documents should be handled differently
        if doc_type == "certification":
            return self._extract_from_certification_doc(structured_doc)
            
        # For resume documents, check specific sections
        if "sections" in structured_doc:
            sections = structured_doc["sections"]
            
            # Check certification sections first
            if "certifications" in sections:
                cert_lines = sections["certifications"]
                cert_section_certs = self._extract_from_lines(cert_lines, "certifications_section")
                extracted_certs.extend(cert_section_certs)
                
            # Also check education sections
            if "education" in sections:
                education_lines = sections["education"]
                education_certs = self._extract_from_lines(education_lines, "education_section")
                extracted_certs.extend(education_certs)
        
        # For PDF documents, check layout-based information
        if "pages" in structured_doc:
            for page in structured_doc["pages"]:
                # Check for certification mentions in headings
                if "structure" in structured_doc and "headings" in structured_doc["structure"]:
                    for heading in structured_doc["structure"]["headings"]:
                        if heading["page"] == page["number"]:
                            heading_text = heading["text"]
                            if "certif" in heading_text.lower() or "credential" in heading_text.lower():
                                # Extract certifications from the heading and nearby content
                                page_text = page["text"]
                                heading_certs = self._extract_from_text(page_text, "heading_context")
                                extracted_certs.extend(heading_certs)
        
        # Use raw text as fallback
        if "raw_text" in structured_doc:
            raw_text_certs = self._extract_from_text(structured_doc["raw_text"], "raw_text")
            extracted_certs.extend(raw_text_certs)
        
        # Use metadata from document filename
        if "metadata" in structured_doc and "filename" in structured_doc["metadata"]:
            filename = structured_doc["metadata"]["filename"]
            if "certification" in filename.lower() or "certificate" in filename.lower() or "credential" in filename.lower():
                # Try to extract certification name from filename
                filename_no_ext = os.path.splitext(filename)[0]
                name_parts = re.split(r'[-_\s]', filename_no_ext)
                
                for provider in self.certification_providers:
                    if provider.lower() in [part.lower() for part in name_parts]:
                        # Found a provider name in the filename
                        extracted_certs.append({
                            "name": filename_no_ext.replace('_', ' ').replace('-', ' '),
                            "confidence": 0.8,
                            "provider": provider,
                            "source": "filename",
                            "metadata": {
                                "extracted_from": "filename"
                            }
                        })
        
        # Deduplicate certifications
        deduplicated_certs = self._deduplicate_certifications(extracted_certs)
        
        return deduplicated_certs
        
    def _extract_from_certification_doc(self, structured_doc):
        """
        Extract certification details from a certification document
        
        Args:
            structured_doc (dict): Structured document representation
            
        Returns:
            list: List of certification details
        """
        certifications = []
        
        # Metadata already contains a lot of useful information
        metadata = structured_doc.get("metadata", {})
        filename = metadata.get("filename", "")
        
        # Prepare certificate information
        cert_info = {
            "name": "",
            "confidence": 0.9,  # High confidence for dedicated cert docs
            "source": "certification_document",
            "metadata": {
                "extracted_from": "certification_document",
                "filename": filename
            }
        }
        
        # Try to extract from document title or headings first
        if "structure" in structured_doc and "title" in structured_doc["structure"]:
            title = structured_doc["structure"]["title"]
            if title:
                cert_info["name"] = title
                
        # If no title, try to extract from raw text
        if not cert_info["name"] and "raw_text" in structured_doc:
            raw_text = structured_doc["raw_text"]
            
            # Look for certificate name patterns
            name_patterns = [
                r'certificate\s+(?:of|in|for)\s+([^.,:;]+)',
                r'certification\s+(?:of|in|for)\s+([^.,:;]+)',
                r'certified\s+(?:as|in)\s+([^.,:;]+)',
                r'this certifies that.*completed\s+([^.,:;]+)',
                r'successfully completed\s+([^.,:;]+)'
            ]
            
            for pattern in name_patterns:
                matches = re.search(pattern, raw_text, re.IGNORECASE)
                if matches:
                    cert_info["name"] = matches.group(1).strip()
                    break
                    
        # If still no name, use filename
        if not cert_info["name"]:
            # Clean up filename to create a reasonable cert name
            clean_name = os.path.splitext(filename)[0]
            clean_name = clean_name.replace('_', ' ').replace('-', ' ')
            clean_name = re.sub(r'\s+', ' ', clean_name).strip()
            
            # Check if it has typical certification terms
            if not any(term in clean_name.lower() for term in ['certificate', 'certification', 'credential']):
                clean_name += " Certificate"
                
            cert_info["name"] = clean_name
            
        # Extract additional metadata
        if "raw_text" in structured_doc:
            raw_text = structured_doc["raw_text"]
            
            # Look for dates
            date_patterns = [
                r'(?:issue|issuance|issued|completion)\s+date\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'date\s+(?:issued|of issuance|of completion)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(?:valid|issued)\s+(?:from|on)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})'
            ]
            
            for pattern in date_patterns:
                matches = re.search(pattern, raw_text, re.IGNORECASE)
                if matches:
                    cert_info["metadata"]["issue_date"] = matches.group(1)
                    break
                    
            # Look for credential ID
            id_patterns = [
                r'(?:credential|certificate|certification)\s+(?:id|number)\s*[:\-]?\s*([A-Za-z0-9\-]+)',
                r'(?:id|number)\s*[:\-]?\s*([A-Za-z0-9\-]+)',
                r'verification\s+code\s*[:\-]?\s*([A-Za-z0-9\-]+)'
            ]
            
            for pattern in id_patterns:
                matches = re.search(pattern, raw_text, re.IGNORECASE)
                if matches:
                    cert_info["metadata"]["credential_id"] = matches.group(1)
                    break
                    
            # Look for issuing organization
            org_patterns = [
                r'(?:issued|provided|authorized)\s+by\s+([^.,:;]+)',
                r'(?:issuing|certifying)\s+(?:organization|authority|body)\s*[:\-]?\s*([^.,:;]+)',
                r'([^.,:;]+)\s+(?:certifies|hereby certifies|confirms)'
            ]
            
            for pattern in org_patterns:
                matches = re.search(pattern, raw_text, re.IGNORECASE)
                if matches:
                    cert_info["metadata"]["issuing_organization"] = matches.group(1).strip()
                    break
        
        # Add to results
        certifications.append(cert_info)
        
        return certifications
        
    def _extract_from_lines(self, lines, source):
        """
        Extract certifications from a list of text lines
        
        Args:
            lines (list): List of text lines
            source (str): Source section name
            
        Returns:
            list: Extracted certifications
        """
        extracted_certs = []
        
        for line in lines:
            # Clean the line
            clean_line = line.strip()
            if not clean_line:
                continue
                
            # Check for known certifications
            for cert in self.known_certifications:
                if cert.lower() in clean_line.lower():
                    # Found a known certification
                    extracted_certs.append({
                        "name": cert,
                        "confidence": 0.9,  # High confidence for known certs
                        "source": source,
                        "metadata": {
                            "extracted_from": source,
                            "context": clean_line
                        }
                    })
                    continue
                    
            # Check for certification patterns
            for pattern in self.cert_patterns:
                matches = pattern.search(clean_line)
                if matches:
                    groups = matches.groups()
                    
                    if len(groups) >= 2:
                        # Handle certification statements
                        if groups[0].lower() in ['certified', 'certificate', 'certification', 'qualified', 'diploma']:
                            cert_name = groups[1].strip()
                            
                            # Clean up the certification name
                            cert_name = re.sub(r'\s+', ' ', cert_name)
                            cert_name = cert_name.strip()
                            
                            if cert_name:
                                extracted_certs.append({
                                    "name": cert_name,
                                    "confidence": 0.8,
                                    "source": source,
                                    "metadata": {
                                        "extracted_from": source,
                                        "pattern_matched": "certification_statement",
                                        "context": clean_line
                                    }
                                })
                                
                    elif len(groups) >= 1:
                        # Handle certification ID patterns
                        if "id" in clean_line.lower() or "number" in clean_line.lower():
                            # This is likely a credential ID, look for the cert name nearby
                            cert_name = self._extract_cert_name_from_context(clean_line)
                            if cert_name:
                                extracted_certs.append({
                                    "name": cert_name,
                                    "confidence": 0.7,
                                    "source": source,
                                    "metadata": {
                                        "extracted_from": source,
                                        "credential_id": groups[0],
                                        "context": clean_line
                                    }
                                })
        
        return extracted_certs
        
    def _extract_from_text(self, text, source):
        """
        Extract certifications from text
        
        Args:
            text (str): Text to analyze
            source (str): Source name
            
        Returns:
            list: Extracted certifications
        """
        extracted_certs = []
        
        # Skip if text is empty
        if not text or not text.strip():
            return extracted_certs
            
        # Process with spaCy for context-aware extraction
        doc = nlp(text)
        
        # Look for sentences containing certification keywords
        cert_keywords = ["certified", "certification", "certificate", "credential", "qualified", "diploma"]
        
        for sent in doc.sents:
            sent_text = sent.text.lower()
            
            # Skip if sentence doesn't contain certification keywords
            if not any(keyword in sent_text for keyword in cert_keywords):
                continue
                
            # Check for known certifications
            for cert in self.known_certifications:
                if cert.lower() in sent_text:
                    # Found a known certification
                    extracted_certs.append({
                        "name": cert,
                        "confidence": 0.85,
                        "source": source,
                        "metadata": {
                            "extracted_from": source,
                            "context": sent.text
                        }
                    })
                    continue
                    
            # Check for certification patterns
            for pattern in self.cert_patterns:
                matches = pattern.search(sent.text)
                if matches:
                    groups = matches.groups()
                    
                    if len(groups) >= 2:
                        # Handle certification statements
                        if groups[0].lower() in ['certified', 'certificate', 'certification', 'qualified', 'diploma']:
                            cert_name = groups[1].strip()
                            
                            # Clean up the certification name
                            cert_name = re.sub(r'\s+', ' ', cert_name)
                            cert_name = cert_name.strip()
                            
                            if cert_name:
                                extracted_certs.append({
                                    "name": cert_name,
                                    "confidence": 0.75,
                                    "source": source,
                                    "metadata": {
                                        "extracted_from": source,
                                        "pattern_matched": "certification_statement",
                                        "context": sent.text
                                    }
                                })
        
        return extracted_certs
        
    def _extract_cert_name_from_context(self, context):
        """
        Extract certification name from context
        
        Args:
            context (str): Context text
            
        Returns:
            str or None: Extracted certification name or None
        """
        # Process with spaCy
        doc = nlp(context)
        
        # Look for noun phrases that might be certification names
        for chunk in doc.noun_chunks:
            # Skip short chunks
            if len(chunk.text) < 3:
                continue
                
            # Check if chunk contains certification keywords
            chunk_text = chunk.text.lower()
            if any(keyword in chunk_text for keyword in ['certification', 'certificate', 'certified', 'credential']):
                # Clean up the chunk text
                clean_chunk = re.sub(r'\s+', ' ', chunk.text)
                clean_chunk = clean_chunk.strip()
                
                return clean_chunk
                
        # No suitable certification name found
        return None
        
    def _deduplicate_certifications(self, certifications):
        """
        Deduplicate certifications while preserving the highest confidence and metadata
        
        Args:
            certifications (list): List of certification dictionaries
            
        Returns:
            list: Deduplicated certifications
        """
        cert_map = {}
        
        for cert in certifications:
            cert_name = cert["name"].lower()
            confidence = cert["confidence"]
            
            if cert_name not in cert_map or confidence > cert_map[cert_name]["confidence"]:
                # Create a clean copy with the original name (not lowercase)
                cert_map[cert_name] = {
                    "name": cert["name"],  # Keep original capitalization
                    "confidence": confidence,
                    "source": cert["source"],
                    "metadata": cert.get("metadata", {})
                }
                
                # Copy other fields if present
                if "provider" in cert:
                    cert_map[cert_name]["provider"] = cert["provider"]
                    
        return list(cert_map.values())
        
    def link_skills_to_certifications(self, skills, certifications):
        """
        Link skills to related certifications
        
        Args:
            skills (list): List of skill dictionaries
            certifications (list): List of certification dictionaries
            
        Returns:
            list: Updated skill dictionaries with certification links
        """
        updated_skills = []
        
        for skill in skills:
            skill_name = skill["name"].lower()
            skill_linked = False
            
            # Check if the skill matches any certification directly
            for cert in certifications:
                cert_name = cert["name"].lower()
                
                # Check if skill name is in certification name
                if skill_name in cert_name:
                    updated_skill = skill.copy()
                    updated_skill["is_backed"] = True
                    updated_skill["backing_certificate"] = cert["name"]
                    updated_skill["confidence_score"] = max(skill["confidence_score"], 0.8)  # Increase confidence
                    updated_skills.append(updated_skill)
                    skill_linked = True
                    break
                    
            # Check skill-cert map if not directly linked
            if not skill_linked:
                for skill_key, cert_patterns in self.skill_cert_map.items():
                    if skill_key in skill_name or skill_name in skill_key:
                        # Find matching certifications
                        for cert in certifications:
                            cert_name = cert["name"].lower()
                            
                            if any(pattern.lower() in cert_name for pattern in cert_patterns):
                                updated_skill = skill.copy()
                                updated_skill["is_backed"] = True
                                updated_skill["backing_certificate"] = cert["name"]
                                updated_skill["confidence_score"] = max(skill["confidence_score"], 0.75)  # Increase confidence
                                updated_skills.append(updated_skill)
                                skill_linked = True
                                break
                                
                    if skill_linked:
                        break
                        
            # Keep original skill if not linked
            if not skill_linked:
                updated_skills.append(skill)
                
        return updated_skills 