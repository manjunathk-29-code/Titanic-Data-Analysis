import pandas as pd

df = pd.read_csv("Titanic-Dataset.csv")

print(df.shape)
print(df.columns.tolist())
print(df.isnull().sum())