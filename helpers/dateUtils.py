# dateUtils.py
# This module provides utility functions for date manipulation, specifically for converting between different date formats used in the application.

#───imports───#
from datetime import datetime

#───function <check_date>───#
def check_date(date_str, format="%d%m%Y"):
    """Check if the provided date string matches the expected format."""
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False

#───function <convert_date_format>───#
def convert_date_format(date_str, from_format="%d%m%Y", to_format="%Y%m%d"):
    """Convert a date string from one format to another."""
    try:
        date_obj = datetime.strptime(date_str, from_format)
        return date_obj.strftime(to_format)
    except ValueError:
        return None