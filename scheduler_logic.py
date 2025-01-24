import random
from datetime import datetime

def generate_schedule(start_date, database, num_schedules=100):
    """
    Generate multiple random schedules and rank them based on fairness criteria.
    :param start_date: A string in the format "yyyy-MM-dd" representing the start date of the schedule.
    :param database: A Database object to retrieve employee data.
    :param num_schedules: Number of random schedules to generate.
    :return: The best schedule based on points-based ranking.
    """
    # Parse the start date
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    time_slots = ["12am-6am", "6am-12pm", "9am-3pm", "12pm-6pm", "3pm-9pm", "6pm-12pm", "9pm-3am"]

    # Fetch all employees from the database
    employees = database.get_all_employees()

    # Build a shift availability pool
    availability_pool = {
        (day, slot): [
            employee["name"]
            for employee in employees
            if slot in employee["availability"].get(day, [])
        ]
        for day in days_of_week
        for slot in time_slots
    }

    # Helper function to evaluate a schedule's points
    def evaluate_schedule(schedule):
        points = 0

        # Count shifts assigned to each employee
        shift_counts = {employee["name"]: 0 for employee in employees}
        daily_shifts = {employee["name"]: {day: 0 for day in days_of_week} for employee in employees}

        # Iterate through the schedule
        for day, slots in schedule.items():
            for slot, assigned in slots.items():
                if not assigned:  # Deduct points for empty time slots
                    points -= 1
                for employee in assigned:
                    shift_counts[employee] += 1
                    daily_shifts[employee][day] += 1

                    # Add extra points for preferred shifts
                    if f"{slot} *" in employee_preference[employee][day]:
                        points += 5  # Award 5 points for a preferred shift

                    # Deduct points if an employee works more than once per day
                    if daily_shifts[employee][day] > 1:
                        points -= 5

        # Evaluate shifts per employee
        for employee in employees:
            name = employee["name"]
            min_shifts = employee["min_shifts"]
            max_shifts = employee["max_shifts"]
            assigned_shifts = shift_counts[name]

            # Add points if within min/max shifts
            if min_shifts <= assigned_shifts <= max_shifts:
                points += 10
            # Deduct points if below min or above max shifts
            if assigned_shifts < min_shifts:
                points -= (min_shifts - assigned_shifts) * 2
            if assigned_shifts > max_shifts:
                points -= (assigned_shifts - max_shifts) * 2

        return points

    # Build a dictionary of employee preferences based on shifts with "*"
    employee_preference = {
        employee["name"]: {
            day: [
                slot
                for slot in employee["availability"].get(day, [])
                if f"{slot} *" in employee["availability"].get(day, [])
            ]
            for day in days_of_week
        }
        for employee in employees
    }

    # Generate multiple random schedules
    schedules = []
    for _ in range(num_schedules):
        # Initialize a new schedule
        schedule = {day: {slot: [] for slot in time_slots} for day in days_of_week}

        # Assign shifts randomly
        shift_counts = {employee["name"]: 0 for employee in employees}  # Track assigned shifts
        for (day, slot), available_employees in availability_pool.items():
            # Add a "No Employee" option if no one is available or employees exceed max shifts
            valid_employees = [
                emp
                for emp in available_employees
                if shift_counts[emp] < next(
                    e["max_shifts"] for e in employees if e["name"] == emp
                )
            ]
            options = valid_employees + ["No Employee"]  # Allow leaving the shift unfilled
            selected_employee = random.choice(options)

            if selected_employee != "No Employee":
                schedule[day][slot].append(selected_employee)
                shift_counts[selected_employee] += 1

        schedules.append(schedule)

    # Rank schedules by points
    best_schedule = max(schedules, key=evaluate_schedule)
    return best_schedule
