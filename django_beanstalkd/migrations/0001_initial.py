# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'JobRecord'
        db.create_table('django_beanstalkd_jobrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('createdDate', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('jid', self.gf('django.db.models.fields.IntegerField')()),
            ('uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('tube', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('body', self.gf('django.db.models.fields.TextField')(max_length=1024)),
            ('status', self.gf('django.db.models.fields.SmallIntegerField')()),
        ))
        db.send_create_signal('django_beanstalkd', ['JobRecord'])

    def backwards(self, orm):
        # Deleting model 'JobRecord'
        db.delete_table('django_beanstalkd_jobrecord')

    models = {
        'django_beanstalkd.jobrecord': {
            'Meta': {'object_name': 'JobRecord'},
            'body': ('django.db.models.fields.TextField', [], {'max_length': '1024'}),
            'createdDate': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jid': ('django.db.models.fields.IntegerField', [], {}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {}),
            'tube': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['django_beanstalkd']