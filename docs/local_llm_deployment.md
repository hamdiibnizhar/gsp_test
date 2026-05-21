# Local LLM Deployment Strategy

## Menjalankan LLM Lokal : Ollama
- Download ollama dan install ollama
- pilih model yang akan dijalankan, dengan ollama pull <nama model>
- Ollama host yang diasumsikan aplikasi ini: `http://localhost:11434` untuk local, `http://10.30.50.2:11434` untuk vpn
- Model yang tersedia adalah gpt-oss:20b karena kompatible dengan local LLM saya di Mac Studio
- Jalankan model di host Ollama: `ollama run gpt-oss:20b`.

## Pemilihan Model
- Pemilihan model tergantung resource yang tersedia di local, untuk case saya di home server dengan mac studio dengan unified memory 32GB maka GPU yang bisa terpakai hanya 75% = 24GB. maka pilih ukuran atau size model yang ukurannya 75% dan memory GPU yang tersedia.
- pilih berdasarkan ekosistem dari resource yang terdia, misal jika mac maka lebih baik pakai mlx type. jika gpu-dedicated seperti nvidia maka pakai gguf.
- semakin tinggi parameter semakin besar kebutuhan memory dan semakin akurat inferencenya.
- pilih presisi yang rendah misalnya 4bit int aga model bisa berjalan lancar untuk mendapatkan fisrt tokennya.
- Untuk device terbatas, pilih 3B atau 1.5B + retrieval kuat.

## Quantization
- Jika model yang tersedia di repository ollama atau hugging face lebih kecil dari ukuran memory GPU dan compatible maka pakai saja yang ada
- jika tidak ada maka kita bisa melakukan quantisasi dari model yang tersedia misalnya model yaang terdia qwen2.5-mlx 16bf. maka kita bisa menurunkan nya dengan quantisasi ke 4bit dengan tools llama.cpp
- semakin kecil quantisasi maka kebutuhan memory akan berkuran dan kulitas model akan semakin rendah karena rendahnya presisi.

## Trade-off Quality vs Latency
misal ada infra A dengan spec tertentu, dengan model yang sama tetapi ukuran paramnya dan presisinya berbeda maka :
- Quality makn besar maka latency semakin besar
- Latency semakin kecil maka quality model akan rendah
- Model besar: jawaban lebih natural, latency lebih tinggi.
- Model kecil: cepat dan murah, perlu prompt dan retrieval lebih ketat.

## Estimasi Resource
 - ada 3 komponen utama untuk meningkatkan inference dari AI yaitu jumlah core dari CPU dan GPU, memory bandwidth dan memory CPU (RAM) dan memory GPU (VRAM)
- dari blog nvidia untuk kebutuhan LLM dengan KV cache dan transformer, kebutuhan memory GPU bisa di estimasikan dengan rumus :
Jumlah Param * 4B / (32/number precission) * 1.2
- Semaki banyak jumlah corenya maka throughput akan semakin tinggi, dan sebaliknya latensi akan besar
- Memory bandwidth semakin besar maka akan semakin cepat minggasi datanya yang artinya akan semakin cepat inference.
- untuk local LLM saya butuh 20GB Memory GPU


## Fallback ke Cloud LLM
- Jika local model timeout/error, route ke OpenAI-compatible endpoint.
- Kirim hanya context terpilih (top-k) untuk minimalkan eksposur data.

## Security untuk Data Sensitif
- Isolasi network host inference.
- Audit log untuk akses query dan dokumen.
- Masking data sensitif pada prompt sebelum fallback cloud.
