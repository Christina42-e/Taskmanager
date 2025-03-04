from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func

# Create Flask app
app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todolist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy (without binding to app yet)
db = SQLAlchemy()

# Custom Jinja filter to format datetime
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%dT%H:%M'):
    if value is None:
        return ""
    return value.strftime(format)

class TodoModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    todo = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.String, nullable=True)  # Change duration to String type
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_working_minutes(self):
        """Calculate duration in hours if start_time and end_time exist."""
        if self.start_time and self.end_time:
            total_seconds = (self.end_time - self.start_time).total_seconds()
            if total_seconds >= 3600:
                return f"{total_seconds / 3600:.2f} hours"
            else:
                return f"{total_seconds / 60:.2f} minutes"
        return None  # Return None if no valid time range exists

    def __repr__(self):
        return f"<Task {self.todo}, Category: {self.category}, Status: {self.status}>"

# Now bind SQLAlchemy to the Flask app
db.init_app(app)

# Ensure database and tables are created
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        todo_item = request.form['todo_item']
        category = request.form.get('category', 'General')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        # Convert time fields if provided
        start_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M') if start_time else None
        end_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M') if end_time else None

        # Calculate duration
        duration = TodoModel().calculate_working_minutes() if start_dt and end_dt else None

        # Task status
        status = 'Completed' if end_dt and datetime.now() > end_dt else 'Pending'

        new_todo = TodoModel(
            todo=todo_item,
            category=category,
            start_time=start_dt,
            end_time=end_dt,
            duration=duration,
            status=status
        )

        try:
            db.session.add(new_todo)
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an error while adding the task'
    else:
        category_filter = request.args.get('category')
        if category_filter:
            tasks = TodoModel.query.filter_by(category=category_filter).all()
        else:
            tasks = TodoModel.query.all()
        return render_template("index.html", tasks=tasks)

# Update task
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    task = TodoModel.query.get_or_404(id)
    
    if request.method == 'POST':
        task.todo = request.form['todo_item']
        task.category = request.form['category']
        task.start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M') if request.form['start_time'] else None
        task.end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M') if request.form['end_time'] else None
        task.duration = task.calculate_working_minutes()
        task.status = 'Completed' if task.end_time and datetime.now() > task.end_time else 'Pending'

        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an issue while updating that task.'
    else:
        return render_template('update.html', task=task)

# Delete task
@app.route('/delete/<int:id>')
def delete(id):
    todo_to_delete = TodoModel.query.get_or_404(id)
    try:
        db.session.delete(todo_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was an error while deleting that todo.'

# Start Task Route
@app.route('/start_task/<int:id>', methods=['POST'])
def start_task(id):
    task = TodoModel.query.get_or_404(id)
    task.start_time = datetime.now()
    task.status = 'In Progress'
    try:
        db.session.commit()
        return redirect('/')
    except:
        return 'There was an error starting the task.'

# End Task Route
@app.route('/end_task/<int:id>', methods=['POST'])
def end_task(id):
    task = TodoModel.query.get_or_404(id)
    task.end_time = datetime.now()
    task.duration = task.calculate_working_minutes()
    task.status = 'Completed'
    try:
        db.session.commit()
        return redirect('/')
    except:
        return 'There was an error ending the task.'

# Daily Work Summary Route
@app.route('/summary/daily', methods=['GET'])
def daily_summary():
    today = datetime.now().date()
    tasks = TodoModel.query.filter(func.date(TodoModel.start_time) == today).all()

    total_minutes = sum(
        (float(task.duration.split()[0]) * 60 if "hours" in task.duration else float(task.duration.split()[0])) 
        for task in tasks if task.duration
    )

    # Ensure that even very small durations (less than 1 min) are counted as 1 min
    if 0 < total_minutes < 1:
        total_minutes = 1

    hours, minutes = divmod(int(total_minutes), 60)
    return jsonify(message=f"Total work today: {hours} hours {minutes} minutes"), 200


# Weekly Work Summary Route
@app.route('/summary/weekly', methods=['GET'])
def weekly_summary():
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday() + 1)  # Move back to Sunday
    week_end = today  # Set the end to today (dynamic)

    tasks = TodoModel.query.filter(
        func.date(TodoModel.start_time) >= week_start,
        func.date(TodoModel.start_time) <= week_end
    ).all()

    total_minutes = sum(
        float(task.duration.split()[0]) * 60 if "hours" in task.duration else float(task.duration.split()[0])
        for task in tasks if task.duration
    )

    # Ensure that even very small durations (less than 1 min) are counted
    if 0 < total_minutes < 1:
        total_minutes = 1

    hours, minutes = divmod(int(total_minutes), 60)
    return jsonify(message=f"Total work this week (from {week_start} to {week_end}): {hours} hours {minutes} minutes"), 200



# API for fetching all tasks
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = TodoModel.query.all()
    return jsonify([{
        'id': task.id,
        'todo': task.todo,
        'category': task.category,
        'start_time': task.start_time,
        'end_time': task.end_time,
        'duration': task.duration,
        'status': task.status
    } for task in tasks]), 200

# API for fetching a single task by id
@app.route('/api/tasks/<int:id>', methods=['GET'])
def get_task(id):
    task = TodoModel.query.get_or_404(id)
    return jsonify({
        'id': task.id,
        'todo': task.todo,
        'category': task.category,
        'start_time': task.start_time,
        'end_time': task.end_time,
        'duration': task.duration,
        'status': task.status
    }), 200

# API for updating a task by id
@app.route('/api/tasks/<int:id>', methods=['PUT'])
def update_task_api(id):
    task = TodoModel.query.get_or_404(id)
    data = request.json

    task.todo = data.get('todo', task.todo)
    task.category = data.get('category', task.category)
    task.start_time = datetime.strptime(data['start_time'], '%Y-%m-%dT%H:%M') if 'start_time' in data else task.start_time
    task.end_time = datetime.strptime(data['end_time'], '%Y-%m-%dT%H:%M') if 'end_time' in data else task.end_time
    task.duration = task.calculate_working_minutes()
    task.status = data.get('status', task.status)

    try:
        db.session.commit()
        return jsonify({
            'id': task.id,
            'todo': task.todo,
            'category': task.category,
            'start_time': task.start_time,
            'end_time': task.end_time,
            'duration': task.duration,
            'status': task.status
        }), 200
    except:
        return jsonify({'error': 'There was an error while updating the task'}), 500

if __name__ == "__main__":
    app.run(debug=True)
