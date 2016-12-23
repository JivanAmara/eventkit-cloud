#!/bin/bash
/var/lib/eventkit/.virtualenvs/eventkit/bin/python /var/lib/eventkit/manage.py collectstatic --noinput
chown -R eventkit:eventkit /var/log/eventkit /var/lib/eventkit
/var/lib/eventkit/.virtualenvs/eventkit/bin/python /var/lib/eventkit/manage.py celery beat --loglevel=$LOGLEVEL
