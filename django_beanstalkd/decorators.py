
'''
Anything that's been decorated with this function 
'''
from json.decoder import JSONDecoder
class async_job(object):
    """
    Decorator marking a function inside some_app/async_job.py as a
    beanstalk job
    """

    def __init__(self, f):            
        self.f = f #the function reference
        self.__name__ = f.__name__ # the name of the function
        
        self.app = self.__getAppNameFromModule()

        # store function in per-app job list (to be picked up by a worker)
        bs_module = __import__(f.__module__)
        try:
            bs_module.beanstalk_job_list.append(self)
        except AttributeError:
            bs_module.beanstalk_job_list = [self]

    def __call__(self, args):
        try :
            args = JSONDecoder().decode(args)
        except Exception :
            # Cannot parse json - attempt to call the function directly.
            pass
        return self.f(args)
    
    def __module__(self):
        return self.__getAppNameFromModule()
        

    def __getAppNameFromModule(self):
        # determine app name
        parts = self.f.__module__.split('.')
        if len(parts) > 1:
            appName = ".".join(parts[:len(parts)])
        else:
            appName = ''
            
        return appName
