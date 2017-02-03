from __future__ import absolute_import

import os
from enum import Enum
from celery import Celery
from celery.utils.log import get_logger


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventkit_cloud.settings.prod')

from django.conf import settings  # noqa

# Get an instance of a logger
logger = get_logger(__name__)

class TaskPriority(Enum):
    CANCEL = 80                 # If cancel isn't higher than new tasks, long running processes will needlessly
                                # take resources while the cancel message is blocked.
    FINALIZE_PROVIDER = 60      # It is better to finalize a previous task before starting a new one so that the
                                # processed file is made available to the user.
    TASK_RUNNER = 50            # Running tasks should be higher than picking up tasks
    DEFAULT = 0                 # The default task priority in RabbitMQ is zero, so not having a priority is the same as
                                # the the default, it is here to be explicit. https://www.rabbitmq.com/priority.html


app = Celery('eventkit_cloud', strict_typing=False)

app.config_from_object('django.conf:settings')
app.autodiscover_tasks()

app.conf.task_protocol = 1


