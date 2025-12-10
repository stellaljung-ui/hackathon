import asyncio
from dotenv import load_dotenv
from air import DistillerClient, AsyncAIRefinery
import os
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ----------------------------
# Local Variables
# ----------------------------

# API Key
load_dotenv() # loads your API_KEY from your local '.env' file
api_key=str(os.getenv("API_KEY"))

# Configurations 
config = {
      "pinterest_csv_path": "data/pins.csv",                              # pinterest data
      "cosmic_mart_csv_path": "data/cosmicmart_generic_products_600.csv", # cosmic mart data
      "pinterest_text_cols": ["title", "details"],                        # chosen pinterest columns
      "cosmic_text_cols": ["title", "details"],               # chosen cosmic columns
      "embedding_model": "intfloat/e5-mistral-7b-instruct",
      "top_k": 10,                                                        # num of results                          
      "similarity_threshold": 0.25,                                       # ??
      "output_csv_path": "pin_to_sku_matches.csv",
      "output_json_path": "matches.json",
} 

# 1. Read pinterest.csv and cosmic_mart.csv into pandas dataframe
pinterest_df = pd.read_csv(config.get("pinterest_csv_path"))
cosmic_df = pd.read_csv(config.get("cosmic_mart_csv_path"))

# 2. Choose the specific columns to embed
chosen_pinterest = pinterest_df[config.get("pinterest_text_cols")]
chosen_cosmic = cosmic_df[config.get("cosmic_text_cols")]

# ----------------------------
# 3. Generate Embeddings
# ----------------------------
def create_all_embeddings(df):
    # Initialize the AI client with authentication details
    client = AsyncAIRefinery(api_key=api_key)  # Supports a async AIRefinery client too

    for row in df: 
        # Create an embedding for the input text
        response = client.embeddings.create(
            input=row,
            model="intfloat/e5-mistral-7b-instruct",
        )

        # Add the embedding to the end of the row
        row.append(response)
        print(response)

# ----------------------------
# 4. Calculate Cosine Similarity
# ----------------------------
def calculate_cosine_similarity(p_df, c_df):
    """
        Returns: 
            The code produces an m × n matrix of cosine similarity scores, where:
                m = number of rows in pinterest_df (each row’s embedding)
                n = number of rows in cosmic_df (each row’s embedding)
                Each entry similarity_matrix[i, j] = cosine similarity between the embedding in row i of pinterest_df and row j of cosmic_df.
    """
    # 1. Get the last column of each dataframe
    p_embeddings = p_df[:, -1] 
    c_embeddings = c_df[:, -1]

    # 2. Normalize both embeddings
    p_norm = p_embeddings / np.linalg.norm(p_embeddings, axis=1, keepdims=True)
    c_norm = c_embeddings / np.linalg.norm(c_embeddings, axis=1, keepdims=True)

    # 3. Compute cosine similarity with matrix multiplication
    similarity_matrix = np.dot(p_norm, c_norm.T)

    return similarity_matrix

# ----------------------------
# 5. Find the top results for each row
# ----------------------------
def find_top_k_results(matrix, num_results=2):
    # 1. for each row in pinterest_df, sort by descending order the index of the top cosmic_mart similarity score      
    sorted_cosmic = np.argsort(-matrix, axis=1) # keeps the indexes of j

    ## THIS IS WHERE I'M CONFUSED
    # 2. for each row in pinterest_df, take the top n results and find the corresponding cosmic_mart id
    top_idx = sorted_cosmic[:, :num_results] # (num_pins, n)
    top_ids = cosmic_df[top_idx] 

def main():
    # 3. Generate Embeddings
    create_all_embeddings(chosen_pinterest)
    create_all_embeddings(chosen_cosmic)

    # Calculate Cosine Similarity
    cosine_matrix = calculate_cosine_similarity()

    # Find the top results
    find_top_k_results(cosine_matrix)

# Example call to create_embedding function
if __name__ == "__main__":
    ayncio.run(main())