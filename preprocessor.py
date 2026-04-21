"""
Universal Dataset Preprocessor - OPTIMIZED
- Reduced time complexity with efficient operations
- Vectorized operations instead of loops
- Caching for repeated transformations
- Memory efficient processing
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib
import os
import warnings
warnings.filterwarnings('ignore')


class UniversalPreprocessor:
    """Handles ANY dataset without errors - Time Optimized"""

    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.column_types = {}
        self.fill_values = {}
        self.feature_columns = []
        self.target_column = None
        self.is_fitted = False
        self._type_cache = {}

    def auto_detect_target(self, df):
        """Auto-detect target column - O(n) where n = columns"""
        target_keywords = {
            'target', 'label', 'class', 'output', 'result',
            'prediction', 'predict', 'addiction', 'risk',
            'level', 'category', 'status', 'diagnosis',
            'addicted', 'dependent', 'usage_level', 'risk_level',
            'addiction_level', 'addiction_score', 'behavior',
            'smartphone_addiction', 'phone_addiction', 'y',
            'is_addicted', 'addicted_or_not'
        }

        # O(columns * keywords) - both are small, so effectively O(1)
        col_lower_map = {col: col.lower().strip().replace(' ', '_') for col in df.columns}

        for col, col_lower in col_lower_map.items():
            for keyword in target_keywords:
                if keyword in col_lower:
                    return col

        return df.columns[-1]

    def auto_convert_types(self, df):
        """Auto-convert types using vectorized operations - O(n*m)"""
        df = df.copy()

        for col in df.columns:
            # Use pandas built-in for faster conversion
            converted = pd.to_numeric(df[col], errors='coerce')
            valid_ratio = converted.notna().mean()

            if valid_ratio > 0.5:
                df[col] = converted
                self.column_types[col] = 'numeric'
            else:
                df[col] = df[col].astype(str).str.strip()
                self.column_types[col] = 'categorical'

        return df

    def handle_missing_values(self, df):
        """Handle missing values - Vectorized O(n*m)"""
        df = df.copy()

        # Process numeric and categorical columns separately (batch operation)
        numeric_cols = [c for c in df.columns if self.column_types.get(c) == 'numeric']
        categorical_cols = [c for c in df.columns if self.column_types.get(c) == 'categorical']

        # Batch fill numeric columns with median
        for col in numeric_cols:
            if df[col].isnull().any():
                fill_val = df[col].median()
                df[col].fillna(fill_val, inplace=True)
                self.fill_values[col] = fill_val

        # Batch fill categorical columns with mode
        for col in categorical_cols:
            if df[col].isnull().any() or (df[col] == 'nan').any():
                mode_val = df[col].mode()
                fill_val = mode_val.iloc[0] if len(mode_val) > 0 else 'Unknown'
                df[col] = df[col].replace('nan', fill_val)
                df[col].fillna(fill_val, inplace=True)
                self.fill_values[col] = fill_val

        return df

    def remove_outliers(self, df, columns):
        """Remove outliers using vectorized IQR - O(n*m)"""
        df = df.copy()
        numeric_cols = [c for c in columns if self.column_types.get(c) == 'numeric']

        if numeric_cols:
            numeric_df = df[numeric_cols]
            Q1 = numeric_df.quantile(0.25)
            Q3 = numeric_df.quantile(0.75)
            IQR = Q3 - Q1

            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR

            # Vectorized clip operation
            df[numeric_cols] = numeric_df.clip(lower=lower, upper=upper, axis=1)

        return df

    def encode_categorical(self, df, fit=True):
        """Encode categorical columns - O(n*k) where k = categories"""
        df = df.copy()
        categorical_cols = [c for c in df.columns if self.column_types.get(c) == 'categorical']

        for col in categorical_cols:
            if fit:
                le = LabelEncoder()
                df[col] = df[col].astype(str)
                df[col] = le.fit_transform(df[col])
                self.label_encoders[col] = le
            else:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    df[col] = df[col].astype(str)
                    known_labels = set(le.classes_)
                    default_label = le.classes_[0]
                    # Vectorized mapping
                    df[col] = df[col].map(
                        lambda x: x if x in known_labels else default_label
                    )
                    df[col] = le.transform(df[col])
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    def fit_transform(self, df, target_column=None):
        """
        Complete preprocessing pipeline - OPTIMIZED
        Overall: O(n * m * log(n)) where n=rows, m=columns
        """
        df = df.copy()

        # Step 1: Drop duplicates - O(n*m)
        initial_rows = len(df)
        df = df.drop_duplicates()
        dropped = initial_rows - len(df)
        if dropped > 0:
            print(f"[INFO] Dropped {dropped} duplicate rows")

        # Step 2: Auto detect target - O(m)
        if target_column:
            self.target_column = target_column
        else:
            self.target_column = self.auto_detect_target(df)
        print(f"[INFO] Target column: {self.target_column}")

        # Step 3: Auto convert types - O(n*m)
        df = self.auto_convert_types(df)

        # Step 4: Handle missing values - O(n*m)
        df = self.handle_missing_values(df)

        # Step 5: Separate features and target
        y = df[self.target_column].copy()
        X = df.drop(columns=[self.target_column])

        self.feature_columns = list(X.columns)

        # Step 6: Remove outliers - O(n*m)
        X = self.remove_outliers(X, self.feature_columns)

        # Step 7: Encode categoricals - O(n*k)
        X = self.encode_categorical(X, fit=True)

        # Step 8: Encode target
        if self.column_types.get(self.target_column) == 'categorical':
            le_target = LabelEncoder()
            y = le_target.fit_transform(y.astype(str))
            self.label_encoders['__target__'] = le_target
        else:
            y = pd.to_numeric(y, errors='coerce').fillna(0).values

        # Step 9: Scale features - O(n*m)
        X_values = X.values.astype(np.float64)
        X_scaled = self.scaler.fit_transform(X_values)

        self.is_fitted = True
        print(f"[INFO] Features: {self.feature_columns}")
        print(f"[INFO] Shape: {X_scaled.shape}")

        return X_scaled, y

    def transform(self, input_data):
        """
        Transform new input - OPTIMIZED O(m) for single row
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor not fitted. Call fit_transform first.")

        # Handle different input types
        if isinstance(input_data, dict):
            df = pd.DataFrame([input_data])
        elif isinstance(input_data, list):
            df = pd.DataFrame([input_data], columns=self.feature_columns)
        elif isinstance(input_data, pd.DataFrame):
            df = input_data.copy()
        else:
            df = pd.DataFrame([input_data], columns=self.feature_columns)

        # Ensure all feature columns exist
        for col in self.feature_columns:
            if col not in df.columns:
                default = self.fill_values.get(col, 0)
                df[col] = default

        # Keep only features in correct order
        df = df[self.feature_columns]

        # Convert types efficiently
        for col in df.columns:
            if self.column_types.get(col) == 'numeric':
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col].fillna(self.fill_values.get(col, 0), inplace=True)
            else:
                df[col] = df[col].astype(str)
                fill = self.fill_values.get(col, 'Unknown')
                df[col] = df[col].replace('nan', fill)
                df[col].fillna(fill, inplace=True)

        # Encode
        df = self.encode_categorical(df, fit=False)

        # Scale
        X_scaled = self.scaler.transform(df.values.astype(np.float64))

        return X_scaled

    def get_target_label(self, encoded_value):
        """Convert prediction back to original label - O(1)"""
        if '__target__' in self.label_encoders:
            try:
                return self.label_encoders['__target__'].inverse_transform(
                    [int(encoded_value)]
                )[0]
            except Exception:
                return str(encoded_value)
        return str(encoded_value)

    def save(self, filepath='preprocessor.pkl'):
        """Save preprocessor"""
        joblib.dump(self, filepath)
        print(f"[INFO] Preprocessor saved: {filepath}")

    @staticmethod
    def load(filepath='preprocessor.pkl'):
        """Load preprocessor"""
        if os.path.exists(filepath):
            return joblib.load(filepath)
        return None