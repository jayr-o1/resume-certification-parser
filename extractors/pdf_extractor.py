import pdfplumber
import os

class PDFExtractor:
    """
    Class for extracting text from PDF documents using pdfplumber
    """
    
    def __init__(self):
        self.extracted_text = ""
        self.extracted_pages = []
        
    def extract(self, file_path):
        """
        Extract text from a PDF file
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
            
        if not file_path.lower().endswith('.pdf'):
            raise ValueError(f"File {file_path} is not a PDF file")
            
        self.extracted_text = ""
        self.extracted_pages = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract text with better layout preservation
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    if page_text:
                        self.extracted_text += page_text + "\n\n"
                        self.extracted_pages.append(page_text)
                    
            return self.extracted_text
            
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
            
    def get_extracted_text(self):
        """
        Get the extracted text
        
        Returns:
            str: The extracted text
        """
        return self.extracted_text
        
    def get_page_text(self, page_num):
        """
        Get text from a specific page
        
        Args:
            page_num (int): Page number (0-indexed)
            
        Returns:
            str: Text from the specified page
        """
        if 0 <= page_num < len(self.extracted_pages):
            return self.extracted_pages[page_num]
        return ""
        
    def extract_with_layout(self, file_path):
        """
        Extract text from a PDF with layout information
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            dict: Dictionary with page texts and their layout information
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
            
        result = {
            "text": "",
            "pages": []
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # Extract text with layout info
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    
                    # Extract words with positions
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    
                    # Extract lines
                    lines = []
                    if page_text:
                        lines = page_text.split('\n')
                        
                    page_info = {
                        "number": i + 1,
                        "text": page_text,
                        "lines": lines,
                        "words": words
                    }
                    
                    result["pages"].append(page_info)
                    result["text"] += page_text + "\n\n" if page_text else ""
                    
            return result
            
        except Exception as e:
            raise Exception(f"Error extracting text with layout from PDF: {str(e)}") 