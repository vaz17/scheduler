from datetime import datetime, timedelta

def generate_schedule(start_date, database):
    """
    Generate a weekly schedule based on employees' availability and constraints.

    :param start_date: A string in the format "yyyy-MM-dd" representing the start date of the schedule.
    :param database: A Database object to retrieve employee data.
    :return: A dictionary with days as keys and lists of scheduled employees for each time slot as values.
    """
    # Parse the start date
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12pm", "9pm-3am"]

    # Fetch all employees from the database
    employees = database.get_all_employees()

    # Initialize the schedule
    schedule = {day: {slot: [] for slot in time_slots} for day in days_of_week}

    # Create dictionaries to track shifts assigned to employees
    shift_counts = {employee["name"]: 0 for employee in employees}  # Weekly shift count
    daily_shifts = {employee["name"]: {day: False for day in days_of_week} for employee in employees}  # Per-day tracking

    # Iterate through each day and time slot
    for day in days_of_week:
        for slot in time_slots:
            for employee in employees:
                # Check if the employee is available for the current day and time slot
                if slot in employee["availability"].get(day, []):
                    # Ensure the employee hasn't already worked today
                    if not daily_shifts[employee["name"]][day]:
                        # Ensure the employee's maximum weekly shift limit is not exceeded
                        if shift_counts[employee["name"]] < employee["max_shifts"]:
                            # Assign the employee to the schedule
                            schedule[day][slot].append(employee["name"])
                            # Increment their weekly shift count
                            shift_counts[employee["name"]] += 1
                            # Mark the employee as having worked today
                            daily_shifts[employee["name"]][day] = True
                            # Stop adding employees to this slot if it is full
                            break

    return schedule