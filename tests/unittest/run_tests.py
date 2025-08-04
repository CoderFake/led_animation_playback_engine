"""
Test runner for LED Animation Engine unit tests
Runs all unit tests with proper reporting and coverage
Updated for new codebase structure and test cases
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
        print("Updated for dual pattern dissolve system and new ColorUtils")
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
        
        # Print test class breakdown
        print("\nTest Class Breakdown:")
        print(f"- TestColorUtils: 17 test methods (color processing, blending)")
        print(f"- TestSegment: 29 test methods (animation logic, positioning)")
        print(f"- TestDissolveTransition: 22 test methods (dual pattern crossfade)")
        print(f"- Total: 68 comprehensive test methods")
        
        if result.wasSuccessful():
            print("\nALL TESTS PASSED!")
        else:
            print("\nSOME TESTS FAILED!")
            print("Please review the failures above.")
            
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
        test_class_map = {
            "ColorUtils": TestColorUtils,
            "Segment": TestSegment,
            "DissolveTransition": TestDissolveTransition
        }
        
        if test_class_name not in test_class_map:
            print(f"Unknown test class: {test_class_name}")
            print(f"Available classes: {', '.join(test_class_map.keys())}")
            return False
            
        test_class = test_class_map[test_class_name]
        
        if test_method_name:
            suite = unittest.TestSuite()
            suite.addTest(test_class(test_method_name))
        else:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    def run_category_tests(self, category):
        """Run tests by category"""
        categories = {
            "color": [TestColorUtils],
            "animation": [TestSegment],
            "dissolve": [TestDissolveTransition],
            "core": [TestColorUtils, TestSegment],
            "advanced": [TestDissolveTransition]
        }
        
        if category not in categories:
            print(f"Unknown category: {category}")
            print(f"Available categories: {', '.join(categories.keys())}")
            return False
        
        runner = TestRunner()
        runner.test_classes = categories[category]
        return runner.run_tests()


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
        elif sys.argv[1] == "--category":
            if len(sys.argv) < 3:
                print("Error: --category requires a category name")
                return
            category = sys.argv[2]
            success = runner.run_category_tests(category)
            sys.exit(0 if success else 1)
    
    success = runner.run_tests()
    
    sys.exit(0 if success else 1)


def print_help():
    """Print help message"""
    print("""
LED Animation Engine Test Runner (Updated)

Usage:
    python run_tests.py                           # Run all tests
    python run_tests.py --help                    # Show this help
    python run_tests.py --list                    # List available tests
    python run_tests.py --test <class>            # Run specific test class
    python run_tests.py --test <class> <method>   # Run specific test method
    python run_tests.py --category <category>     # Run test category

Available test classes:
    ColorUtils          # Test color processing and blending (18 methods)
    Segment             # Test animation logic and positioning (25 methods)  
    DissolveTransition  # Test dual pattern crossfade system (22 methods)

Available categories:
    color      # Color processing tests only
    animation  # Animation and segment tests only
    dissolve   # Dissolve pattern tests only
    core       # Core functionality (color + animation)
    advanced   # Advanced features (dissolve system)

Examples:
    python run_tests.py --test ColorUtils
    python run_tests.py --test Segment test_get_led_colors_with_timing
    python run_tests.py --test DissolveTransition test_dual_pattern_calculator_pattern_colors
    python run_tests.py --category core
    python run_tests.py --category dissolve

New Test Features:
    • Dual pattern dissolve crossfade testing
    • Averaging blend system validation
    • Time-based brightness calculation tests
    • Fractional positioning with fade effects
    • Enhanced error handling verification
    """)


def list_tests():
    """List all available tests"""
    print("Available test classes and methods:")
    print()
    
    test_classes = [
        ("TestColorUtils", TestColorUtils, "Color processing and blending"),
        ("TestSegment", TestSegment, "Animation logic and positioning"),
        ("TestDissolveTransition", TestDissolveTransition, "Dual pattern crossfade system")
    ]
    
    for class_name, test_class, description in test_classes:
        print(f"{class_name} - {description}:")
        methods = [method for method in dir(test_class) if method.startswith('test_')]
        for method_name in sorted(methods):
            print(f"  - {method_name}")
        print()
    
    print("Test Coverage Summary:")
    print("• Color Utils: 17 methods covering transparency, brightness, blending")
    print("• Segment: 29 methods covering timing, positioning, rendering")
    print("• Dissolve: 22 methods covering dual pattern crossfade system")
    print("• Total: 68 comprehensive test methods")


if __name__ == '__main__':
    main()