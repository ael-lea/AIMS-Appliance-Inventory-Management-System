import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from Admin.core.session import SessionManager
from Admin.views.dashboard_view import DashboardWindow


def main():
    if not SessionManager.is_admin():
        raise SystemExit("Please log in first.")
    DashboardWindow()


if __name__ == "__main__":
    main()