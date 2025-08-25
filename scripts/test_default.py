import os
import time
from pathlib import Path
import fitz  # PyMuPDF
from paddleocr import PPStructureV3

# ---- Konfigurasi input/output ----
pdf_path = Path("tests/test_samples/KB SMKN 1 BIREUN TTD 2024 VALIDASI.pdf")
max_pages = 2
work_dir = Path("output-test") / pdf_path.stem  # contoh: output/KB SMKN 1 BIREUN TTD 2024 VALIDASI
img_dir = work_dir / "pages"
os.makedirs(img_dir, exist_ok=True)

def fmt(s):
    # format detik -> 'xxx ms' atau 'x.xxx s'
    return f"{s*1000:.1f} ms" if s < 1 else f"{s:.3f} s"

t0_total = time.perf_counter()

# ---- Render 2 halaman pertama PDF ke PNG ----
t0_open = time.perf_counter()
doc = fitz.open(pdf_path.as_posix())
t1_open = time.perf_counter()

if doc.page_count == 0:
    raise RuntimeError("PDF kosong / tidak bisa dibaca.")

num_to_process = min(max_pages, doc.page_count)

page_images = []
render_times = []
for i in range(num_to_process):
    t0_render = time.perf_counter()
    page = doc.load_page(i)
    # DPI 200 sudah cukup bagus untuk OCR; naikkan kalau teks kecil.
    pix = page.get_pixmap(dpi=200, alpha=False)
    img_path = img_dir / f"{pdf_path.stem}_p{i+1:02d}.png"
    pix.save(img_path.as_posix())
    page_images.append(img_path.as_posix())
    t1_render = time.perf_counter()
    render_times.append(t1_render - t0_render)

doc.close()

# ---- Inisialisasi pipeline (default config) ----
t0_init = time.perf_counter()
pipeline = PPStructureV3()
t1_init = time.perf_counter()

# ---- OCR per halaman & simpan hasil ----
inference_times = []
save_times = []
for img_path in page_images:
    t0_inf = time.perf_counter()
    outputs = pipeline.predict(img_path)  # kembalikan list dengan satu result untuk gambar ini
    t1_inf = time.perf_counter()
    inference_times.append(t1_inf - t0_inf)

    t0_save = time.perf_counter()
    # Biasanya satu elemen per gambar; iterasi untuk aman
    for res in outputs:
        # Tampilkan ringkas di console
        res.print()
        # Simpan hasil terstruktur
        res.save_to_json(save_path=work_dir.as_posix())
    t1_save = time.perf_counter()
    save_times.append(t1_save - t0_save)

t1_total = time.perf_counter()

# ---- Ringkasan waktu ----
print("\n=== RINGKASAN WAKTU ===")
print(f"Open PDF         : {fmt(t1_open - t0_open)}")
print(f"Render {num_to_process} halaman:")
for idx, rt in enumerate(render_times, 1):
    print(f"  - Halaman {idx} : {fmt(rt)}")
print(f"Inisialisasi PPStructureV3 : {fmt(t1_init - t0_init)}")
for idx, (it, st) in enumerate(zip(inference_times, save_times), 1):
    print(f"Inferensi h{idx}  : {fmt(it)}")
    print(f"Simpan h{idx}     : {fmt(st)}")
print(f"TOTAL             : {fmt(t1_total - t0_total)}")

print(f"\nSelesai. Gambar halaman ada di: {img_dir}")
print(f"Hasil JSON ada di: {work_dir}")
