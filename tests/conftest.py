"""
Pytest configuration for the HDFC Mutual Fund RAG Chatbot test suite.
Sets up the project root on sys.path so all tests can import project modules.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
