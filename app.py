from flask import Flask, render_template, request, jsonify
import numpy as np
from PIL import Image
import io, base64, math

app = Flask(__name__)

# =========================================================
# Utilidades de imagen
# =========================================================
def json_number(x):
    # JSON no soporta inf/nan, convertimos a None para evitar errores en JS
    if x is None: return None
    if isinstance(x, float) and (math.isinf(x) or math.isnan(x)): return None
    return float(x)

def read_image_grayscale_255(file_bytes: bytes) -> np.ndarray:
    """Lee imagen, convierte a grises y devuelve float64 en [0,255]."""
    img = Image.open(io.BytesIO(file_bytes)).convert("L")
    arr = np.asarray(img).astype(np.float64)
    return arr

def normalize01(img255: np.ndarray) -> np.ndarray:
    # Normalización al rango [0, 1] para facilitar cálculos numéricos
    return np.clip(img255 / 255.0, 0.0, 1.0)

def add_gaussian_noise(img01: np.ndarray, sigma: float, seed: int = 0) -> np.ndarray:
    # Simulación de ruido aditivo gaussiano: f'(x,y) = f(x,y) + n(x,y)
    # Útil para probar la robustez de los filtros pasa-bajas.
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, sigma, img01.shape)
    return np.clip(img01 + noise, 0.0, 1.0)

def to_png_base64(img255: np.ndarray) -> str:
    img_u8 = np.clip(img255, 0, 255).astype(np.uint8)
    pil = Image.fromarray(img_u8)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# =========================================================
# FFT / IFFT + Espectro (Marco Matemático)
# =========================================================

def fft2(img: np.ndarray) -> np.ndarray:
    # Aplica la Transformada Discreta de Fourier 2D (DFT).
    # Descompone la imagen espacial f(x,y) en sus componentes de frecuencia F(u,v).
    return np.fft.fft2(img)

def ifft2(F: np.ndarray) -> np.ndarray:
    # Aplica la Transformada Inversa (IDFT) para recuperar la imagen espacial.
    # Toma solo la parte real debido a posibles errores de redondeo numérico (residuales imaginarios).
    return np.real(np.fft.ifft2(F))

def shift(F: np.ndarray) -> np.ndarray:
    # Desplaza el componente de frecuencia cero (DC) al centro del espectro.
    # Esto reorganiza los cuadrantes para que las bajas frecuencias estén en el centro (M/2, N/2).
    return np.fft.fftshift(F)

def ishift(Fs: np.ndarray) -> np.ndarray:
    # Deshace el desplazamiento del centro para preparar la IFFT.
    return np.fft.ifftshift(Fs)

def log_spectrum_centered(F: np.ndarray) -> np.ndarray:
    """
    Calcula el espectro de magnitud logarítmico para visualización:
    S = c * log(1 + |F(u,v)|)
    Permite observar detalles en frecuencias altas que tienen mucha menos energía que la componente DC.
    """
    Fs = shift(F)
    spec = np.log1p(np.abs(Fs))
    spec = spec - spec.min()
    if spec.max() > 0:
        spec = spec / spec.max()
    return spec * 255.0

# =========================================================
# Métricas: MSE, PSNR, Nitidez
# =========================================================

def mse(a: np.ndarray, b: np.ndarray) -> float:
    # Error Cuadrático Medio (MSE): Promedio de las diferencias al cuadrado entre píxeles.
    # MSE = (1/N) * Σ(f(x,y) - g(x,y))^2
    return float(np.mean((a - b) ** 2))

def psnr(mse_val: float, max_i: float = 255.0) -> float:
    # Peak Signal-to-Noise Ratio (PSNR) en decibeles (dB).
    # Fórmula: 10 * log10(MAX^2 / MSE)
    # Una mayor PSNR indica una mejor fidelidad de reconstrucción.
    if mse_val <= 1e-12: return float("inf")
    return float(10.0 * np.log10((max_i * max_i) / mse_val))

def laplacian_sharpness(img01: np.ndarray) -> float:
    """
    Métrica de nitidez basada en la varianza del Laplaciano.
    El operador Laplaciano (∇²f) resalta cambios rápidos de intensidad (bordes).
    Una mayor varianza implica más bordes y texturas definidas (frecuencias altas).
    """
    x = img01
    xp = np.pad(x, 1, mode="edge")
    out = (xp[:-2,1:-1] + xp[1:-1,:-2] - 4.0 * xp[1:-1,1:-1] + xp[1:-1,2:] + xp[2:,1:-1])
    return float(np.var(out))

# =========================================================
# Máscaras pasa-bajas / pasa-altas
# =========================================================

def circular_ideal_mask(shape, radius, pass_type="low"):
    # Filtro Ideal: H(u,v) = 1 si D(u,v) <= D0, else 0.
    # Matemáticamente es un cilindro en el dominio de la frecuencia.
    # Genera "ringing" (artefactos de anillo) en el dominio espacial debido a que 
    # la transformada inversa de un escalón es una función Sinc.
    h, w = shape
    cy, cx = h // 2, w // 2
    Y, X = np.ogrid[:h, :w]
    dist2 = (Y - cy) ** 2 + (X - cx) ** 2
    low = (dist2 <= radius ** 2).astype(np.float64)
    return low if pass_type == "low" else (1.0 - low)

def gaussian_mask(shape, sigma, pass_type="low"):
    # Filtro Gaussiano: H(u,v) = exp(-D^2(u,v) / 2σ^2).
    # No genera ringing porque la transformada de Fourier de una Gaussiana es otra Gaussiana.
    # Produce transiciones más suaves.
    h, w = shape
    cy, cx = h // 2, w // 2
    Y, X = np.ogrid[:h, :w]
    dist2 = (Y - cy) ** 2 + (X - cx) ** 2
    low = np.exp(-dist2 / (2.0 * (sigma ** 2)))
    return low.astype(np.float64) if pass_type == "low" else (1.0 - low).astype(np.float64)

def apply_frequency_filter(img255: np.ndarray, mask_centered: np.ndarray):
    """
    Implementación del Teorema de Convolución:
    La multiplicación en el dominio de la frecuencia equivale a la convolución en el espacio.
    g(x,y) = f(x,y) * h(x,y) <==> G(u,v) = F(u,v) H(u,v)
    
    1. FFT2 -> Dominio Frecuencia
    2. Shift -> Centrar frecuencias
    3. Multiplicación por Máscara (Filtrado)
    4. IFFT2 -> Retorno al Dominio Espacial
    """
    F = fft2(img255)
    Fs = shift(F)
    Fs_f = Fs * mask_centered
    F_f = ishift(Fs_f)
    recon = ifft2(F_f)
    return recon, F, Fs_f

# =========================================================
# Rutas Flask
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    """
    Endpoint ÚNICO para Filtrado (Opción 3).
    Procesa la imagen y devuelve los resultados codificados en Base64.
    """
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No se recibió imagen"}), 400

    # Parámetros generales
    add_noise = request.form.get("add_noise", "false").lower() == "true"
    noise_sigma = float(request.form.get("noise_sigma", "0.03"))
    noise_seed = int(request.form.get("noise_seed", "0"))

    img255 = read_image_grayscale_255(file.read())
    img01 = normalize01(img255)

    if add_noise:
        img01 = add_gaussian_noise(img01, sigma=noise_sigma, seed=noise_seed)
        img255_work = img01 * 255.0
    else:
        img255_work = img255

    # Base FFT
    F_base = fft2(img255_work)
    spec_before = log_spectrum_centered(F_base)
    sharp_in = laplacian_sharpness(normalize01(img255_work))

    # --- LÓGICA DE FILTRADO (ÚNICA OPCIÓN) ---
    pass_type = request.form.get("pass_type", "low")  # low|high|both
    mask_type = request.form.get("mask_type", "ideal")  # ideal|gaussian

    h, w = img255_work.shape
    r_max = int(min(h, w) * 0.5)

    def build_mask(pt: str) -> np.ndarray:
        if mask_type == "ideal":
            radius = int(float(request.form.get("radius", str(max(2, r_max // 6)))))
            radius = max(1, min(radius, r_max))
            return circular_ideal_mask((h, w), radius, pass_type=pt)
        else:
            sigma = float(request.form.get("sigma", str(max(2, r_max // 6))))
            sigma = max(1.0, min(sigma, float(r_max)))
            return gaussian_mask((h, w), sigma, pass_type=pt)

    def spectrum_from_centered(Fs_centered: np.ndarray) -> np.ndarray:
        spec = np.log1p(np.abs(Fs_centered))
        spec = spec - spec.min()
        if spec.max() > 0: spec = spec / spec.max()
        return spec * 255.0

    # Caso Comparación (Both)
    if pass_type == "both":
        mask_low = build_mask("low")
        mask_high = build_mask("high")

        # Aplicamos Teorema de Convolución (Multiplicación en frecuencia)
        recon_low, _, Fs_low = apply_frequency_filter(img255_work, mask_low)
        recon_high, _, Fs_high = apply_frequency_filter(img255_work, mask_high)

        spec_after_low = spectrum_from_centered(Fs_low)
        spec_after_high = spectrum_from_centered(Fs_high)

        mse_low = mse(img255_work, recon_low)
        mse_high = mse(img255_work, recon_high)

        psnr_low = psnr(mse_low)
        psnr_high = psnr(mse_high)

        sharp_low = laplacian_sharpness(normalize01(np.clip(recon_low, 0, 255)))
        sharp_high = laplacian_sharpness(normalize01(np.clip(recon_high, 0, 255)))

        return jsonify({
            "mode": "filter",
            "pass_type": "both",
            "compare": True,
            "original": to_png_base64(img255_work),
            "spec_before": to_png_base64(spec_before),
            "recon_low": to_png_base64(recon_low),
            "recon_high": to_png_base64(recon_high),
            "mask_low": to_png_base64(mask_low * 255.0),
            "mask_high": to_png_base64(mask_high * 255.0),
            "spec_after_low": to_png_base64(spec_after_low),
            "spec_after_high": to_png_base64(spec_after_high),
            "mse_low": mse_low,
            "mse_high": mse_high,
            "psnr_low": json_number(psnr_low),
            "psnr_high": json_number(psnr_high),
            "sharp_in": sharp_in,
            "sharp_low": sharp_low,
            "sharp_high": sharp_high
        })

    # Caso Normal (Low o High individual)
    mask = build_mask(pass_type)
    recon, _, Fs_filtered = apply_frequency_filter(img255_work, mask)
    spec_after = spectrum_from_centered(Fs_filtered)

    mse_val = mse(img255_work, recon)
    psnr_val = psnr(mse_val)
    sharp_out = laplacian_sharpness(normalize01(np.clip(recon, 0, 255)))

    return jsonify({
        "mode": "filter",
        "pass_type": pass_type,
        "compare": False,
        "original": to_png_base64(img255_work),
        "spec_before": to_png_base64(spec_before),
        "spec_after": to_png_base64(spec_after),
        "mask": to_png_base64(mask * 255.0),
        "recon": to_png_base64(recon),
        "mse": mse_val,
        "psnr": json_number(psnr_val),
        "sharp_in": sharp_in,
        "sharp_out": sharp_out
    })

if __name__ == "__main__":
    app.run(debug=True)