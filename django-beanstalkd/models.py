from django.db import models
import logging

class JobStatus(object):
    # constants for Status.
    READY, BURIED, RESERVED, \
    FAILED_TO_REGISTER, FINISHED_SUCCESSFULLY, \
    CANCELLED = range(1, 7)
    DICT = {# Status provided by beanstalk.
            READY:'Ready',
            BURIED:'Buried',
            RESERVED:'Reserved',
            # For messages that have failed to register to beanstalk.
            FAILED_TO_REGISTER:'Failed to Register',
            FINISHED_SUCCESSFULLY: 'Finished Successfully',
            CANCELLED: 'Cancelled'}
    CHOICES = DICT.items()
    CHOICES.sort()
class JobRecord(models.Model):
    createdDate = models.DateTimeField(auto_now_add=True,
        help_text='Created date of the beanstalk job.')
    # Job ID is only unique up to the runtime of beanstalk daemon.
    jid = models.IntegerField(
        help_text='Job ID of the beanlstalk job.')
    uuid = models.CharField(max_length=32, unique=True)
    tube = models.CharField(max_length=128)
    body = models.TextField(max_length=1024)
    status = models.SmallIntegerField(choices=JobStatus.CHOICES)


    @staticmethod
    def updateJobStatus(uuid, newStatus):
        logger = logging.getLogger('beanstalk_worker.work')
        try :
            if uuid is not None:
                JobRecord.objects.filter(uuid=uuid).update(status=newStatus)
        except Exception, ex :
            logger.exception("Failed to update the job status " + str(uuid) + " - " + str(newStatus) + " " + str(ex))