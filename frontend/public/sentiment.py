from openai import OpenAI
from prompt import prompt
import pandas as pd
from tqdm import tqdm

def sentiment_predict(texts):
    deepseek_predicts = []
    for text in tqdm(texts):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        deepseek_predicts.append(response.choices[0].message.content)
    return deepseek_predicts


api_key = "sk-4802fe532e994cca99e66865c7674b4d"  # # Step 1:  Replace by your api key
base_url = "https://api.deepseek.com"
client = OpenAI(api_key=api_key, base_url=base_url)

df = pd.read_excel("data/Anno117.xlsx")  # Step 2:  Change the file name
print(df.info())
texts = df["content"].astype(str).tolist()
deepseek_predicts = sentiment_predict(texts)

df["deepseek_predict"] = deepseek_predicts
df.to_excel("output/Anno117_predicted.xlsx")   # Step 3:  Change the output file name