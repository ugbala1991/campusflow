import os
import json
import unittest

# Import the core classes and functions from campus_flow.py
from campus_flow import CampusFlowManager, calculate_priority, CATEGORIES, URGENCIES, STATUSES


class TestCampusFlowEdgeCases(unittest.TestCase):
    def setUp(self):
        """Set up a temporary isolation storage file before each test."""
        self.test_file = "test_edge_cases_temp.json"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        self.manager = CampusFlowManager(storage_file=self.test_file)

    def tearDown(self):
        """Clean up temporary test storage files after each test."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    # ==========================================
    # 1. PRIORITY CALCULATION ENGINE EDGE CASES
    # ==========================================
    def test_priority_rules_exact_boundaries(self):
        """Verify priority rules match specifications precisely at boundary conditions."""
        # Rule 1: high urgency AND >= 10 affected users -> critical
        self.assertEqual(calculate_priority("high", 10), "critical")
        self.assertEqual(calculate_priority("HIGH", 100), "critical")
        
        # Rule 2: high urgency OR >= 10 affected users -> high
        self.assertEqual(calculate_priority("high", 9), "high")    # High urgency, < 10 users
        self.assertEqual(calculate_priority("low", 10), "high")    # Low urgency, >= 10 users
        self.assertEqual(calculate_priority("medium", 15), "high") # Medium urgency, >= 10 users

        # Rule 3: medium urgency OR >= 3 affected users -> medium
        self.assertEqual(calculate_priority("medium", 2), "medium") # Medium urgency, < 3 users
        self.assertEqual(calculate_priority("low", 3), "medium")    # Low urgency, exactly 3 users
        self.assertEqual(calculate_priority("low", 9), "medium")    # Low urgency, 9 users

        # Rule 4: all remaining valid tickets -> low
        self.assertEqual(calculate_priority("low", 1), "low")
        self.assertEqual(calculate_priority("low", 2), "low")
        self.assertEqual(calculate_priority("medium", 1), "medium") # wait, medium urgency triggers Rule 3 even with 1 user

    # ==========================================
    # 2. INPUT VALIDATION & EDGE CASES (F1)
    # ==========================================
    def test_create_ticket_invalid_titles(self):
        """Ensure blank, whitespace-only, or non-string titles are safely rejected."""
        with self.assertRaises(ValueError):
            self.manager.create_ticket("", "Network", "high", 5)
        with self.assertRaises(ValueError):
            self.manager.create_ticket("   ", "Network", "high", 5)

    def test_create_ticket_case_insensitivity_and_normalization(self):
        """Ensure categories and urgencies handle mixed-case variations correctly."""
        ticket = self.manager.create_ticket("  Wi-Fi down in library  ", "netWork", "HIGH", 12)
        self.assertEqual(ticket["title"], "Wi-Fi down in library")
        self.assertEqual(ticket["category"], "Network")
        self.assertEqual(ticket["urgency"], "high")

    def test_create_ticket_invalid_categories(self):
        """Ensure unsupported categories are rejected."""
        with self.assertRaises(ValueError):
            self.manager.create_ticket("Broken Projector", "CloudComputing", "high", 4)

    def test_create_ticket_invalid_urgencies(self):
        """Ensure unsupported urgency strings are rejected."""
        with self.assertRaises(ValueError):
            self.manager.create_ticket("Broken Projector", "Hardware", "super-urgent", 4)

    def test_create_ticket_affected_users_edge_cases(self):
        """Test strict validation of affected users (rejects zero, negatives, decimals, and text strings)."""
        invalid_inputs = [0, -1, -15, 2.5, 0.1, "abc", "12a", "", None]
        for bad_val in invalid_inputs:
            with self.assertRaises(ValueError, msg=f"Failed to reject invalid affected_users: {bad_val}"):
                self.manager.create_ticket("Edge test", "Software", "low", bad_val)

    # ==========================================
    # 3. ASSIGNMENT EDGE CASES (F3)
    # ==========================================
    def test_assignment_edge_cases(self):
        """Test staff assignment validations and non-existent ID handling."""
        t = self.manager.create_ticket("Laptop Screen Broken", "Hardware", "medium", 1)
        
        # Blank staff name rejection
        with self.assertRaises(ValueError):
            self.manager.assign_ticket(t["id"], "")
        with self.assertRaises(ValueError):
            self.manager.assign_ticket(t["id"], "   ")

        # Unknown ticket ID rejection
        with self.assertRaises(ValueError):
            self.manager.assign_ticket("T9999", "Sarah Connor")

        # Valid assignment
        updated = self.manager.assign_ticket(t["id"], "  Dr. Jane Doe  ")
        self.assertEqual(updated["assigned_to"], "Dr. Jane Doe") # should be stripped

    # ==========================================
    # 4. WORKFLOW STATE MACHINE EDGE CASES (F4)
    # ==========================================
    def test_workflow_state_transitions(self):
        """Verify strict lifecycle constraints: open -> in_progress -> resolved -> reopen."""
        t = self.manager.create_ticket("Canvas LMS Unavailable", "Software", "high", 20)
        
        # Constraint 1: Unassigned ticket cannot move to 'in_progress'
        with self.assertRaises(ValueError):
            self.manager.update_status(t["id"], "in_progress")

        # Assign ticket, now move to 'in_progress' should succeed
        self.manager.assign_ticket(t["id"], "IT Staff John")
        self.manager.update_status(t["id"], "in_progress")
        self.assertEqual(self.manager.get_ticket_by_id(t["id"])["status"], "in_progress")

        # Move to 'resolved'
        self.manager.update_status(t["id"], "resolved")
        self.assertEqual(self.manager.get_ticket_by_id(t["id"])["status"], "resolved")

        # Constraint 2: Resolved ticket cannot be moved directly to 'in_progress' or 'open' without explicit check
        # (Note: resolved to open is allowed via reopen, but direct to in_progress from resolved is blocked)
        with self.assertRaises(ValueError):
            self.manager.update_status(t["id"], "in_progress")

        # Explicit reopen to 'open'
        self.manager.update_status(t["id"], "open")
        self.assertEqual(self.manager.get_ticket_by_id(t["id"])["status"], "open")

    # ==========================================
    # 5. WORK QUEUE SORTING EDGE CASES (F5)
    # ==========================================
    def test_work_queue_sorting_and_filtering(self):
        """Ensure work queue excludes resolved tickets and sorts correctly by priority then ID."""
        t1 = self.manager.create_ticket("Low prio", "Other", "low", 1)         # T001 (low)
        t2 = self.manager.create_ticket("Critical prio", "Network", "high", 15) # T002 (critical)
        t3 = self.manager.create_ticket("Medium prio", "Hardware", "medium", 2)  # T003 (medium)
        
        # Resolve T002 (critical) to verify it disappears from active work queue
        self.manager.assign_ticket(t2["id"], "Admin")
        self.manager.update_status(t2["id"], "in_progress")
        self.manager.update_status(t2["id"], "resolved")

        queue = self.manager.get_work_queue()
        # T002 is resolved, so queue should only contain T003 (medium) and T001 (low)
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue[0]["id"], "T003") # medium ranks higher than low
        self.assertEqual(queue[1]["id"], "T001") # low

    # ==========================================
    # 6. PERSISTENCE & MALFORMED DATA EDGE CASES (F7)
    # ==========================================
    def test_persistence_malformed_json_protection(self):
        """Ensure malformed JSON files produce a clean RuntimeError instead of crashing or wiping data."""
        self.manager.create_ticket("Valid initial ticket", "Network", "high", 5)

        # Corrupt the storage file with invalid syntax
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("{broken json syntax... [missing closing brackets")

        # Initializing manager with corrupted file must raise RuntimeError safely
        with self.assertRaises(RuntimeError):
            CampusFlowManager(storage_file=self.test_file)


if __name__ == "__main__":
    unittest.main()