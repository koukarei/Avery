#
# Gunicorn config file
#
wsgi_app = '/blip2/app/main:app'

# Server Mechanics
#========================================
# current directory
chdir = '/'

# daemon mode
daemon = False

# backlog
backlog = 2048

# enviroment variables
raw_env = [
    'ENV_TYPE=dev',
    'HOGEHOGE_KEY=xxxxxxxxxxxxxxxxxxxxxxxxx'
]

# Server Socket
#========================================
bind = '0.0.0.0:7874'

# Worker Processes
#========================================
workers = 1

#  Logging
#========================================
# access log
accesslog = '/access.log'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# gunicorn log
errorlog = '-'
loglevel = 'info'
