from model import build_classifier

print('Building binary model...')
mb = build_classifier(num_classes=2)
mb.summary()
print('\nBuilding 3-class model...')
mc = build_classifier(num_classes=3)
mc.summary()
print('\nSuccess')
