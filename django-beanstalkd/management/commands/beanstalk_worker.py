from django.conf import settings
from django.core.management.base import NoArgsCommand
from fdrasync import connect_beanstalkd, BeanstalkClient
from fdrasync.models import JobRecord, JobStatus
from json.decoder import JSONDecoder
from json.encoder import JSONEncoder
from optparse import make_option
import logging
import os
import sys
import time



class Command(NoArgsCommand):
    help = "Start a Beanstalk worker serving all registered Beanstalk jobs"
    __doc__ = help
    option_list = NoArgsCommand.option_list + (
        make_option('-w', '--workers', action='store', dest='worker_count',
                    default='1', help='Number of workers to spawn.'),
                    
        make_option('--tube', dest='tube_name',
                    default=None, help='The tube to listen on'),
                    
        make_option('--start', dest='start', action='store_true',
                    default=None, help='Starts a worker'),
                    
        make_option('--shutdown', dest='shutdown', action="store_true", 
                    help='Schedules a high priority shutdown job that will then cause all workers to shutdown.')
                    
    )
    children = [] # list of worker processes
    jobs = {'shutdown' : 1}

    def __init__(self):
        #time this worker was executed
        self.__cTime = time.time()

    def handle_noargs(self, **options):
        if options['start'] :
            '''
            for each worker, increment the worker count 
            '''
            self.__start(**options)
        elif options['shutdown'] :
            self.__shutdown()
            
    def __start(self, **options):
        # find beanstalk job modules
        tubeName = options['tube_name']
        bs_modules = []
        if tubeName :
            try :
                bs_modules.append(__import__("%s.fdrasync_jobs" % tubeName))
            except ImportError :
                pass
        else :
            for app in settings.INSTALLED_APPS:
                try:
                    bs_modules.append(__import__("%s.fdrasync_jobs" % app))
                except ImportError:
                    pass
        if not bs_modules:
            print "No fdrasync_jobs modules found!"
            return

        # find all jobs
        jobs = []
        for bs_module in bs_modules:
            try:
                bs_module.beanstalk_job_list
            except AttributeError:
                continue
            jobs += bs_module.beanstalk_job_list
        if not jobs:
            print "No beanstalk jobs found!"
            return
        print "Available jobs:"
        for job in jobs:
            # determine right name to register function with
            app = job.app
            jobname = job.__name__
            try:
                func = settings.BEANSTALK_JOB_NAME % {
                    'app': app,
                    'job': jobname,
                }
            except (AttributeError, Exception):
                func = '%s.%s' % (app, jobname)
            self.jobs[func] = job
            print "* %s" % func

        # spawn all workers and register all jobs
        try:
            worker_count = int(options['worker_count'])
            assert(worker_count > 0)
        except (ValueError, AssertionError):
            worker_count = 1
        self.spawn_workers(worker_count)

        # start working
        print "Starting to work... (press ^C to exit)"
        try:
            for child in self.children:
                os.waitpid(child, 0)
        except KeyboardInterrupt:
            sys.exit(0)


    def spawn_workers(self, worker_count):
        """
        Spawn as many workers as desired (at least 1).
        Accepts:
        - worker_count, positive int
        """
        # no need for forking if there's only one worker
        if worker_count == 1:
            return self.work()

        print "Spawning %s worker(s)" % worker_count
        # spawn children and make them work (hello, 19th century!)
        for i in range(worker_count):
            child = os.fork()
            if child:
                self.children.append(child)
                continue
            else:
                self.work()
                break
    
    def __get_uuid__(self, job):
        # Return the UUID of the job from the given Job.
        uuid = None
        try:
            json = JSONDecoder().decode(job.body)
            if '__uuid__' in json:
                uuid = json['__uuid__']
        except Exception:
            uuid = None
        return uuid
    
    def __hasJobBeenProcessed(self, uuid):
        processed = False
        if uuid :
            try :   
                JobRecord.objects.get(uuid=uuid, status=JobStatus.FINISHED_SUCCESSFULLY)
                processed = True
            except Exception:
                pass
            
        return processed
            
                
    def work(self):
        """children only: watch tubes for all jobs, start working"""
        beanstalk = connect_beanstalkd()
        for job in self.jobs.keys():
            beanstalk.watch(job)
        beanstalk.ignore('default')
        logger = logging.getLogger('beanstalk_worker.work')
        try:
            while True:
                try :
                    job = beanstalk.reserve()
                    
                    if self.__checkShutdown(job) :
                        continue
                    else :
                        
                        job_uuid = self.__get_uuid__(job)
                        
                        #Jobs may be requeued, in the event that we detect beanstalk went down or is an 
                        #an inconsistent state.  Therefore, we'll just ignore this job if it already exists in the system and 
                        #has finished successfully
                        if not self.__hasJobBeenProcessed(job_uuid) :
                        
                            # Create the JobRecord here, since the JobRecord gets created in
                            # BaseAsyncTasks.run()
                            # only if job queuing has failed.
                            job_name = job.stats()['tube']
                            JobRecord.updateJobStatus(job_uuid, JobStatus.RESERVED)
                            
                            if job_name in self.jobs:
                                logger.debug("Calling %s with arg: %s" % (job_name, job.body))
                                try:
                                    self.jobs[job_name](job.body) 
                                except Exception, e:
                                    
                                    logger.error('Error while calling "%s" with arg "%s": '
                                        '%s' % (
                                            job_name,
                                            job.body,
                                            e,
                                        )
                                    )
                                    
                                    job.bury()
                                    JobRecord.updateJobStatus(job_uuid, JobStatus.BURIED)
                                else:
                                    job.delete()
                                    JobRecord.updateJobStatus(job_uuid, JobStatus.FINISHED_SUCCESSFULLY)
                            else:
                                job.release()
                        else :
                            job.delete()
                except Exception, unknownErr :
                    logger.exception("An unexpected beanstalk error occured! %s" % str(unknownErr))
            
        except KeyboardInterrupt:
            sys.exit(0)
            
            
            
    '''
    Cleanly shuts down the beanstalk workers
    '''
    def __shutdown(self):
        beanstalkClient = BeanstalkClient()
        jsonEncoder = JSONEncoder()
        args = {'timestamp' : time.time()}
        pid = beanstalkClient.call("shutdown", jsonEncoder.encode(args), priority=0) #high pri job
        
    '''
    If the worker needs to shutdown, it shuts it down here
    '''
    def __checkShutdown(self, job):
        shutdown = False
        decoder = JSONDecoder()
        if job.stats()['tube'] == "shutdown" :
            shutdown = True
            args = decoder.decode(job.body)
            time = args['timestamp']
            if time > self.__cTime :
                sys.exit(0)
            job.delete()
                    
        return shutdown