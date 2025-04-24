import os
import mimetypes
import re
import glob

def get_file_type(file_path):
    """
    Determine the type of a file based on extension or content
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: File type ('pdf', 'image', or None)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")
        
    # Get the file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Check by extension
    if file_ext == '.pdf':
        return 'pdf'
    elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        return 'image'
    else:
        # Try to determine by MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type:
            if mime_type == 'application/pdf':
                return 'pdf'
            elif mime_type.startswith('image/'):
                return 'image'
                
    return None
    
def is_supported_file(file_path):
    """
    Check if a file is supported by the system
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if the file is supported, False otherwise
    """
    file_type = get_file_type(file_path)
    return file_type is not None
    
def get_output_path(input_path, output_dir=None, output_format='json'):
    """
    Generate an output file path based on input path
    
    Args:
        input_path (str): Path to the input file
        output_dir (str, optional): Output directory
        output_format (str, optional): Output file format
        
    Returns:
        str: Path to the output file
    """
    # Get the base name without extension
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # Create output path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{base_name}_skills.{output_format}")
    else:
        output_path = os.path.join(os.path.dirname(input_path), f"{base_name}_skills.{output_format}")
        
    return output_path

def validate_file_naming(file_path):
    """
    Validate if the file has the expected naming convention
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        tuple: (is_valid, file_type) where file_type is 'resume', 'certification', or None if invalid
    """
    # Get the file name without extension
    file_name = os.path.basename(file_path)
    file_name_without_ext = os.path.splitext(file_name)[0].lower()
    
    # Check if it contains 'resume' keyword
    if re.search(r'resume', file_name_without_ext, re.IGNORECASE):
        return True, 'resume'
    
    # Check if it contains 'certification' or 'certificate' keywords
    if re.search(r'certif', file_name_without_ext, re.IGNORECASE):
        return True, 'certification'
    
    # Not a valid naming convention
    return False, None

def sort_files_by_type(file_paths):
    """
    Sort files into resume and certification categories based on naming convention
    
    Args:
        file_paths (list): List of file paths to sort
        
    Returns:
        tuple: (resume_files, certification_files, unknown_files)
    """
    resume_files = []
    certification_files = []
    unknown_files = []
    
    for file_path in file_paths:
        is_valid_name, file_type = validate_file_naming(file_path)
        if is_valid_name:
            if file_type == 'resume':
                resume_files.append(file_path)
            elif file_type == 'certification':
                certification_files.append(file_path)
        else:
            unknown_files.append(file_path)
    
    return resume_files, certification_files, unknown_files

def get_supported_files_in_directory(directory_path):
    """
    Find all supported files in a directory
    
    Args:
        directory_path (str): Path to the directory
        
    Returns:
        list: List of supported file paths
    """
    all_files = []
    
    # Get all files with supported extensions
    for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        all_files.extend(glob.glob(os.path.join(directory_path, f"*{ext}")))
    
    return all_files 