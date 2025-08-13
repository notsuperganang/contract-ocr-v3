#!/usr/bin/env python3
"""
Test Data Extractor on Contract Samples

This script tests the new DataExtractor class on all available contract JSON outputs
and displays the extracted structured data.

Usage:
    python scripts/test_data_extractor.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from loguru import logger
from app.services.data_extractor import DataExtractor
from app.models.schemas import TelkomContractData


def find_contract_json_files() -> dict:
    """Find all contract JSON result files organized by contract"""
    output_dir = Path("output")
    contracts = {}
    
    for item in output_dir.iterdir():
        if item.is_dir() and "results" in item.name:
            # Extract contract name from directory name
            contract_name = item.name.replace("_page_1_results", "").replace("_page_2_results", "")
            
            # Find JSON file in the directory
            json_file = item / "page_1_res.json"
            if json_file.exists():
                page_num = "page_1" if "page_1" in item.name else "page_2"
                
                if contract_name not in contracts:
                    contracts[contract_name] = {}
                
                contracts[contract_name][page_num] = str(json_file)
    
    return contracts


def test_single_contract(contract_name: str, json_files: dict, extractor: DataExtractor) -> TelkomContractData:
    """Test extraction on a single contract"""
    
    logger.info(f"Testing extraction for: {contract_name}")
    
    # Prepare list of JSON files for this contract
    file_paths = []
    for page_key in sorted(json_files.keys()):
        file_paths.append(json_files[page_key])
    
    logger.info(f"Processing {len(file_paths)} JSON files: {[Path(f).parent.name for f in file_paths]}")
    
    # Extract data
    result = extractor.extract_from_json_files(file_paths)
    
    return result


def display_extraction_results(contract_name: str, data: TelkomContractData):
    """Display extracted data in a readable format"""
    
    print(f"\n{'='*60}")
    print(f"EXTRACTION RESULTS: {contract_name}")
    print(f"{'='*60}")
    
    # Contract Information
    print(f"\n📄 CONTRACT INFORMATION:")
    if data.informasi_kontrak:
        print(f"   Contract Number: {data.informasi_kontrak.nomor_kontrak or 'Not found'}")
        if data.informasi_kontrak.jangka_waktu:
            print(f"   Start Date: {data.informasi_kontrak.jangka_waktu.mulai or 'Not found'}")
            print(f"   End Date: {data.informasi_kontrak.jangka_waktu.akhir or 'Not found'}")
    else:
        print("   No contract information extracted")
    
    # Customer Information
    print(f"\n👤 CUSTOMER INFORMATION:")
    if data.informasi_pelanggan:
        print(f"   Customer Name: {data.informasi_pelanggan.nama_pelanggan or 'Not found'}")
        print(f"   Address: {data.informasi_pelanggan.alamat or 'Not found'}")
        print(f"   NPWP: {data.informasi_pelanggan.npwp or 'Not found'}")
        print(f"   Contact Person: {data.informasi_pelanggan.kontak_person or 'Not found'}")
        if data.informasi_pelanggan.perwakilan:
            print(f"   Representative: {data.informasi_pelanggan.perwakilan.nama or 'Not found'}")
            print(f"   Position: {data.informasi_pelanggan.perwakilan.jabatan or 'Not found'}")
    else:
        print("   No customer information extracted")
    
    # Telkom Contact
    print(f"\n📞 TELKOM CONTACT:")
    print(f"   Contact Person: {data.kontak_person_telkom or 'Not found'}")
    
    # Services
    print(f"\n🛠️  SERVICE INFORMATION:")
    if data.layanan_utama:
        print(f"   Connectivity Services: {data.layanan_utama.connectivity_telkom}")
        print(f"   Non-Connectivity Services: {data.layanan_utama.non_connectivity_telkom}")
        print(f"   Bundling Services: {data.layanan_utama.bundling}")
    
    if data.rincian_layanan_tabel:
        print(f"\n📊 SERVICE DETAILS ({len(data.rincian_layanan_tabel)} entries):")
        for i, service in enumerate(data.rincian_layanan_tabel, 1):
            print(f"   {i}. Service: {service.LAYANAN or 'N/A'}")
            print(f"      Quantity: {service.JUMLAH or 'N/A'}")
            print(f"      Location: {service.LOKASI or 'N/A'}")
            print(f"      Bandwidth: {service.LEBAR_PITA or 'N/A'}")
            print(f"      Monthly Cost: {service.BULANAN or 'N/A'}")
    else:
        print("   No service details extracted")
    
    # Payment Information
    print(f"\n💳 PAYMENT INFORMATION:")
    if data.tata_cara_pembayaran:
        print(f"   Payment Method: {data.tata_cara_pembayaran[:100]}...")
    else:
        print("   No payment information extracted")


def save_extraction_results(contract_name: str, data: TelkomContractData):
    """Save extracted data to JSON file"""
    
    # Create results directory
    results_dir = Path("output/extraction_results")
    results_dir.mkdir(exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = contract_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"{clean_name}_extracted_{timestamp}.json"
    
    # Save data
    output_path = results_dir / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        # Convert Pydantic model to dict, then to JSON
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Extraction results saved to: {output_path}")
    return output_path


def main():
    """Main test function"""
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )
    
    logger.info("="*70)
    logger.info("TELKOM CONTRACT DATA EXTRACTOR TEST")
    logger.info("="*70)
    
    # Find all contract JSON files
    contracts = find_contract_json_files()
    
    if not contracts:
        logger.error("No contract JSON files found in output directory")
        logger.info("Make sure you've run the pipeline processor first")
        return
    
    logger.info(f"Found {len(contracts)} contracts to test:")
    for contract_name in contracts.keys():
        pages = list(contracts[contract_name].keys())
        logger.info(f"  - {contract_name} ({len(pages)} pages)")
    
    # Initialize extractor
    extractor = DataExtractor()
    extractor.set_debug_mode(True)  # Enable debug logging
    
    # Test each contract
    all_results = {}
    
    for contract_name, json_files in contracts.items():
        try:
            # Extract data
            extracted_data = test_single_contract(contract_name, json_files, extractor)
            
            # Display results
            display_extraction_results(contract_name, extracted_data)
            
            # Save results
            output_path = save_extraction_results(contract_name, extracted_data)
            
            all_results[contract_name] = {
                "success": True,
                "data": extracted_data,
                "output_file": str(output_path)
            }
            
        except Exception as e:
            logger.error(f"Error testing contract {contract_name}: {str(e)}")
            all_results[contract_name] = {
                "success": False,
                "error": str(e)
            }
    
    # Final summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    
    successful = sum(1 for r in all_results.values() if r["success"])
    total = len(all_results)
    
    print(f"Contracts tested: {total}")
    print(f"Successful extractions: {successful}")
    print(f"Failed extractions: {total - successful}")
    
    if successful > 0:
        print(f"\n✓ Extracted data saved to: output/extraction_results/")
    
    if total - successful > 0:
        print(f"\n✗ Failed contracts:")
        for contract_name, result in all_results.items():
            if not result["success"]:
                print(f"  - {contract_name}: {result['error']}")
    
    print(f"{'='*70}")
    logger.info("Data extraction testing completed")


if __name__ == "__main__":
    main()