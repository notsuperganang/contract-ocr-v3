import os
import sys
import importlib
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
    
    # PP-StructureV3 Configuration - SIMPLIFIED WORKING CONFIG
    # Model Selection (None = use PPStructureV3 defaults)
    text_recognition_model: Optional[str] = None    # Let PPStructureV3 choose automatically
    text_detection_model: Optional[str] = None      # Let PPStructureV3 choose automatically  
    layout_detection_model: Optional[str] = None    # Let PPStructureV3 choose automatically
    
    # Core Recognition Features - OPTIMIZED FOR TELKOM CONTRACTS
    use_table_recognition: bool = True               # ✅ Essential for service count extraction
    use_seal_recognition: bool = False               # ❌ Disabled - not needed for contracts
    use_formula_recognition: bool = False            # ❌ Disabled - not needed for contracts
    
    # Performance Optimization - TESTED AND WORKING
    enable_hpi: bool = True                          # ✅ High Performance Inference for CPU
    device: str = "cpu"                              # CPU-only production environment
    
    # Processing Pipeline Configuration  
    use_doc_orientation_classify: Optional[bool] = None    # Use PPStructureV3 defaults
    use_doc_unwarping: Optional[bool] = None               # Use PPStructureV3 defaults
    use_textline_orientation: Optional[bool] = None        # Use PPStructureV3 defaults
    
    # Advanced Parameters (None = use defaults)
    text_det_thresh: Optional[float] = None
    text_det_box_thresh: Optional[float] = None
    text_det_unclip_ratio: Optional[float] = None
    text_rec_score_thresh: Optional[float] = None
    text_det_limit_side_len: Optional[int] = None
    text_det_limit_type: Optional[str] = None
    text_recognition_batch_size: Optional[int] = None
    layout_threshold: Optional[float] = None
    layout_nms: Optional[bool] = None
    
    # Logging Configuration - COMPREHENSIVE DEBUGGING
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/app.log"
    
    # Detailed Logging Options
    log_config_details: bool = True              # Log all config parameters 
    log_model_loading: bool = True               # Log model selection and loading
    log_processing_steps: bool = True            # Log each processing step with timing
    log_ocr_results_quality: bool = True         # Log OCR result quality analysis
    log_performance_metrics: bool = True         # Log performance and timing data
    log_debug_model_info: bool = True            # Log internal model information
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def force_reload_config():
    """Force reload of configuration by clearing cached modules"""
    # Clear this module from cache
    module_name = __name__
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    # Also clear any related config modules
    config_modules = [key for key in sys.modules.keys() if 'config' in key.lower()]
    for module in config_modules:
        if module.startswith('app.config'):
            del sys.modules[module]

def get_fresh_settings():
    """Get a fresh instance of settings, bypassing any caches"""
    # Force reload this module
    current_module = sys.modules[__name__]
    importlib.reload(current_module)
    return Settings()

def validate_and_log_config(settings_instance):
    """Validate configuration and log important settings"""
    print(f"[CONFIG] ={'='*60}")
    print(f"[CONFIG] {settings_instance.app_name} v{settings_instance.version}")
    print(f"[CONFIG] ={'='*60}")
    
    # Core Configuration
    print(f"[CONFIG] 🏭 PP-StructureV3 Configuration:")
    print(f"[CONFIG]   📝 Text Recognition Model: {settings_instance.text_recognition_model or 'DEFAULT'}")
    print(f"[CONFIG]   🔍 Text Detection Model: {settings_instance.text_detection_model or 'DEFAULT'}")  
    print(f"[CONFIG]   📐 Layout Detection Model: {settings_instance.layout_detection_model or 'DEFAULT'}")
    
    # Recognition Features
    print(f"[CONFIG] 🎯 Recognition Features:")
    print(f"[CONFIG]   📊 Table Recognition: {settings_instance.use_table_recognition}")
    print(f"[CONFIG]   🔐 Seal Recognition: {settings_instance.use_seal_recognition}")
    print(f"[CONFIG]   🧮 Formula Recognition: {settings_instance.use_formula_recognition}")
    
    # Performance Settings
    print(f"[CONFIG] ⚡ Performance Settings:")
    print(f"[CONFIG]   🚀 High Performance Inference: {settings_instance.enable_hpi}")
    print(f"[CONFIG]   💻 Device: {settings_instance.device}")
    
    # Logging Configuration
    print(f"[CONFIG] 📋 Logging Configuration:")
    print(f"[CONFIG]   📝 Log Level: {settings_instance.log_level}")
    print(f"[CONFIG]   💾 Config Details: {settings_instance.log_config_details}")
    print(f"[CONFIG]   🔧 Model Loading: {settings_instance.log_model_loading}")
    print(f"[CONFIG]   📊 Processing Steps: {settings_instance.log_processing_steps}")
    print(f"[CONFIG]   🔍 Results Quality: {settings_instance.log_ocr_results_quality}")
    print(f"[CONFIG]   ⏱️ Performance Metrics: {settings_instance.log_performance_metrics}")
    
    # Validation - only check essential settings
    assert settings_instance.use_table_recognition == True, \
        "Table recognition must be enabled for service count extraction"
    assert settings_instance.use_seal_recognition == False, \
        "Seal recognition should be disabled for contract processing"
    assert settings_instance.use_formula_recognition == False, \
        "Formula recognition should be disabled for contract processing"
    assert settings_instance.enable_hpi == True, \
        "HPI should be enabled for CPU performance"
    
    print(f"[CONFIG] ✅ Configuration validation passed")
    print(f"[CONFIG] 🎯 Optimized for Telkom contract processing")
    print(f"[CONFIG] ={'='*60}")
    return True

def get_pipeline_params(settings_instance):
    """Get PPStructureV3 parameters from settings, filtering out None values"""
    params = {}
    
    # Add non-None model parameters
    if settings_instance.text_recognition_model is not None:
        params["text_recognition_model_name"] = settings_instance.text_recognition_model
    if settings_instance.text_detection_model is not None:
        params["text_detection_model_name"] = settings_instance.text_detection_model
    if settings_instance.layout_detection_model is not None:
        params["layout_detection_model_name"] = settings_instance.layout_detection_model
    
    # Core recognition features (always set)
    params["use_table_recognition"] = settings_instance.use_table_recognition
    params["use_seal_recognition"] = settings_instance.use_seal_recognition
    params["use_formula_recognition"] = settings_instance.use_formula_recognition
    
    # Performance settings (always set)
    params["enable_hpi"] = settings_instance.enable_hpi
    params["device"] = settings_instance.device
    
    # Add optional parameters only if they're not None
    optional_params = [
        "use_doc_orientation_classify", "use_doc_unwarping", "use_textline_orientation",
        "text_det_thresh", "text_det_box_thresh", "text_det_unclip_ratio",
        "text_rec_score_thresh", "text_det_limit_side_len", "text_det_limit_type",
        "text_recognition_batch_size", "layout_threshold", "layout_nms"
    ]
    
    for param in optional_params:
        value = getattr(settings_instance, param)
        if value is not None:
            params[param] = value
    
    return params

# Create global settings instance
settings = Settings()

# Validate configuration on import
validate_and_log_config(settings)

# Create directories if they don't exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)
os.makedirs("logs", exist_ok=True)