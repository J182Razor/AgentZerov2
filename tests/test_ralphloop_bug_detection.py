"""
Ralphloop-Style Iterative Bug Testing Framework

This module provides automated, continuous, coverage-guided bug detection
using systematic exploration, failure injection, property-based testing,
and adaptive test generation.
"""

import asyncio
import random
import string
import json
import os
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import inspect
import ast


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_id: str
    passed: bool
    execution_time: float
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    coverage: Set[str] = field(default_factory=set)
    properties_violated: List[str] = field(default_factory=list)
    is_crash: bool = False


@dataclass 
class CoverageTracker:
    """Track code coverage during test execution"""
    lines_covered: Set[int] = field(default_factory=set)
    branches_covered: Set[Tuple[int, int]] = field(default_factory=set)
    functions_called: Set[str] = field(default_factory=set)
    files_covered: Set[str] = field(default_factory=set)
    
    def update(self, coverage: Set[str]):
        """Update coverage with new items"""
        self.lines_covered.update(coverage)
    
    def get_coverage_percentage(self, total_lines: int) -> float:
        """Calculate coverage percentage"""
        if total_lines == 0:
            return 0.0
        return (len(self.lines_covered) / total_lines) * 100


class Fuzzer:
    """Fuzzer for generating test inputs"""
    
    def __init__(self, seed_corpus: Optional[List[Any]] = None):
        self.seed_corpus = seed_corpus or []
        self.generated_inputs: List[Any] = []
    
    def generate(self) -> Any:
        """Generate a random test input"""
        choice = random.randint(0, 5)
        
        if choice == 0:
            return self._generate_string()
        elif choice == 1:
            return self._generate_dict()
        elif choice == 2:
            return self._generate_list()
        elif choice == 3:
            return self._generate_number()
        elif choice == 4:
            return self._generate_malformed_json()
        else:
            return self._generate_edge_case()
    
    def _generate_string(self) -> str:
        """Generate random string with various patterns"""
        patterns = [
            lambda: ''.join(random.choices(string.ascii_letters, k=random.randint(0, 100))),
            lambda: ' ' * random.randint(1, 10),
            lambda: '\x00' * random.randint(1, 5),
            lambda: 'a' * 10000,  # Long string
            lambda: random.choice(['', '\n', '\r', '\t']),
        ]
        return random.choice(patterns)()
    
    def _generate_dict(self) -> Dict:
        """Generate random dictionary"""
        return {
            f"key_{i}": self.generate()
            for i in range(random.randint(0, 10))
        }
    
    def _generate_list(self) -> List:
        """Generate random list"""
        return [self.generate() for _ in range(random.randint(0, 10))]
    
    def _generate_number(self) -> Any:
        """Generate various number types"""
        choice = random.randint(0, 3)
        if choice == 0:
            return random.randint(-1000000, 1000000)
        elif choice == 1:
            return random.uniform(-1e10, 1e10)
        elif choice == 2:
            return 0
        else:
            return float('inf')
    
    def _generate_malformed_json(self) -> str:
        """Generate malformed JSON strings"""
        patterns = [
            '{"incomplete":',
            '{"trailing": "comma",}',
            '["unclosed]',
            '{"duplicated": 1, "duplicated": 2}',
            'not json at all',
            '{"nested": {"deep": {"value":}}}',
        ]
        return random.choice(patterns)
    
    def _generate_edge_case(self) -> Any:
        """Generate edge cases"""
        return random.choice([None, True, False, {}, [], "", 0, -1])


class PropertyChecker:
    """Check properties/invariants during test execution"""
    
    def __init__(self):
        self.properties: Dict[str, Callable[[Any], bool]] = {}
        self.register_default_properties()
    
    def register_default_properties(self):
        """Register default properties to check"""
        
        def not_none(value):
            return value is not None
        
        def is_valid_json(value):
            if isinstance(value, str):
                try:
                    json.loads(value)
                    return True
                except:
                    return False
            return True
        
        def no_crash(value):
            return not isinstance(value, Exception)
        
        self.properties["not_none"] = not_none
        self.properties["valid_json"] = is_valid_json
        self.properties["no_crash"] = no_crash
    
    def register_property(self, name: str, checker: Callable[[Any], bool]):
        """Register a custom property"""
        self.properties[name] = checker
    
    def check(self, value: Any) -> List[str]:
        """Check all properties and return violations"""
        violations = []
        for name, checker in self.properties.items():
            try:
                if not checker(value):
                    violations.append(name)
            except Exception:
                violations.append(f"{name}_error")
        return violations


class CrashAnalyzer:
    """Analyze crashes and generate reports"""
    
    def __init__(self):
        self.crashes: List[Dict] = []
    
    def analyze(self, result: TestResult) -> Dict:
        """Analyze a crash and extract useful information"""
        crash_info = {
            "test_id": result.test_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(result.error).__name__ if result.error else "Unknown",
            "error_message": str(result.error) if result.error else "No message",
            "stack_trace": result.stack_trace,
            "likely_cause": self._determine_likely_cause(result),
            "suggested_fix": self._generate_fix_suggestion(result)
        }
        
        self.crashes.append(crash_info)
        return crash_info
    
    def _determine_likely_cause(self, result: TestResult) -> str:
        """Determine likely cause of crash"""
        if not result.stack_trace:
            return "Unknown"
        
        stack = result.stack_trace.lower()
        
        if "indexerror" in stack or "list index" in stack:
            return "Index out of bounds"
        elif "keyerror" in stack:
            return "Missing dictionary key"
        elif "attributeerror" in stack:
            return "NoneType access or missing attribute"
        elif "type:
            return "error" in stackType mismatch"
        elif "valueerror" in stack:
            return "Invalid value"
        elif "timeout" in stack:
            return "Timeout or infinite loop"
        elif "memory" in stack:
            return "Memory issue"
        else:
            return "Undetermined"
    
    def _generate_fix_suggestion(self, result: TestResult) -> str:
        """Generate suggested fix based on crash analysis"""
        cause = self._determine_likely_cause(result)
        
        suggestions = {
            "Index out of bounds": "Add bounds checking before accessing list indices",
            "Missing dictionary key": "Use .get() method or check key existence first",
            "Type mismatch": "Add type validation or use isinstance() checks",
            "Invalid value": "Add input validation with clear error messages",
            "Timeout or infinite loop": "Add iteration limits or timeout handling",
            "Memory issue": "Consider streaming or chunking large data"
        }
        
        return suggestions.get(cause, "Review stack trace for details")


class RalphloopBugTester:
    """
    Ralphloop-style iterative bug detection system.
    
    Combines:
    - Systematic Exploration: Every code path exercised
    - Failure Injection: Intentional chaos testing
    - Property-Based: Invariant verification
    - Coverage-Guided: Optimize test selection
    """
    
    def __init__(
        self,
        target_modules: Optional[List[str]] = None,
        max_iterations: int = 1000,
        timeout_per_test: float = 30.0
    ):
        self.target_modules = target_modules or []
        self.max_iterations = max_iterations
        self.timeout_per_test = timeout_per_test
        
        self.coverage_tracker = CoverageTracker()
        self.fuzzer = Fuzzer()
        self.property_checker = PropertyChecker()
        self.crash_analyzer = CrashAnalyzer()
        
        self.test_results: List[TestResult] = []
        self.generated_tests: List[Callable] = []
        self.regression_tests: List[Dict] = []
        
        self.stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "crashes": 0,
            "property_violations": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def iterative_test(
        self,
        test_function: Callable[[Any], Any],
        property_checker: Optional[PropertyChecker] = None
    ) -> Dict[str, Any]:
        """
        Main testing loop - run iterative tests with fuzzing and coverage tracking.
        
        Args:
            test_function: Function to test (should accept one argument)
            property_checker: Optional custom property checker
        
        Returns:
            Test results summary
        """
        self.stats["start_time"] = datetime.now()
        if property_checker:
            self.property_checker = property_checker
        
        for i in range(self.max_iterations):
            # 1. Generate test input
            test_input = self.fuzzer.generate()
            
            # 2. Execute with tracking
            result = await self._execute_with_tracking(test_function, test_input, f"test_{i}")
            
            # 3. Update stats
            self._update_stats(result)
            
            # 4. Verify properties
            if result.passed:
                violations = self.property_checker.check(result)
                if violations:
                    result.properties_violated = violations
                    self.stats["property_violations"] += 1
            
            # 5. Analyze crashes
            if result.is_crash():
                self.crash_analyzer.analyze(result)
                self._generate_regression_test(result)
            
            # 6. Update coverage
            self.coverage_tracker.update(result.coverage)
            
            # 7. Adaptive iteration - more tests for complex areas
            if self._is_complex_area():
                # Run additional tests for complex code
                await self._increase_testing_intensity(test_function)
        
        self.stats["end_time"] = datetime.now()
        
        return self._generate_summary()
    
    async def _execute_with_tracking(
        self,
        test_function: Callable[[Any], Any],
        test_input: Any,
        test_id: str
    ) -> TestResult:
        """Execute a test with full tracking"""
        start_time = time.time()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(test_function, test_input),
                timeout=self.timeout_per_test
            )
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_id=test_id,
                passed=True,
                execution_time=execution_time,
                coverage=self._extract_coverage(test_function)
            )
            
        except asyncio.TimeoutError:
            return TestResult(
                test_id=test_id,
                passed=False,
                execution_time=self.timeout_per_test,
                error="Test timed out",
                is_crash=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return TestResult(
                test_id=test_id,
                passed=False,
                execution_time=execution_time,
                error=str(e),
                stack_trace=traceback.format_exc(),
                is_crash=True
            )
    
    def _extract_coverage(self, func: Callable) -> Set[str]:
        """Extract coverage information from function"""
        coverage = set()
        
        try:
            source = inspect.getsource(func)
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    coverage.add(f"func:{node.name}")
                elif isinstance(node, ast.If):
                    coverage.add(f"branch:{node.lineno}")
                elif isinstance(node, ast.For):
                    coverage.add(f"loop:{node.lineno}")
        except:
            pass
        
        return coverage
    
    def _update_stats(self, result: TestResult):
        """Update test statistics"""
        self.stats["total_tests"] += 1
        
        if result.passed:
            self.stats["passed"] += 1
        else:
            self.stats["failed"] += 1
        
        if result.is_crash():
            self.stats["crashes"] += 1
    
    def _is_complex_area(self) -> bool:
        """Detect if current code area is complex"""
        return len(self.coverage_tracker.branches_covered) > 10
    
    async def _increase_testing_intensity(self, test_function: Callable):
        """Run additional tests for complex areas"""
        # Generate more inputs for complex areas
        for _ in range(5):
            test_input = self.fuzzer.generate()
            result = await self._execute_with_tracking(test_function, test_input, f"intensive_test")
            self._update_stats(result)
    
    def _generate_regression_test(self, crash_result: TestResult):
        """Generate regression test from crash"""
        self.regression_tests.append({
            "test_id": crash_result.test_id,
            "error": crash_result.error,
            "stack_trace": crash_result.stack_trace,
            "suggested_fix": self.crash_analyzer._generate_fix_suggestion(crash_result),
            "timestamp": datetime.now().isoformat()
        })
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        return {
            "statistics": {
                **self.stats,
                "duration_seconds": duration,
                "tests_per_second": self.stats["total_tests"] / duration if duration > 0 else 0,
                "pass_rate": self.stats["passed"] / self.stats["total_tests"] if self.stats["total_tests"] > 0 else 0
            },
            "coverage": {
                "lines_covered": len(self.coverage_tracker.lines_covered),
                "functions_called": len(self.coverage_tracker.functions_called),
                "files_covered": len(self.coverage_tracker.files_covered)
            },
            "crashes": self.crash_analyzer.crashes,
            "regression_tests": self.regression_tests,
            "property_violations": self.property_checker.properties
        }


async def run_ralphloop_test(
    target_function: Callable,
    max_iterations: int = 100,
    custom_properties: Optional[Dict[str, Callable]] = None
) -> Dict[str, Any]:
    """
    Convenience function to run Ralphloop-style testing.
    
    Args:
        target_function: Function to test
        max_iterations: Number of test iterations
        custom_properties: Optional custom properties to check
    
    Returns:
        Test results summary
    """
    tester = RalphloopBugTester(max_iterations=max_iterations)
    
    if custom_properties:
        for name, checker in custom_properties.items():
            tester.property_checker.register_property(name, checker)
    
    return await tester.iterative_test(target_function)


# Example usage
if __name__ == "__main__":
    async def example_test_function(input_data):
        """Example function to test"""
        # Example: Try to parse JSON and access nested data
        if isinstance(input_data, str):
            data = json.loads(input_data)
            return data.get("key", {}).get("nested")
        return input_data
    
    # Run tests
    results = asyncio.run(run_ralphloop_test(example_test_function, max_iterations=100))
    
    print(json.dumps(results, indent=2))
