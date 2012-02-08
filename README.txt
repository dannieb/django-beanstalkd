Modification of django-beanstalkd (https://github.com/jonasvp/django-beanstalkd/) by jonasvp.

New Features:

Storing all jobs and the current statuses to the local db.  
- In an older version of beanstalk, the binlog functionality had issues, so this mitigated the risk when beanstalk is restarted.
- Also if the beanstalk server goes down, no jobs will be lost.
- There are jobs included that will requeue jobs that weren't processed.


Proper shutdown of beanstalk workers.
- The original method involved killing worker processes, but jobs can be killed midpoint leading to unexpected behaviour.


Ability to run workers for specific django apps.

MESSAGE PRODUCERS:

How to create a new asynchronous job:

1.) In your django application, create a module called fdrasync_jobs.py (asynchronous jobs). Exact naming is necessary.
2.) Within that file define your business logic 

i.e 

@fdrasync_job
def myBusinessLogic(args)
	#your business logic here
	
	
Notes:
1.) You must annotate your business logic method with the @fdrasync_job decorator
2.) args will be returned as a json array


Finally, call the asynchronous methods.

1.) The following control variables can be passed into your asynctask instance.
	
	@priority -> you can set a priority for your task, so the consumers can process it accordingly
	@delay -> you can set a delay, the default is 0
	@ttr -> ttr value.  see: http://github.com/kr/beanstalkd/wiki/faq

2.) Call the run method of BaseAsyncTask with the following parameters
	Mandatory Parameters
	@function -> the reference to the annotated asynchronous business logic function
	@args -> a json serializable list of parameters

i.e: Subclassing the base tasks for domain specific behaviour
class MyAsyncJobs(BaseAsyncTasks):
	def myBusinessLogicJob(self) :
		#myBusinessLogic is the actual business logic located somewhere.
		self.run( myBusinessLogic, {'arg1' : arg1})
		
@fdrasync_job
def myBusinessLogic(args)
	#your business logic here
	                 
	                 
MESSAGE CONSUMERS:

run: python manage.py beanstalk_worker [app name]

this will sit and wait for new work and process the tasks produced by the producers.	  
specify a [app name] to spawn a worker that listens for jobs for a specific django application               
