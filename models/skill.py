class Skill:
    """
    Class representing a skill with its attributes
    """
    
    # Proficiency levels
    PROFICIENCY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]
    
    def __init__(self, name, proficiency=None, is_backed=False, 
                 confidence_score=0.0, backing_certificate=None, source=None):
        """
        Initialize a Skill object
        
        Args:
            name (str): The name of the skill
            proficiency (str, optional): Proficiency level (Beginner, Intermediate, Advanced, Expert)
            is_backed (bool, optional): Whether the skill is backed by a certificate
            confidence_score (float, optional): The confidence score of the skill extraction (0.0-1.0)
            backing_certificate (str, optional): The name of the certificate backing this skill
            source (str, optional): The source of the skill (e.g., "Skills section", "Experience section")
        """
        self.name = name
        self.proficiency = proficiency if proficiency in self.PROFICIENCY_LEVELS else None
        self.is_backed = is_backed
        self.confidence_score = min(max(confidence_score, 0.0), 1.0)  # Ensure between 0.0 and 1.0
        self.backing_certificate = backing_certificate
        self.source = source
        
    def set_backing(self, certificate_name):
        """
        Set the skill as backed with a certificate
        
        Args:
            certificate_name (str): The name of the certificate
        """
        self.is_backed = True
        self.backing_certificate = certificate_name
        # Increase confidence for backed skills
        self.confidence_score = min(self.confidence_score * 1.5, 1.0)
        
    def adjust_confidence(self, confidence_score):
        """
        Adjust the confidence score
        
        Args:
            confidence_score (float): The new confidence score
        """
        self.confidence_score = min(max(confidence_score, 0.0), 1.0)
        
    def to_dict(self):
        """
        Convert to dictionary for serialization
        
        Returns:
            dict: Dictionary representation of the skill
        """
        return {
            'name': self.name,
            'proficiency': self.proficiency,
            'is_backed': self.is_backed,
            'confidence_score': self.confidence_score,
            'backing_certificate': self.backing_certificate,
            'source': self.source
        }
    
    def __str__(self):
        """String representation of the skill"""
        backed_status = "Backed" if self.is_backed else "Unbacked"
        certificate_info = f" by {self.backing_certificate}" if self.backing_certificate else ""
        source_info = f" (from {self.source})" if self.source else ""
        
        return f"{self.name}: {self.proficiency or 'Unknown'} ({backed_status}{certificate_info}) - {self.confidence_score:.2f} confidence{source_info}" 