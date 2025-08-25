from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# === Customer Information ===
class Perwakilan(BaseModel):
    nama: Optional[str] = None
    jabatan: Optional[str] = None

class KontakPersonPelanggan(BaseModel):
    nama: Optional[str] = None
    jabatan: Optional[str] = None
    email: Optional[str] = None
    telepon: Optional[str] = None

class InformasiPelanggan(BaseModel):
    nama_pelanggan: Optional[str] = None
    alamat: Optional[str] = None
    npwp: Optional[str] = None
    perwakilan: Optional[Perwakilan] = None
    kontak_person: Optional[KontakPersonPelanggan] = None

# === Contract Information ===
class JangkaWaktu(BaseModel):
    mulai: Optional[str] = None  # YYYY-MM-DD
    akhir: Optional[str] = None  # YYYY-MM-DD

class KontakPersonTelkom(BaseModel):
    nama: Optional[str] = None
    jabatan: Optional[str] = None
    email: Optional[str] = None
    telepon: Optional[str] = None

# === Service Information ===
class LayananUtama(BaseModel):
    connectivity_telkom: int = 0
    non_connectivity_telkom: int = 0
    bundling: int = 0

class RincianLayanan(BaseModel):
    biaya_instalasi: float = 0.0
    biaya_langganan_tahunan: float = 0.0
    tata_cara_pembayaran: Optional["TataCaraPembayaran"] = None

# === Payment Method Information ===
class TerminPayment(BaseModel):
    """Individual termin payment entry"""
    termin_number: int = Field(..., description="Termin sequence number (1, 2, 3, etc.)")
    period: str = Field(..., description="Payment period (e.g., 'Maret 2025', 'Juni 2025')")
    amount: float = Field(..., description="Payment amount in Rupiah")
    raw_text: Optional[str] = Field(None, description="Original text for debugging")

class TataCaraPembayaran(BaseModel):
    """Payment method information supporting multiple payment types"""
    method_type: str = Field(..., description="Payment method type: 'one_time_charge', 'recurring', 'termin'")
    
    # For simple methods (one_time_charge, recurring)
    description: Optional[str] = Field(None, description="Payment method description for simple methods")
    
    # For termin method
    termin_payments: Optional[List[TerminPayment]] = Field(None, description="List of termin payment entries")
    total_termin_count: Optional[int] = Field(None, description="Total number of termin payments")
    total_amount: Optional[float] = Field(None, description="Total amount across all termin payments")
    
    # Original raw text for all types
    raw_text: Optional[str] = Field(None, description="Original extracted text for debugging")

# === Main Extraction Result ===
class TelkomContractData(BaseModel):
    # inti kontrak
    informasi_pelanggan: Optional[InformasiPelanggan] = None
    layanan_utama: Optional[LayananUtama] = None
    rincian_layanan: List[RincianLayanan] = Field(default_factory=list)
    tata_cara_pembayaran: Optional[TataCaraPembayaran] = None
    kontak_person_telkom: Optional[KontakPersonTelkom] = None
    jangka_waktu: Optional[JangkaWaktu] = None

    # metadata ekstraksi
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
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