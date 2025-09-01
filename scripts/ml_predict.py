#!/usr/bin/env python3
"""
Content Intelligence Platform - ML ROI Prediction Script

This script trains and runs LightGBM models for predicting content ROI
based on various features including channel, vertical, format, and engagement metrics.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import pickle

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import lightgbm as lgb
    import shap
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError as e:
    print(f"Required ML libraries not found: {e}")
    print("Please install: pip install lightgbm scikit-learn shap matplotlib seaborn")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentROIPredictor:
    """Content ROI prediction using LightGBM"""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or "models/roi_predictor.pkl"
        self.model = None
        self.feature_encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        self.training_history = []
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML model"""
        logger.info("Preparing features for ML model")
        
        # Create feature dataframe
        features_df = df.copy()
        
        # Encode categorical variables
        categorical_features = ['channel', 'vertical', 'format', 'region', 'owner_team']
        for feature in categorical_features:
            if feature in features_df.columns:
                le = LabelEncoder()
                features_df[f'{feature}_encoded'] = le.fit_transform(features_df[feature].astype(str))
                self.feature_encoders[feature] = le
        
        # Calculate derived features
        features_df['recency_days'] = (datetime.now() - pd.to_datetime(features_df['publish_dt'])).dt.days
        
        # Production cost ratio (production cost / total cost)
        if 'production_cost' in features_df.columns and 'allocated_cost' in features_df.columns:
            features_df['production_cost_ratio'] = features_df['production_cost'] / features_df['allocated_cost'].replace(0, 1)
        else:
            features_df['production_cost_ratio'] = 0.5  # Default value
        
        # Engagement score (weighted combination of engagement metrics)
        if 'engagement_rate_pct' in features_df.columns:
            features_df['engagement_score'] = features_df['engagement_rate_pct'] / 100
        else:
            features_df['engagement_score'] = 0.1  # Default value
        
        # Channel performance tier
        channel_tiers = {
            'YouTube': 3, 'TikTok': 3, 'Blog': 2, 'Email': 1, 
            'Paid Social': 2, 'LinkedIn': 2, 'Twitter': 1, 'Instagram': 2
        }
        features_df['channel_tier'] = features_df['channel'].map(channel_tiers).fillna(1)
        
        # Vertical business impact
        vertical_impact = {
            'B2B SaaS': 3, 'Technology': 3, 'Finance': 3,
            'E-commerce': 2, 'Marketing': 2, 'Sales': 2,
            'Healthcare': 2, 'Education': 1, 'Retail': 1
        }
        features_df['vertical_impact'] = features_df['vertical'].map(vertical_impact).fillna(1)
        
        # Format complexity
        format_complexity = {
            'video': 3, 'blog': 1, 'ad': 2, 'email': 1, 'social': 2
        }
        features_df['format_complexity'] = features_df['format'].map(format_complexity).fillna(1)
        
        # Time-based features
        features_df['days_since_publish'] = features_df['recency_days']
        features_df['week_of_year'] = pd.to_datetime(features_df['publish_dt']).dt.isocalendar().week
        features_df['month_of_year'] = pd.to_datetime(features_df['publish_dt']).dt.month
        features_df['quarter'] = pd.to_datetime(features_df['publish_dt']).dt.quarter
        
        # Performance indicators
        if 'performance_score' in features_df.columns:
            features_df['performance_score_normalized'] = features_df['performance_score'] / 100
        else:
            features_df['performance_score_normalized'] = 0.5
        
        # Select final features for model
        feature_columns = [
            'channel_encoded', 'vertical_encoded', 'format_encoded',
            'recency_days', 'production_cost_ratio', 'engagement_score',
            'channel_tier', 'vertical_impact', 'format_complexity',
            'week_of_year', 'month_of_year', 'quarter',
            'performance_score_normalized'
        ]
        
        # Filter to available features
        available_features = [col for col in feature_columns if col in features_df.columns]
        features_df = features_df[available_features].fillna(0)
        
        self.feature_names = available_features
        logger.info(f"Prepared {len(available_features)} features: {available_features}")
        
        return features_df
    
    def prepare_target(self, df: pd.DataFrame) -> pd.Series:
        """Prepare target variable (ROI) for ML model"""
        logger.info("Preparing target variable")
        
        if 'roi_pct' in df.columns:
            target = df['roi_pct'].fillna(0)
        elif 'total_revenue' in df.columns and 'allocated_cost' in df.columns:
            # Calculate ROI if not present
            target = ((df['total_revenue'] - df['allocated_cost']) / df['allocated_cost'].replace(0, 1)) * 100
            target = target.fillna(0)
        else:
            raise ValueError("No ROI data found in dataframe")
        
        # Clip extreme values
        target = target.clip(-50, 200)  # ROI between -50% and 200%
        
        logger.info(f"Target variable prepared: range [{target.min():.2f}, {target.max():.2f}], mean: {target.mean():.2f}")
        
        return target
    
    def train_model(self, features: pd.DataFrame, target: pd.Series, 
                   test_size: float = 0.2, random_state: int = 42) -> Dict:
        """Train LightGBM model for ROI prediction"""
        logger.info("Training LightGBM model")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, target, test_size=test_size, random_state=random_state
        )
        
        # LightGBM parameters
        params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': random_state
        }
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        # Train model
        self.model = lgb.train(
            params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=1000,
            callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(100)]
        )
        
        # Make predictions
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        # Calculate metrics
        metrics = {
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
            'train_mape': mean_absolute_percentage_error(y_train, y_pred_train),
            'test_mape': mean_absolute_percentage_error(y_test, y_pred_test),
            'train_r2': r2_score(y_train, y_pred_train),
            'test_r2': r2_score(y_test, y_pred_test)
        }
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, features, target, cv=5, scoring='neg_mean_squared_error')
        metrics['cv_rmse'] = np.sqrt(-cv_scores.mean())
        
        logger.info(f"Model training completed. Test MAPE: {metrics['test_mape']:.4f}")
        
        # Store training history
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'feature_count': len(self.feature_names),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        })
        
        return metrics
    
    def predict_roi(self, content_attributes: Dict) -> Dict:
        """Predict ROI for given content attributes"""
        if self.model is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        logger.info("Making ROI prediction")
        
        # Create feature vector
        features = self._create_feature_vector(content_attributes)
        
        # Make prediction
        predicted_roi = self.model.predict([features])[0]
        
        # Calculate confidence (using model's prediction variance if available)
        confidence_score = 0.8  # Placeholder - would be calculated from model uncertainty
        
        # Get feature importance for this prediction
        feature_importance = self._get_feature_importance(features)
        
        prediction_result = {
            'predicted_roi': float(predicted_roi),
            'confidence_score': float(confidence_score),
            'feature_importance': feature_importance,
            'model_version': 'v1.0',
            'model_type': 'lightgbm',
            'features_used': self.feature_names,
            'prediction_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"ROI prediction: {predicted_roi:.2f}% with confidence {confidence_score:.2f}")
        
        return prediction_result
    
    def _create_feature_vector(self, content_attributes: Dict) -> List[float]:
        """Create feature vector from content attributes"""
        features = []
        
        # Map attributes to feature values
        for feature in self.feature_names:
            if 'channel_encoded' in feature:
                channel = content_attributes.get('channel', 'Blog')
                le = self.feature_encoders.get('channel')
                features.append(le.transform([channel])[0] if le else 0)
            elif 'vertical_encoded' in feature:
                vertical = content_attributes.get('vertical', 'Marketing')
                le = self.feature_encoders.get('vertical')
                features.append(le.transform([vertical])[0] if le else 0)
            elif 'format_encoded' in feature:
                format_type = content_attributes.get('format', 'blog')
                le = self.feature_encoders.get('format')
                features.append(le.transform([format_type])[0] if le else 0)
            elif 'recency_days' in feature:
                publish_date = content_attributes.get('publish_date', datetime.now())
                if isinstance(publish_date, str):
                    publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                recency = (datetime.now() - publish_date).days
                features.append(recency)
            elif 'production_cost_ratio' in feature:
                features.append(content_attributes.get('production_cost_ratio', 0.5))
            elif 'engagement_score' in feature:
                features.append(content_attributes.get('engagement_score', 0.1))
            elif 'channel_tier' in feature:
                channel_tiers = {'YouTube': 3, 'TikTok': 3, 'Blog': 2, 'Email': 1, 'Paid Social': 2, 'LinkedIn': 2, 'Twitter': 1, 'Instagram': 2}
                features.append(channel_tiers.get(content_attributes.get('channel', 'Blog'), 1))
            elif 'vertical_impact' in feature:
                vertical_impact = {'B2B SaaS': 3, 'Technology': 3, 'Finance': 3, 'E-commerce': 2, 'Marketing': 2, 'Sales': 2, 'Healthcare': 2, 'Education': 1, 'Retail': 1}
                features.append(vertical_impact.get(content_attributes.get('vertical', 'Marketing'), 1))
            elif 'format_complexity' in feature:
                format_complexity = {'video': 3, 'blog': 1, 'ad': 2, 'email': 1, 'social': 2}
                features.append(format_complexity.get(content_attributes.get('format', 'blog'), 1))
            elif 'week_of_year' in feature:
                features.append(datetime.now().isocalendar()[1])
            elif 'month_of_year' in feature:
                features.append(datetime.now().month)
            elif 'quarter' in feature:
                features.append((datetime.now().month - 1) // 3 + 1)
            elif 'performance_score_normalized' in feature:
                features.append(content_attributes.get('performance_score', 50) / 100)
            else:
                features.append(0.0)
        
        return features
    
    def _get_feature_importance(self, features: List[float]) -> Dict[str, float]:
        """Get feature importance for a specific prediction"""
        if self.model is None:
            return {}
        
        # Get SHAP values for this prediction
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values([features])
        
        # Create feature importance dictionary
        feature_importance = {}
        for i, feature in enumerate(self.feature_names):
            if i < len(shap_values[0]):
                feature_importance[feature] = float(abs(shap_values[0][i]))
        
        # Sort by importance
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        
        return feature_importance
    
    def save_model(self, filepath: str = None) -> None:
        """Save trained model and encoders"""
        filepath = filepath or self.model_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_encoders': self.feature_encoders,
            'feature_names': self.feature_names,
            'training_history': self.training_history,
            'model_info': {
                'version': 'v1.0',
                'created_at': datetime.now().isoformat(),
                'algorithm': 'lightgbm'
            }
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str = None) -> None:
        """Load trained model and encoders"""
        filepath = filepath or self.model_path
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        with open(filepath, 'rb') as f:
            pickle.load(f)
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.feature_encoders = model_data['feature_encoders']
        self.feature_names = model_data['feature_names']
        self.training_history = model_data.get('training_history', [])
        
        logger.info(f"Model loaded from {filepath}")
    
    def generate_shap_summary(self, features: pd.DataFrame, output_path: str = None) -> None:
        """Generate SHAP summary plot"""
        if self.model is None:
            logger.warning("No model available for SHAP analysis")
            return
        
        logger.info("Generating SHAP summary plot")
        
        # Create SHAP explainer
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(features)
        
        # Create summary plot
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, features, feature_names=self.feature_names, show=False)
        
        # Save plot
        output_path = output_path or f"shap_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        logger.info(f"SHAP summary plot saved to {output_path}")
    
    def backtest_model(self, features: pd.DataFrame, actual_roi: pd.Series, 
                      window_size: int = 30) -> Dict:
        """Backtest model performance using rolling windows"""
        logger.info("Running model backtest")
        
        if self.model is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        predictions = self.model.predict(features)
        
        # Calculate rolling metrics
        results = []
        for i in range(window_size, len(features)):
            window_pred = predictions[i-window_size:i]
            window_actual = actual_roi[i-window_size:i]
            
            mape = mean_absolute_percentage_error(window_actual, window_pred)
            rmse = np.sqrt(mean_squared_error(window_actual, window_pred))
            
            results.append({
                'window_end': i,
                'mape': mape,
                'rmse': rmse,
                'prediction_count': len(window_pred)
            })
        
        # Aggregate results
        avg_mape = np.mean([r['mape'] for r in results])
        avg_rmse = np.mean([r['rmse'] for r in results])
        
        backtest_results = {
            'window_size': window_size,
            'total_windows': len(results),
            'avg_mape': avg_mape,
            'avg_rmse': avg_rmse,
            'window_results': results
        }
        
        logger.info(f"Backtest completed. Average MAPE: {avg_mape:.4f}")
        
        return backtest_results

def main():
    """Main function for ML prediction script"""
    logger.info("Starting Content Intelligence Platform ML prediction")
    
    # Initialize predictor
    predictor = ContentROIPredictor()
    
    # Check if model exists
    if os.path.exists(predictor.model_path):
        logger.info("Loading existing model")
        predictor.load_model()
    else:
        logger.info("No existing model found. Training new model...")
        
        # Load sample data (in production, this would come from database)
        # For now, create synthetic data
        sample_data = create_sample_data()
        
        # Prepare features and target
        features = predictor.prepare_features(sample_data)
        target = predictor.prepare_target(sample_data)
        
        # Train model
        metrics = predictor.train_model(features, target)
        logger.info(f"Training metrics: {metrics}")
        
        # Save model
        predictor.save_model()
    
    # Example prediction
    content_attributes = {
        'channel': 'YouTube',
        'vertical': 'B2B SaaS',
        'format': 'video',
        'region': 'global',
        'publish_date': datetime.now() - timedelta(days=30),
        'production_cost_ratio': 0.7,
        'engagement_score': 0.15,
        'performance_score': 75
    }
    
    prediction = predictor.predict_roi(content_attributes)
    logger.info(f"Prediction result: {json.dumps(prediction, indent=2)}")
    
    # Generate SHAP summary if we have training data
    if hasattr(predictor, 'model') and predictor.model is not None:
        try:
            # Create sample features for SHAP analysis
            sample_features = predictor.prepare_features(create_sample_data())
            predictor.generate_shap_summary(sample_features)
        except Exception as e:
            logger.warning(f"Could not generate SHAP summary: {e}")
    
    logger.info("ML prediction script completed")

def create_sample_data() -> pd.DataFrame:
    """Create sample data for training/testing"""
    np.random.seed(42)
    
    # Generate synthetic content data
    n_samples = 1000
    
    channels = ['YouTube', 'TikTok', 'Blog', 'Email', 'Paid Social', 'LinkedIn', 'Twitter', 'Instagram']
    verticals = ['B2B SaaS', 'E-commerce', 'Healthcare', 'Marketing', 'Education', 'Finance', 'Technology', 'Sales']
    formats = ['video', 'blog', 'ad', 'email', 'social']
    
    data = {
        'channel': np.random.choice(channels, n_samples),
        'vertical': np.random.choice(verticals, n_samples),
        'format': np.random.choice(formats, n_samples),
        'region': ['global'] * n_samples,
        'publish_dt': [datetime.now() - timedelta(days=np.random.randint(1, 365)) for _ in range(n_samples)],
        'owner_team': ['Marketing'] * n_samples,
        'production_cost': np.random.uniform(1000, 50000, n_samples),
        'allocated_cost': np.random.uniform(1000, 50000, n_samples),
        'total_revenue': np.random.uniform(5000, 100000, n_samples),
        'engagement_rate_pct': np.random.uniform(5, 25, n_samples),
        'performance_score': np.random.uniform(30, 95, n_samples)
    }
    
    # Calculate ROI
    data['roi_pct'] = ((data['total_revenue'] - data['allocated_cost']) / data['allocated_cost']) * 100
    
    return pd.DataFrame(data)

if __name__ == "__main__":
    main() 