import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

def clean_text(text):
    """
    Clean and normalize extracted text
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
        
    # Ensure NLTK resources are available
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('punkt')
        nltk.download('stopwords')
        
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters and digits (but keep hyphens in words)
    text = re.sub(r'[^\w\s\-]', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
    
def preprocess_text(text, remove_stopwords=False):
    """
    Preprocess text for analysis
    
    Args:
        text (str): The text to preprocess
        remove_stopwords (bool, optional): Whether to remove stopwords
        
    Returns:
        str: Preprocessed text
    """
    if not text:
        return ""
        
    # Clean the text
    cleaned_text = clean_text(text)
    
    if remove_stopwords:
        try:
            stop_words = set(stopwords.words('english'))
            tokens = word_tokenize(cleaned_text)
            filtered_tokens = [word for word in tokens if word.lower() not in stop_words]
            preprocessed_text = ' '.join(filtered_tokens)
        except LookupError:
            nltk.download('stopwords')
            stop_words = set(stopwords.words('english'))
            tokens = word_tokenize(cleaned_text)
            filtered_tokens = [word for word in tokens if word.lower() not in stop_words]
            preprocessed_text = ' '.join(filtered_tokens)
    else:
        preprocessed_text = cleaned_text
        
    return preprocessed_text
    
def extract_sentences_with_keyword(text, keyword, window_size=1):
    """
    Extract sentences containing a keyword and surrounding context
    
    Args:
        text (str): The text to search in
        keyword (str): The keyword to search for
        window_size (int, optional): Number of sentences to include before and after
        
    Returns:
        str: Extracted sentences
    """
    if not text or not keyword:
        return ""
        
    try:
        sentences = nltk.sent_tokenize(text)
    except LookupError:
        nltk.download('punkt')
        sentences = nltk.sent_tokenize(text)
        
    keyword_pattern = r'\b' + re.escape(keyword) + r'\b'
    result_sentences = []
    
    for i, sentence in enumerate(sentences):
        if re.search(keyword_pattern, sentence, re.IGNORECASE):
            # Add sentences within window
            start = max(0, i - window_size)
            end = min(len(sentences), i + window_size + 1)
            
            for j in range(start, end):
                if sentences[j] not in result_sentences:
                    result_sentences.append(sentences[j])
                    
    return ' '.join(result_sentences) 