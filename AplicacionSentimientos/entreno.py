# entrenar.py - Script para entrenar y guardar el modelo
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences
import numpy as np
import pickle
import os

# --- 1. PREPARACIÓN DE DATOS DE EJEMPLO ---
# Reemplaza esto con tu conjunto de datos real si ya lo tienes.
texts = [
    "La reunión de hoy fue muy productiva y el equipo trabajó bien.", # Neutral
    "Este mensaje es una amenaza y lo reportaré a recursos humanos.", # Acoso/Violencia
    "Me siento muy feliz con los resultados de mi último proyecto.", # Positivo
    "Necesito que me transfieras 500 dólares o publicaré tus datos.", # Extorsión
    "Por favor, no me escribas más, me siento intimidado.", # Acoso/Violencia
    "El informe se entregó a tiempo y con una calidad excelente.", # Positivo
    "Si no me das la información, te haré la vida imposible en el trabajo." # Acoso/Violencia
]
# Las etiquetas deben coincidir con las del diccionario en ml.py:
# 0: 'Neutral', 1: 'Positivo', 2: 'Acoso/Violencia', 3: 'Extorsión'
labels = [0, 2, 1, 3, 2, 1, 2]

# --- 2. CONFIGURACIÓN DEL MODELO ---
VOCAB_SIZE = 1000  # Tamaño del vocabulario
MAX_SEQUENCE_LENGTH = 100 # Longitud máxima de las secuencias

# --- 3. TOKENIZADOR ---
print("Creando y entrenando el tokenizador...")
tokenizer = Tokenizer(num_words=VOCAB_SIZE, oov_token="<unk>")
tokenizer.fit_on_texts(texts)

# --- 4. PREPROCESAMIENTO DE DATOS ---
sequences = tokenizer.texts_to_sequences(texts)
padded_sequences = pad_sequences(sequences, maxlen=MAX_SEQUENCE_LENGTH, padding='post', truncating='post')
labels = np.array(labels)

# --- 5. CREACIÓN Y ENTRENAMIENTO DEL MODELO ---
print("Creando y entrenando el modelo...")
model = keras.Sequential([
    keras.layers.Embedding(VOCAB_SIZE, 16, input_length=MAX_SEQUENCE_LENGTH),
    keras.layers.GlobalAveragePooling1D(),
    keras.layers.Dense(4, activation='softmax') # 4 neuronas para las 4 clases
])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(padded_sequences, labels, epochs=20, verbose=1)

# --- 6. GUARDAR EL MODELO Y EL TOKENIZADOR ---
# Define la ruta de la carpeta donde se guardarán los archivos
project_base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AppIA')

# Asegúrate de que el directorio exista
if not os.path.exists(project_base_dir):
    os.makedirs(project_base_dir)
    
model_save_path = os.path.join(project_base_dir, "modelo_emociones.h5")
tokenizer_save_path = os.path.join(project_base_dir, "tokenizer.pickle")

print("Guardando el modelo y el tokenizador...")
model.save(model_save_path)
with open(tokenizer_save_path, 'wb') as handle:
    pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)

print(f"\n¡Proceso finalizado!")
print(f"Modelo guardado en: {model_save_path}")
print(f"Tokenizador guardado en: {tokenizer_save_path}")