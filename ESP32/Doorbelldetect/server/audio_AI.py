import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import librosa
import csv


# Load the YAMNet model from TensorFlow Hub
model = hub.load('https://tfhub.dev/google/yamnet/1')

# Load the class names for YAMNet
class_map_path = tf.keras.utils.get_file(
    'yamnet_class_map.csv',
    'https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv'  # Updated URL
)

# Read the class names from the CSV file
class_names = []
with open(class_map_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        class_names.append(row['display_name'])

# Debug print to check class names
# print(f'Class names: {class_names}')

# Function to classify a WAV file and return the class name
def classify_wav(file_path):
    # Load the audio file
    audio_data, sample_rate = librosa.load(file_path)

    # Run the model on the audio data
    scores, embeddings, spectrogram = model(audio_data)

    # Get the class with highest score and its confidence
    predicted_class_index = tf.argmax(scores, axis=1).numpy()[0]
    confidence = float(scores[0][predicted_class_index].numpy())  # Convert to Python float

    # Get the class name
    predicted_class_name = class_names[predicted_class_index]

    return predicted_class_name, confidence

if __name__ == "__main__":
    class_name, confidence = classify_wav('doorbell_part.wav')
    print(f'Predicted class: {class_name} (confidence: {confidence:.2%})')
