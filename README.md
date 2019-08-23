# ACPool API server

```bash
# Create Virtualenv
python3 -m venv venv

# Activate Virtualenv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# DB Migrate
python manage.py db init
python manage.py db migrate
python manage.py db upgrade

# run server
python app.py

```
