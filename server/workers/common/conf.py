import os
from celery import Celery
from server.environ import ENV_NAME_REDIS, REDIS_URL
celery = Celery(__name__)
celery.conf.broker_url = os.environ.get(ENV_NAME_REDIS, REDIS_URL)
celery.conf.result_backend = os.environ.get(ENV_NAME_REDIS, REDIS_URL)
celery.conf.beat_schedule = {
    'tick-every-5s': {
        'task': 'common.allow_list_reconciliation',
        'schedule': 5.0,
        'args': ()
    },
    'tick-every-10s': {
        'task': 'common.queue_reconciliation',
        'schedule': 10.0,
        'args': ()
    },
    'desired-state-docker-32s':{
        'task': 'common.containers.desired_state',
        'schedule': 32.0,
        'args': ()
    }
}
celery.conf.task_routes = {
    'common.*':{'queue':'common'},
    'gpu.*': {'queue':'gpu'}
}
celery.conf.timezone = 'UTC'
celery.conf.result_expires = 1800 #Results are kept for 30m


