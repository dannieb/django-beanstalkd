from django.core.management.base import BaseCommand
from django.db import transaction
from fdrasync import BeanstalkClient
from fdrasync.models import JobRecord, JobStatus
from json.decoder import JSONDecoder
from optparse import make_option
import logging

class Command(BaseCommand):
    help_text = 'Performs maintenance operations on the fdrasync jobs'
    
    option_list = BaseCommand.option_list + (
        make_option('--clearFinished',
            dest='clear_finished',
            action='store',
            default=None,
            help='Clear all successfully finished job records'),
        
        make_option('--rescheduleReady',
            dest='reschedule_ready',
            action='store',
            default=None,
            help='Reschedules all the currently ready jobs again.  This is necessary when the queue goes down for whatever reason.'),
            
        make_option('--kickBuried',
            dest='kick_buried',
            action='store',
            default=None,
            help='Kicks all the currently buried jobs. After proper investigation into the issues.'),
            
        make_option('--cancelJobs',
            dest='cancel_jobs',
            action='store',
            default=None,
            help='Cancels all the jobs in a specific queue.'
                    )

        )
      
    def handle(self, **options):
        if options['clear_finished'] :
            self._clearAllFinishedJobs(options['clear_finished'])
        if options['reschedule_ready'] :
            self._rescheduleReadiedJobs(options['reschedule_ready'])
        if options['kick_buried'] :
            self._kickBuriedJobs(options['kick_buried'])
        if options['cancel_jobs'] :
            self._cancelJobs(options['cancel_jobs'])

    '''
    Clears all the finished jobs in the beanstalk queue that belongs to a particular tube pattern
    '''
    def _clearAllFinishedJobs(self, tube):
        count = JobRecord.objects.filter(status=JobStatus.FINISHED_SUCCESSFULLY, tube__istartswith=tube).count()
        print "Deleting %d rows." % count
        JobRecord.objects.filter(status=JobStatus.FINISHED_SUCCESSFULLY, tube__istartswith=tube).delete()
        print "Done."
        
    '''
    Cancels the jobs in the beanstalk queue that belongs to a particular tube pattern
    '''
    @transaction.commit_manually
    def _cancelJobs(self, tube):
        jobs = JobRecord.objects.filter(status=JobStatus.READY, tube__istartswith=tube).only('jid', 'uuid')
        beanstalk = BeanstalkClient()
        if jobs :
            for job in jobs :
                job.status = JobStatus.CANCELLED
                job.save()
                existingJob = beanstalk.getJob(job.jid)
                uuid = self.__get_uuid__(existingJob)
                success = True
                if uuid == job.uuid :
                    success = beanstalk.delete(job.jid)
                if not success :
                    transaction.rollback()
                else :
                    transaction.commit()
    
    '''
    Kicks the jobs in the beanstalk queue that belongs to a particular tube pattern
    '''
    @transaction.commit_manually 
    def _kickBuriedJobs(self, tube):
        buriedJobs = JobRecord.objects.filter(status=JobStatus.BURIED, tube__istartswith=tube).only('id')
        beanstalk = BeanstalkClient()
        if buriedJobs :
            for job in buriedJobs :
                job.status = JobStatus.READY
                job.save()
        
            success = beanstalk.kick(len(buriedJobs), tube)
            if not success :
                transaction.rollback()
            else :
                transaction.commit()
        
    '''
    Reschedules bunch of "ready" jobs to run again.
    '''
    def _rescheduleReadiedJobs(self, tube):
        logger = logging.getLogger('beanstalk_worker.work')
        logger.info("Rescheduling all jobs in tubes that starts with: " + tube)
        pageSize = 50
        pageNumber = 1
        while True :
            start = ( pageNumber - 1 ) * pageSize
            end = pageNumber * pageSize 
            jobs = JobRecord.objects.filter(status=JobStatus.READY, tube__istartswith=tube)[start:end]
            if not jobs or len(jobs) == 0 :
                break
            
            for job in jobs :
                try :
                    #simply just creates a new beanstalk job, workers will never run a job
                    #again if it has already been finished successfully.
                    beanstalkClient = BeanstalkClient()
                    newJID = beanstalkClient.call(job.tube, job.body)
                    job.jid = newJID
                    job.save()
                except Exception, ex :
                    logger.exception("Failed to schedule the new job: " + str(ex))
            
            pageNumber += 1
            
            
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