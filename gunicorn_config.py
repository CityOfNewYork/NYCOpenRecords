import os
from multiprocessing import cpu_count

#   bind - The socket to bind.
#
#       A string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'.
#       An IP is a valid HOST.

bind = ":8080"

#
# Worker processes
#
#   workers - The number of worker processes that this server
#       should keep alive for handling requests.
#
#       A positive integer generally in the 2-4 x $(NUM_CORES)
#       range. You'll want to vary this a bit to find the best
#       for your particular application's work load.
#
#   timeout - If a worker does not notify the master process in this
#       number of seconds it is killed and a new worker is spawned
#       to replace it.
#
#       Generally set to thirty seconds. Only set this noticeably
#       higher if you're sure of the repercussions for sync workers.
#       For the non sync workers it just means that the worker
#       process is still communicating and is not tied to the length
#       of time required to handle a single request.
#
#   keepalive - The number of seconds to wait for the next request
#       on a Keep-Alive HTTP connection.
#
#       A positive integer. Generally set in the 1-5 seconds range.
#

# In a container cpu_count() reports the host's cores, not the container's
# allocation, so set WEB_CONCURRENCY in Azure Container Apps.
workers = int(os.environ.get('WEB_CONCURRENCY', cpu_count() * 2))
timeout = 120
keepalive = 2

#
#   Logging
#
#   logfile - The path to a log file to write to.
#
#       A path string. "-" means log to stdout.
#
#   loglevel - The granularity of log output
#
#       A string of "debug", "info", "warning", "error", "critical"
#

errorlog = "-"
loglevel = "info"
accesslog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
# logconfig = gunicorn_logging.conf

#
#   Server Mechanics
#
#   pidfile - A filename to use for the PID file.
#
#        A path string. If not set, no PID file will be written.

# No PID file: the app directory is read-only in the container.
pidfile = None

# Azure Container Apps ingress terminates TLS and is the only way in, so trust
# its X-Forwarded-* headers; SAML needs the original https scheme.
forwarded_allow_ips = "*"

# Worker heartbeat files in memory rather than on the container's overlay disk.
worker_tmp_dir = "/dev/shm"

#
#   SSL
#
#   keyfile - SSL key file.
#       A path string.
#
#   certfile - SSL certificate file.
#       A path string.
#

# keyfile = os.path.join(os.environ.get('HOME'), 'ssl', 'key.pem')
# certfile = os.path.join(os.environ.get('HOME'), 'ssl', 'cert.pem')
