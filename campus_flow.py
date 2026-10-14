import os
import json
import unittest

# ==========================================
# DOMAIN CONSTANTS & VALIDATION RULES
# ==========================================
CATEGORIES = {"Network", "Hardware", "Software", "Other"}
URGENCIES = {"low", "medium", "high"}
STATUSES = {"open", "in_progress", "resolved"}

PRIORITY_RANKS = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3
}

def calculate_priority(urgency: str, affected_users: int) -> str:
    """
    Calculates priority exactly as specified by the rules in order:
    RULE 1: high urgency AND 10 or more affected users -> critical
    RULE 2: high urgency OR 10 or more affected users  -> high
    RULE 3: medium urgency OR 3 or more affected users -> medium
    RULE 4: all remaining valid tickets                -> low
    """
    u = urgency.lower().strip()
    if u == "high" and affected_users >= 10:
        return "critical"
    if u == "high" or affected_users >= 10:
        return "high"
    if u == "medium" or affected_users >= 3:
        return "medium"
    return "low"


class CampusFlowManager:
    def __init__(self, storage_file="campus_flow_tickets.json"):
        self.storage_file = storage_file
        self.tickets = []
        self._next_id_num = 1
        self.load_data()

    # ==========================================
    # F7 — PERSISTENCE
    # ==========================================
    def load_data(self):
        if not os.path.exists(self.storage_file):
            self.tickets = []
            self._next_id_num = 1
            return

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self.tickets = []
                    self._next_id_num = 1
                    return
                data = json.loads(content)
                if not isinstance(data, list):
                    raise ValueError("Stored data must be a JSON list.")
                self.tickets = data
                self._update_next_id()
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"ERROR: Malformed JSON detected in '{self.storage_file}'. "
                f"Data file is corrupted. Fix or remove the file before restarting. Details: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"ERROR loading data from persistence: {e}")

    def save_data(self):
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.tickets, f, indent=4)
        except Exception as e:
            print(f"[Error] Failed to save data to disk: {e}")

    def _update_next_id(self):
        max_id = 0
        for t in self.tickets:
            tid = t.get("id", "")
            if tid.startswith("T") and tid[1:].isdigit():
                num = int(tid[1:])
                if num > max_id:
                    max_id = num
        self._next_id_num = max_id + 1

    def _generate_id(self) -> str:
        new_id = f"T{self._next_id_num:03d}"
        self._next_id_num += 1
        return new_id

    # ==========================================
    # F1 — CREATE
    # ==========================================
    def create_ticket(self, title: str, category: str, urgency: str, affected_users_input) -> dict:
        if not title or not title.strip():
            raise ValueError("Title must not be blank.")
        clean_title = title.strip()

        cat_normalized = None
        for cat in CATEGORIES:
            if cat.lower() == category.lower().strip():
                cat_normalized = cat
                break
        if not cat_normalized:
            raise ValueError(f"Invalid category. Choose from: {', '.join(CATEGORIES)}")

        urg_normalized = urgency.lower().strip()
        if urg_normalized not in URGENCIES:
            raise ValueError(f"Invalid urgency. Choose from: {', '.join(URGENCIES)}")

        if isinstance(affected_users_input, float):
            raise ValueError("Affected users must be an integer, not a decimal.")
        
        try:
            raw_str = str(affected_users_input).strip()
            if "." in raw_str or "-" in raw_str:
                raise ValueError("Affected users must be a positive integer.")
            affected_users = int(raw_str)
        except (ValueError, TypeError):
            raise ValueError("Affected users must be a valid positive integer greater than zero.")

        if affected_users <= 0:
            raise ValueError("Affected users must be a positive integer greater than zero.")

        priority = calculate_priority(urg_normalized, affected_users)

        new_ticket = {
            "id": self._generate_id(),
            "title": clean_title,
            "category": cat_normalized,
            "urgency": urg_normalized,
            "affected_users": affected_users,
            "priority": priority,
            "status": "open",
            "assigned_to": None
        }

        self.tickets.append(new_ticket)
        self.save_data()
        return new_ticket

    # ==========================================
    # F2 — LIST / VIEW
    # ==========================================
    def get_all_tickets(self):
        return self.tickets

    def get_ticket_by_id(self, ticket_id: str):
        for t in self.tickets:
            if t["id"].lower() == ticket_id.strip().lower():
                return t
        return None

    # ==========================================
    # F3 — ASSIGN
    # ==========================================
    def assign_ticket(self, ticket_id: str, staff_name: str):
        if not staff_name or not staff_name.strip():
            raise ValueError("Staff member name must not be empty.")
        
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket ID '{ticket_id}' not found.")

        ticket["assigned_to"] = staff_name.strip()
        self.save_data()
        return ticket

    # ==========================================
    # F4 — WORKFLOW
    # ==========================================
    def update_status(self, ticket_id: str, new_status: str):
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket ID '{ticket_id}' not found.")

        ns = new_status.lower().strip()
        if ns not in STATUSES:
            raise ValueError(f"Invalid status. Choose from: {', '.join(STATUSES)}")

        current_status = ticket["status"]

        if current_status == "resolved" and ns != "open":
            raise ValueError("A resolved ticket can only be modified by reopening it to 'open' first.")

        if current_status == "open" and ns == "in_progress":
            if not ticket["assigned_to"]:
                raise ValueError("Cannot move an unassigned ticket into 'in_progress'. Assign staff first.")

        ticket["status"] = ns
        self.save_data()
        return ticket

    # ==========================================
    # F5 — WORK QUEUE
    # ==========================================
    def get_work_queue(self):
        unresolved = [t for t in self.tickets if t["status"] in ("open", "in_progress")]

        def sort_key(t):
            p_rank = PRIORITY_RANKS.get(t["priority"], 4)
            try:
                num_id = int(t["id"][1:])
            except ValueError:
                num_id = 0
            return (p_rank, num_id)

        return sorted(unresolved, key=sort_key)

    # ==========================================
    # F6 — REPORTS
    # ==========================================
    def get_reports(self):
        total = len(self.tickets)
        status_breakdown = {s: 0 for s in STATUSES}
        priority_breakdown = {p: 0 for p in PRIORITY_RANKS.keys()}

        for t in self.tickets:
            st = t.get("status")
            pr = t.get("priority")
            if st in status_breakdown:
                status_breakdown[st] += 1
            if pr in priority_breakdown:
                priority_breakdown[pr] += 1

        return {
            "total_tickets": total,
            "status_breakdown": status_breakdown,
            "priority_breakdown": priority_breakdown
        }


# ==========================================
# COMMAND LINE INTERFACE (CLI)
# ==========================================
def print_ticket_table(tickets):
    if not tickets:
        print("\n  [Info] No tickets match this view.")
        return
    print("\n" + "-" * 105)
    print(f"{'ID':<6} | {'Title':<28} | {'Category':<10} | {'Urgency':<8} | {'Users':<6} | {'Priority':<9} | {'Status':<11} | {'Assigned To'}")
    print("-" * 105)
    for t in tickets:
        assigned = t["assigned_to"] if t["assigned_to"] else "Unassigned"
        print(f"{t['id']:<6} | {t['title'][:27]:<28} | {t['category']:<10} | {t['urgency']:<8} | {str(t['affected_users']):<6} | {t['priority']:<9} | {t['status']:<11} | {assigned}")
    print("-" * 105)


def cli_main():
    manager = CampusFlowManager()
    
    while True:
        print("\n========================================")
        print("         CAMPUSFLOW TICKET MANAGER       ")
        print("========================================")
        print("1. F1 - Create Ticket")
        print("2. F2 - List All Tickets / View Ticket Details")
        print("3. F3 - Assign Ticket to Staff")
        print("4. F4 - Update Ticket Status (Workflow)")
        print("5. F5 - View Active Work Queue")
        print("6. F6 - Reports & Statistics")
        print("7. Exit")
        
        choice = input("\nSelect an option (1-7): ").strip()
        
        if choice == "1":
            print("\n--- Create New Ticket ---")
            title = input("Enter ticket title: ")
            print(f"Available Categories: {', '.join(CATEGORIES)}")
            category = input("Enter category: ")
            print(f"Available Urgencies: {', '.join(URGENCIES)}")
            urgency = input("Enter urgency: ")
            affected_users_input = input("Enter affected users (positive integer): ")
            
            try:
                ticket = manager.create_ticket(title, category, urgency, affected_users_input)
                print(f"\n[Success] Ticket created successfully with ID: {ticket['id']} (Priority: {ticket['priority'].upper()})")
            except Exception as e:
                print(f"\n[Validation Error] {e}")

        elif choice == "2":
            print("\n--- List / View Tickets ---")
            sub_choice = input("View (1) All Tickets or (2) Specific Ticket Details? Enter 1 or 2: ").strip()
            if sub_choice == "1":
                print_ticket_table(manager.get_all_tickets())
            elif sub_choice == "2":
                tid = input("Enter Ticket ID (e.g., T001): ").strip()
                t = manager.get_ticket_by_id(tid)
                if t:
                    print(json.dumps(t, indent=4))
                else:
                    print(f"\n[Error] Ticket ID '{tid}' not found.")
            else:
                print("\n[Error] Invalid selection.")

        elif choice == "3":
            print("\n--- Assign Ticket ---")
            tid = input("Enter Ticket ID to assign: ").strip()
            staff = input("Enter staff member name: ").strip()
            try:
                t = manager.assign_ticket(tid, staff)
                print(f"\n[Success] Ticket {t['id']} successfully assigned to {t['assigned_to']}.")
            except Exception as e:
                print(f"\n[Error] {e}")

        elif choice == "4":
            print("\n--- Update Ticket Status (Workflow) ---")
            tid = input("Enter Ticket ID: ").strip()
            t = manager.get_ticket_by_id(tid)
            if not t:
                print(f"\n[Error] Ticket ID '{tid}' not found.")
                continue
            print(f"Current Status: {t['status']} | Assigned To: {t['assigned_to'] or 'Unassigned'}")
            print(f"Allowed Statuses: {', '.join(STATUSES)}")
            new_status = input("Enter new status: ").strip()
            try:
                updated = manager.update_status(tid, new_status)
                print(f"\n[Success] Ticket {updated['id']} status updated to '{updated['status']}'.")
            except Exception as e:
                print(f"\n[Error] {e}")

        elif choice == "5":
            print("\n--- Active Work Queue (Open & In Progress) ---")
            queue = manager.get_work_queue()
            if not queue:
                print("\n  [Status Report]: Work queue is currently empty (no open or in-progress tickets found).")
            else:
                print_ticket_table(queue)
            input("\nPress Enter to return to main menu...")

        elif choice == "6":
            print("\n--- Reports & Statistics ---")
            rep = manager.get_reports()
            print(f"\nTotal Tickets in System: {rep['total_tickets']}")
            if rep['total_tickets'] == 0:
                print("  [Status Report]: No tickets recorded yet. Create some tickets via Option 1 to see stats.")
            else:
                print("\nStatus Breakdown:")
                for st, count in rep['status_breakdown'].items():
                    print(f"  - {st.capitalize()}: {count}")
                print("\nPriority Breakdown:")
                for pr, count in rep['priority_breakdown'].items():
                    print(f"  - {pr.capitalize()}: {count}")
            input("\nPress Enter to return to main menu...")

        elif choice == "7":
            print("\nThank You for Using CampusFlow. Goodbye For Now!")
            break
        else:
            print("\n[Error] Invalid option. Please choose between 1 and 7.")


# ==========================================
# AUTOMATED TEST SUITE
# ==========================================
class TestCampusFlow(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_campus_flow_temp.json"
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        self.manager = CampusFlowManager(storage_file=self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_1_priority_calculation_rules(self):
        self.assertEqual(calculate_priority("high", 15), "critical")
        self.assertEqual(calculate_priority("high", 4), "high")
        self.assertEqual(calculate_priority("low", 12), "high")
        self.assertEqual(calculate_priority("medium", 4), "medium")
        self.assertEqual(calculate_priority("low", 5), "medium")
        self.assertEqual(calculate_priority("low", 1), "low")

    def test_2_create_ticket_validations(self):
        with self.assertRaises(ValueError):
            self.manager.create_ticket("", "Network", "high", 5)
        with self.assertRaises(ValueError):
            self.manager.create_ticket("Wi-Fi down", "InvalidCat", "high", 5)
        with self.assertRaises(ValueError):
            self.manager.create_ticket("Wi-Fi down", "Network", "high", 0)

    def test_3_successful_ticket_creation_and_id(self):
        t1 = self.manager.create_ticket("Wi-Fi Down", "Network", "high", 12)
        self.assertEqual(t1["id"], "T001")
        self.assertEqual(t1["priority"], "critical")

    def test_4_ticket_assignment(self):
        t = self.manager.create_ticket("VPN Issue", "Network", "medium", 2)
        assigned = self.manager.assign_ticket(t["id"], "Alice Smith")
        self.assertEqual(assigned["assigned_to"], "Alice Smith")

    def test_5_workflow_transitions_and_constraints(self):
        t = self.manager.create_ticket("Canvas down", "Software", "high", 5)
        with self.assertRaises(ValueError):
            self.manager.update_status(t["id"], "in_progress")
        self.manager.assign_ticket(t["id"], "Charlie")
        self.manager.update_status(t["id"], "in_progress")
        self.assertEqual(self.manager.get_ticket_by_id(t["id"])["status"], "in_progress")

    def test_6_work_queue_ordering(self):
        self.manager.create_ticket("Low prio old", "Other", "low", 1)
        self.manager.create_ticket("Critical issue", "Network", "high", 20)
        queue = self.manager.get_work_queue()
        self.assertEqual(queue[0]["id"], "T002")

    def test_7_reports_generation(self):
        rep_empty = self.manager.get_reports()
        self.assertEqual(rep_empty["total_tickets"], 0)

    def test_8_persistence_survival(self):
        self.manager.create_ticket("Persistent Ticket", "Software", "medium", 5)
        manager2 = CampusFlowManager(storage_file=self.test_file)
        self.assertEqual(len(manager2.get_all_tickets()), 1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.argv.pop()
        unittest.main()
    else:
        cli_main()