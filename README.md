# Employee Scheduler

A Python desktop app for managing weekly employee schedules using a GUI built with PyQt5 and backed by SQLite.

## 📋 Features

- GUI to manage employee records
- Add/remove/edit employees
- Assign weekly shifts and prevent conflicts
- Automatically generate and display a schedule
- Data saved in a local SQLite database

## 🛠 Tech Stack

- Python 3.x
- PyQt5
- SQLite
- OR-Tools for schedule optimization)

## 🖼️ Screenshots

![Main Window](screenshots/main_ui.png)  
![Schedule View](screenshots/schedule.png)

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- `pip install pyqt5`

### Run the App

```bash
git clone https://github.com/vaz17/scheduler
cd scheduler
python main.py
```

Make sure you allow GUI windows if running on Linux.

## 💡 Design Highlights

- Built with PyQt5 using custom QWidgets
- Modular structure: UI logic, database handling, and schedule generator
- GUI runs as a standalone executable on Windows or Mac (optional pyinstaller build)

## 📚 Learning Goals

- Deepen GUI app development with PyQt5
- Integrate GUI with SQLite backend
- Build CRUD workflows in a visual desktop app

## 📄 License

MIT — free to use and extend.
