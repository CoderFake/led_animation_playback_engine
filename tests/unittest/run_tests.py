"""
Test runner for LED Engine Unit Tests
"""
import subprocess
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


def run_all_tests():
    """Run all unit tests"""
    print("=== Run all Unit Tests ===")
    
    test_dir = Path(__file__).parent
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(test_dir),
        "-v",
        "--tb=short",
        "--color=yes"
    ], capture_output=False)
    
    return result.returncode == 0


def run_specific_test(test_file):
    """Run specific test"""
    print(f"=== Run test: {test_file} ===")
    
    test_dir = Path(__file__).parent
    test_path = test_dir / test_file
    
    if not test_path.exists():
        print(f"ERROR: Test file does not exist: {test_path}")
        return False
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(test_path),
        "-v",
        "--tb=short",
        "--color=yes"
    ], capture_output=False)
    
    return result.returncode == 0


def run_coverage():
    """Run tests with coverage report"""
    print("=== Run tests with Coverage ===")
    
    test_dir = Path(__file__).parent
    
    try:
        import coverage
    except ImportError:
        print("Installing coverage...")
        subprocess.run([sys.executable, "-m", "pip", "install", "coverage"])
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(test_dir),
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ], capture_output=False)
    
    if result.returncode == 0:
        print("\n=== Coverage Report ===")
        print(f"HTML Coverage Report: {project_root}/htmlcov/index.html")
    
    return result.returncode == 0


def list_available_tests():
    """List all test files"""
    print("=== List of Unit Tests ===")
    
    test_dir = Path(__file__).parent
    test_files = sorted(test_dir.glob("test_*.py"))
    
    for i, test_file in enumerate(test_files, 1):
        print(f"{i}. {test_file.name}")
    
    return test_files


def main():
    """Main function"""
    print("LED Engine Unit Test Runner")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "all":
            success = run_all_tests()
        elif command == "coverage":
            success = run_coverage()
        elif command == "list":
            list_available_tests()
            return
        elif command.startswith("test_"):
            success = run_specific_test(command)
        else:
            print(f"Unknown command: {command}")
            print_usage()
            return
    else:
        print_usage()
        return
    
    if 'success' in locals():
        sys.exit(0 if success else 1)


def print_usage():
    """Print usage instructions"""
    print("\nUsage:")
    print("  python run_tests.py all              - Run all tests")
    print("  python run_tests.py coverage         - Run tests with coverage")
    print("  python run_tests.py list             - List all test files")
    print("  python run_tests.py test_*.py        - Run specific test")
    print("\nExamples:")
    print("  python run_tests.py test_animation_engine.py")
    print("  python run_tests.py test_osc_handler.py")
    print("  python run_tests.py test_scene_manager.py")
    print("  python run_tests.py test_monitor_components.py")


if __name__ == "__main__":
    main() 