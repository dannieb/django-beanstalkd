'''
Created on Nov 4, 2010

@author: jee
'''
from django.contrib import admin
from fdrasync.models import JobRecord

class JobRecord_admin(admin.ModelAdmin):
    list_display = ('createdDate', 'jid', 'uuid', 'tube', 'body', 'status')
    list_filter = ('tube', 'status')

admin.site.register(JobRecord, JobRecord_admin)
