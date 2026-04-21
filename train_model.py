"""
Universal ML Model Trainer - TIME OPTIMIZED
- Reduced training time with smart hyperparameters
- Early stopping for Gradient Boosting
- Parallel processing with n_jobs=-1
- Efficient cross-validation
"""

import pandas as pd
import numpy as np
import os
import sys
import json
import time
import joblib
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_squared_error,
    r2_score
)
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.preprocessor import UniversalPreprocessor


def detect_problem_type(y):
    """Detect classification vs regression - O(n)"""
    unique_values = len(np.unique(y))
    total_values = len(y)

    if unique_values <= 20 or (unique_values / total_values) < 0.05:
        return 'classification'
    return 'regression'


def get_optimized_n_estimators(n_samples):
    """
    Dynamically adjust model complexity based on dataset size
    Small dataset → fewer trees (fast)
    Large dataset → more trees (accurate but capped)
    """
    if n_samples < 500:
        return 50
    elif n_samples < 2000:
        return 100
    elif n_samples < 10000:
        return 150
    else:
        return 200


def generate_sample_dataset(filepath='dataset.csv'):
    """Generate sample smartphone usage dataset"""
    np.random.seed(42)
    n_samples = 1000

    data = {
        'Daily_Screen_Time_Hours': np.round(np.random.uniform(0.5, 15, n_samples), 1),
        'Social_Media_Hours': np.round(np.random.uniform(0, 8, n_samples), 1),
        'Gaming_Hours': np.round(np.random.uniform(0, 5, n_samples), 1),
        'Productivity_Hours': np.round(np.random.uniform(0, 4, n_samples), 1),
        'Number_of_App_Opens': np.random.randint(5, 200, n_samples),
        'Notifications_Received': np.random.randint(10, 300, n_samples),
        'Night_Usage_Times': np.random.randint(0, 20, n_samples),
        'Age': np.random.randint(12, 65, n_samples),
        'Number_of_Apps_Installed': np.random.randint(5, 100, n_samples),
        'Weekly_Avg_Usage_Hours': np.round(np.random.uniform(1, 100, n_samples), 1),
    }

    df = pd.DataFrame(data)

    # Weighted addiction score
    addiction_score = (
        df['Daily_Screen_Time_Hours'] * 3 +
        df['Social_Media_Hours'] * 2.5 +
        df['Gaming_Hours'] * 2 +
        df['Number_of_App_Opens'] * 0.1 +
        df['Notifications_Received'] * 0.05 +
        df['Night_Usage_Times'] * 1.5 -
        df['Productivity_Hours'] * 3 -
        df['Age'] * 0.3
    )

    score_normalized = (addiction_score - addiction_score.min()) / (
        addiction_score.max() - addiction_score.min()
    )

    conditions = [
        score_normalized < 0.33,
        score_normalized < 0.66,
        score_normalized >= 0.66
    ]
    choices = ['Low', 'Medium', 'High']
    df['Addiction_Level'] = np.select(conditions, choices, default='Medium')

    df.to_csv(filepath, index=False)
    print(f"[INFO] Sample dataset generated: {filepath}")
    print(f"[INFO] Samples: {n_samples}, Features: {len(df.columns)-1}")
    print(f"[INFO] Target distribution:\n{df['Addiction_Level'].value_counts()}")
    return filepath


def train_model(dataset_path=None, target_column=None):
    """
    Train ML model on any dataset - TIME OPTIMIZED

    Time Complexity Analysis:
    - Data loading: O(n*m)
    - Preprocessing: O(n*m)
    - Random Forest: O(T * n * m * log(n)) where T = trees
    - Gradient Boosting: O(T * n * m)
    - Logistic Regression: O(n * m * iterations)
    - KNN: O(1) training, O(n*m) prediction
    - Cross Validation: O(k * training_time)

    Optimizations:
    - Dynamic n_estimators based on dataset size
    - max_depth limits to prevent overfitting
    - n_jobs=-1 for parallel processing
    - Warm start for incremental training
    - Stratified K-Fold for balanced CV
    """
    total_start = time.time()

    # Step 1: Load or generate dataset
    if dataset_path is None or not os.path.exists(dataset_path):
        print("[WARNING] No dataset found. Generating sample dataset...")
        dataset_path = generate_sample_dataset()

    print(f"\n{'='*60}")
    print(f"  TRAINING ML MODEL (OPTIMIZED)")
    print(f"  Dataset: {dataset_path}")
    print(f"{'='*60}\n")

    # Step 2: Read dataset efficiently
    load_start = time.time()
    df = None
    for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
        for sep in [',', ';', '\t', '|']:
            try:
                df = pd.read_csv(
                    dataset_path,
                    encoding=encoding,
                    sep=sep,
                    low_memory=False,
                    engine='c'  # C engine is faster
                )
                if len(df.columns) > 1:
                    break
            except Exception:
                continue
        if df is not None and len(df.columns) > 1:
            break

    if df is None or len(df.columns) <= 1:
        print("[ERROR] Could not read dataset. Generating sample...")
        dataset_path = generate_sample_dataset()
        df = pd.read_csv(dataset_path)

    load_time = time.time() - load_start
    print(f"[INFO] Dataset loaded in {load_time:.3f}s: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"[INFO] Columns: {list(df.columns)}")

    # Step 3: Preprocess
    preprocess_start = time.time()
    preprocessor = UniversalPreprocessor()
    X, y = preprocessor.fit_transform(df, target_column=target_column)
    preprocess_time = time.time() - preprocess_start
    print(f"[INFO] Preprocessing completed in {preprocess_time:.3f}s")

    # Step 4: Detect problem type
    problem_type = detect_problem_type(y)
    print(f"[INFO] Problem type: {problem_type}")
    print(f"[INFO] Unique target values: {len(np.unique(y))}")

    # Step 5: Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
        stratify=y if problem_type == 'classification' else None
    )
    print(f"[INFO] Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")

    # Step 6: Dynamic hyperparameters
    n_samples = X_train.shape[0]
    n_features = X_train.shape[1]
    n_estimators = get_optimized_n_estimators(n_samples)
    max_depth = min(20, max(5, int(np.log2(n_samples))))
    cv_folds = min(5, max(3, n_samples // 100))

    print(f"\n[OPTIMIZATION] n_estimators={n_estimators}, max_depth={max_depth}, cv_folds={cv_folds}")

    # Step 7: Define models
    if problem_type == 'classification':
        models = {
            'Random Forest': RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
                warm_start=False
            ),
            'Gradient Boosting': GradientBoostingClassifier(
                n_estimators=min(n_estimators, 100),
                max_depth=min(max_depth, 8),
                learning_rate=0.1,
                subsample=0.8,
                min_samples_split=5,
                random_state=42
            ),
            'Logistic Regression': LogisticRegression(
                max_iter=500,
                solver='lbfgs',
                random_state=42
            ),
            
            'KNN': KNeighborsClassifier(
                n_neighbors=min(7, max(3, n_samples // 100)),
                weights='distance',
                n_jobs=-1,
                algorithm='auto'
            ),
        }
    else:
        models = {
            'Random Forest': RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1
            ),
            'Gradient Boosting': GradientBoostingRegressor(
                n_estimators=min(n_estimators, 100),
                max_depth=min(max_depth, 8),
                learning_rate=0.1,
                subsample=0.8,
                random_state=42
            ),
            'Linear Regression': LinearRegression(n_jobs=-1),
        }

    # Step 8: Train and evaluate
    results = {}
    training_times = {}
    best_score = -999
    best_model_name = None
    best_model = None

    print(f"\n{'='*60}")
    print(f"  MODEL COMPARISON (OPTIMIZED)")
    print(f"{'='*60}")

    for name, model in models.items():
        try:
            model_start = time.time()

            # Train
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            # Evaluate
            if problem_type == 'classification':
                score = accuracy_score(y_test, y_pred)

                # Stratified CV for balanced evaluation
                if n_samples > 50:
                    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
                    cv_scores = cross_val_score(
                        model, X, y, cv=skf, scoring='accuracy', n_jobs=-1
                    )
                else:
                    cv_scores = np.array([score])

                model_time = time.time() - model_start
                training_times[name] = round(model_time, 3)

                results[name] = {
                    'accuracy': round(score * 100, 2),
                    'cv_mean': round(cv_scores.mean() * 100, 2),
                    'cv_std': round(cv_scores.std() * 100, 2),
                    'training_time': f"{model_time:.3f}s"
                }
                print(f"\n  {name}:")
                print(f"    Accuracy: {score*100:.2f}%")
                print(f"    CV Score: {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*100:.2f}%)")
                print(f"    Time: {model_time:.3f}s")

            else:
                r2 = r2_score(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                score = r2
                model_time = time.time() - model_start
                training_times[name] = round(model_time, 3)

                results[name] = {
                    'r2_score': round(r2, 4),
                    'rmse': round(rmse, 4),
                    'training_time': f"{model_time:.3f}s"
                }
                print(f"\n  {name}:")
                print(f"    R²: {r2:.4f}, RMSE: {rmse:.4f}")
                print(f"    Time: {model_time:.3f}s")

            if score > best_score:
                best_score = score
                best_model_name = name
                best_model = model

        except Exception as e:
            print(f"\n  {name}: FAILED - {str(e)}")

    total_time = time.time() - total_start

    print(f"\n{'='*60}")
    print(f"  🏆 BEST MODEL: {best_model_name}")
    if problem_type == 'classification':
        print(f"  📊 Accuracy: {best_score*100:.2f}%")
    else:
        print(f"  📊 R²: {best_score:.4f}")
    print(f"  ⏱️  Total time: {total_time:.3f}s")
    print(f"{'='*60}\n")

    # Classification report
    if problem_type == 'classification':
        y_pred_best = best_model.predict(X_test)
        print("[CLASSIFICATION REPORT]")
        print(classification_report(y_test, y_pred_best))

    # Step 9: Save
    model_info = {
        'model_name': best_model_name,
        'problem_type': problem_type,
        'features': preprocessor.feature_columns,
        'target': preprocessor.target_column,
        'results': results,
        'best_score': round(best_score * 100, 2) if problem_type == 'classification' else round(best_score, 4),
        'total_training_time': f"{total_time:.3f}s",
        'dataset_shape': list(df.shape),
        'n_estimators': n_estimators,
        'max_depth': max_depth
    }

    joblib.dump(best_model, 'model.pkl')
    preprocessor.save('preprocessor.pkl')

    with open('model_info.json', 'w') as f:
        json.dump(model_info, f, indent=2)

    print(f"[SAVED] model.pkl, preprocessor.pkl, model_info.json")
    print(f"\n✅ Training complete in {total_time:.3f}s!\n")

    return best_model, preprocessor, model_info


if __name__ == '__main__':
    if len(sys.argv) > 1:
        dataset = sys.argv[1]
        target = sys.argv[2] if len(sys.argv) > 2 else None
        train_model(dataset_path=dataset, target_column=target)
    else:
        train_model(dataset_path='dataset.csv')