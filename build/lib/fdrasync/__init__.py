from fdrasync.models import JobRecord, JobStatus
from json.encoder import JSONEncoder
from uuid import uuid4
import beanstalkc
import logging
import settings


DEFAULT_JOB_PRIORITY = beanstalkc.DEFAULT_PRIORITY
DEFAULT_JOB_TTR = beanstalkc.DEFAULT_TTR


def connect_beanstalkd():
    """Connect to beanstalkd server(s) from settings file"""
    logger = logging.getLogger('fdrasync.connect_beanstalkd')
    
    server = getattr(settings, 'BEANSTALK_SERVER', '127.0.0.1')
    port = 11300
    if server.find(':') > -1:
        server, port = server.split(':', 1)
    
    connection = None
    try:
        port = int(port)
        connection = beanstalkc.Connection(server, port)
    except Exception, ex :
        logger.critical("Can't connect to beanstalk - jobs are being lost!" + str(ex))
        
    return connection
    
class BeanstalkConnection(object):
    connection = None
    
    @staticmethod
    def getConnection(refresh=False):
        if not BeanstalkConnection.connection or refresh :
            BeanstalkConnection.connection = connect_beanstalkd()
        return BeanstalkConnection.connection

class BeanstalkClient(object):
    """beanstalk client, automatically connecting to server"""

    def call(self, func, arg='', priority=DEFAULT_JOB_PRIORITY, delay=0, ttr=DEFAULT_JOB_TTR):
        logger = logging.getLogger('fdrasync.call')
        """
        Calls the specified function (in beanstalk terms: put the specified arg
        in tube func)
        
        priority: an integer number that specifies the priority. Jobs with a
                  smaller priority get executed first
        delay: how many seconds to wait before the job can be reserved
        ttr: how many seconds a worker has to process the job before it gets requeued
        """
        pid = -1
        try :
            if self._beanstalk :
                self._beanstalk.use(func)
                pid = self._beanstalk.put(str(arg), priority=priority, delay=delay, ttr=ttr)
        except Exception :
            # If the connection to BeanStalk is lost,
            # we need a logic to reconnect.
            logger.exception("Error while calling beanstalk.")
        
        return pid
    
    def getJob(self, jid):
        logger = logging.getLogger('fdrasync.getJob')
        job = None
        try :
            if self._beanstalk :
                job = self._beanstalk.peek(jid)
        except Exception, ex :
            logger.exception("Failed to retrieve job: " + str(jid) + " "  + str(ex))
        return job
    
    def delete(self, jid):
        logger = logging.getLogger('fdrasync.delete')
        success = False
        try :
            if self._beanstalk :
                self._beanstalk.delete(jid)
                success = True
        except Exception, ex :
            if ex.args and ex.args[1] == 'NOT_FOUND' :
                success = True
            logger.exception("Error while trying to cancel job: " + str(jid))
            
        return success
            
    def kick(self, numJobs, tube):
        logger = logging.getLogger('fdrasync.kick')
        success = False
        try :
            if self._beanstalk :
                self._beanstalk.use(tube)
                self._beanstalk.kick(numJobs)
                success = True
        except Exception, ex :
            logger.exception("Error while trying to kick the jobs in tube: " + tube + " " + str(ex))
                
        return success
            
    def __init__(self, **kwargs):
        self._beanstalk = BeanstalkConnection.getConnection()

class BaseAsyncTasks(object):
    
    def __init__(self, priority=DEFAULT_JOB_PRIORITY, delay=0, ttr=DEFAULT_JOB_TTR):
        self._priority = priority
        self._delay = delay
        self._ttr = ttr
        self._jsonEncoder = JSONEncoder()
    
    '''
    @function -> the reference to the annotated asynchronous business logic function
    @args -> a json serializable list of parameters
    @priority -> you can set a priority for your task, so the consumers can process it accordingly
    @delay -> you can set a delay, the default is 0
    @ttr -> ttr value.  see: http://github.com/kr/beanstalkd/wiki/faq
    '''
    def run(self, function, args):
        logger = logging.getLogger('BaseAsyncTasks.run')
        
        if settings.BEANSTALK_ENABLED :
            beanstalkClient = BeanstalkClient()
            module = function.__module__.__self__.app
            # Add more metadata to the args
            args['__uuid__'] = str(uuid4()).replace('-', '')
            func = ".".join([module, function.__name__])
            body = self._jsonEncoder.encode(args)
            pid = beanstalkClient.call(func, body,
                                         priority=self._priority,
                                         delay=self._delay,
                                         ttr=self._ttr)


            try :
                if not pid >= 0:
                    logger.critical("Failed to execute task: " + str(function) + " " + str(args))
                    JobRecord.objects.create(jid=pid, tube=func, body=body, uuid=args['__uuid__'], status=JobStatus.FAILED_TO_REGISTER)
                else:
                    JobRecord.objects.create(jid=pid, tube=func, body=body, uuid=args['__uuid__'], status=JobStatus.READY)
            except Exception, ex:
                logger.exception('Error while persisting Job object. %s' % str(ex))
                    
        else :
            ret = None
            try :
                ret = function(args)
            except Exception, ex :
                logger.exception("Error while handling async. function.: " + str(ex))
                pass
            
            return ret
    
