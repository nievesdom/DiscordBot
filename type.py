import cv2
import easyocr
import os
import json

# Crear lector de EasyOCR con japonés
reader = easyocr.Reader(['ja'], gpu=False)

# Diccionario de traducciones
TRADUCCIONES = {
    "攻撃": "attack",
    "防御": "defense",
    "回復": "recovery",
    "補助": "support"
}

CARPETA = "cartas"
ARCHIVO_JSON = os.path.join(CARPETA, "cartas.json")

# Cargar cartas.json
with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
    cartas = json.load(f)

# Resumen de tipos encontrados
resumen = {"attack": 0, "defense": 0, "recovery": 0, "support": 0, "indeterminado": 0}

# Procesar cada imagen en la carpeta
for carta in cartas:
    nombre_archivo = carta["nombre"] + ".png"
    ruta = os.path.join(CARPETA, nombre_archivo)

    if not os.path.exists(ruta):
        print(f"⚠️ No se encontró la imagen para {carta['nombre']}")
        carta["tipo"] = "indeterminado"
        resumen["indeterminado"] += 1
        continue

    img = cv2.imread(ruta)

    # Recortar la región superior (coordenadas fijas)
    x1, y1 = 102, 23
    x2, y2 = 176, 57
    rect_top = img[y1:y2, x1:x2]

    # Reconocer texto
    resultado = reader.readtext(rect_top)

    tipo_detectado = "indeterminado"
    if resultado:
        for (_, texto, prob) in resultado:
            texto = texto.strip()
            if texto in TRADUCCIONES:
                tipo_detectado = TRADUCCIONES[texto]
                break
            else:
                tipo_detectado = "indeterminado"

    carta["tipo"] = tipo_detectado
    resumen[tipo_detectado] += 1
    print(f"{carta['nombre']} → {tipo_detectado}")

# Guardar cambios en cartas.json
with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
    json.dump(cartas, f, ensure_ascii=False, indent=2)

# Mostrar resumen final
print("\n📊 Resumen de tipos detectados:")
for tipo, cantidad in resumen.items():
    print(f"{tipo}: {cantidad}")
