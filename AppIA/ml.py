# AppIA/ml.py
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.utils import pad_sequences
import numpy as np
import pickle
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#  Cargar el tokenizador (necesario para preprocesar el texto)
# Es CRUCIAL usar el mismo tokenizador con el que se entrenó el modelo.
try:
    with open(os.path.join(BASE_DIR, 'tokenizer.pickle'), 'rb') as handle:
        tokenizer = pickle.load(handle)
except FileNotFoundError:
    print("Error: No se encontró el archivo 'tokenizer.pickle'. Asegúrate de que existe.")
    tokenizer = None

#  Cargar el modelo de Keras previamente entrenado
model_path = os.path.join(BASE_DIR, 'modelo_emociones.h5')
try:
    model = keras.models.load_model(model_path)
    print("Modelo cargado exitosamente.")
except (IOError, ValueError) as e:
    print(f"Error al cargar el modelo: {e}. Asegúrate de que el archivo existe y es válido.")
    model = None

# Definir las etiquetas de las emociones
EMOTION_LABELS = {
    0: 'Neutral',
    1: 'Positivo',
    2: 'Acoso/Violencia',
    3: 'Extorsión'
}

# Configurar parámetros del preprocesamiento
MAX_SEQUENCE_LENGTH = 100 # La longitud máxima de las secuencias de texto

def preprocess_text(text):
    """
    Preprocesa un texto para que el modelo lo pueda entender.
    """
    if tokenizer is None:
        return None
    
    # Tokenizar y convertir a secuencias de números
    sequence = tokenizer.texts_to_sequences([text])
    
    # Rellenar (padding) para que todas las secuencias tengan la misma longitud
    padded_sequence = pad_sequences(sequence, maxlen=MAX_SEQUENCE_LENGTH, padding='post', truncating='post')
    
    return padded_sequence

# Palabras clave para corrección de clasificación

# Palabras FUERTEMENTE positivas (alta evidencia emocional)
STRONG_POSITIVE_KEYWORDS = [
    'te amo', 'te quiero', 'te adoro', 'amor mío', 'mi amor',
    'emocionada', 'emocionado', 'felicísima', 'felicísimo',
    'me encanta', 'adoro', 'amo', 'te extraño mucho', 'te necesito',
    'maravilloso', 'increíble', 'fantástico', 'espectacular',
    'hermosa', 'hermoso', 'bellísima', 'bellísimo'
]

# Palabras moderadamente positivas (pueden ser neutrales en contexto)
MILD_POSITIVE_KEYWORDS = [
    'amor', 'cariño', 'corazón', 'feliz', 'alegre', 'contenta', 'contento',
    'genial', 'excelente', 'lindo', 'linda', 'bella', 'bello', 'bueno', 'buena',
    'gracias', 'bendiciones', 'besos', 'abrazos', 'sonrisa', 'felicidad',
    'divino', 'perfecto', 'me gusta'
]

# Palabras de violencia CRÍTICAS (amenazas directas - alta prioridad)
CRITICAL_VIOLENCE_KEYWORDS = [
    'te mato', 'te voy a matar', 'te golpeo', 'te pego', 'te destruyo',
    'voy a matarte', 'te voy a golpear', 'te hago daño', 'te lastimo',
    'alejate de', 'aléjate de', 'te disparo', 'te corto'
]

# Palabras de violencia MODERADAS (contexto puede ser inocente)
MODERATE_VIOLENCE_KEYWORDS = [
    'matar', 'golpear', 'pegar', 'muerte', 'violencia',
    'agredir', 'atacar', 'herir', 'lastimar', 'odio',
    'amenaza', 'venganza', 'destruir', 'sangre', 'arma', 'cuchillo',
    'pistola', 'disparo', 'golpe', 'pelea'
]

# Patrones de extorsión CRÍTICOS (chantaje directo)
CRITICAL_EXTORTION_KEYWORDS = [
    'dame dinero o', 'paga o', 'si no pagas', 'tengo fotos tuyas',
    'tengo videos tuyos', 'voy a publicar', 'fotos comprometedoras',
    'si no me das'
]

# Patrones de extorsión MODERADOS
MODERATE_EXTORTION_KEYWORDS = [
    'dame dinero', 'transfiere', 'deposita', 'cuenta bancaria',
    'envía dinero', 'manda dinero', 'fotos intimas', 'fotos íntimas',
    'envías fotos', 'envias fotos', 'mándame fotos', 'mandame fotos',
    'fotos desnuda', 'fotos desnudo', 'fotos privadas', 'nudes'
]

def apply_keyword_correction(text, predicted_label, confidence):
    """
    Aplica correcciones basadas en palabras clave para mejorar la precisión.
    Sistema híbrido INTELIGENTE: combina IA con reglas contextuales.

    IMPORTANTE: Si el modelo está clasificando incorrectamente, este sistema
    tiene prioridad para corregir errores evidentes.
    """
    text_lower = text.lower()

    # Detectar palabras por nivel de intensidad y criticidad
    strong_positive_count = sum(1 for keyword in STRONG_POSITIVE_KEYWORDS if keyword in text_lower)
    mild_positive_count = sum(1 for keyword in MILD_POSITIVE_KEYWORDS if keyword in text_lower)

    critical_violence_count = sum(1 for keyword in CRITICAL_VIOLENCE_KEYWORDS if keyword in text_lower)
    moderate_violence_count = sum(1 for keyword in MODERATE_VIOLENCE_KEYWORDS if keyword in text_lower)

    critical_extortion_count = sum(1 for keyword in CRITICAL_EXTORTION_KEYWORDS if keyword in text_lower)
    moderate_extortion_count = sum(1 for keyword in MODERATE_EXTORTION_KEYWORDS if keyword in text_lower)

    # DETECCIÓN PREVENTIVA: Si es un mensaje muy corto y simple, es probablemente neutral
    word_count = len(text_lower.split())
    if word_count <= 3 and critical_violence_count == 0 and critical_extortion_count == 0:
        # Mensajes cortos como "hola", "cómo estás", "ok", etc.
        if moderate_violence_count == 0 and moderate_extortion_count == 0:
            if strong_positive_count > 0:
                return 'Positivo', 0.85
            elif mild_positive_count > 0:
                return 'Positivo', 0.75
            else:
                return 'Neutral', 0.80

    # PRIORIDAD 1: Amenazas CRÍTICAS directas (forzar clasificación)
    # Ejemplos: "te mato", "te voy a golpear", "alejate de él"
    if critical_violence_count >= 1:
        return 'Acoso/Violencia', 0.95

    # PRIORIDAD 2: Extorsión CRÍTICA directa (forzar clasificación)
    # Ejemplos: "dame dinero o...", "tengo fotos tuyas", "si no pagas"
    if critical_extortion_count >= 1:
        return 'Extorsión', 0.95

    # PRIORIDAD 3: Corregir falsos positivos evidentes
    # Si tiene palabras fuertemente positivas y la red se equivocó
    if strong_positive_count >= 1:
        # Si NO hay amenazas críticas, corregir
        if critical_violence_count == 0 and critical_extortion_count == 0:
            if predicted_label in ['Acoso/Violencia', 'Extorsión']:
                return 'Positivo', 0.90

    # PRIORIDAD 4: Violencia/Extorsión MODERADA (requiere contexto)
    # Solo forzar si hay 2+ palabras moderadas (indica patrón real)
    if moderate_violence_count >= 2 and critical_violence_count == 0:
        # Solo si no hay señales positivas fuertes
        if strong_positive_count == 0:
            return 'Acoso/Violencia', 0.75

    if moderate_extortion_count >= 2 and critical_extortion_count == 0:
        if strong_positive_count == 0:
            return 'Extorsión', 0.75

    # PRIORIDAD 5: Reforzar positivos con múltiples señales
    total_positive = strong_positive_count + mild_positive_count
    if total_positive >= 2:
        # Si no hay amenazas críticas, es positivo
        if critical_violence_count == 0 and critical_extortion_count == 0:
            if predicted_label in ['Acoso/Violencia', 'Extorsión']:
                return 'Positivo', 0.80

    # PRIORIDAD 6: Ayudar a la red en casos de baja confianza
    if confidence < 0.50:
        # Solo intervenir si hay señales CLARAS
        if strong_positive_count >= 1 and critical_violence_count == 0:
            return 'Positivo', 0.65
        if critical_violence_count >= 1:
            return 'Acoso/Violencia', 0.65
        if critical_extortion_count >= 1:
            return 'Extorsión', 0.65

    # PRIORIDAD 7: Si la red predice violencia/extorsión pero NO hay evidencia
    # BYPASS del modelo si está clasificando mal masivamente
    if predicted_label in ['Acoso/Violencia', 'Extorsión']:
        # Si NO hay ninguna palabra crítica ni moderada de violencia/extorsión
        total_negative = critical_violence_count + moderate_violence_count + critical_extortion_count + moderate_extortion_count

        if total_negative == 0:
            # No hay NINGUNA señal negativa, la red se equivocó
            if strong_positive_count > 0 or total_positive >= 1:
                return 'Positivo', 0.70
            else:
                # Mensaje completamente neutral
                return 'Neutral', 0.70

    # DEFAULT: CONFIAR en la red neuronal
    # Solo corregir errores MUY evidentes, la red es buena
    return predicted_label, confidence

def predict_emotion(text):
    """
    Predice la emoción de un texto dado con corrección por palabras clave.
    """
    if model is None or tokenizer is None:
        return "Error en la carga del modelo o tokenizador."

    # Preprocesar el texto de entrada
    processed_input = preprocess_text(text)
    if processed_input is None:
        return "Error en el preprocesamiento."

    # Realizar la predicción
    # 'predict' devuelve un array de probabilidades para cada clase
    prediction_probs = model.predict(processed_input, verbose=0)

    # Obtener el índice de la clase con la mayor probabilidad
    predicted_class_index = np.argmax(prediction_probs, axis=1)[0]

    # Obtener la etiqueta de la emoción
    predicted_label = EMOTION_LABELS.get(predicted_class_index, 'Desconocido')

    # Obtener la probabilidad de la predicción
    confidence = prediction_probs[0][predicted_class_index]

    # Aplicar corrección basada en palabras clave
    corrected_label, corrected_confidence = apply_keyword_correction(
        text, predicted_label, float(confidence)
    )

    return {
        'etiqueta': corrected_label,
        'confianza': corrected_confidence
    }