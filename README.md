# campusflow
Campus_Flow — Campus Technical Support Ticket Manager
1. How to Run the Program
Prerequisites

    Python 3.x installed on your system. No external third-party libraries are required (the application uses Python's built-in standard library).

Instructions

    Save the main script as campus_flow.py and ensure it is in your working directory.

    Open your terminal or command prompt.

    To launch the interactive CLI application:
    Bash

    python / python3 campus_flow.py

    To run the automated test suite:
    Bash

    python / python3 campus_flow.py test

2. General Description of the Program

CampusFlow is a robust, command-line ticket management system engineered specifically for campus technical support staff (handling Wi-Fi outages, faulty laptops, broken development environments, and inaccessible platforms).

Unlike informal reports that get easily lost in chats or emails, CampusFlow provides a centralized, persistent text-based interface to record problems, calculate precise priorities, assign responsibility, enforce strict workflow transitions, inspect active work queues, and generate summary statistics.
3. The Problem the Program is Intended to Solve

Campus IT and technical support teams frequently struggle with:

    Unstructured Reporting: Issues communicated via verbal chats or informal emails lack tracking, categorization, and ownership.

    Subjective Prioritization: Staff often waste time guessing which issue is most critical. CampusFlow solves this by applying an automated, deterministic priority engine based on urgency levels and affected user thresholds.

    Workflow Bottlenecks: Preventing tickets from moving into active progress before staff are assigned, and ensuring resolved tickets cannot be altered without an explicit reopening step.

    Data Loss: Informal tracking tools lose history upon closure or crashes. CampusFlow provides automated JSON file persistence with ID continuity and corruption safeguards.

4. Miscellaneous

    File Persistence: CampusFlow automatically creates and reads from a local JSON file (campus_flow_tickets.json) in the execution directory. If the file is missing, it initializes cleanly; if corrupted or malformed, it raises a safe diagnostic error rather than silently wiping data.

    Unique ID Generation: Tickets are assigned auto-incrementing sequential IDs (e.g., T001, T002, T003), which are preserved even across application restarts.

    Automated Testing: Includes a built-in unit test suite verifying priority calculation logic, input validations, workflow guardrails, work queue sorting, report generation, and persistence survival.