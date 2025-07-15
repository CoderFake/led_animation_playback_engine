"""
Test Result Data Models
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timedelta

class TestStatus(Enum):
    """Test status types"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class TestSeverity(Enum):
    """Test severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[timedelta] = None
    message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    severity: TestSeverity = TestSeverity.MEDIUM
    
    def __post_init__(self):
        if self.end_time and self.duration is None:
            self.duration = self.end_time - self.start_time
    
    def set_end_time(self, end_time: datetime = None):
        """Set end time and calculate duration"""
        self.end_time = end_time or datetime.now()
        self.duration = self.end_time - self.start_time
    
    def is_passed(self) -> bool:
        """Check if test passed"""
        return self.status == TestStatus.PASSED

@dataclass
class TestSuiteResult:
    """Test suite result collection"""
    suite_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: Optional[timedelta] = None
    test_results: List[TestResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: TestResult):
        """Add test result to suite"""
        self.test_results.append(result)
    
    def finalize(self):
        """Finalize suite results"""
        self.end_time = datetime.now()
        self.total_duration = self.end_time - self.start_time
    
    @property
    def total_tests(self) -> int:
        """Get total number of tests"""
        return len(self.test_results)
    
    @property
    def passed_tests(self) -> int:
        """Get number of passed tests"""
        return sum(1 for result in self.test_results if result.status == TestStatus.PASSED)
    
    @property
    def failed_tests(self) -> int:
        """Get number of failed tests"""
        return sum(1 for result in self.test_results if result.status == TestStatus.FAILED)
    
    @property
    def skipped_tests(self) -> int:
        """Get number of skipped tests"""
        return sum(1 for result in self.test_results if result.status == TestStatus.SKIPPED)
    
    @property
    def error_tests(self) -> int:
        """Get number of error tests"""
        return sum(1 for result in self.test_results if result.status == TestStatus.ERROR)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test suite summary"""
        return {
            "suite_name": self.suite_name,
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "skipped": self.skipped_tests,
            "errors": self.error_tests,
            "success_rate": round(self.success_rate, 2),
            "duration": str(self.total_duration) if self.total_duration else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None
        }

@dataclass
class PerformanceMetrics:
    """Performance test metrics"""
    response_time: float
    throughput: float
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    concurrent_users: int = 1
    error_rate: float = 0.0
    
    def is_acceptable(self, max_response_time: float = 1.0, min_throughput: float = 100.0) -> bool:
        """Check if performance meets criteria"""
        return (self.response_time <= max_response_time and 
                self.throughput >= min_throughput and 
                self.error_rate < 0.05)

@dataclass
class TestReport:
    """Complete test report"""
    report_id: str
    generated_at: datetime
    test_suites: List[TestSuiteResult] = field(default_factory=list)
    performance_metrics: Optional[PerformanceMetrics] = None
    environment_info: Dict[str, Any] = field(default_factory=dict)
    
    def add_suite(self, suite: TestSuiteResult):
        """Add test suite to report"""
        self.test_suites.append(suite)
    
    def get_overall_summary(self) -> Dict[str, Any]:
        """Get overall test report summary"""
        total_tests = sum(suite.total_tests for suite in self.test_suites)
        total_passed = sum(suite.passed_tests for suite in self.test_suites)
        total_failed = sum(suite.failed_tests for suite in self.test_suites)
        total_skipped = sum(suite.skipped_tests for suite in self.test_suites)
        total_errors = sum(suite.error_tests for suite in self.test_suites)
        
        overall_success_rate = (total_passed / total_tests * 100.0) if total_tests > 0 else 0.0
        
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "total_suites": len(self.test_suites),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_errors": total_errors,
            "overall_success_rate": round(overall_success_rate, 2),
            "suites": [suite.get_summary() for suite in self.test_suites],
            "performance": self.performance_metrics.__dict__ if self.performance_metrics else None
        } 