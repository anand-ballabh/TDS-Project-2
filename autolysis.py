###This code is written for a data analysis project. It takes a dataset as input, performs various data analysis tasks, generates visualizations, and sends the results to an LLM for interpretation.

## Import Libraries
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
from dotenv import load_dotenv
import base64

# import openai
import matplotlib
matplotlib.use('Agg')
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

# /// script
# requires.python = ">=3.13"
# dependencies = [
#    "requests",
#    "python-dotenv",
#    "python-dotenv",
#    "scikit-learn",
#    "matplotlib",
#    "seaborn",
#    "pandas",
#    "requests",
#    "tabulate",
#    "numpy",
#    "chardet"
# ]
# ///
load_dotenv()  # Load the .env file
api_key = os.getenv("AIPROXY_TOKEN") # Load the API key from environment variable
if not api_key:
    raise ValueError("AIPROXY_TOKEN is missing. Please set the environment variable.")

# Function to send a POST request to the LLM for narating a story and feedback
def analyze_data_with_feedback_and_code(filename, column_info, summary_stats, missing_values, correlation_matrix, top_3_corr, regression_results, geo_results, cluster_results, image_paths):

    # Encode the images as Base64 strings
    image_base64_strings = []
    for image_path in image_paths:
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_base64_strings.append(image_base64)

    # Create the message with embedded images as Base64
    message = f"""
    I am analyzing the following dataset:
    
    Filename: {filename}
    Columns and Data Types: {column_info}
    Summary Statistics: {summary_stats}
    Missing Values: {missing_values}
    Correlation Matrix: {correlation_matrix}
    Top 3 Correlated Feature Pairs: {top_3_corr}
    Regression Results: {regression_results}
    Geographical Analysis: {geo_results}
    Cluster Analysis: {cluster_results}
    
    Attached are images related to this dataset (e.g., a correlation heatmap and clustering visualization).

    1. Please narrate story of the dataset and its context. Basis images and the analysis results.
    2. Please evaluate and rate the analysis results.
   
       
    ### Embedded Images (Base64 Encoded):
    {', '.join([f'Image {i+1} (Base64): {img[:100]}...' for i, img in enumerate(image_base64_strings)])}  # Display first 100 characters of the base64
    """
    
    # Formulate the data for the POST request
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": message}]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Send the POST request to the LLM API
    response = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code} - {response.text}"



# Extract General info about data
def extract_general_info(data):
    """Extract general information about the dataset."""
    general_info = pd.DataFrame({
        "Column Name": data.columns,
        "Data Type": data.dtypes.astype(str)
    })
    return general_info

# Function to detect missing values
def detect_missing_values(data):
    """Detect missing values and their percentage."""
    missing = data.isnull().sum()
    missing_percentage = (missing / len(data)) * 100
    return pd.DataFrame({"Missing Count": missing, "Missing Percentage": missing_percentage})
def get_column_info(data):
    """Return column names and data types as a serializable dictionary."""
    column_info = {}
    for col in data.columns:
        # Convert the dtype to a string representation
        column_info[col] = str(data[col].dtype)
    return column_info

# Function to Generate basic summary
def generate_summary(data):
    """Generate basic summary statistics for the dataset."""
    summary = data.describe()
    return summary

# Function for Correlation analysis
def correlation_analysis(data, file_name):
    """Generate correlation matrix, save heatmap, and write results to README.md."""
    
    # Select numeric columns
    numeric_cols = data.select_dtypes(include=[np.number])
    
    if numeric_cols.empty:
        return "No numeric columns for correlation analysis."
    
    # Compute the correlation matrix
    correlation_matrix = numeric_cols.corr()
    
    # Find top 3 correlated feature pairs (absolute correlation, excluding self-correlation)
    corr_pairs = (
        correlation_matrix
        .abs()
        .unstack()
        .sort_values(ascending=False)
        .drop_duplicates()
    )
    top_3_corr = corr_pairs[corr_pairs < 1].head(3)  # Exclude perfect self-correlations
    
    # Create and save the heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        correlation_matrix, 
        annot=True, 
        cmap='coolwarm', 
        fmt='.2f', 
        xticklabels=numeric_cols.columns, 
        yticklabels=numeric_cols.columns
    )
    plt.title('Correlation Heatmap')
    plt.savefig("correlation_heatmap.png")
    plt.close()
    return correlation_matrix, top_3_corr

#Function for Regression analysis
def regression_analysis(data):
    """Perform regression analysis for numeric columns and summarize the results."""
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    regression_results = []
    feature_groups = {}  # Store results grouped by feature pair for better organization
    
    # Loop over combinations of numeric features
    for i, col1 in enumerate(numeric_cols):
        for j, col2 in enumerate(numeric_cols):
            if i < j:  # Avoid duplicate pairs and self-pairs
                X = data[[col1]].dropna()
                y = data[col2].dropna()
                common_index = X.index.intersection(y.index)
                X = X.loc[common_index]
                y = y.loc[common_index]
                
                if len(X) > 1:  # Ensure there are enough data points
                    model = LinearRegression()
                    model.fit(X, y)
                    y_pred = model.predict(X)
                    mse = mean_squared_error(y, y_pred)
                    
                    # Add results to the list
                    result = {
                        'Feature 1': col1,
                        'Feature 2': col2,
                        'MSE': mse,
                        'Intercept': model.intercept_,
                        'Coefficient': model.coef_[0]
                    }
                    regression_results.append(result)
                    
                    # Group by feature pair
                    feature_pair = f"{col1} & {col2}"
                    if feature_pair not in feature_groups:
                        feature_groups[feature_pair] = []
                    feature_groups[feature_pair].append(result)
    
    return pd.DataFrame(regression_results), feature_groups

## function to ferform Geographical analysis
def geo_analysis(data, country_column):
    """Analyze geographical data."""
    if country_column not in data.columns:
        return pd.DataFrame(), 0  # Return an empty DataFrame if the column doesn't exist

    exclude_keywords = ['date', 'year', 'time']
    numeric_cols = [
        col for col in data.select_dtypes(include=[float, int]).columns
        if not any(keyword in col.lower() for keyword in exclude_keywords)
    ]
    if not numeric_cols:
        return pd.DataFrame(), 0  # Return an empty DataFrame if no numeric columns

    # Drop rows with missing data in numeric columns
    clean_data = data.dropna(subset=numeric_cols)
    rows_removed = len(data) - len(clean_data)

    grouped = clean_data.groupby(country_column)
    rows = []

    for col in numeric_cols:
        for group_name, group_data in grouped:
            top_5 = group_data[col].quantile(0.95)
            bottom_5 = group_data[col].quantile(0.05)
            mean = group_data[col].mean()
            median = group_data[col].median()
            mode = group_data[col].mode().iloc[0] if not group_data[col].mode().empty else None
            max_val = group_data[col].max()
            min_val = group_data[col].min()

            rows.append({
                "Numeric Feature Name": col,
                "Country Name": group_name,
                "Mean": mean,
                "Median": median,
                "Mode": mode,
                "Top 5%": top_5,
                "Bottom 5%": bottom_5,
                "Max": max_val,
                "Min": min_val
            })

    geo_results = pd.DataFrame(rows)
    return geo_results, rows_removed

# Function to generate images
def generate_images(correlation_matrix):
    images = []
    
    # Create the heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f')
    heatmap_path = "correlation_heatmap.png"
    plt.title("Correlation Heatmap")
    plt.savefig(heatmap_path)
    plt.close()
    
    images.append(heatmap_path)
    return images

#Function for Clustering analysis using scikit-learn, KMeans
def cluster_analysis(data, n_clusters=4):
    """Perform clustering on numeric columns with missing value handling."""
    numeric_cols = data.select_dtypes(include=[np.number])
    if numeric_cols.empty:
        return "No numeric columns for clustering."
    
    # Impute missing values with the mean for numeric columns
    imputer = SimpleImputer(strategy='mean')
    imputed_data = imputer.fit_transform(numeric_cols)
    
    # Scale the data for better clustering performance
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(imputed_data)
    
    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(scaled_data)
    
    # Add cluster labels to the original data
    data['Cluster'] = clusters
    return data[['Cluster']]


# Main function to process the dataset
def main(filename):
    # Load the dataset
    data = pd.read_csv(filename, encoding="ISO-8859-1")
    file_name = os.path.basename(filename)

    # Generate a histogram of the data
    plt.figure(figsize=(6, 5))
    data.hist(bins=20, figsize=(15, 10))
    plt.savefig('histogram.png')

    plt.close()
    
    # Get basic column information and data types
    column_info = get_column_info(data)

    # Extract general info about the dataset
    general_info = extract_general_info(data)
    
    # Generate summary statistics for the data
    summary_stats = generate_summary(data)

    # Generate missing value analysis
    missing_values = detect_missing_values(data)

    # Correlation analysis
    correlation_matrix, top_3_corr = correlation_analysis(data, file_name)
    
    # Regression analysis
    regression_results, feature_groups = regression_analysis(data)

    # Generate images
    image_paths = generate_images(correlation_matrix)
    
    # Geographical analysis. (Geographical Analysis is only for countries, Languagages)
    groupby_col_candidates = ["country", "Country", "country_code", "Country Code", "country_name", "Country Name", "nationality", "Nationality", "nation", "Nation", "region", "Region", "Country name", "language", "Language", "language_code", "Language Code", "lang", "Lang", "lang_code", "Lang Code", "lang_name", "Lang Name", "lang_code", "Lang Code", "Zip Code"]
    # check if dataset has Country or language or Reagion or ZIP code column
    country_column = None
    for col in groupby_col_candidates:
        if col in data.columns:
            country_column = col
            break
    if country_column:
        geo_results, rows_removed = geo_analysis(data, country_column)
    else:
        geo_results = {}
    
    # Cluster analysis
    cluster_results = cluster_analysis(data)
    
    
    # Get a narrative analysis from LLM
    analysis_story = analyze_data_with_feedback_and_code(filename, column_info, summary_stats.to_string(),  missing_values.to_string(), correlation_matrix.to_string(), top_3_corr, regression_results.to_string(), geo_results.to_string(), cluster_results.to_string(), image_paths)
    
    # Write analysis and visualizations to README.md
    with open("README.md", "w", encoding="utf-8") as readme_file:
        readme_file.write(f"# Automated Data Analysis for {filename}\n")
        readme_file.write("\n## Dataset Overview\n")
        readme_file.write(general_info.to_markdown())
        readme_file.write("\n## Summary Statistics\n")
        readme_file.write(summary_stats.to_markdown())
        readme_file.write("\n\n ## Missing Value Report\n") # Missing values in data set
        readme_file.write(missing_values.to_markdown())
        readme_file.write("\n\n## Histogram\n\n") # 
        readme_file.write("\n\n![Histogram](histogram.png)\n")
        readme_file.write("\n## Correlation Matrix\n")
        readme_file.write("\n\n![Correlation Matrix](correlation_heatmap.png)\n")
        readme_file.write("\n## Analysis\n")
        readme_file.write(analysis_story)

    print("Analysis and visualizations saved to README.md and PNG files.")

# Entry point for the script
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)

    dataset_file = sys.argv[1]
    main(dataset_file)
