"""
Data Extractor for Telkom Contract Documents

This module extracts structured data from PP-StructureV3 JSON outputs using 
template-based sequential processing. It leverages the consistent document 
template structure to reliably extract contract information.

Author: Claude Code Assistant
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from loguru import logger
from bs4 import BeautifulSoup

from app.models.schemas import (
    TelkomContractData, InformasiPelanggan, InformasiKontrak, 
    LayananUtama, RincianLayanan, Perwakilan, JangkaWaktu
)


class DataExtractor:
    """
    Template-based data extractor for Telkom contract documents.
    
    Uses the consistent document template structure and sequential label processing
    to extract contract information from PP-StructureV3 JSON outputs.
    """
    
    def __init__(self):
        self.debug_mode = False
        
        # Contract number regex pattern as backup
        self.contract_number_pattern = re.compile(r'K\.TEL\.[^/]+/[^/]+/[^/]+/\d{4}')
        
        # NPWP pattern
        self.npwp_pattern = re.compile(r'\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}')
    
    def set_debug_mode(self, enabled: bool = True):
        """Enable debug logging for troubleshooting"""
        self.debug_mode = enabled
    
    def debug_log(self, message: str):
        """Log debug message if debug mode is enabled"""
        if self.debug_mode:
            logger.debug(f"[DataExtractor] {message}")
    
    def extract_from_json_files(self, json_file_paths: List[str]) -> TelkomContractData:
        """
        Main extraction method - processes multiple JSON files (pages)
        
        Args:
            json_file_paths: List of paths to JSON result files from PP-StructureV3
            
        Returns:
            TelkomContractData: Structured contract data
        """
        try:
            logger.info(f"Starting data extraction from {len(json_file_paths)} JSON files")
            
            # Load and parse all JSON files
            all_pages_data = []
            for json_path in json_file_paths:
                page_data = self._load_json_file(json_path)
                if page_data:
                    all_pages_data.append(page_data)
            
            if not all_pages_data:
                logger.error("No valid JSON data found")
                return TelkomContractData()
            
            # Combine all parsing results from all pages
            combined_blocks = []
            for page_data in all_pages_data:
                if "parsing_res_list" in page_data:
                    combined_blocks.extend(page_data["parsing_res_list"])
            
            self.debug_log(f"Combined {len(combined_blocks)} blocks from all pages")
            
            # Extract different types of information
            contract_info = self._extract_contract_information(combined_blocks)
            customer_info = self._extract_customer_information(combined_blocks)
            telkom_contact = self._extract_telkom_contact(combined_blocks)
            service_summary = self._extract_service_summary(combined_blocks)
            service_details = self._extract_service_details(combined_blocks)
            payment_info = self._extract_payment_information(combined_blocks)
            
            # Build final result
            result = TelkomContractData(
                informasi_pelanggan=customer_info,
                informasi_kontrak=contract_info,
                layanan_utama=service_summary,
                rincian_layanan_tabel=service_details,
                tata_cara_pembayaran=payment_info,
                kontak_person_telkom=telkom_contact
            )
            
            logger.info("Data extraction completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in data extraction: {str(e)}")
            return TelkomContractData()
    
    def _load_json_file(self, json_path: str) -> Optional[Dict[str, Any]]:
        """Load and parse a JSON file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.debug_log(f"Loaded JSON file: {json_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading JSON file {json_path}: {str(e)}")
            return None
    
    def _find_section_marker(self, blocks: List[Dict], marker: str) -> Optional[int]:
        """
        Find the index of a section marker in the blocks
        
        Args:
            blocks: List of parsing result blocks
            marker: Section marker to find (e.g., "2.PELANGGAN")
            
        Returns:
            Index of the block containing the marker, or None if not found
        """
        # Try exact match first
        for i, block in enumerate(blocks):
            content = block.get("block_content", "").strip()
            if marker in content:
                self.debug_log(f"Found section marker '{marker}' at block {i}")
                return i
        
        # Try alternative patterns for PELANGGAN
        if "PELANGGAN" in marker:
            alternative_markers = [
                "PELANGGAN CUSTOMER", 
                "2.PELANGGAN CUSTOMER",
                "CUSTOMER",
                "Identitas Perusahaan/Institusi"
            ]
            
            for alt_marker in alternative_markers:
                for i, block in enumerate(blocks):
                    content = block.get("block_content", "").strip()
                    if alt_marker in content:
                        self.debug_log(f"Found alternative section marker '{alt_marker}' at block {i}")
                        return i
        
        self.debug_log(f"Section marker '{marker}' not found")
        return None
    
    def _get_next_labeled_block(self, blocks: List[Dict], start_index: int, label: str) -> Optional[Tuple[int, str]]:
        """
        Find the next block with a specific label and return the following block's content
        
        Args:
            blocks: List of parsing result blocks
            start_index: Index to start searching from
            label: Label to search for (e.g., "Nama", "Alamat")
            
        Returns:
            Tuple of (block_index, content) or None if not found
        """
        for i in range(start_index, len(blocks) - 1):
            content = blocks[i].get("block_content", "").strip()
            
            # Check if this block contains the label
            if label in content:
                # Return the content of the next block
                next_block = blocks[i + 1]
                next_content = next_block.get("block_content", "").strip()
                
                self.debug_log(f"Found label '{label}' at block {i}, next content: '{next_content[:50]}...'")
                return (i + 1, next_content)
        
        self.debug_log(f"Label '{label}' not found after index {start_index}")
        return None
    
    def _extract_contract_information(self, blocks: List[Dict]) -> InformasiKontrak:
        """Extract contract number and date information"""
        try:
            self.debug_log("Extracting contract information")
            
            contract_number = None
            
            # Method 1: Look for "Nomor Kontrak" label
            contract_result = self._get_next_labeled_block(blocks, 0, "Nomor Kontrak")
            if contract_result:
                _, content = contract_result
                # Use regex to extract contract number from the content
                match = self.contract_number_pattern.search(content)
                if match:
                    contract_number = match.group(0)
            
            # Method 2: Fallback - search all blocks for contract number pattern
            if not contract_number:
                for block in blocks:
                    content = block.get("block_content", "")
                    match = self.contract_number_pattern.search(content)
                    if match:
                        contract_number = match.group(0)
                        break
            
            self.debug_log(f"Extracted contract number: {contract_number}")
            
            # TODO: Extract date range information
            # This would require finding date patterns or specific date sections
            
            return InformasiKontrak(
                nomor_kontrak=contract_number,
                jangka_waktu=None  # Will implement date extraction later
            )
            
        except Exception as e:
            logger.error(f"Error extracting contract information: {str(e)}")
            return InformasiKontrak()
    
    def _extract_customer_information(self, blocks: List[Dict]) -> InformasiPelanggan:
        """Extract customer information using template-based sequential processing"""
        try:
            self.debug_log("Extracting customer information")
            
            # Find the customer section using improved detection
            pelanggan_index = self._find_section_marker(blocks, "2.PELANGGAN")
            
            if pelanggan_index is None:
                logger.warning("Could not find PELANGGAN section, trying fallback methods")
                # Fallback: look for any customer-related data in the blocks
                return self._extract_customer_fallback(blocks)
            
            # Extract customer data sequentially after the section marker
            search_start = pelanggan_index
            
            # Get customer name - look for "Nama" that's not Telkom contact
            customer_name = None
            nama_results = []
            
            # Find all "Nama" occurrences
            current_search = search_start
            while current_search < len(blocks):
                nama_result = self._get_next_labeled_block(blocks, current_search, "Nama")
                if nama_result:
                    idx, content = nama_result
                    nama_results.append((idx, content))
                    current_search = idx + 1
                else:
                    break
            
            # Take the first "Nama" after the PELANGGAN section
            if nama_results:
                customer_name = nama_results[0][1]
            
            # Get customer address (after "Alamat")
            alamat_result = self._get_next_labeled_block(blocks, search_start, "Alamat")
            customer_address = alamat_result[1] if alamat_result else None
            
            # Get NPWP (after "NPWP")
            npwp_result = self._get_next_labeled_block(blocks, search_start, "NPWP")
            npwp_number = None
            if npwp_result:
                _, content = npwp_result
                # Use regex to clean up NPWP format
                match = self.npwp_pattern.search(content)
                npwp_number = match.group(0) if match else content.strip()
            
            # Get representative information
            representative_name = None
            representative_position = None
            
            # Look for representative after customer info
            if len(nama_results) > 1:
                # Take the second name occurrence as representative
                representative_name = nama_results[1][1]
                
                # Get representative position
                rep_start = nama_results[1][0]
                rep_jabatan_result = self._get_next_labeled_block(blocks, rep_start, "Jabatan")
                representative_position = rep_jabatan_result[1] if rep_jabatan_result else None
            
            # Create representative object
            perwakilan = None
            if representative_name or representative_position:
                perwakilan = Perwakilan(nama=representative_name, jabatan=representative_position)
            
            self.debug_log(f"Extracted customer: {customer_name}, Address: {customer_address[:50] if customer_address else None}...")
            
            return InformasiPelanggan(
                nama_pelanggan=customer_name,
                alamat=customer_address,
                npwp=npwp_number,
                perwakilan=perwakilan,
                kontak_person=representative_name
            )
            
        except Exception as e:
            logger.error(f"Error extracting customer information: {str(e)}")
            return InformasiPelanggan()
    
    def _extract_customer_fallback(self, blocks: List[Dict]) -> InformasiPelanggan:
        """Fallback method to extract customer information without section markers"""
        try:
            self.debug_log("Using fallback customer extraction")
            
            # Look for common customer patterns in the text
            for i, block in enumerate(blocks):
                content = block.get("block_content", "").strip()
                
                # Check if this looks like customer name (after getting contract number)
                if any(school_indicator in content.upper() for school_indicator in ["SMK", "NEGERI", "ABIPRAYA", "PT ", "CV ", "KOPERASI"]):
                    # This might be customer name
                    customer_name = content
                    
                    # Look for address in nearby blocks
                    customer_address = None
                    npwp_number = None
                    
                    # Check next few blocks for address and NPWP
                    for j in range(i + 1, min(i + 5, len(blocks))):
                        next_content = blocks[j].get("block_content", "").strip()
                        
                        # Check for NPWP pattern
                        npwp_match = self.npwp_pattern.search(next_content)
                        if npwp_match and not npwp_number:
                            npwp_number = npwp_match.group(0)
                        
                        # Check for address pattern (contains street/location indicators)
                        if any(addr_indicator in next_content.upper() for addr_indicator in ["JL.", "JALAN", "NO.", "KOTA", "ACEH", "BANDA"]) and not customer_address:
                            customer_address = next_content
                    
                    if customer_name:
                        self.debug_log(f"Fallback extracted customer: {customer_name[:50]}...")
                        return InformasiPelanggan(
                            nama_pelanggan=customer_name,
                            alamat=customer_address,
                            npwp=npwp_number
                        )
            
            return InformasiPelanggan()
            
        except Exception as e:
            logger.error(f"Error in fallback customer extraction: {str(e)}")
            return InformasiPelanggan()
    
    def _extract_telkom_contact(self, blocks: List[Dict]) -> Optional[str]:
        """Extract Telkom contact person (first 'Diwakili secara sah oleh')"""
        try:
            self.debug_log("Extracting Telkom contact information")
            
            # Find first "Diwakili secara sah oleh" (Telkom side)
            for i, block in enumerate(blocks):
                content = block.get("block_content", "").strip()
                if "Diwakili secara sah oleh" in content:
                    # Get the next "Nama" after this marker
                    nama_result = self._get_next_labeled_block(blocks, i, "Nama")
                    if nama_result:
                        _, telkom_contact = nama_result
                        self.debug_log(f"Extracted Telkom contact: {telkom_contact}")
                        return telkom_contact
                    break
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Telkom contact: {str(e)}")
            return None
    
    def _extract_service_summary(self, blocks: List[Dict]) -> LayananUtama:
        """Extract service summary counts"""
        try:
            # This will be implemented to analyze table data for service counts
            # For now, return empty structure
            return LayananUtama()
            
        except Exception as e:
            logger.error(f"Error extracting service summary: {str(e)}")
            return LayananUtama()
    
    def _extract_service_details(self, blocks: List[Dict]) -> List[RincianLayanan]:
        """Extract detailed service information from tables"""
        try:
            self.debug_log("Extracting service details from tables")
            
            service_details = []
            
            # Find table blocks
            for block in blocks:
                if block.get("block_label") == "table":
                    html_content = block.get("block_content", "")
                    if html_content:
                        # Parse HTML table
                        parsed_services = self._parse_service_table(html_content)
                        service_details.extend(parsed_services)
            
            self.debug_log(f"Extracted {len(service_details)} service entries")
            return service_details
            
        except Exception as e:
            logger.error(f"Error extracting service details: {str(e)}")
            return []
    
    def _parse_service_table(self, html_content: str) -> List[RincianLayanan]:
        """Parse HTML table content to extract service details"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            services = []
            
            # Find table rows
            rows = soup.find_all('tr')
            
            # Skip header rows and process data rows
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                
                # Skip rows with too few cells or header rows
                if len(cells) < 3 or i < 2:  # Skip first 2 rows (headers)
                    continue
                
                # Extract cell text
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                
                # Skip empty rows
                if not any(cell_texts):
                    continue
                
                # Map cells to service structure (adjust indices based on table structure)
                service = RincianLayanan()
                
                if len(cell_texts) > 0 and cell_texts[0]:
                    service.NO = cell_texts[0]
                if len(cell_texts) > 1 and cell_texts[1]:
                    service.LAYANAN = cell_texts[1]
                if len(cell_texts) > 2 and cell_texts[2]:
                    service.JUMLAH = cell_texts[2]
                if len(cell_texts) > 3 and cell_texts[3]:
                    service.LOKASI = cell_texts[3]
                if len(cell_texts) > 4 and cell_texts[4]:
                    service.ALAMAT_INSTALASI = cell_texts[4]
                if len(cell_texts) > 5 and cell_texts[5]:
                    service.PIC = cell_texts[5]
                if len(cell_texts) > 6 and cell_texts[6]:
                    service.LEBAR_PITA = cell_texts[6]
                if len(cell_texts) > 7 and cell_texts[7]:
                    service.INSTALASI = cell_texts[7]
                if len(cell_texts) > 8 and cell_texts[8]:
                    service.BULANAN = cell_texts[8]
                if len(cell_texts) > 9 and cell_texts[9]:
                    service.TAHUNAN = cell_texts[9]
                if len(cell_texts) > 10 and cell_texts[10]:
                    service.KET = cell_texts[10]
                
                # Only add if we have meaningful data
                if service.LAYANAN:
                    services.append(service)
            
            self.debug_log(f"Parsed {len(services)} services from HTML table")
            return services
            
        except Exception as e:
            logger.error(f"Error parsing service table: {str(e)}")
            return []
    
    def _extract_payment_information(self, blocks: List[Dict]) -> Optional[str]:
        """Extract payment method information"""
        try:
            self.debug_log("Extracting payment information")
            
            # Look for payment-related sections
            payment_keywords = ["TATA CARA PEMBAYARAN", "PEMBAYARAN", "PAYMENT"]
            
            for keyword in payment_keywords:
                marker_index = self._find_section_marker(blocks, keyword)
                if marker_index is not None:
                    # Get text from next few blocks
                    payment_text_parts = []
                    for i in range(marker_index + 1, min(marker_index + 5, len(blocks))):
                        content = blocks[i].get("block_content", "").strip()
                        if content and len(content) > 10:  # Avoid short text
                            payment_text_parts.append(content)
                    
                    if payment_text_parts:
                        payment_info = " ".join(payment_text_parts)
                        self.debug_log(f"Extracted payment info: {payment_info[:100]}...")
                        return payment_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting payment information: {str(e)}")
            return None