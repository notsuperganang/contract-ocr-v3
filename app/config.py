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
    
    # Recognition Features - FIXES APPLIED
    use_table_recognition: bool = True        # ✅ ENABLE for service counts extraction
    use_seal_recognition: bool = False        # Keep disabled for contracts  
    use_formula_recognition: bool = False     # Keep disabled for contracts
    
    # Text Detection Thresholds - TARGETED FOR MISSING ELEMENTS
    text_det_thresh: float = 0.05            # ✅ Hyper-aggressive for small digits
    text_det_box_thresh: float = 0.2         # ✅ Ultra-low for tiny boxes
    text_det_unclip_ratio: float = 1.8       # ✅ INCREASED - capture text slightly outside detected boxes
    text_rec_score_thresh: float = 0.0       # ✅ Accept all recognized text
    text_det_limit_side_len: int = 1600      # ✅ INCREASED resolution for better small text
    text_det_limit_type: str = "max"         # ✅ Max limit type
    
    # Text Recognition - IMPROVED FOR FONT VARIATIONS
    text_recognition_batch_size: int = 4     # ✅ INCREASED batch processing for efficiency
    
    # Layout Detection - ENHANCED FOR EDGE CASES  
    layout_threshold: float = 0.4            # ✅ LOWER threshold to catch more layout elements
    layout_nms: bool = True                  # ✅ Keep NMS for accuracy
    
    # Performance Optimization
    enable_hpi: bool = True                   # ✅ ENABLE for better accuracy
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