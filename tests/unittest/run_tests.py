"""
Test runner for LED Animation Engine unit tests
Runs all unit tests with proper reporting and coverage
"""

import unittest
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.unittest.test_color_utils import TestColorUtils
from tests.unittest.test_segment import TestSegment
from tests.unittest.test_dissolve_pattern import TestDissolveTransition


class TestRunner:
    """Test runner with enhanced reporting"""
    
    def __init__(self):
        """Initialize test runner with all test classes"""
        self.test_classes = [
            TestColorUtils,
            TestSegment,
            TestDissolveTransition
        ]
        self.test_suite = unittest.TestSuite()
        self.test_results = []
        
    def add_test_class(self, test_class):
        """Add a test class to the suite"""
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        self.test_suite.addTests(tests)
        
    def run_tests(self, verbosity=2):
        """Run all tests with specified verbosity"""
        for test_class in self.test_classes:
            self.add_test_class(test_class)
            
        print("=" * 70)
        print("LED Animation Engine - Unit Test Suite")
        print("=" * 70)
        
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(self.test_suite)
       
        self._print_summary(result)
        
        return result.wasSuccessful()
    
    def _print_summary(self, result):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
        
        print(f"Total tests run: {total_tests}")
        print(f"Successes: {total_tests - failures - errors - skipped}")
        print(f"Failures: {failures}")
        print(f"Errors: {errors}")
        print(f"Skipped: {skipped}")
        
        if result.wasSuccessful():
            print("\n ALL TESTS PASSED!")
        else:
            print("\n SOME TESTS FAILED!")
            
        if result.failures:
            print("\nFAILURES:")
            print("-" * 40)
            for test, traceback in result.failures:
                print(f"FAIL: {test}")
                print(traceback)
                
        if result.errors:
            print("\nERRORS:")
            print("-" * 40)
            for test, traceback in result.errors:
                print(f"ERROR: {test}")
                print(traceback)
    
    def run_specific_test(self, test_class_name, test_method_name=None):
        """Run a specific test class or method"""
        if test_class_name == "ColorUtils":
            test_class = TestColorUtils
        elif test_class_name == "Segment":
            test_class = TestSegment
        else:
            print(f"Unknown test class: {test_class_name}")
            return False
            
        if test_method_name:
            suite = unittest.TestSuite()
            suite.addTest(test_class(test_method_name))
        else:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()


def main():
    """Main entry point"""
    runner = TestRunner()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print_help()
            return
        elif sys.argv[1] == "--list":
            list_tests()
            return
        elif sys.argv[1] == "--test":
            if len(sys.argv) < 3:
                print("Error: --test requires a test class name")
                return
            test_class = sys.argv[2]
            test_method = sys.argv[3] if len(sys.argv) > 3 else None
            success = runner.run_specific_test(test_class, test_method)
            sys.exit(0 if success else 1)
    
    runner.add_test_class(TestColorUtils)
    runner.add_test_class(TestSegment)
    
    success = runner.run_tests()
    
    sys.exit(0 if success else 1)


def print_help():
    """Print help message"""
    print("""
LED Animation Engine Test Runner

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --help             # Show this help
    python run_tests.py --list             # List available tests
    python run_tests.py --test <class>     # Run specific test class
    python run_tests.py --test <class> <method>  # Run specific test method

Available test classes:
    ColorUtils      # Test ColorUtils class
    Segment         # Test Segment class

Examples:
    python run_tests.py --test ColorUtils
    python run_tests.py --test Segment test_transparency_bug_fix
    """)


def list_tests():
    """List all available tests"""
    print("Available test classes and methods:")
    print()
    
    print("TestColorUtils:")
    for method_name in dir(TestColorUtils):
        if method_name.startswith('test_'):
            print(f"  - {method_name}")
    
    print()
    
    print("TestSegment:")
    for method_name in dir(TestSegment):
        if method_name.startswith('test_'):
            print(f"  - {method_name}")


if __name__ == '__main__':
    main() 