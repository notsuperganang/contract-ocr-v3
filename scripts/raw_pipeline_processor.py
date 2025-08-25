#!/usr/bin/env python3
"""
Pipeline Processor for Telkom Contract Documents

Based on the working example, this script processes PDF contract files using 
PP-StructureV3 pipeline and saves the raw JSON results using the built-in
save_to_json() method.

Usage:
    python scripts/pipeline_processor.py
"""

import os
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import mean

# Add the app directory to Python path for config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import fitz  # PyMuPDF
from loguru import logger
from paddleocr import PPStructureV3
from pdf2image import convert_from_path

from app.config import settings, get_pipeline_params


class PipelineProcessor:
    """PP-StructureV3 pipeline processor using the working blueprint"""
    
    def __init__(self):
        self.pipeline = None
        self.temp_dir = None
        self._setup_temp_dir()
        self._initialize_pipeline()
    
    def _setup_temp_dir(self):
        """Create temporary directory for processing"""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="telkom_pipeline_")
            logger.info(f"Temporary directory created: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to create temp directory: {str(e)}")
            raise
    
    def _initialize_pipeline(self):
        """Initialize PP-StructureV3 pipeline using centralized configuration"""
        try:
            if settings.log_config_details:
                logger.info("="*80)
                logger.info("🏭 INITIALIZING PP-STRUCTUREV3 PIPELINE")
                logger.info("="*80)
            
            # Get pipeline parameters from centralized config
            pipeline_params = get_pipeline_params(settings)
            
            if settings.log_model_loading:
                logger.info("📋 Pipeline Parameters from Config:")
                for key, value in pipeline_params.items():
                    logger.info(f"   {key}: {value}")
                
                logger.info(f"🎯 Pipeline Strategy:")
                logger.info(f"   Model Selection: {'CUSTOM' if any(k.endswith('_model_name') for k in pipeline_params) else 'DEFAULT'}")
                logger.info(f"   Contract Optimized: ✅ (seal={pipeline_params['use_seal_recognition']}, formula={pipeline_params['use_formula_recognition']})")
                logger.info(f"   HPI Acceleration: {'✅' if pipeline_params['enable_hpi'] else '❌'}")
                logger.info(f"   Table Recognition: {'✅' if pipeline_params['use_table_recognition'] else '❌'}")
            
            t_load_start = time.perf_counter()
            
            if settings.log_model_loading:
                logger.info("🔄 Creating PPStructureV3 pipeline...")
            
            # Initialize pipeline with centralized config
            self.pipeline = PPStructureV3(**pipeline_params)
            
            t_load_end = time.perf_counter()
            t_load = t_load_end - t_load_start
            
            if settings.log_performance_metrics:
                logger.info("="*80)
                logger.info("✅ PIPELINE INITIALIZATION COMPLETE")
                logger.info("="*80)
                logger.info(f"⏱️  Initialization Time: {t_load:.3f}s")
                logger.info(f"🎯 Target: Telkom contract processing with optimal accuracy")
                logger.info(f"💾 Config Source: Centralized (app/config.py)")
                logger.info("="*80)
            else:
                logger.info(f"Pipeline initialized (load time: {t_load:.3f}s)")
            
            # Log model verification if enabled
            if settings.log_debug_model_info:
                self._log_model_verification()
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize pipeline: {str(e)}")
            logger.error(f"💡 Check PaddlePaddle version compatibility and HPI dependencies")
            raise

    def _log_model_verification(self):
        """Log detailed model verification information"""
        try:
            logger.info("🔍 MODEL VERIFICATION:")
            
            if hasattr(self.pipeline, 'paddlex_pipeline'):
                px_pipeline = self.pipeline.paddlex_pipeline
                logger.info(f"   PaddleX Pipeline: {type(px_pipeline).__name__}")
                
                if hasattr(px_pipeline, '_pipeline'):
                    internal = px_pipeline._pipeline
                    logger.info(f"   Internal Pipeline: {type(internal).__name__}")
                    
                    # Try to get model information
                    components = []
                    for attr_name in dir(internal):
                        if 'model' in attr_name.lower() and not attr_name.startswith('_'):
                            attr_value = getattr(internal, attr_name, None)
                            if attr_value is not None:
                                components.append(f"{attr_name}: {type(attr_value).__name__}")
                    
                    if components:
                        logger.info("   Pipeline Components:")
                        for component in components:
                            logger.info(f"     • {component}")
            
            logger.info("✅ Model verification complete")
            
        except Exception as e:
            logger.warning(f"⚠️  Could not verify models: {str(e)}")
            logger.warning("   This is not critical - pipeline should still work")
    
    def cut_pdf_to_first_two_pages(self, input_path: str, output_path: str) -> bool:
        """Cut PDF to first 2 pages using PyMuPDF"""
        try:
            logger.info(f"Cutting PDF to first 2 pages: {os.path.basename(input_path)}")
            
            pdf_document = fitz.open(input_path)
            
            if len(pdf_document) == 0:
                logger.warning(f"PDF has no pages: {input_path}")
                return False
            
            # Create new PDF with first 2 pages
            pages_to_extract = min(2, len(pdf_document))
            new_pdf = fitz.open()
            
            for page_num in range(pages_to_extract):
                new_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
            
            new_pdf.save(output_path)
            new_pdf.close()
            pdf_document.close()
            
            logger.info(f"PDF cut completed. Pages extracted: {pages_to_extract}")
            return True
            
        except Exception as e:
            logger.error(f"Error cutting PDF {input_path}: {str(e)}")
            return False
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> list:
        """Convert PDF to images using pdf2image"""
        try:
            logger.info(f"Converting PDF to images @ {dpi} DPI: {os.path.basename(pdf_path)}")
            t_pdf_start = time.perf_counter()
            
            # Convert PDF to images
            pages = convert_from_path(pdf_path, dpi=dpi)
            
            t_pdf_end = time.perf_counter()
            t_pdf = t_pdf_end - t_pdf_start
            
            # Save images to temp directory
            image_paths = []
            for idx, page in enumerate(pages, start=1):
                img_path = os.path.join(self.temp_dir, f"page_{idx}.png")
                page.save(img_path, "PNG")
                image_paths.append(img_path)
            
            logger.info(f"PDF converted to {len(image_paths)} images (time: {t_pdf:.3f}s)")
            return image_paths
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            return []
    
    def process_single_pdf(self, pdf_path: str) -> dict:
        """Process a single PDF file with comprehensive logging"""
        try:
            pdf_name = Path(pdf_path).stem
            
            if settings.log_processing_steps:
                logger.info("="*80)
                logger.info(f"📄 PROCESSING: {pdf_name}")
                logger.info("="*80)
            else:
                logger.info(f"Processing: {pdf_name}")
                
            t_all_start = time.perf_counter()
            
            # Step 1: Cut PDF to first 2 pages
            if settings.log_processing_steps:
                logger.info("📋 STEP 1: Preparing PDF...")
            
            temp_pdf_path = os.path.join(self.temp_dir, f"{pdf_name}_first2pages.pdf")
            if not self.cut_pdf_to_first_two_pages(pdf_path, temp_pdf_path):
                raise Exception(f"Failed to cut PDF: {pdf_path}")
            
            # Step 2: Convert PDF to images
            if settings.log_processing_steps:
                logger.info("🖼️  STEP 2: Converting PDF to images...")
                
            image_paths = self.pdf_to_images(temp_pdf_path, dpi=200)
            if not image_paths:
                raise Exception(f"Failed to convert PDF to images: {temp_pdf_path}")
                
            if settings.log_processing_steps:
                logger.info(f"   ✅ Generated {len(image_paths)} images for processing")
            
            # Step 3: Process each image with pipeline and save JSON results
            if settings.log_processing_steps:
                logger.info("🔍 STEP 3: Running OCR on each page...")
                
            per_page_ocr_times = []
            t_ocr_total_start = time.perf_counter()
            
            json_output_dirs = []
            
            for i, img_path in enumerate(image_paths, 1):
                base_name = os.path.splitext(os.path.basename(img_path))[0]
                
                if settings.log_processing_steps:
                    logger.info(f"   📄 Processing Page {i}/{len(image_paths)}: {base_name}")
                else:
                    logger.info(f"Processing image: {base_name}")
                
                t_page_start = time.perf_counter()
                
                # Run pipeline prediction
                results = self.pipeline.predict(img_path)
                
                # Save results using the built-in save_to_json method
                save_dir = os.path.join(settings.output_dir, f"{pdf_name}_{base_name}_results")
                
                for res in results:
                    res.save_to_json(save_path=save_dir)
                
                json_output_dirs.append(save_dir)
                
                t_page_end = time.perf_counter()
                t_page = t_page_end - t_page_start
                per_page_ocr_times.append(t_page)
                
                if settings.log_performance_metrics:
                    logger.info(f"     ⏱️  Page {i} completed: {t_page:.3f}s")
                    logger.info(f"     💾 Results saved to: {os.path.basename(save_dir)}")
                else:
                    logger.info(f"  ⤷ OCR+parse completed: {t_page:.3f}s (JSON saved to: {save_dir})")
            
            t_ocr_total_end = time.perf_counter()
            t_ocr_total = t_ocr_total_end - t_ocr_total_start
            
            t_all_end = time.perf_counter()
            t_all = t_all_end - t_all_start
            
            # Clean up temporary files
            self._cleanup_temp_files([temp_pdf_path] + image_paths)
            
            # Final processing summary
            if settings.log_performance_metrics:
                logger.info("="*80)
                logger.info("✅ PROCESSING COMPLETE")
                logger.info("="*80)
                logger.info(f"📊 Performance Summary:")
                logger.info(f"   ⏱️  Total Time: {t_all:.3f}s")
                logger.info(f"   🔍 OCR Time: {t_ocr_total:.3f}s ({(t_ocr_total/t_all*100):.1f}%)")
                logger.info(f"   📄 Pages Processed: {len(image_paths)}")
                logger.info(f"   ⚡ Avg per Page: {mean(per_page_ocr_times):.3f}s")
                logger.info(f"   📁 Output Directories: {len(json_output_dirs)}")
                logger.info("="*80)
            else:
                logger.info(f"Processing completed - Total time: {t_all:.3f}s, OCR time: {t_ocr_total:.3f}s")
            
            # Return processing summary
            return {
                "pdf_name": pdf_name,
                "original_path": pdf_path,
                "json_output_dirs": json_output_dirs,
                "processing_times": {
                    "total_seconds": round(t_all, 3),
                    "ocr_total_seconds": round(t_ocr_total, 3),
                    "ocr_average_per_page": round(mean(per_page_ocr_times) if per_page_ocr_times else 0, 3),
                    "per_page_times": [round(t, 3) for t in per_page_ocr_times]
                },
                "pages_processed": len(image_paths),
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return {
                "pdf_name": Path(pdf_path).stem,
                "original_path": pdf_path,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def _cleanup_temp_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")
    
    def cleanup(self):
        """Clean up temporary directory"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"Temporary directory cleaned up: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up temp directory: {str(e)}")


def clean_filename_for_output(filename: str) -> str:
    """Clean filename for use in output files"""
    clean = Path(filename).stem.lower()
    clean = clean.replace(' ', '_').replace('-', '_')
    clean = ''.join(c for c in clean if c.isalnum() or c == '_')
    while '__' in clean:
        clean = clean.replace('__', '_')
    return clean.strip('_')


def main():
    """Main batch processing function"""
    
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )
    
    # Add file logging
    log_file = os.path.join("logs", f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    os.makedirs("logs", exist_ok=True)
    logger.add(log_file, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="DEBUG")
    
    logger.info("="*70)
    logger.info("TELKOM CONTRACT PIPELINE PROCESSOR")
    logger.info("="*70)
    logger.info("Using PP-StructureV3 with built-in save_to_json() method")
    logger.info("Configuration: seal_recognition=False, formula_recognition=False")
    logger.info("="*70)
    
    # Define test files to process
    test_files = [
        # "tests/test_samples/KB SMKN 1 BIREUN TTD 2024 VALIDASI.pdf",
        # "tests/test_samples/KONTRAK PT LKMS MAHIRAH MUAMALAH  2025 VALIDASI.pdf",
        # "tests/test_samples/KONTRAK SMK PENERBANGAN 2025 VALIDASI.pdf"
    ]
    
    processor = None
    batch_start_time = time.perf_counter()
    summary = {
        "total_files": len(test_files),
        "successful": 0,
        "failed": 0,
        "results": []
    }
    
    try:
        # Initialize processor
        processor = PipelineProcessor()
        
        # Process each file
        for i, pdf_path in enumerate(test_files, 1):
            logger.info(f"\n[{i}/{len(test_files)}] Processing: {os.path.basename(pdf_path)}")
            
            if not os.path.exists(pdf_path):
                logger.error(f"File not found: {pdf_path}")
                summary["failed"] += 1
                continue
            
            # Process the document
            result = processor.process_single_pdf(pdf_path)
            
            if result.get("success", False):
                summary["successful"] += 1
                summary["results"].append({
                    "file": os.path.basename(pdf_path),
                    "output_dirs": result["json_output_dirs"],
                    "processing_time": result["processing_times"]["total_seconds"],
                    "pages": result["pages_processed"],
                    "status": "success"
                })
                
                logger.success(f"✓ Successfully processed: {os.path.basename(pdf_path)}")
                for output_dir in result["json_output_dirs"]:
                    logger.info(f"  JSON results saved to: {output_dir}")
                
            else:
                summary["failed"] += 1
                summary["results"].append({
                    "file": os.path.basename(pdf_path),
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                })
                
                logger.error(f"✗ Failed to process: {os.path.basename(pdf_path)}")
        
        # Print final summary
        batch_end_time = time.perf_counter()
        total_batch_time = batch_end_time - batch_start_time
        
        logger.info("\n" + "="*70)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("="*70)
        logger.info(f"Total files: {summary['total_files']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Total batch time: {total_batch_time:.3f} seconds")
        
        if summary["successful"] > 0:
            logger.info(f"\nJSON outputs saved to: {settings.output_dir}/")
            for result in summary["results"]:
                if result["status"] == "success":
                    logger.info(f"📄 {result['file']} ({result['processing_time']}s, {result['pages']} pages)")
                    for output_dir in result["output_dirs"]:
                        logger.info(f"    → {os.path.basename(output_dir)}")
            
            logger.info(f"\n🔧 These JSON files contain the raw PP-StructureV3 pipeline output")
            logger.info(f"📊 Use them to understand the data structure for building extractors")
        
        if summary["failed"] > 0:
            logger.warning(f"\nFailed files:")
            for result in summary["results"]:
                if result["status"] == "failed":
                    logger.warning(f"  - {result['file']}: {result.get('error', 'Unknown error')}")
        
        logger.info("="*70)
        
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        raise
    finally:
        # Cleanup
        if processor:
            processor.cleanup()
        logger.info("Pipeline processing completed")


if __name__ == "__main__":
    main()