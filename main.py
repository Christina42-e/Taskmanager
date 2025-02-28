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

# Import models after initializing db


class TodoModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    todo = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_working_hours(self):
        """Calculate duration in hours if start_time and end_time exist."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 3600
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
        duration = (end_dt - start_dt).total_seconds() / 3600 if start_dt and end_dt else None

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
        tasks = TodoModel.query.all()
        return render_template("index.html", tasks=tasks)
    
    # update the todo task

@app.route('/update/<int:id>', methods = ['GET', 'POST'])
def update(id):
    task = TodoModel.query.get_or_404(id)
    
    if request.method == 'POST':
        task.todo = request.form['todo_item']
        
        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an issue while updating that task.'
    else:
        return render_template('update.html', task = task)

# delete
@app.route('/delete/<int:id>')
def delete(id):
    todo_to_delete = TodoModel.query.get_or_404(id)
    try:
        db.session.delete(todo_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was an error while deleting that todo.'


if __name__ == "__main__":
    app.run(debug=True)
