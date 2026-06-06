# clustering/clusterer.py
# K-means clusters JDs into groups by similarity
# PCA reduces dimensions for visualization

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize


# N_CLUSTERS = 3  # FAANG / Series A / Mid-market
RANDOM_STATE = 42


def cluster(embeddings: np.ndarray) -> np.ndarray:
    """
    Runs k-means on embeddings.
    Returns array of cluster labels (0, 1, 2) for each job.
    """
    n = min(3, len(embeddings))  # auto-reduce clusters if too few jobs
    print(f"  [Clusterer] Running k-means with {n} clusters...")

    
    # Normalize — cosine similarity works better than euclidean for text
    normalized = normalize(embeddings)
    
    kmeans = KMeans(
        n_clusters=n,
        random_state=RANDOM_STATE,
        n_init=10  # run 10 times, pick best
    )
    labels = kmeans.fit_predict(normalized)
    
    # Print cluster sizes
    unique, counts = np.unique(labels, return_counts=True)
    for cluster_id, count in zip(unique, counts):
        print(f"    Cluster {cluster_id}: {count} jobs")
    
    return labels


def get_pca_coords(embeddings: np.ndarray) -> np.ndarray:
    """
    Reduces embeddings to 2D for scatter plot visualization.
    Returns (n_jobs, 2) array of x,y coordinates.
    """
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    return pca.fit_transform(normalize(embeddings))