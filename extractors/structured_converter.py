import json
import re
import os
import cv2
import pytesseract
import pdfplumber
from collections import defaultdict

class StructuredFormatConverter:
    """
    Converts PDF and image documents to a structured format (JSON)
    that preserves layout and identifies document sections
    """
    
    def __init__(self, tesseract_cmd=None):
        """
        Initialize the converter
        
        Args:
            tesseract_cmd (str, optional): Path to tesseract executable
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Common section headers in resumes and certifications
        self.section_keywords = {
            "skills": [
                "skills", "technical skills", "core competencies", "key skills",
                "professional skills", "areas of expertise", "technologies"
            ],
            "certifications": [
                "certifications", "certificates", "professional certifications",
                "credentials", "qualifications", "professional development"
            ],
            "education": [
                "education", "academic background", "academic qualifications",
                "educational background", "academic credentials"
            ],
            "experience": [
                "experience", "work experience", "professional experience",
                "employment history", "job history", "work history"
            ],
            "projects": [
                "projects", "project experience", "relevant projects",
                "key projects", "personal projects"
            ],
            "summary": [
                "summary", "professional summary", "career summary",
                "executive summary", "profile", "overview"
            ]
        }
        
    def convert(self, file_path):
        """
        Convert a file to structured format
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            dict: Structured representation of the document
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
            
        file_extension = os.path.splitext(file_path.lower())[1]
        
        if file_extension == '.pdf':
            return self._convert_pdf(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            return self._convert_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _convert_pdf(self, file_path):
        """
        Convert a PDF to structured format
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            dict: Structured representation of the document
        """
        # Initialize the result structure
        result = {
            "document_type": self._detect_document_type(file_path),
            "metadata": {
                "filename": os.path.basename(file_path),
                "file_type": "pdf"
            },
            "raw_text": "",
            "sections": defaultdict(list),
            "pages": []
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                current_section = "unknown"
                
                for i, page in enumerate(pdf.pages):
                    # Extract text with layout info
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    
                    # Extract words with positions
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    
                    # Extract lines
                    lines = []
                    if page_text:
                        lines = page_text.split('\n')
                        
                    # Process each line to identify sections
                    for line in lines:
                        # Add to raw text
                        result["raw_text"] += line + "\n"
                        
                        # Check if this line is a section header
                        detected_section = self._detect_section(line)
                        if detected_section:
                            current_section = detected_section
                        else:
                            # Add content to the current section
                            result["sections"][current_section].append(line)
                    
                    # Create structured page info
                    page_info = {
                        "number": i + 1,
                        "text": page_text,
                        "lines": lines,
                        "words": words
                    }
                    
                    result["pages"].append(page_info)
                
                # Identify key elements by position and font attributes
                result["structure"] = self._analyze_pdf_structure(pdf)
                
                # Post-process sections
                self._post_process_sections(result)
                
            return result
            
        except Exception as e:
            raise Exception(f"Error converting PDF to structured format: {str(e)}")
    
    def _convert_image(self, file_path):
        """
        Convert an image to structured format
        
        Args:
            file_path (str): Path to the image file
            
        Returns:
            dict: Structured representation of the document
        """
        # Initialize the result structure
        result = {
            "document_type": self._detect_document_type(file_path),
            "metadata": {
                "filename": os.path.basename(file_path),
                "file_type": "image"
            },
            "raw_text": "",
            "sections": defaultdict(list),
            "layout": {}
        }
        
        try:
            # Read image using OpenCV
            image = cv2.imread(file_path)
            
            # Apply image preprocessing
            processed_image = self._preprocess_image(image)
            
            # Use Tesseract OCR with additional page segmentation options
            # PSM 1: Automatic page segmentation with OSD
            raw_text = pytesseract.image_to_string(processed_image)
            result["raw_text"] = raw_text
            
            # Get detailed information including positions
            layout_data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            result["layout"] = layout_data
            
            # Extract structured data using hOCR
            hocr_data = pytesseract.image_to_pdf_or_hocr(processed_image, extension='hocr')
            result["hocr_data"] = str(hocr_data)
            
            # Process lines to identify sections
            lines = raw_text.split('\n')
            current_section = "unknown"
            
            for line in lines:
                if not line.strip():
                    continue
                    
                # Check if this line is a section header
                detected_section = self._detect_section(line)
                if detected_section:
                    current_section = detected_section
                else:
                    # Add content to the current section
                    result["sections"][current_section].append(line)
            
            # Post-process sections
            self._post_process_sections(result)
            
            return result
            
        except Exception as e:
            raise Exception(f"Error converting image to structured format: {str(e)}")
    
    def _detect_section(self, line):
        """
        Detect if a line is a section header
        
        Args:
            line (str): Line of text to check
            
        Returns:
            str or None: Section type if detected, None otherwise
        """
        line_lower = line.lower().strip()
        
        # Check against section keywords
        for section_type, keywords in self.section_keywords.items():
            for keyword in keywords:
                # Check for exact match or section header patterns
                pattern1 = r'^{}[:\s]*$'.format(re.escape(keyword))  # Exact match with optional colon
                pattern2 = r'^[•\-\*\s]*{}[:\s]*$'.format(re.escape(keyword))  # With bullet points
                
                if (re.match(pattern1, line_lower) or 
                    re.match(pattern2, line_lower) or 
                    line_lower == keyword):
                    return section_type
                
        return None
    
    def _detect_document_type(self, file_path):
        """
        Detect if the document is a resume or certification
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: Document type ("resume", "certification", or "unknown")
        """
        filename = os.path.basename(file_path).lower()
        
        # Check filename for clues
        if "resume" in filename or "cv" in filename:
            return "resume"
        elif "cert" in filename or "diploma" in filename:
            return "certification"
            
        # We'll do further content-based detection after extracting text
        return "unknown"
    
    def _preprocess_image(self, image):
        """
        Preprocess image for better OCR results
        
        Args:
            image (numpy.ndarray): Image to preprocess
            
        Returns:
            numpy.ndarray: Preprocessed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to handle different lighting conditions
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Apply dilation to enhance text visibility
        dilated = cv2.dilate(opening, kernel, iterations=1)
        
        return dilated
    
    def _analyze_pdf_structure(self, pdf):
        """
        Analyze the structure of a PDF document
        
        Args:
            pdf (pdfplumber.PDF): PDF document
            
        Returns:
            dict: Structured information about the document
        """
        structure = {
            "title": None,
            "headings": [],
            "lists": [],
            "tables": []
        }
        
        # Analyze font and positioning to identify structural elements
        fonts = defaultdict(int)
        
        for page in pdf.pages:
            # Extract table information if available
            tables = page.find_tables()
            if tables:
                for table in tables:
                    structure["tables"].append({
                        "page": page.page_number,
                        "bbox": table.bbox,
                        "content": table.extract()
                    })
            
            # Get all text elements with their styles
            if hasattr(page, 'chars') and page.chars:
                for char in page.chars:
                    if 'fontname' in char:
                        fonts[char['fontname']] += 1
                        
                        # Identify likely headings by font size and style
                        if char.get('size', 0) > 12:  # Assume larger fonts are headings
                            # Check if this is part of an existing heading or a new one
                            text = char.get('text', '')
                            if text and text.strip():
                                structure["headings"].append({
                                    "text": text,
                                    "page": page.page_number,
                                    "bbox": (char['x0'], char['top'], char['x1'], char['bottom']),
                                    "font": char['fontname'],
                                    "size": char.get('size', 0)
                                })
        
        # Identify the likely title (largest font on first page)
        if structure["headings"]:
            title_candidate = max(
                [h for h in structure["headings"] if h["page"] == 1], 
                key=lambda x: x["size"], 
                default=None
            )
            if title_candidate:
                structure["title"] = title_candidate["text"]
        
        return structure
    
    def _post_process_sections(self, result):
        """
        Post-process identified sections
        
        Args:
            result (dict): The document structure to process
            
        Returns:
            dict: Processed document structure
        """
        # If the document type is unknown, try to determine from content
        if result["document_type"] == "unknown":
            if "certifications" in result["sections"] and len(result["sections"]["certifications"]) > 5:
                result["document_type"] = "certification"
            elif "experience" in result["sections"] and "education" in result["sections"]:
                result["document_type"] = "resume"
        
        # For certification documents, extract issuer, date, and credential ID
        if result["document_type"] == "certification":
            # Look for dates in the format MM/DD/YYYY or similar
            date_pattern = r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})'
            dates = re.findall(date_pattern, result["raw_text"])
            if dates:
                result["metadata"]["dates"] = dates
            
            # Look for credential ID patterns
            id_patterns = [
                r'credential\s+id[:\s]*([A-Za-z0-9\-]+)',
                r'certificate\s+number[:\s]*([A-Za-z0-9\-]+)',
                r'certification\s+id[:\s]*([A-Za-z0-9\-]+)',
                r'id[:\s]*([A-Za-z0-9\-]+)'
            ]
            
            for pattern in id_patterns:
                id_match = re.search(pattern, result["raw_text"], re.IGNORECASE)
                if id_match:
                    result["metadata"]["credential_id"] = id_match.group(1).strip()
                    break
        
        # For resume documents, extract contact information
        if result["document_type"] == "resume":
            # Look for email addresses
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, result["raw_text"])
            if emails:
                result["metadata"]["email"] = emails[0]
            
            # Look for phone numbers
            phone_pattern = r'(\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}'
            phones = re.findall(phone_pattern, result["raw_text"])
            if phones:
                result["metadata"]["phone"] = phones[0]
        
        return result
