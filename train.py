# train.py
import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import tensorflow as tf
from model import build_classifier
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

def prepare_datasets(data_dir, img_size=(224,224), batch_size=16, val_split=0.2, seed=1337):
    """
    Uses tf.keras.utils.image_dataset_from_directory to read folders directly.
    Returns train_ds, val_ds, class_names
    """
    class_names = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
    num_classes = len(class_names)
    label_mode = 'binary' if num_classes == 2 else 'categorical'

    train_ds = tf.keras.preprocessing.image_dataset_from_directory(
        data_dir,
        validation_split=val_split,
        subset="training",
        seed=seed,
        image_size=img_size,
        batch_size=batch_size,
        label_mode=label_mode
    )
    val_ds = tf.keras.preprocessing.image_dataset_from_directory(
        data_dir,
        validation_split=val_split,
        subset="validation",
        seed=seed,
        image_size=img_size,
        batch_size=batch_size,
        label_mode=label_mode
    )
    class_names = train_ds.class_names
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.prefetch(buffer_size=AUTOTUNE)
    return train_ds, val_ds, class_names

def plot_history(history, out_dir="models"):
    import os
    ensure = lambda p: os.makedirs(p, exist_ok=True)
    ensure(out_dir)
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.plot(history.history['accuracy'], label='train_acc')
    plt.plot(history.history['val_accuracy'], label='val_acc')
    plt.legend(); plt.title('Accuracy')

    plt.subplot(1,2,2)
    plt.plot(history.history['loss'], label='train_loss')
    plt.plot(history.history['val_loss'], label='val_loss')
    plt.legend(); plt.title('Loss')
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'training_history.png'))
    plt.close()

def evaluate_model(model, val_ds, class_names, out_dir="models"):
    """
    Runs predictions on validation set and prints report + saves confusion matrix.
    """
    import os
    ensure = lambda p: os.makedirs(p, exist_ok=True)
    ensure(out_dir)

    y_true = []
    y_pred = []
    
    for images, labels in val_ds:
        probs = model.predict(images, verbose=0)
        pred_labels = np.argmax(probs, axis=1)
        
        if len(labels.shape) == 2 and labels.shape[1] > 1:
            true_labels = np.argmax(labels.numpy(), axis=1)
        else:
            true_labels = labels.numpy()

        y_pred.extend(pred_labels.tolist())
        y_true.extend(true_labels.tolist())

    print("\n--- Classification Report ---")
    print(classification_report(y_true, y_pred, target_names=class_names))
    cm = confusion_matrix(y_true, y_pred)
    print("--- Confusion Matrix ---")
    print(cm)

    plt.figure(figsize=(5,4))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title("Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45)
    plt.yticks(tick_marks, class_names)
    plt.xlabel('Predicted')
    plt.ylabel('True')
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, cm[i, j], horizontalalignment="center", color="white" if cm[i,j] > cm.max()/2 else "black")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'confusion_matrix.png'))
    plt.close()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="dataset", help="path to dataset folder")
    parser.add_argument("--epochs", type=int, default=30, help="total epochs (stage1 + stage2)")
    parser.add_argument("--stage1_epochs", type=int, default=10, help="epochs to train head before fine-tuning")
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--unfreeze_at", type=int, default=40, help="number of layers from end of backbone to unfreeze (40 is good)")
    parser.add_argument("--model_out", type=str, default="models/insect_rat_model.keras")
    args = parser.parse_args()

    # Prepare data
    train_ds, val_ds, class_names = prepare_datasets(args.data_dir, batch_size=args.batch_size)

    # Build model
    num_classes = len(class_names)
    model = build_classifier(input_shape=(224,224,3), base_trainable=False, dropout=0.5, num_classes=num_classes)
    model.summary()

    # Callbacks
    checkpoint = ModelCheckpoint(args.model_out, monitor='val_accuracy', save_best_only=True, verbose=1)
    early = EarlyStopping(monitor='val_loss', patience=6, restore_best_weights=True, verbose=1)
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1)

    # Train head first (stage 1)
    stage1_epochs = min(args.stage1_epochs, args.epochs)
    print(f"Training head for {stage1_epochs} epochs...")
    history1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=stage1_epochs,
        callbacks=[checkpoint, early, reduce_lr]
    )

    # If total epochs greater than stage1, unfreeze tail of backbone and fine-tune
    if args.epochs > stage1_epochs:
        print("Starting fine-tuning stage: unfreezing backbone layers...")
        
        # Load the best model from stage 1 to continue
        print("Restoring best weights from checkpoint...")
        model = tf.keras.models.load_model(args.model_out)
        
        try:
            # --- THIS IS THE BUG FIX ---
            # We find the backbone layer by its name, not the attribute
            backbone = model.get_layer("mobilenet_backbone")
            if backbone is None:
                raise AttributeError("Could not find layer with name 'mobilenet_backbone'")
            # --- END OF BUG FIX ---

            backbone.trainable = True # Unfreeze the *whole* backbone
            
            # unfreeze last N layers
            unfreeze_at = int(args.unfreeze_at)
            total_layers = len(backbone.layers)
            cutoff = max(0, total_layers - unfreeze_at)
            
            # Then, re-freeze the first layers up to the cutoff
            for i, layer in enumerate(backbone.layers):
                if i < cutoff:
                    layer.trainable = False
            
            print(f"Fine-tuning: Unfrozen {len(backbone.layers) - cutoff} layers.")

            # recompile with lower lr
            model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5), loss=model.loss, metrics=['accuracy'])
            model.summary()
            
            # continue training remaining epochs
            remaining = args.epochs - stage1_epochs
            print(f"Fine-tuning for {remaining} epochs (last {unfreeze_at} backbone layers unfrozen)")
            history2 = model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=args.epochs, # Train for the total number of epochs
                initial_epoch=stage1_epochs, # Start from where stage 1 left off
                callbacks=[checkpoint, early, reduce_lr]
            )
        except Exception as e:
            print("Fine-tuning skipped: could not unfreeze backbone:", e)
            
    # Load the best model saved during the *entire* process
    print("\nLoading best saved model for final evaluation...")
    model = tf.keras.models.load_model(args.model_out)

    # Save final model and class names (class order used by Keras)
    class_file = os.path.join(os.path.dirname(args.model_out) or '.', 'class_names.txt')
    with open(class_file, 'w', encoding='utf-8') as f:
        for c in class_names:
            f.write(c + '\n')

    # Plot history and evaluate
    history = history2 if 'history2' in locals() else history1
    plot_history(history, out_dir=os.path.dirname(args.model_out) or ".")
    evaluate_model(model, val_ds, class_names, out_dir=os.path.dirname(args.model_out) or ".")

if __name__ == "__main__":
    main()