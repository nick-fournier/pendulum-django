web: gunicorn config.wsgi --log-file -
release: python manage.py makemigrations && python manage.py migrate && python manage.py loaddata users.json && python manage.py loaddata dummy.json