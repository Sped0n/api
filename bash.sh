python3 manage.py makemigrations
python3 manage.py migrate
echo "migration complete, starting service."
python3 manage.py runserver 0.0.0.0:8080