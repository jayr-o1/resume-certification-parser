import os
import re

def get_file_type(file_path):
    """
    Determine the type of file based on extension
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str or None: 'pdf' or 'image' or None if not supported
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        return 'image'
    else:
        return None

def is_supported_file(file_path):
    """
    Check if the file is supported
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if file is supported, False otherwise
    """
    return get_file_type(file_path) is not None

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

def get_output_path(input_path):
    """
    Generate output path for results
    
    Args:
        input_path (str): Path to the input file
        
    Returns:
        str: Path to the output file
    """
    base_path = os.path.splitext(input_path)[0]
    return f"{base_path}_skills.json" 

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
    import glob
    
    all_files = []
    
    # Get all files with supported extensions
    for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
        all_files.extend(glob.glob(os.path.join(directory_path, f"*{ext}")))
    
    return all_files 