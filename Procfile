release: python manage.py makemigrations
release: python manage.py migrate
release: python manage.py loaddata users.json
release: python manage.py loaddata dummy.json

web: gunicorn config.wsgi --log-file -
