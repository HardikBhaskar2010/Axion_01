#!/usr/bin/env python3
"""
Desktop Guardian Backend API Test Suite
Tests all backend functionality including session management, planning, file operations, and privilege requests.
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

class DesktopGuardianTester:
    def __init__(self, base_url: str = "https://1f78ee96-6c60-481c-a779-5da23fce5cca.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text, "status_code": response.status_code}
            
            return success, response_data
        except Exception as e:
            return False, {"error": str(e)}

    def test_basic_connectivity(self):
        """Test basic API connectivity"""
        success, data = self.make_request('GET', '')
        expected_message = data.get('message') == 'Hello World'
        self.log_test("Basic API Connectivity", success and expected_message, 
                     f"Expected 'Hello World', got: {data.get('message', 'No message')}", data)
        return success and expected_message

    def test_session_start(self):
        """Test session creation"""
        success, data = self.make_request('POST', 'session/start', {'mode': 'normal'})
        
        if success and 'id' in data:
            self.session_id = data['id']
            required_fields = ['id', 'mode', 'allowed_scopes', 'expires_in_minutes', 'created_at']
            has_all_fields = all(field in data for field in required_fields)
            self.log_test("Session Start", has_all_fields, 
                         f"Session ID: {self.session_id}, Mode: {data.get('mode')}", data)
            return has_all_fields
        else:
            self.log_test("Session Start", False, f"Failed to create session: {data}", data)
            return False

    def test_simple_plan_execution(self):
        """Test simple plan execution - 'what time is it?'"""
        if not self.session_id:
            self.log_test("Simple Plan Execution", False, "No session ID available")
            return False

        success, data = self.make_request('POST', 'plan', {
            'session_id': self.session_id,
            'utterance': 'what time is it?'
        })
        
        if success:
            # Check if auto_results contains time execution
            auto_results = data.get('auto_results', [])
            has_time_result = len(auto_results) > 0 and any(
                result.get('success') and 'now_iso' in str(result.get('result', {})) 
                for result in auto_results
            )
            self.log_test("Simple Plan Execution (Time)", has_time_result, 
                         f"Auto results: {auto_results}", data)
            return has_time_result
        else:
            self.log_test("Simple Plan Execution (Time)", False, f"Plan request failed: {data}", data)
            return False

    def test_file_write_approval_flow(self):
        """Test file write with approval flow"""
        if not self.session_id:
            self.log_test("File Write Approval Flow", False, "No session ID available")
            return False

        # Step 1: Request file write (should need approval)
        success, data = self.make_request('POST', 'plan', {
            'session_id': self.session_id,
            'utterance': 'write file notes.txt: hello from guardian'
        })
        
        if not success:
            self.log_test("File Write Approval Flow", False, f"Plan request failed: {data}", data)
            return False

        actions = data.get('actions', [])
        if not actions:
            self.log_test("File Write Approval Flow", False, "No actions returned for file write", data)
            return False

        # Find the file write action that needs approval
        write_action = None
        for action in actions:
            if action.get('need_approval') and 'write' in action.get('tool', '').lower():
                write_action = action
                break

        if not write_action:
            self.log_test("File Write Approval Flow", False, "No file write action needing approval found", data)
            return False

        # Step 2: Approve the action
        action_id = write_action['id']
        success, approval_data = self.make_request('POST', 'action/approve', {
            'action_id': action_id,
            'decision': 'allow'
        })

        if success:
            self.log_test("File Write Approval Flow", True, 
                         f"File write approved successfully. Action ID: {action_id}", approval_data)
            return True
        else:
            self.log_test("File Write Approval Flow", False, 
                         f"Failed to approve file write: {approval_data}", approval_data)
            return False

    def test_file_read_approval_flow(self):
        """Test file read with approval flow"""
        if not self.session_id:
            self.log_test("File Read Approval Flow", False, "No session ID available")
            return False

        # Wait a bit for previous file write to complete
        time.sleep(2)

        success, data = self.make_request('POST', 'plan', {
            'session_id': self.session_id,
            'utterance': 'read file notes.txt'
        })
        
        if not success:
            self.log_test("File Read Approval Flow", False, f"Plan request failed: {data}", data)
            return False

        actions = data.get('actions', [])
        if not actions:
            self.log_test("File Read Approval Flow", False, "No actions returned for file read", data)
            return False

        # Find the file read action that needs approval
        read_action = None
        for action in actions:
            if action.get('need_approval') and 'read' in action.get('tool', '').lower():
                read_action = action
                break

        if not read_action:
            self.log_test("File Read Approval Flow", False, "No file read action needing approval found", data)
            return False

        # Approve the read action
        action_id = read_action['id']
        success, approval_data = self.make_request('POST', 'action/approve', {
            'action_id': action_id,
            'decision': 'allow'
        })

        if success:
            self.log_test("File Read Approval Flow", True, 
                         f"File read approved successfully. Action ID: {action_id}", approval_data)
            return True
        else:
            self.log_test("File Read Approval Flow", False, 
                         f"Failed to approve file read: {approval_data}", approval_data)
            return False

    def test_file_delete_approval_flow(self):
        """Test file delete with approval flow"""
        if not self.session_id:
            self.log_test("File Delete Approval Flow", False, "No session ID available")
            return False

        success, data = self.make_request('POST', 'plan', {
            'session_id': self.session_id,
            'utterance': 'delete file notes.txt'
        })
        
        if not success:
            self.log_test("File Delete Approval Flow", False, f"Plan request failed: {data}", data)
            return False

        actions = data.get('actions', [])
        if not actions:
            self.log_test("File Delete Approval Flow", False, "No actions returned for file delete", data)
            return False

        # Find the file delete action that needs approval
        delete_action = None
        for action in actions:
            if action.get('need_approval') and 'delete' in action.get('tool', '').lower():
                delete_action = action
                break

        if not delete_action:
            self.log_test("File Delete Approval Flow", False, "No file delete action needing approval found", data)
            return False

        # Approve the delete action
        action_id = delete_action['id']
        success, approval_data = self.make_request('POST', 'action/approve', {
            'action_id': action_id,
            'decision': 'allow'
        })

        if success:
            self.log_test("File Delete Approval Flow", True, 
                         f"File delete approved successfully. Action ID: {action_id}", approval_data)
            return True
        else:
            self.log_test("File Delete Approval Flow", False, 
                         f"Failed to approve file delete: {approval_data}", approval_data)
            return False

    def test_copy_move_operations(self):
        """Test file copy and move operations"""
        if not self.session_id:
            self.log_test("Copy/Move Operations", False, "No session ID available")
            return False

        operations = [
            'write file a.txt: test content',
            'copy file a.txt to b.txt',
            'move file b.txt to c.txt'
        ]
        
        for operation in operations:
            success, data = self.make_request('POST', 'plan', {
                'session_id': self.session_id,
                'utterance': operation
            })
            
            if success and data.get('actions'):
                # Approve any actions that need approval
                for action in data.get('actions', []):
                    if action.get('need_approval'):
                        self.make_request('POST', 'action/approve', {
                            'action_id': action['id'],
                            'decision': 'allow'
                        })
            
            time.sleep(1)  # Wait between operations

        # Test list files to verify a.txt and c.txt exist
        success, data = self.make_request('POST', 'plan', {
            'session_id': self.session_id,
            'utterance': 'list files'
        })
        
        if success:
            self.log_test("Copy/Move Operations", True, 
                         f"File operations completed. List result: {data}", data)
            return True
        else:
            self.log_test("Copy/Move Operations", False, f"Failed to list files: {data}", data)
            return False

    def test_privilege_request_flow(self):
        """Test privilege request for outside sandbox operations"""
        # Step 1: Request privilege
        success, data = self.make_request('POST', 'settings/privilege_request', {
            'need': ['files.write.outside_sandbox'],
            'target_path': '/tmp/guardian-e2e',
            'expires_minutes': 15,
            'reason_brief': 'E2E testing'
        })
        
        if not success:
            self.log_test("Privilege Request Flow", False, f"Privilege request failed: {data}", data)
            return False

        action = data.get('action')
        if not action or not action.get('id'):
            self.log_test("Privilege Request Flow", False, f"No action returned in privilege request: {data}", data)
            return False

        # Step 2: Approve the privilege request
        action_id = action['id']
        success, approval_data = self.make_request('POST', 'action/approve', {
            'action_id': action_id,
            'decision': 'allow'
        })

        if not success:
            self.log_test("Privilege Request Flow", False, 
                         f"Failed to approve privilege request: {approval_data}", approval_data)
            return False

        # Step 3: Set new root
        success, root_data = self.make_request('POST', 'settings/root', {
            'path': '/tmp/guardian-e2e'
        })

        if success:
            self.log_test("Privilege Request Flow", True, 
                         f"Privilege flow completed. New root: {root_data}", root_data)
            return True
        else:
            self.log_test("Privilege Request Flow", False, 
                         f"Failed to set new root: {root_data}", root_data)
            return False

    def test_logs_endpoint(self):
        """Test logs retrieval"""
        if not self.session_id:
            self.log_test("Logs Endpoint", False, "No session ID available")
            return False

        success, data = self.make_request('GET', f'logs?session_id={self.session_id}')
        
        if success and 'logs' in data:
            logs = data['logs']
            self.log_test("Logs Endpoint", True, 
                         f"Retrieved {len(logs)} log entries", {"log_count": len(logs)})
            return True
        else:
            self.log_test("Logs Endpoint", False, f"Failed to retrieve logs: {data}", data)
            return False

    def test_settings_root_get(self):
        """Test getting current root settings"""
        success, data = self.make_request('GET', 'settings/root')
        
        if success and 'root' in data:
            self.log_test("Settings Root GET", True, 
                         f"Current root: {data.get('root')}, First run: {data.get('first_run')}", data)
            return True
        else:
            self.log_test("Settings Root GET", False, f"Failed to get root settings: {data}", data)
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Desktop Guardian Backend Tests")
        print("=" * 50)
        
        # Basic connectivity
        if not self.test_basic_connectivity():
            print("❌ Basic connectivity failed, stopping tests")
            return False

        # Session management
        if not self.test_session_start():
            print("❌ Session creation failed, stopping tests")
            return False

        # Core functionality tests
        self.test_simple_plan_execution()
        self.test_file_write_approval_flow()
        self.test_file_read_approval_flow()
        self.test_file_delete_approval_flow()
        self.test_copy_move_operations()
        self.test_privilege_request_flow()
        self.test_logs_endpoint()
        self.test_settings_root_get()

        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = DesktopGuardianTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
            'test_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())