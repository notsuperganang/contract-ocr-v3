# telkom_extractor.py
# Ekstraktor Telkom Contract — Page 1 (One Time Charge) + merge helper untuk Page 2
# -----------------------------------------------------
# Prasyarat: file schemas.py berisi kelas Pydantic yang sudah kamu kirim.

from __future__ import annotations
import re
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import model pydantic kamu
# Import pydantic models (support both "python -m app.services.data_extractor" and direct script run)
try:  # Preferred absolute import when package root is on sys.path
    from app.models.schemas import (
        Perwakilan,
        KontakPersonPelanggan,
        InformasiPelanggan,
        JangkaWaktu,
        KontakPersonTelkom,
        LayananUtama,
        RincianLayanan,
        TataCaraPembayaran,
        TerminPayment,
        TelkomContractData,
    )
except ModuleNotFoundError:  # Fallback for direct invocation: python app/services/data_extractor.py
    import os, sys as _sys
    _ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _ROOT not in _sys.path:
        _sys.path.insert(0, _ROOT)
    from app.models.schemas import (
        Perwakilan,
        KontakPersonPelanggan,
        InformasiPelanggan,
        JangkaWaktu,
        KontakPersonTelkom,
        LayananUtama,
        RincianLayanan,
        TataCaraPembayaran,
        TerminPayment,
        TelkomContractData,
    )

# -------------------- Utilities --------------------
_MONEY_TOKEN = re.compile(r"^\s*(?:Rp\.?|Rp)?\s*[\d\.\,]+\s*$", re.I)

def _texts_from_ocr(ocr_json: Any) -> List[str]:
    """
    Normalisasi struktur OCR ke list of strings (urutan token baris/kolom).
    Kompatibel dengan PaddleOCR-style: ocr['overall_ocr_res']['rec_texts'].
    """
    if isinstance(ocr_json, dict):
        # PaddleOCR aggregated
        overall = ocr_json.get("overall_ocr_res") or {}
        if isinstance(overall, dict) and isinstance(overall.get("rec_texts"), list):
            return [str(t) for t in overall["rec_texts"]]
        # Generic variants
        if isinstance(ocr_json.get("lines"), list):
            return [str(t) for t in ocr_json["lines"]]
        if isinstance(ocr_json.get("text"), str):
            return [ln for ln in ocr_json["text"].splitlines()]
    if isinstance(ocr_json, list):
        return [str(t) for t in ocr_json]
    if isinstance(ocr_json, str):
        return ocr_json.splitlines()
    return []

def _find_eq(texts: List[str], label: str, start: int = 0) -> Optional[int]:
    """Cari index token yang sama persis (case-insensitive) dengan label."""
    tgt = label.strip().lower()
    for i in range(start, len(texts)):
        if texts[i].strip().lower() == tgt:
            return i
    return None

def _value_after(texts: List[str], label: str, start: int = 0) -> Optional[str]:
    """Ambil token setelah label tertentu (exact-match)."""
    idx = _find_eq(texts, label, start)
    if idx is not None and idx + 1 < len(texts):
        return texts[idx + 1].strip()
    return None

def _parse_rupiah_token(tok: str) -> float:
    """Konversi token rupiah 'Rp 1.234.567,89' -> 1234567.89 (float)."""
    s = re.sub(r"[^\d,\.]", "", tok)
    if s.count(",") == 1 and s.count(".") >= 1:
        # Format ID: titik thousand, koma decimal
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0

def _next_money(texts: List[str], start_idx: int) -> float:
    """Ambil token uang pada posisi sesudah start_idx."""
    for j in range(start_idx + 1, min(start_idx + 5, len(texts))):
        if _MONEY_TOKEN.match(texts[j]):
            return _parse_rupiah_token(texts[j])
    # fallback: token persis setelahnya
    if start_idx + 1 < len(texts) and any(ch.isdigit() for ch in texts[start_idx + 1]):
        return _parse_rupiah_token(texts[start_idx + 1])
    return 0.0

def _find_count_after_phrase(texts: List[str], phrase: str) -> int:
    """Cari angka tepat setelah sebuah frasa (exact-match token)."""
    idx = _find_eq(texts, phrase)
    if idx is not None and idx + 1 < len(texts):
        nxt = re.sub(r"[^\d]", "", texts[idx + 1])
        if nxt.isdigit():
            return int(nxt)
    return 0

def _slice_after_keyword(texts: List[str], keyword: str, span: int = 12) -> str:
    """Gabung beberapa token setelah kata kunci (untuk raw_text simpanan)."""
    # cari token yang mengandung keyword (case-insensitive)
    for i, t in enumerate(texts):
        if keyword.lower() in t.lower():
            return " ".join(texts[i : min(i + span, len(texts))]).strip()
    return ""

def _get_payment_section_text(texts: List[str]) -> str:
    """
    Ekstrak teks dari seksi pembayaran untuk analisis metode pembayaran.
    Prioritas: teks di sekitar header TATA CARA PEMBAYARAN, lalu fallback ke seluruh dokumen.
    """
    # Cari teks di sekitar header pembayaran dengan span lebih besar
    payment_section = _slice_after_keyword(texts, "TATA CARA PEMBAYARAN", span=20)
    if payment_section:
        return payment_section
    
    # Fallback: cari header pembayaran alternatif
    payment_section = _slice_after_keyword(texts, "PEMBAYARAN", span=20)
    if payment_section:
        return payment_section
        
    payment_section = _slice_after_keyword(texts, "KETENTUAN PEMBAYARAN", span=20)
    if payment_section:
        return payment_section
    
    # Fallback terakhir: gabung seluruh teks dokumen
    return " ".join(texts)

def _normalize_payment_text(text: str) -> str:
    """
    Normalisasi teks pembayaran untuk deteksi yang konsisten.
    """
    text = text.lower().strip()
    # Hapus spasi berlebih dan normalize
    text = re.sub(r'\s+', ' ', text)
    # Standardisasi singkatan bulan
    text = text.replace('/bln', ' per bulan')
    text = text.replace('bln', ' bulan')
    return text

def _detect_payment_type(texts: List[str]) -> tuple[str, str, str]:
    """
    Deteksi metode pembayaran dari teks OCR.
    
    Returns:
        tuple: (method_type, description, confidence)
        - method_type: "one_time_charge", "recurring", atau "unknown"
        - description: Deskripsi metode pembayaran
        - confidence: "high", "medium", "low"
    """
    # Ekstrak teks dari seksi pembayaran
    payment_text = _get_payment_section_text(texts)
    normalized_text = _normalize_payment_text(payment_text)
    
    # Pattern untuk deteksi termin (prioritas tinggi - exclude dari recurring)
    termin_patterns = [
        r'\btermin[-\s]*\d+\b',           # Termin-1, Termin 1, etc.
        r'\btermin\s+(pertama|kedua|ketiga|keempat|kelima)\b',  # Termin pertama, dll
    ]
    
    # Cek eksplisit "One Time Charge" untuk prioritas tinggi
    if re.search(r'\bone\s*time\s*charge\b', normalized_text, re.I):
        return "one_time_charge", "One Time Charge", "high"
    
    # Cek apakah ada pola termin
    for pattern in termin_patterns:
        if re.search(pattern, normalized_text, re.I):
            # Deteksi termin sebagai method type tersendiri
            return "termin", "Pembayaran termin terdeteksi", "high"
    
    # Pattern untuk deteksi recurring (Indonesian + English)
    recurring_patterns = [
        r'\brecurring\b',                          # Explicit "recurring"
        r'\bperbulan\b|\bper\s*bulan\b',          # "perbulan", "per bulan"
        r'\bbulanan\b',                           # "bulanan"
        r'\bsetiap\s*bulan\b',                    # "setiap bulan"
        r'\bpembayaran\s*bulanan\b',              # "pembayaran bulanan"
        r'\btagihan\s*bulanan\b',                 # "tagihan bulanan"
        r'\blangganan\s*bulanan\b',               # "langganan bulanan"
        r'\bmonthly\b',                           # "monthly"
        r'\brecurring\s*monthly\b',               # "recurring monthly"
        r'\bbilling\s*cycle\s*:\s*monthly\b',     # "billing cycle: monthly"
        r'\bper\s*/?\s*bulan\b',                  # "per/bulan"
    ]
    
    # Cari pola recurring dalam teks seksi pembayaran (confidence tinggi)
    payment_section_only = _slice_after_keyword(texts, "TATA CARA PEMBAYARAN", span=20)
    if payment_section_only:
        normalized_section = _normalize_payment_text(payment_section_only)
        for pattern in recurring_patterns:
            match = re.search(pattern, normalized_section, re.I)
            if match:
                matched_phrase = match.group(0)
                return "recurring", f"Pembayaran bulanan terdeteksi (frasa: '{matched_phrase}')", "high"
    
    # Cari pola recurring di seluruh dokumen (confidence medium)
    for pattern in recurring_patterns:
        match = re.search(pattern, normalized_text, re.I)
        if match:
            matched_phrase = match.group(0)
            return "recurring", f"Pembayaran bulanan terdeteksi (frasa: '{matched_phrase}')", "medium"
    
    # Cek keberadaan header tabel "BULANAN" sebagai indikator recurring
    # Tapi hanya jika tidak ada indikator One Time Charge yang eksplisit
    full_text = " ".join(texts)
    if re.search(r'\bBULANAN\b', full_text, re.I):
        return "recurring", "Pembayaran bulanan terdeteksi (tabel biaya bulanan)", "medium"
    
    # Default: tidak dapat menentukan, assume one_time_charge untuk backward compatibility
    return "one_time_charge", "Metode pembayaran tidak terdeteksi", "low"

def _extract_termin_payments(texts: List[str]) -> tuple[List[TerminPayment], int, float]:
    """
    Ekstrak daftar pembayaran termin dari teks OCR.
    
    Returns:
        tuple: (termin_list, total_count, total_amount)
    """
    # Cari teks dari seksi pembayaran
    payment_text = _get_payment_section_text(texts)
    
    # Pattern untuk menangkap termin dengan berbagai format
    # Cocokkan bulan dan tahun, lalu kata kunci sebelum Rp
    termin_pattern = re.compile(
        r'Termin[-\s]*(\d+)[,\s]*yaitu\s+periode\s+(\w+\s*\d{4})\s*(?:sebesar\s*[:]*\s*)?[:]?\s*Rp\.?([\d\.,]+)',
        re.IGNORECASE
    )
    
    termin_payments = []
    total_amount = 0.0
    
    # Cari semua matches dalam teks
    matches = termin_pattern.findall(payment_text)
    
    for match in matches:
        try:
            termin_num = int(match[0])
            period = match[1].strip()
            amount_str = match[2].strip()
            
            # Bersihkan amount string dari karakter trailing
            amount_str = re.sub(r'[^\d\.,]', '', amount_str)
            # Parse amount dengan handling format Indonesia (titik sebagai thousand separator, koma sebagai decimal)
            amount = _parse_rupiah_token("Rp " + amount_str)
            
            # Buat raw text untuk debugging
            raw_match = re.search(
                rf'Termin[-\s]*{termin_num}[^R]*?[Rp\.\s]*{re.escape(amount_str)}[,\.]?',
                payment_text, re.IGNORECASE
            )
            raw_text = raw_match.group(0) if raw_match else f"Termin-{termin_num} {period} {amount_str}"
            
            termin_payment = TerminPayment(
                termin_number=termin_num,
                period=period,
                amount=amount,
                raw_text=raw_text.strip()
            )
            
            termin_payments.append(termin_payment)
            total_amount += amount
            
        except (ValueError, IndexError) as e:
            # Log error tapi lanjutkan parsing termin lainnya
            continue
    
    # Sort berdasarkan nomor termin
    termin_payments.sort(key=lambda t: t.termin_number)
    
    return termin_payments, len(termin_payments), total_amount


# -------------------- Page 1 Extractor (One Time Charge) --------------------
def extract_from_page1_one_time(ocr_json_page1: Any) -> TelkomContractData:
    """
    Ekstraksi dari PAGE 1 untuk kasus 'One Time Charge'.
    - Mengisi: informasi_pelanggan (nama, alamat, npwp, perwakilan jika ada),
               layanan_utama (count),
               rincian_layanan (biaya instalasi & langganan tahunan),
               tata_cara_pembayaran (one_time_charge + raw_text).
    - Placeholder: kontak_person_telkom, informasi_pelanggan.kontak_person, jangka_waktu.
    """
    t0 = time.time()
    texts = _texts_from_ocr(ocr_json_page1)

    # --- Informasi Pelanggan ---
    # Heuristik: cari blok "2.PELANGGAN" lalu ambil "Nama", "Alamat", "NPWP" setelahnya
    nama_pelanggan = alamat = npwp = None
    perwakilan_nama = perwakilan_jabatan = None

    # Cari anchor pelanggan
    idx_pelanggan = None
    for i, tok in enumerate(texts):
        if tok.strip().startswith("2.PELANGGAN"):
            idx_pelanggan = i
            break

    if idx_pelanggan is not None:
        nama_pelanggan = _value_after(texts, "Nama", start=idx_pelanggan) or nama_pelanggan
        alamat = _value_after(texts, "Alamat", start=idx_pelanggan) or alamat
        npwp = _value_after(texts, "NPWP", start=idx_pelanggan) or npwp

        # Jika di page 1 ada "Diwakili secara sah oleh:" untuk pelanggan → isi perwakilan
        # (Kalau tidak ada, biarkan None)
        # Cari token "Diwakili secara sah oleh:" sesudah anchor
        idx_rep = None
        for j in range(idx_pelanggan + 1, len(texts)):
            if "Diwakili secara sah oleh:" in texts[j]:
                idx_rep = j
                break
        if idx_rep is not None:
            perwakilan_nama = _value_after(texts, "Nama", start=idx_rep) or perwakilan_nama
            perwakilan_jabatan = _value_after(texts, "Jabatan", start=idx_rep) or perwakilan_jabatan

    informasi_pelanggan = InformasiPelanggan(
        nama_pelanggan=nama_pelanggan,
        alamat=alamat,
        npwp=npwp,
        perwakilan=Perwakilan(nama=perwakilan_nama, jabatan=perwakilan_jabatan) if (perwakilan_nama or perwakilan_jabatan) else None,
        kontak_person=None,  # placeholder (ada di Page 2)
    )

    # --- Layanan Utama (counts) ---
    connectivity = _find_count_after_phrase(texts, "Layanan Connectivity TELKOM")
    non_connectivity = _find_count_after_phrase(texts, "Layanan Non-Connectivity TELKOM")
    # Jika bundling tidak muncul dengan angka di halaman 1 → set 0
    bundling = _find_count_after_phrase(texts, "Bundling Layanan Connectivity TELKOM& Solusi")
    layanan_utama = LayananUtama(
        connectivity_telkom=connectivity,
        non_connectivity_telkom=non_connectivity,
        bundling=bundling or 0,
    )

    # --- Rincian Layanan (biaya) ---
    biaya_instalasi = 0.0
    biaya_langganan_tahunan = 0.0

    idx_bi_inst = _find_eq(texts, "Biaya Instalasi")
    if idx_bi_inst is not None:
        biaya_instalasi = _next_money(texts, idx_bi_inst)

    idx_bi_lang_tahun = _find_eq(texts, "Biaya Langganan Tahunan")
    if idx_bi_lang_tahun is not None:
        biaya_langganan_tahunan = _next_money(texts, idx_bi_lang_tahun)

    rincian_layanan = [
        RincianLayanan(
            biaya_instalasi=biaya_instalasi,
            biaya_langganan_tahunan=biaya_langganan_tahunan,
            tata_cara_pembayaran=None,  # di level utama kita isi di bawah
        )
    ]

    # --- Tata Cara Pembayaran (Dynamic Detection) ---
    raw_tata = _slice_after_keyword(texts, "TATA CARA PEMBAYARAN", span=16)
    
    # Deteksi metode pembayaran secara dinamis
    method_type, description, confidence = _detect_payment_type(texts)
    
    # Jika termin, ekstrak detail pembayaran termin
    termin_payments = None
    total_termin_count = None
    total_amount = None
    
    if method_type == "termin":
        termin_list, count, amount = _extract_termin_payments(texts)
        if termin_list:  # Jika berhasil ekstrak termin
            termin_payments = termin_list
            total_termin_count = count
            total_amount = amount
            description = f"Pembayaran termin ({count} periode)"
        else:
            # Fallback jika deteksi termin gagal
            method_type = "one_time_charge"
            description = "Pembayaran termin terdeteksi (gagal ekstrak detail)"
    
    tata_cara_pembayaran = TataCaraPembayaran(
        method_type=method_type,
        description=description,
        termin_payments=termin_payments,
        total_termin_count=total_termin_count,
        total_amount=total_amount,
        raw_text=raw_tata or None,
    )

    # --- Kontak Person Telkom (placeholder; ada di Page 2) ---
    kontak_person_telkom = KontakPersonTelkom(
        nama=None, jabatan=None, email=None, telepon=None
    )

    # --- Jangka Waktu (placeholder; ada di Page 2) ---
    jangka_waktu = JangkaWaktu(mulai=None, akhir=None)

    data = TelkomContractData(
        informasi_pelanggan=informasi_pelanggan,
        layanan_utama=layanan_utama,
        rincian_layanan=rincian_layanan,
        tata_cara_pembayaran=tata_cara_pembayaran,
        kontak_person_telkom=kontak_person_telkom,
        jangka_waktu=jangka_waktu,
        extraction_timestamp=datetime.now(),
        processing_time_seconds=round(time.time() - t0, 3),
    )
    return data


# -------------------- Indonesian date parsing (robust) --------------------
_ID_MONTHS = {
    "jan": 1, "januari": 1,
    "feb": 2, "februari": 2,
    "mar": 3, "maret": 3,
    "apr": 4, "april": 4,
    "mei": 5,
    "jun": 6, "juni": 6,
    "jul": 7, "juli": 7,
    "agu": 8, "agustus": 8,
    "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "des": 12, "desember": 12,
}

def _to_iso_date(y: int, m: int, d: int) -> Optional[str]:
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        return None

def _parse_date_id(s: str) -> Optional[str]:
    s = s.strip()
    # ISO: YYYY-MM-DD
    m = re.search(r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        return _to_iso_date(m.group(1), m.group(2), m.group(3))
    # DD[-/]MM[-/]YYYY
    m = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](20\d{2}|19\d{2})\b", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _to_iso_date(y, mo, d)
    # D Month YYYY (Indonesia) with spaces
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z\.]+)\s+(20\d{2}|19\d{2})\b", s)
    if m:
        d = int(m.group(1))
        mon = m.group(2).lower().strip(".")
        y = int(m.group(3))
        if mon in _ID_MONTHS:
            return _to_iso_date(y, _ID_MONTHS[mon], d)
    # Concatenated format: DDMonthYYYY (e.g., "01Januari2025", "31Desember2025")
    m = re.search(r"\b(\d{1,2})([A-Za-z]+)(\d{4})\b", s)
    if m:
        d = int(m.group(1))
        mon = m.group(2).lower()
        y = int(m.group(3))
        if mon in _ID_MONTHS:
            return _to_iso_date(y, _ID_MONTHS[mon], d)
    # Format with optional spaces: DD [space] Month YYYY (e.g., "31 Desember2025")
    m = re.search(r"\b(\d{1,2})\s*([A-Za-z]+)(\d{4})\b", s)
    if m:
        d = int(m.group(1))
        mon = m.group(2).lower()
        y = int(m.group(3))
        if mon in _ID_MONTHS:
            return _to_iso_date(y, _ID_MONTHS[mon], d)
    return None

# -------------------- Page 2: robust jangka waktu + kontak --------------------
def _blob(texts: List[str]) -> str:
    return "\n".join(texts)

def _norm_label(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("*", "").replace(")", "").replace("(", "")
    s = s.replace(":", "")
    s = s.replace("telepon/gsm", "telepon")
    s = s.replace("e-mail", "email").replace("email", "email")
    return s.strip()  # Final strip to remove any trailing spaces

_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.I)
_PHONE_RE = re.compile(r"(?:\+62|0)[\d\-\s]{7,20}", re.I)

def _is_email(tok: str) -> bool:
    return bool(_EMAIL_RE.fullmatch(tok.strip()))

def _is_phone(tok: str) -> bool:
    return bool(_PHONE_RE.fullmatch(tok.strip()))

def _extract_jangka_waktu(texts: List[str]) -> tuple[Optional[str], Optional[str]]:
    b = _blob(texts)
    
    # Pattern 1: "berlaku sejak tanggal X hingga Y"
    m = re.search(
        r"berlaku\s+sejak\s*tanggal?\s+(.+?)\s+(?:hingga|sampai(?:\s+dengan)?)\s+(.+?)(?:\s|$)",
        b, flags=re.I
    )
    if m:
        start = _parse_date_id(m.group(1))
        end = _parse_date_id(m.group(2))
        if start and end:  # Only return if both dates are successfully parsed
            return start, end
    
    # Pattern 2: Handle concatenated dates like "01Januari2025 sampai dengan31 Desember2025"
    m = re.search(
        r"berlaku\s+sejak[^0-9]*(\d{1,2}[A-Za-z]+\d{4})\s*(?:sampai\s+dengan|hingga)\s*(\d{1,2}\s*[A-Za-z]+\s*\d{4})",
        b, flags=re.I
    )
    if m:
        start = _parse_date_id(m.group(1))
        end = _parse_date_id(m.group(2))
        if start and end:  # Only return if both dates are successfully parsed
            return start, end
    
    # Fallback: ambil 2 tanggal pertama apapun formatnya
    candidates = []
    for tok in texts:
        d = _parse_date_id(tok)
        if d:
            candidates.append(d)
        if len(candidates) >= 2:
            break
    if len(candidates) >= 2:
        return candidates[0], candidates[1]
    return None, None

def _extract_contact_blocks(texts: List[str]) -> tuple[Dict[str, str], Dict[str, str]]:
    """
    Ambil dua blok kontak di bawah '7.KONTAK PERSON':
    - Blok pertama: TELKOM
    - Blok kedua: PELANGGAN
    Menggunakan pembacaan sekuens label→nilai yang toleran noise.
    """
    # Cari anchor "7.KONTAK PERSON"
    start = next((i for i, t in enumerate(texts) if "7.KONTAKPERSON" in t.replace(" ", "") or "7.KONTAK PERSON" in t), None)
    if start is None:
        return {}, {}

    # Ambil subarray wajar (hingga sebelum tanda tangan)
    sub = texts[start : min(start + 120, len(texts))]

    # Cari token "TELKOM" pertama sebagai awal blok TELKOM
    try:
        telkom_anchor = sub.index("TELKOM")
    except ValueError:
        telkom_anchor = 0  # kalau tidak ada, mulai dari awal sub
    telkom_tokens = sub[telkom_anchor : ]

    # Setelah telkom block, akan ada label "Nama" lagi untuk PELANGGAN
    # Strategi: ekstrak 2 contact berturut-turut menggunakan parser label→nilai
    def read_contact(seq: List[str]) -> tuple[Dict[str, str], int]:
        fields = {"nama": None, "jabatan": None, "telepon": None, "email": None}
        labels = {"nama", "jabatan", "telepon", "email"}
        i = 0
        last_label = None
        hits = 0
        while i < len(seq):
            tok_raw = seq[i].strip()
            tok = _norm_label(tok_raw)
            if tok in labels:
                # Heuristik switch: jika muncul "Nama" baru DAN sudah ada minimal 2 field → akhir blok
                if tok == "nama" and sum(1 for v in fields.values() if v) >= 2:
                    break
                last_label = tok
                i += 1
                continue
            if last_label:
                val = tok_raw.strip()
                # Validasi tipe untuk telepon/email
                if last_label == "email" and not _is_email(val):
                    # Kadang-kadang email muncul di token selanjutnya
                    if i + 1 < len(seq) and _is_email(seq[i + 1].strip()):
                        val = seq[i + 1].strip()
                        i += 1
                    else:
                        # noise → lewati assignment
                        last_label = None
                        i += 1
                        continue
                elif last_label == "telepon" and not _is_phone(val):
                    if i + 1 < len(seq) and _is_phone(seq[i + 1].strip()):
                        val = seq[i + 1].strip()
                        i += 1
                    else:
                        last_label = None
                        i += 1
                        continue
                # Assign jika belum terisi
                if fields.get(last_label) is None:
                    fields[last_label] = val
                    hits += 1
                last_label = None
                i += 1
                # Stop heuristik: jika semua kunci sudah ketemu, break
                if hits >= 3 and all(k in fields for k in ["nama", "jabatan"]):
                    # boleh lanjut sedikit utk email/telepon berikutnya
                    # tapi batasi panjang bacaan
                    pass
                continue

            # Heuristik stop: jika ketemu "*):wajib diisi" → akhir blok
            if "wajib diisi" in tok:
                i += 1
                break
            i += 1

        return fields, i

    telkom_fields, consumed = read_contact(telkom_tokens)

    # PELANGGAN mulai setelah tokens yang telah dibaca
    pelanggan_tokens = telkom_tokens[consumed:]
    pelanggan_fields, _ = read_contact(pelanggan_tokens)

    # Bersihkan nilai kosong
    telkom_fields = {k: v for k, v in telkom_fields.items() if v}
    pelanggan_fields = {k: v for k, v in pelanggan_fields.items() if v}
    return telkom_fields, pelanggan_fields

# -------------------- Page 2 Merge --------------------
def merge_with_page2(existing: TelkomContractData, ocr_json_page2: Any) -> TelkomContractData:
    texts = _texts_from_ocr(ocr_json_page2)

    # 1) Jangka waktu
    start_date, end_date = _extract_jangka_waktu(texts)
    if existing.jangka_waktu is None:
        existing.jangka_waktu = JangkaWaktu()
    if start_date:
        existing.jangka_waktu.mulai = existing.jangka_waktu.mulai or start_date
    if end_date:
        existing.jangka_waktu.akhir = existing.jangka_waktu.akhir or end_date

    # 2) Kontak person (TELKOM & PELANGGAN)
    telkom, pelanggan = _extract_contact_blocks(texts)

    # Isi TELKOM
    if any(telkom.values()):
        existing.kontak_person_telkom = KontakPersonTelkom(
            nama=telkom.get("nama"),
            jabatan=telkom.get("jabatan"),
            email=telkom.get("email"),
            telepon=telkom.get("telepon"),
        )

    # Isi PELANGGAN
    if existing.informasi_pelanggan is None:
        existing.informasi_pelanggan = InformasiPelanggan()
    if any(pelanggan.values()):
        existing.informasi_pelanggan.kontak_person = KontakPersonPelanggan(
            nama=pelanggan.get("nama"),
            jabatan=pelanggan.get("jabatan"),
            email=pelanggan.get("email"),
            telepon=pelanggan.get("telepon"),
        )

    return existing


# -------------------- Convenience I/O --------------------
def extract_page1_file(input_json_path: str) -> Dict[str, Any]:
    """Baca file JSON OCR page 1 dan kembalikan dict hasil model_dump()."""
    with open(input_json_path, "r", encoding="utf-8") as f:
        ocr = json.load(f)
    data = extract_from_page1_one_time(ocr)
    # mode="json" memastikan field datetime / non-JSON-native sudah di-serialize (ISO string)
    return data.model_dump(mode="json")

def merge_page2_file(existing_json_path: str, page2_json_path: str, output_json_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Baca hasil existing (file JSON TelkomContractData) + OCR page 2,
    lakukan merge, lalu simpan (opsional) & kembalikan dict.
    """
    with open(existing_json_path, "r", encoding="utf-8") as f:
        existing_dict = json.load(f)
    # Rekonstruksi model dari dict (jika perlu)
    existing = TelkomContractData(**existing_dict)

    with open(page2_json_path, "r", encoding="utf-8") as f:
        ocr2 = json.load(f)

    merged = merge_with_page2(existing, ocr2)
    # Serialize to JSON-friendly structure
    result = merged.model_dump(mode="json")

    if output_json_path:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result


# -------------------- CLI mini --------------------
if __name__ == "__main__":
    import argparse, sys, os
    ap = argparse.ArgumentParser(description="Ekstraksi Telkom Contract (Page 1 one-time + merge Page 2)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("page1", help="Ekstrak dari page 1 (one-time charge)")
    p1.add_argument("--in", dest="inp", required=True, help="Path ke OCR JSON page 1")
    p1.add_argument("--out", dest="out", help="Path simpan hasil TelkomContractData (JSON)")

    m2 = sub.add_parser("merge2", help="Merge hasil page1 dengan OCR page 2")
    m2.add_argument("--existing", required=True, help="File JSON hasil page1 (TelkomContractData)")
    m2.add_argument("--page2", required=True, help="Path ke OCR JSON page 2")
    m2.add_argument("--out", required=True, help="Path simpan hasil merged JSON")

    args = ap.parse_args()

    if args.cmd == "page1":
        res = extract_page1_file(args.inp)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        else:
            json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    elif args.cmd == "merge2":
        res = merge_page2_file(args.existing, args.page2, args.out)
        # file sudah disimpan; tampilkan ringkas ke stdout
        print(f"Saved merged result to: {args.out}")
