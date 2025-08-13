import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List
import pandas as pd
from loguru import logger

from app.config import settings
from app.models.schemas import TelkomContractData, RincianLayanan

class FileUtils:
    """Utility class for file operations"""
    
    @staticmethod
    def save_uploaded_file(file_content: bytes, filename: str) -> str:
        """
        Save uploaded file to upload directory
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Path to saved file
        """
        try:
            # Generate unique filename
            file_extension = Path(filename).suffix
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(settings.upload_dir, unique_filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    @staticmethod
    def validate_file(filename: str, file_size: int) -> bool:
        """
        Validate uploaded file
        
        Args:
            filename: File name
            file_size: File size in bytes
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check file extension
            file_extension = Path(filename).suffix.lower()
            if file_extension not in settings.allowed_extensions:
                logger.warning(f"Invalid file extension: {file_extension}")
                return False
            
            # Check file size
            if file_size > settings.max_file_size:
                logger.warning(f"File too large: {file_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return False
    
    @staticmethod
    def create_excel_output(contract_data: TelkomContractData, filename: str) -> str:
        """
        Create Excel file with extracted contract data
        
        Args:
            contract_data: Extracted contract data
            filename: Output filename (without extension)
            
        Returns:
            Path to created Excel file
        """
        try:
            # Generate output path
            output_path = os.path.join(settings.output_dir, f"{filename}.xlsx")
            
            # Create Excel writer
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                
                # Sheet 1: Summary Information
                summary_data = FileUtils._create_summary_data(contract_data)
                summary_df = pd.DataFrame(summary_data, columns=['Field', 'Value'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Sheet 2: Service Details
                if contract_data.rincian_layanan_tabel:
                    service_data = FileUtils._create_service_data(contract_data.rincian_layanan_tabel)
                    service_df = pd.DataFrame(service_data)
                    service_df.to_excel(writer, sheet_name='Service Details', index=False)
                
                # Format worksheets
                FileUtils._format_excel_sheets(writer)
            
            logger.info(f"Excel file created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating Excel file: {str(e)}")
            raise
    
    @staticmethod
    def _create_summary_data(contract_data: TelkomContractData) -> List[List[str]]:
        """Create summary data for Excel export"""
        data = []
        
        # Contract Information
        data.append(['INFORMASI KONTRAK', ''])
        if contract_data.informasi_kontrak:
            data.append(['Nomor Kontrak', contract_data.informasi_kontrak.nomor_kontrak or ''])
            if contract_data.informasi_kontrak.jangka_waktu:
                data.append(['Tanggal Mulai', contract_data.informasi_kontrak.jangka_waktu.mulai or ''])
                data.append(['Tanggal Akhir', contract_data.informasi_kontrak.jangka_waktu.akhir or ''])
        
        data.append(['', ''])  # Empty row
        
        # Customer Information
        data.append(['INFORMASI PELANGGAN', ''])
        if contract_data.informasi_pelanggan:
            data.append(['Nama Pelanggan', contract_data.informasi_pelanggan.nama_pelanggan or ''])
            data.append(['Alamat', contract_data.informasi_pelanggan.alamat or ''])
            data.append(['NPWP', contract_data.informasi_pelanggan.npwp or ''])
            data.append(['Kontak Person', contract_data.informasi_pelanggan.kontak_person or ''])
            if contract_data.informasi_pelanggan.perwakilan:
                data.append(['Perwakilan Nama', contract_data.informasi_pelanggan.perwakilan.nama or ''])
                data.append(['Perwakilan Jabatan', contract_data.informasi_pelanggan.perwakilan.jabatan or ''])
        
        data.append(['', ''])  # Empty row
        
        # Service Summary
        data.append(['RINGKASAN LAYANAN', ''])
        if contract_data.layanan_utama:
            data.append(['Connectivity Telkom', str(contract_data.layanan_utama.connectivity_telkom)])
            data.append(['Non-Connectivity Telkom', str(contract_data.layanan_utama.non_connectivity_telkom)])
            data.append(['Bundling', str(contract_data.layanan_utama.bundling)])
        
        data.append(['', ''])  # Empty row
        
        # Other Information
        data.append(['INFORMASI LAINNYA', ''])
        data.append(['Tata Cara Pembayaran', contract_data.tata_cara_pembayaran or ''])
        data.append(['Kontak Person Telkom', contract_data.kontak_person_telkom or ''])
        
        return data
    
    @staticmethod
    def _create_service_data(services: List[RincianLayanan]) -> List[dict]:
        """Create service data for Excel export"""
        data = []
        
        for service in services:
            row = {
                'No': service.NO,
                'Layanan': service.LAYANAN,
                'Jumlah': service.JUMLAH,
                'Lokasi': service.LOKASI,
                'Alamat Instalasi': service.ALAMAT_INSTALASI,
                'PIC': service.PIC,
                'Lebar Pita (Mbps)': service.LEBAR_PITA,
                'Biaya Instalasi': service.INSTALASI,
                'Biaya Bulanan': service.BULANAN,
                'Biaya Tahunan': service.TAHUNAN,
                'Keterangan': service.KET
            }
            data.append(row)
        
        return data
    
    @staticmethod
    def _format_excel_sheets(writer):
        """Format Excel worksheets"""
        try:
            workbook = writer.book
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            data_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1
            })
            
            # Format Summary sheet
            if 'Summary' in writer.sheets:
                worksheet = writer.sheets['Summary']
                worksheet.set_column('A:A', 30)
                worksheet.set_column('B:B', 50)
                
                # Format header rows
                for row in range(20):  # Adjust range as needed
                    worksheet.set_row(row, None, data_format)
            
            # Format Service Details sheet
            if 'Service Details' in writer.sheets:
                worksheet = writer.sheets['Service Details']
                worksheet.set_column('A:K', 15)
                
                # Set header format
                for col in range(11):
                    worksheet.write(0, col, worksheet.cell(0, col).value, header_format)
            
        except Exception as e:
            logger.warning(f"Error formatting Excel sheets: {str(e)}")
    
    @staticmethod
    def cleanup_file(file_path: str) -> None:
        """
        Remove file from filesystem
        
        Args:
            file_path: Path to file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up file {file_path}: {str(e)}")
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Get file information
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        try:
            if not os.path.exists(file_path):
                return {}
            
            stat = os.stat(file_path)
            return {
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'extension': Path(file_path).suffix,
                'created': stat.st_ctime,
                'modified': stat.st_mtime
            }
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {}