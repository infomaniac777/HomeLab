import unittest
import numpy as np
from unittest.mock import patch

# Assuming audio_server.py is in the same directory or accessible via PYTHONPATH
from audio_server import normalize_audio, load_doorbell_template, calculate_correlation

class TestAudioServerBasic(unittest.TestCase):

    def test_normalize_audio_simple(self):
        """Test normalization of a simple audio array."""
        audio_data = np.array([10, 20, -10, 0], dtype=np.int16)
        expected_normalized = np.array([0.5, 1.0, -0.5, 0.0], dtype=np.float32)
        normalized_audio = normalize_audio(audio_data)
        self.assertTrue(np.allclose(normalized_audio, expected_normalized, atol=1e-6),
                        msg="Normalization did not produce the expected result.")

    def test_normalize_audio_zeros(self):
        """Test normalization of an all-zero audio array."""
        audio_data = np.array([0, 0, 0], dtype=np.int16)
        expected_normalized = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        normalized_audio = normalize_audio(audio_data)
        self.assertTrue(np.allclose(normalized_audio, expected_normalized, atol=1e-6),
                        msg="Normalization of zeros did not produce all zeros.")

    @patch('audio_server.os.path.exists')
    def test_load_doorbell_template_file_not_found(self, mock_os_exists):
        """Test load_doorbell_template when the template file does not exist."""
        mock_os_exists.return_value = False
        template, size = load_doorbell_template("non_existent_file.wav")
        self.assertIsNone(template, "Template should be None when file not found.")
        self.assertEqual(size, 0, "Size should be 0 when file not found.")
        mock_os_exists.assert_called_once_with("non_existent_file.wav")

    def test_calculate_correlation_identical_signals(self):
        """Test correlation of identical, non-flat signals."""
        # Use a signal with variation
        raw_signal = np.array([10, 20, 10, 30, 15], dtype=np.float32)
        
        # Template is pre-normalized as it would be by load_doorbell_template
        template_normalized = normalize_audio(raw_signal.copy())
        
        # Audio segment is passed raw; calculate_correlation normalizes it internally
        audio_segment = raw_signal.copy()

        # Ensure the normalized template is not flat (std_dev is not zero)
        # This is crucial for the expected score calculation based on the formula.
        std_template_norm = np.std(template_normalized)
        self.assertNotAlmostEqual(std_template_norm, 0.0,
                                  msg="Normalized template standard deviation should not be zero for this test case.")

        correlation_score = calculate_correlation(audio_segment, template_normalized)
        
        # Expected score for identical signals X (after both are normalized similarly):
        # E[X^2] / Var(X) = (Var(X) + Mean(X)^2) / Var(X) = 1 + (Mean(X)/Std(X))^2
        # This applies if len(audio_segment) == len(template) and mode='valid' for correlate.
        mean_norm = np.mean(template_normalized)
        # Using the already calculated std_template_norm
        expected_score = 1 + (mean_norm / std_template_norm)**2
        
        self.assertAlmostEqual(correlation_score, expected_score, places=5, 
                               msg=f"Correlation for identical signals incorrect. Got {correlation_score}, expected {expected_score}")

    def test_calculate_correlation_uncorrelated_signals(self):
        """Test correlation of highly uncorrelated signals."""
        template_raw = np.array([0.1, 0.5, -0.2, 0.8, -0.5], dtype=np.float32)
        template_normalized = normalize_audio(template_raw)
        
        # Ensure template is not flat, so its std is not zero.
        self.assertNotAlmostEqual(np.std(template_normalized), 0.0,
                                  msg="Normalized template standard deviation should not be zero.")

        # Create a random audio segment, likely uncorrelated with the template
        # Ensure its length is at least that of the template for 'valid' correlation
        audio_segment = np.random.uniform(-1.0, 1.0, size=len(template_normalized) * 2).astype(np.float32)
        
        # If audio_segment happens to be flat after normalization, its std_dev will be 0,
        # and calculate_correlation should return 0.0, which is low (passes the test).
        correlation_score = calculate_correlation(audio_segment, template_normalized)
        
        # For highly uncorrelated signals, the score should be low.
        # The exact value can vary, but it should be significantly less than for matched signals.
        self.assertLess(correlation_score, 0.5, 
                        msg=f"Correlation for uncorrelated signals should be low. Got {correlation_score}")

if __name__ == '__main__':
    unittest.main()
