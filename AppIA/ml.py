# AppIA/ml.py
import tensorflow as tf
from tensorflow import keras
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences
import numpy as np
import pickle
import os

# Define la ruta base para tus archivos de modelo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Cargar el tokenizador (necesario para preprocesar el texto)
# Es CRUCIAL usar el mismo tokenizador con el que se entrenó el modelo.
try:
    with open(os.path.join(BASE_DIR, 'tokenizer.pickle'), 'rb') as handle:
        tokenizer = pickle.load(handle)
except FileNotFoundError:
    print("Error: No se encontró el archivo 'tokenizer.pickle'. Asegúrate de que existe.")
    tokenizer = None

# 2. Cargar el modelo de Keras previamente entrenado
model_path = os.path.join(BASE_DIR, 'modelo_emociones.h5')
try:
    model = keras.models.load_model(model_path)
    print("Modelo cargado exitosamente.")
except (IOError, ValueError) as e:
    print(f"Error al cargar el modelo: {e}. Asegúrate de que el archivo existe y es válido.")
    model = None

# 3. Definir las etiquetas de las emociones
EMOTION_LABELS = {
    0: 'Neutral',
    1: 'Positivo',
    2: 'Acoso/Violencia',
    3: 'Extorsión'
}

# 4. Configurar parámetros del preprocesamiento
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

def predict_emotion(text):
    """
    Predice la emoción de un texto dado.
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
    
    return {
        'etiqueta': predicted_label,
        'confianza': float(confidence)
    }