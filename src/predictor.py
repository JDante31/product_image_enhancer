"""
Purchase prediction module for e-commerce customers.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from xgboost import XGBClassifier
import joblib
from pathlib import Path

class PurchasePredictor:
    """Predicts next purchase category for customers."""
    
    def __init__(self):
        """Initialize the predictor with pre-trained model and artifacts."""
        artifacts_path = Path(__file__).parent.parent / 'models' / 'model_artifacts.joblib'
        
        # Load all artifacts
        artifacts = joblib.load(artifacts_path)
        
        # Unpack artifacts
        self.model = artifacts['model']
        self.scaler = artifacts['scaler']
        self.label_encoder = artifacts['label_encoder']
        self.valid_categories = artifacts['valid_categories']
        self.feature_columns = artifacts['feature_columns']
        self.min_sequences = artifacts['min_sequences']
        self.final_feature_names = artifacts['final_feature_names']
    
    def _prepare_features(self, customer_data):
        """
        Prepare features for prediction.
        
        Args:
            customer_data (pd.DataFrame): Raw customer data
            
        Returns:
            np.array: Processed features
        """
        # Map rare categories to 'Other'
        customer_data = customer_data.copy()
        mask = ~customer_data['current_subcategory'].isin(self.valid_categories[:-1])  # Exclude 'Other'
        customer_data.loc[mask, 'current_subcategory'] = 'Other'
        
        # One-hot encode current subcategory with valid categories
        current_cat_dummies = pd.get_dummies(
            customer_data['current_subcategory'],
            prefix='current'
        )
        
        # Add missing columns with zeros
        for cat in self.valid_categories:
            col = f'current_{cat}'
            if col not in current_cat_dummies.columns:
                current_cat_dummies[col] = 0
                
        # Combine numerical and categorical features
        features = pd.concat([
            customer_data[self.feature_columns],
            current_cat_dummies
        ], axis=1)
        
        # Ensure exact same feature order as during training
        features = features[self.final_feature_names]
        
        # Scale features
        return self.scaler.transform(features)
    
    def predict_batch(self, customer_data):
        """
        Generate predictions for multiple customers.
        
        Args:
            customer_data (pd.DataFrame): Customer behavior data
            
        Returns:
            pd.DataFrame: Predictions with customer_id and predicted_category
        """
        # Prepare features
        X = self._prepare_features(customer_data)
        
        # Generate predictions
        pred_labels = self.model.predict(X)
        pred_proba = self.model.predict_proba(X)
        
        # Get confidence scores
        confidence = np.max(pred_proba, axis=1)
        
        # Convert numeric labels back to categories
        categories = self.label_encoder.inverse_transform(pred_labels)
        
        # Create results dataframe
        results = pd.DataFrame({
            'customer_id': customer_data['user_id'],
            'predicted_category': categories,
            'confidence': confidence
        })
        
        return results
    
    def predict_single(self, customer_data):
        """
        Generate prediction for a single customer.
        
        Args:
            customer_data (pd.Series): Single customer's behavior data
            
        Returns:
            dict: Prediction results with category and confidence
        """
        # Convert series to dataframe
        df = pd.DataFrame([customer_data])
        
        # Get prediction
        prediction = self.predict_batch(df).iloc[0]
        
        return {
            'customer_id': prediction['customer_id'],
            'predicted_category': prediction['predicted_category'],
            'confidence': prediction['confidence']
        } 