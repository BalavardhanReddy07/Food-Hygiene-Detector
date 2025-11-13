# model.py
import tensorflow as tf
from tensorflow.keras import layers, models

def build_classifier(input_shape=(224, 224, 3), base_trainable=False, dropout=0.5, num_classes=2):
    """
    Builds a more robust, "deeper" transfer-learning image classifier
    using MobileNetV2 backbone.
    Returns a compiled model ready for training.
    """
    # Input and preprocessing
    inputs = layers.Input(shape=input_shape)

    # --- 1. More Aggressive Data Augmentation ---
    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.2),  # Increased rotation
        layers.RandomZoom(0.2),    # Increased zoom
        layers.RandomContrast(0.2),  # Added contrast
        layers.RandomBrightness(0.2) # Added brightness
    ], name="data_augmentation")

    # Apply augmentation to the 0-255 inputs
    augmented = data_augmentation(inputs)

    # Preprocessing to match MobileNetV2 expectations (scales to -1, 1)
    preprocessed = tf.keras.applications.mobilenet_v2.preprocess_input(augmented)

    # --- 2. Backbone ---
    base = tf.keras.applications.MobileNetV2(
        input_shape=input_shape, include_top=False, weights='imagenet',
        # --- THIS IS THE FIX ---
        name="mobilenet_backbone" 
    )
    base.trainable = base_trainable 

    # --- 3. CRITICAL Bug Fix ---
    x = base(preprocessed)
    
    # --- 4. Deeper, More "Intelligent" Classification Head ---
    x = layers.GlobalAveragePooling2D()(x) # Pool features
    
    # First "thinking" layer
    x = layers.Dense(512, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
    x = layers.BatchNormalization()(x) # Stabilizes training
    x = layers.Activation('relu')(x)
    x = layers.Dropout(dropout)(x) 
    
    # Second "thinking" layer
    x = layers.Dense(128, kernel_regularizer=tf.keras.regularizers.l2(0.001))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Dropout(dropout * 0.5)(x) 
    
    # --- 5. Output Layer ---
    if num_classes == 2:
        outputs = layers.Dense(1, activation='sigmoid')(x)
        loss = 'binary_crossentropy'
    else:
        outputs = layers.Dense(num_classes, activation='softmax')(x)
        loss = 'categorical_crossentropy'

    model = models.Model(inputs, outputs, name="HYGEIN-DETECTOR-v2-MobileNet")
    
    # We no longer need model.backbone, but it's harmless
    model.backbone = base 

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss=loss,
        metrics=['accuracy']
    )

    return model