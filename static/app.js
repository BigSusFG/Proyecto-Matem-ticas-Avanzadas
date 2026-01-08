/**
 * APP.JS - Controlador del lado del Cliente (Frontend)
 * ---------------------------------------------------
 * Responsabilidades:
 * 1. Capa de Presentación: Gestión de la Interfaz de Usuario (UI) y eventos.
 * 2. Comunicación: Envío de matrices de imagen y parámetros al servidor Python (Flask).
 * 3. Interpretación: Visualización de métricas numéricas (MSE, PSNR).
 */

// ------------------------------
// Helpers (Utilidades del DOM)
// ------------------------------
function $(id){ return document.getElementById(id); }

// Feedback visual para el usuario (UX)
function setStatus(msg){ 
    const el = $("status");
    if(el) {
        el.textContent = msg;
        el.style.opacity = '0.5';
        setTimeout(() => el.style.opacity = '1', 100);
    }
}

// Decodificación de Base64 a Imagen visible
function setImg(id, b64){
  const el = $(id);
  if(el) {
      el.style.opacity = '0'; // Transición suave
      setTimeout(() => {
          // El servidor devuelve la imagen procesada como string Base64 (PNG)
          el.src = b64 ? `data:image/png;base64,${b64}` : "";
          el.onload = () => { el.style.opacity = '1'; }
      }, 150);
  }
}

// Formateo de métricas matemáticas
function fmtPSNR(v){
  // Si v es null o infinito, significa que el MSE es 0 (Reconstrucción perfecta)
  // Matemáticamente: lim(MSE->0) 10*log10(MAX^2/MSE) = Infinito
  if (v === null || v === undefined) return "∞";
  if (!isFinite(v)) return "∞";
  return Number(v).toFixed(2);
}

function fmt(v, d=4){ return (typeof v === "number") ? v.toFixed(d) : "-"; }

// ------------------------------
// Listeners de Interfaz (Inputs Reactivos)
// ------------------------------
// Vinculación de los sliders con sus etiquetas de valor.
// Estos valores (Sigma, Radio) son los parámetros de corte (D0) en las ecuaciones del filtro.
$("noiseSigma").addEventListener("input", ()=> $("noiseSigmaLabel").textContent = $("noiseSigma").value);
$("radius").addEventListener("input", ()=> $("radiusLabel").textContent = $("radius").value);
$("sigma").addEventListener("input", ()=> $("sigmaLabel").textContent = $("sigma").value);

// Lógica de visualización de controles:
// Filtro Ideal usa "Radio" (D0) hard-cut.
// Filtro Gaussiano usa "Sigma" (Desviación estándar) para la atenuación suave.
function updateMaskControls(){
  const t = $("maskType").value;
  $("idealControls").classList.toggle("hidden", t!=="ideal");
  $("gaussControls").classList.toggle("hidden", t!=="gaussian");
}
$("maskType").addEventListener("change", updateMaskControls);
updateMaskControls();

// ------------------------------
// Procesamiento Principal (Cliente -> Servidor)
// ------------------------------
$("run").addEventListener("click", async ()=>{
  const file = $("file").files[0];
  if (!file){
    alert("Por favor, selecciona una imagen primero.");
    return;
  }

  setStatus("Procesando...");
  const btn = $("run");
  const originalBtnText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Calculando..."; 

  try{
    // Construcción del Payload (Carga útil)
    // Se empaqueta la imagen binaria y los parámetros matemáticos
    // para enviarlos al backend Flask.
    const fd = new FormData();
    fd.append("image", file);
    
    // Parámetros de Simulación de Ruido
    fd.append("add_noise", $("addNoise").checked ? "true" : "false");
    fd.append("noise_sigma", $("noiseSigma").value);
    fd.append("noise_seed", $("noiseSeed").value);
    
    // Parámetros de Filtro Frecuencial
    fd.append("pass_type", $("passType").value); // low | high | both
    fd.append("mask_type", $("maskType").value); // ideal | gaussian
    fd.append("radius", $("radius").value);      // Frecuencia de corte D0 (Ideal)
    fd.append("sigma", $("sigma").value);        // Dispersión (Gaussiana)

    // Petición Asíncrona (AJAX / Fetch API)
    // Enviamos los datos a Python para el cálculo de FFT2 e IFFT2
    const res = await fetch("/process", { method:"POST", body: fd });
    const data = await res.json();

    if (!res.ok){
      alert(data.error || "Error desconocido");
      setStatus("Error.");
      return;
    }

    // -------------------------
    // Renderizado de Resultados
    // -------------------------
    
    // 1. Imágenes Base (Espacial y Espectral)
    setImg("imgOriginal", data.original);
    setImg("imgSpecBefore", data.spec_before); // Espectro de magnitud logarítmico

    // Lógica de visualización: Modo Simple vs Modo Comparativo
    const isCompare = !!data.compare;
    if ($("compareBlock")) $("compareBlock").classList.toggle("hidden", !isCompare);

    if (!isCompare){
        // --- MODO SIMPLE (Un solo filtro) ---
        $("singleView")?.classList.remove("hidden");
        $("compareBlock")?.classList.add("hidden");

        // Visualización de la convolución en frecuencia (Multiplicación de espectro x máscara)
        setImg("imgRecon", data.recon);       // Resultado espacial (IFFT)
        setImg("imgSpecAfter", data.spec_after); // Espectro filtrado
        setImg("imgMask", data.mask);         // Función de Transferencia H(u,v)
        $("imgMask").style.display = "block";

        // Actualización de Métricas Cuantitativas
        $("mse").textContent = fmt(data.mse, 4);  // Error Cuadrático Medio
        $("psnr").textContent = fmtPSNR(data.psnr); // Calidad en dB
        // Variación en la nitidez (Varianza del Laplaciano)
        $("sharp").textContent = `${fmt(data.sharp_in,2)} → ${fmt(data.sharp_out,2)}`;

        // Descripción dinámica
        $("note").innerHTML = `<b>Filtro:</b> ${
          $("passType").value === "low"
            ? "Pasa-bajas (Suavizado / Eliminación de altas frecuencias)"
            : "Pasa-altas (Detección de bordes / Eliminación de componente DC)"
        }`;
    } else {
        // --- MODO COMPARATIVO (Dual) ---
        // Permite visualizar simultáneamente los efectos complementarios
        // de filtrar bajas vs altas frecuencias.
        $("singleView")?.classList.add("hidden");
        $("compareBlock")?.classList.remove("hidden");

        setImg("imgOriginalCompare", data.original);
        setImg("imgSpecBeforeCompare", data.spec_before);
        
        // Resultados Pasa-Bajas vs Pasa-Altas
        setImg("imgReconLow", data.recon_low);
        setImg("imgReconHigh", data.recon_high);
        
        // Máscaras (H_low vs H_high)
        setImg("imgMaskLow", data.mask_low);
        setImg("imgMaskHigh", data.mask_high);
        
        // Espectros resultantes
        setImg("imgSpecAfterLow", data.spec_after_low);
        setImg("imgSpecAfterHigh", data.spec_after_high);

        // Limpieza de vista simple
        setImg("imgRecon", "");
        setImg("imgSpecAfter", "");
        if ($("imgMask")) $("imgMask").style.display = "none";

        // Métricas comparadas
        $("mse").textContent = `${fmt(data.mse_low,4)} | ${fmt(data.mse_high,4)}`;
        $("psnr").textContent = `${fmtPSNR(data.psnr_low)} | ${fmtPSNR(data.psnr_high)}`;
        $("sharp").textContent = `${fmt(data.sharp_in,2)} → ${fmt(data.sharp_low,2)} | ${fmt(data.sharp_high,2)}`;

        $("note").innerHTML = `<b>Comparación Dual:</b> Visualización de la descomposición espectral de la imagen.`;
    }

    setStatus("Listo");
    
    // UX: Cerrar sidebar en dispositivos móviles para ver resultado
    if(window.innerWidth <= 1024) toggleSidebar(false);

  } catch(e){
    console.error(e);
    alert("Error procesando: " + e);
    setStatus("Error.");
  } finally {
    btn.disabled = false;
    btn.textContent = originalBtnText;
  }
});

// ------------------------------
// Helpers UI: Modal y Sidebar
// ------------------------------

// Lógica para el Zoom de imágenes (Modal)
const modal = document.getElementById("imageModal");
const modalImg = document.getElementById("imgExpanded");
const closeBtn = document.getElementsByClassName("close")[0];

// Delegación de eventos para abrir modal al hacer click en cualquier imagen de resultado
document.addEventListener("click", (e) => {
  if (e.target.tagName === 'IMG' && (e.target.closest('.view-panel') || e.target.closest('#compareBlock'))) {
    modal.style.display = "flex";
    modal.style.opacity = "0";
    setTimeout(()=> modal.style.opacity = "1", 10);
    modalImg.src = e.target.src;
  }
});

if(closeBtn){ closeBtn.onclick = function() { modal.style.display = "none"; } }
modal.onclick = function(e) { if (e.target === modal) modal.style.display = "none"; }
document.addEventListener('keydown', function(event){ if(event.key === "Escape") modal.style.display = "none"; });

// Lógica para Sidebar responsiva (Móvil)
(function initMobileSidebar(){
    const btn = document.createElement("button");
    btn.className = "sidebar-toggle-btn";
    btn.innerHTML = "☰"; 
    btn.onclick = () => toggleSidebar();
    document.body.appendChild(btn);

    const overlay = document.createElement("div");
    overlay.id = "sidebar-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:40;display:none;backdrop-filter:blur(2px);";
    overlay.onclick = () => toggleSidebar(false);
    document.body.appendChild(overlay);
})();

function toggleSidebar(forceState){
    const sb = document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    const isOpen = sb.classList.contains("open");
    const newState = forceState !== undefined ? forceState : !isOpen;

    if(newState){ sb.classList.add("open"); overlay.style.display = "block"; } 
    else { sb.classList.remove("open"); overlay.style.display = "none"; }
}