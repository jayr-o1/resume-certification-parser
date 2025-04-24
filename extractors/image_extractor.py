import os
import cv2
import pytesseract
from PIL import Image
import numpy as np

class ImageExtractor:
    """
    Class for extracting text from images using OCR
    """
    
    def __init__(self, tesseract_cmd=None):
        """
        Initialize the ImageExtractor
        
        Args:
            tesseract_cmd (str, optional): Path to tesseract executable
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.extracted_text = ""
        
    def preprocess_image(self, image):
        """
        Preprocess the image to improve OCR results
        
        Args:
            image (numpy.ndarray): Image to preprocess
            
        Returns:
            numpy.ndarray: Preprocessed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to handle shadows and clean the image
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Apply morphological operations to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        return opening
        
    def extract(self, file_path):
        """
        Extract text from an image file
        
        Args:
            file_path (str): Path to the image file
            
        Returns:
            str: Extracted text
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
            
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        if not any(file_path.lower().endswith(fmt) for fmt in supported_formats):
            raise ValueError(f"File {file_path} is not a supported image format")
            
        self.extracted_text = ""
        
        try:
            # Read image using OpenCV
            image = cv2.imread(file_path)
            
            # Preprocess the image
            processed_image = self.preprocess_image(image)
            
            # Extract text using pytesseract
            self.extracted_text = pytesseract.image_to_string(processed_image)
            
            return self.extracted_text
            
        except Exception as e:
            raise Exception(f"Error extracting text from image: {str(e)}")
            
    def get_extracted_text(self):
        """
        Get the extracted text
        
        Returns:
            str: The extracted text
        """
        return self.extracted_text 