from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# === Customer Information ===
class Perwakilan(BaseModel):
    nama: Optional[str] = None
    jabatan: Optional[str] = None

class InformasiPelanggan(BaseModel):
    nama_pelanggan: Optional[str] = None
    alamat: Optional[str] = None
    npwp: Optional[str] = None
    perwakilan: Optional[Perwakilan] = None
    kontak_person: Optional[str] = None

# === Contract Information ===
class JangkaWaktu(BaseModel):
    mulai: Optional[str] = None  # Format: YYYY-MM-DD
    akhir: Optional[str] = None  # Format: YYYY-MM-DD

class InformasiKontrak(BaseModel):
    nomor_kontrak: Optional[str] = None
    jangka_waktu: Optional[JangkaWaktu] = None

# === Service Information ===
class LayananUtama(BaseModel):
    connectivity_telkom: Optional[int] = 0
    non_connectivity_telkom: Optional[int] = 0
    bundling: Optional[int] = 0

class RincianLayanan(BaseModel):
    NO: Optional[str] = None
    LAYANAN: Optional[str] = None
    JUMLAH: Optional[str] = None
    LOKASI: Optional[str] = None
    ALAMAT_INSTALASI: Optional[str] = None
    PIC: Optional[str] = None
    LEBAR_PITA: Optional[str] = None
    INSTALASI: Optional[str] = None
    BULANAN: Optional[str] = None
    TAHUNAN: Optional[str] = None
    KET: Optional[str] = None

# === Main Extraction Result ===
class TelkomContractData(BaseModel):
    informasi_pelanggan: Optional[InformasiPelanggan] = None
    informasi_kontrak: Optional[InformasiKontrak] = None
    layanan_utama: Optional[LayananUtama] = None
    rincian_layanan_tabel: Optional[List[RincianLayanan]] = []
    tata_cara_pembayaran: Optional[str] = None
    kontak_person_telkom: Optional[str] = None
    
    # Additional metadata
    extraction_timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    confidence_score: Optional[float] = None
    processing_time_seconds: Optional[float] = None

# === API Request/Response Models ===
class ExtractionRequest(BaseModel):
    file_name: str
    extract_format: str = Field(default="json", description="Output format: json or excel")
    
class ExtractionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[TelkomContractData] = None
    file_path: Optional[str] = None  # Path to generated Excel file if requested
    processing_time: Optional[float] = None
    
class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)