import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    app_name: str = "Telkom Contract Data Extractor"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File Upload Settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: list = [".pdf", ".png", ".jpg", ".jpeg"]
    upload_dir: str = "uploads"
    output_dir: str = "output"
    
    # PP-StructureV3 Configuration
    # Text Recognition (Indonesian + English optimized)
    text_recognition_model: str = "en_PP-OCRv4_mobile_rec"
    
    # Text Detection (CPU-optimized)
    text_detection_model: str = "PP-OCRv5_mobile_det"
    
    # Layout Detection (Balanced speed/accuracy)
    layout_detection_model: str = "PP-DocLayout-L"
    
    # Document Processing Options
    use_doc_orientation_classify: bool = True  # Safety untuk document orientation
    use_doc_unwarping: bool = False           # Skip untuk speed
    use_textline_orientation: bool = True     # Handle slight skew
    
    # Recognition Features
    use_table_recognition: bool = False       # Disable table recognition for contracts
    use_seal_recognition: bool = False        # Disable seal recognition for contracts  
    use_formula_recognition: bool = False     # Disable formula recognition for contracts
    
    # Performance Optimization
    enable_hpi: bool = False                  # Disable HPI due to version compatibility
    device: str = "cpu"                       # CPU-only production environment
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create global settings instance
settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)
os.makedirs("logs", exist_ok=True)