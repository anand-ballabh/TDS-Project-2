import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
from datetime import datetime
from sklearn.impute import SimpleImputer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os
from fastapi import FastAPI
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

app = FastAPI()

# Function to detect missing values
def detect_missing_values(data):
    """Detect missing values and their percentage."""
    missing = data.isnull().sum()
    missing_percentage = (missing / len(data)) * 100
    return pd.DataFrame({"Missing Count": missing, "Missing Percentage": missing_percentage})

# Function to detect outliers
def detect_outliers_iqr(data):
    """Detect outliers using IQR for numeric columns."""
    outlier_report = {}
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        Q1 = data[col].quantile(0.25)
        Q3 = data[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
        outlier_report[col] = len(outliers)
    return outlier_report
# Function to detect anamoly
def detect_anomalies(data):
    """Detect anomalies using Isolation Forest."""
    numeric_cols = data.select_dtypes(include=[np.number])
    if numeric_cols.empty:
        return "No numeric columns for anomaly detection."
    
    # Impute missing values with the mean for numeric columns
    imputer = SimpleImputer(strategy='mean')
    imputed_data = imputer.fit_transform(numeric_cols)
    
    # Scale the data
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(imputed_data)
    
    # Apply Isolation Forest
    model = IsolationForest(contamination=0.05, random_state=42)
    anomalies = model.fit_predict(scaled_data)
    
    # Add anomaly column to the original data
    data['Anomaly'] = anomalies
    return data[data['Anomaly'] == -1]  # Return rows marked as anomalies

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
    plt.figure(figsize=(10, 8))
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

# Function to perform feature importance analysis

def feature_importance(data):
    """Analyze feature importance using RandomForest."""
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) < 2:
        return "Not enough numeric columns for feature importance analysis."
    X = data[numeric_cols[:-1]].dropna()
    y = data[numeric_cols[-1]].dropna()
    common_index = X.index.intersection(y.index)
    X = X.loc[common_index]
    y = y.loc[common_index]
    model = RandomForestRegressor(random_state=42)
    model.fit(X, y)
    importance = pd.DataFrame({
        'Feature': X.columns,
        'Importance': model.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    return importance

# Function to perform time series analysis
def time_series_analysis(data):
    """Analyze time series data."""
    date_cols = data.select_dtypes(include=[np.datetime64]).columns
    if date_cols.empty:
        return "No datetime columns for time series analysis."
    analysis_results = {}
    for col in date_cols:
        data[col] = pd.to_datetime(data[col])
        data.set_index(col, inplace=True)
        resampled = data.resample('M').mean()  # Example: monthly mean
        resampled.plot(figsize=(10, 6))
        plt.title(f"Time Series Analysis: {col}")
        plt.savefig(f"time_series_{col}.png")
        plt.close()
        analysis_results[col] = resampled
    return analysis_results


# Function to perform cluster analysis

def cluster_analysis(data, n_clusters=3):
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

def create_histograms(data):
    """Generate histograms for each numeric feature with axis labels."""
    numeric_cols = data.select_dtypes(include=[np.number])
    if numeric_cols.empty:
        print("No numeric columns to plot histograms.")
        return

    # Create histograms for numeric columns
    axes = numeric_cols.hist(bins=20, figsize=(15, 10), layout=(len(numeric_cols.columns), 1))

    # Adjusting the layout if multiple axes
    if len(numeric_cols.columns) > 1:
        for ax, col in zip(axes.flatten(), numeric_cols.columns):
            ax.set_xlabel(f'{col} (Feature)')
            ax.set_ylabel('Frequency')
            ax.set_title(f'Histogram of {col}')
    else:  # If only one numeric column, `axes` won't be iterable
        axes.set_xlabel(f'{numeric_cols.columns[0]} (Feature)')
        axes.set_ylabel('Frequency')
        axes.set_title(f'Histogram of {numeric_cols.columns[0]}')

    # Save the combined histogram figure
    plt.tight_layout()  # Ensure proper spacing between plots
    plt.savefig("histogram.png")
    plt.close()

def main(file_path):
    data = pd.read_csv(file_path, encoding="ISO-8859-1")
    file_name = os.path.basename(file_path)
    # Data Summary
    summary = data.describe()
    # Missing Value Detection
    missing_report = detect_missing_values(data)

    # Outlier Detection
    outlier_report = detect_outliers_iqr(data)

    # Anomaly Detection
    anomalies = detect_anomalies(data)

    # Correlation Analysis and Heatmap
    correlation_matrix, top_3_corr = correlation_analysis(data, file_name)

    # Regression Analysis
    regression_results, feature_groups = regression_analysis(data)

    # Feature Importance Analysis
    feature_importance_report = feature_importance(data)

    # Time Series Analysis
    time_series_results = time_series_analysis(data)

    # Cluster Analysis
    cluster_results = cluster_analysis(data)

     # Write results to README.md
    with open('README.md', 'w', encoding='utf-8') as readme:
        readme.write(f"# Automated Analysis for file {file_name}\n")
        readme.write("## Summary Statistics\n\n")
        readme.write(summary.to_markdown())
        readme.write("## Missing Value Report\n")
        readme.write(missing_report.to_markdown())
        readme.write("\n\n## Outlier Report\n")
        for col, count in outlier_report.items():
            readme.write(f"- {col}: {count} outliers detected.\n")
        # readme.write("\n\n## Anomalies\n")
        # readme.write(anomalies.to_markdown())
        readme.write("\n\n## Histogram\n\n")
        readme.write("\n\n![Histogram](histogram.png)\n")
  
        # Write top 3 correlated pairs

        readme.write("\n\n## Correlation Analysis\n")
        if isinstance(correlation_matrix, pd.DataFrame):
            readme.write("## Below is the correlation matrix for numeric features in the dataset:\n\n")
            readme.write(correlation_matrix.to_markdown())
            readme.write("\n\n## Heatmap\n")
            readme.write("\n\n![Correlation Heatmap](correlation_heatmap.png)\n")
        else:
            readme.write(correlation_matrix)  # Message if no numeric columns

        if top_3_corr is not None:
            readme.write("\n### Top 3 Correlated Feature Pairs:\n")
            for (feature1, feature2), value in top_3_corr.items():
                readme.write(f"- **{feature1}** and **{feature2}** have a correlation of {value:.2f}.\n")
                readme.write(f"  This indicates a {'strong' if abs(value) > 0.7 else 'moderate'} relationship.\n")
        else:
            readme.write("No significant correlations found.\n")


        readme.write("\n\n## Regression Analysis\n")
        # Write Summary for Feature Pairs
        for feature_pair, results in feature_groups.items():
            readme.write(f"### Feature Pair: {feature_pair}\n")
            for result in results:
                readme.write(f"- **MSE**: {result['MSE']:.2e}, **Intercept**: {result['Intercept']:.2f}, **Coefficient**: {result['Coefficient']:.2f}\n")
            readme.write("\n")
        
        # Optionally, you can also include a full table in markdown format (like before)
        readme.write("\n### Full Regression Results:\n")
        readme.write(regression_results.to_markdown())
        readme.write("\n\n## Feature Importance\n")
        readme.write(feature_importance_report.to_markdown())
        # readme.write("\n\n## Cluster Analysis\n")
        # readme.write(cluster_results.to_markdown())
        # readme.write("\n\n## Histogram\n\n")
        # readme.write("\n\n![Histogram](histogram.png)\n")
        # # if "overall" in data.columns:
        #     readme.write("![Overall Rating Boxplot](overall_rating_boxplot.png)\n")

@app.get("/")
def analyze(file_path: str):
    try:
        # Perform the analysis
        main(file_path)
        return {
            "message": "Analysis complete.",
            "readme": "README.md",
            "charts": ["histogram.png", "overall_rating_boxplot.png"]
        }
    except Exception as e:
        return {"error": str(e)}
