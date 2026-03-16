import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

print("Loading dataset...")

df = pd.read_csv("../dataset/creditcard.csv")

df.rename(columns={"Class": "is_fraud"}, inplace=True)

X = df.drop("is_fraud", axis=1)
y = df["is_fraud"]

print("Splitting data...")

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("Training model...")

model = RandomForestClassifier(
    n_estimators=30,         
    class_weight="balanced", 
    random_state=42,
    n_jobs=-1               
)

model.fit(X_train, y_train)

print("Evaluating model...")

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("ROC-AUC Score:", roc_auc_score(y_test, y_prob))

pickle.dump(model, open("model.pkl", "wb"))

print("\nModel trained and saved successfully!")
