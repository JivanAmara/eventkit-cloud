# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging
import uuid
import os

from django.contrib.auth.models import Group, User
from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.test import TestCase
from mock import patch

from ...jobs.models import ExportFormat, Job, ProviderTask, ExportProvider
from ..models import ExportRun, ExportTask, ExportTaskResult, ExportProviderTask

logger = logging.getLogger(__name__)


class TestExportRun(TestCase):
    """
    Test cases for ExportRun model
    """

    fixtures = ('insert_provider_types.json', 'osm_provider.json',)

    @classmethod
    def setUpTestData(cls):
        formats = ExportFormat.objects.all()
        Group.objects.create(name='TestDefaultExportExtentGroup')
        user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo', is_active=True)
        bbox = Polygon.from_bbox((-7.96, 22.6, -8.14, 27.12))
        the_geom = GEOSGeometry(bbox, srid=4326)
        provider_task = ProviderTask.objects.create(provider=ExportProvider.objects.get(slug='osm-generic'))
        # add the formats to the provider task
        provider_task.formats.add(*formats)
        job = Job.objects.create(name='TestExportRun', description='Test description', user=user, the_geom=the_geom)
        job.provider_tasks.add(provider_task)

    def test_export_run(self, ):
        job = Job.objects.first()
        run = ExportRun.objects.create(job=job, status='SUBMITTED', user=job.user)
        saved_run = ExportRun.objects.get(uid=str(run.uid))
        self.assertIsNotNone(saved_run)
        self.assertEqual(run, saved_run)
        self.assertIsNone(run.notified)
        self.assertIsNotNone(run.expiration)
        self.assertIsNone(saved_run.zipfile_url)

    def test_get_tasks_for_run(self, ):
        job = Job.objects.first()
        run = ExportRun.objects.create(job=job, user=job.user)
        saved_run = ExportRun.objects.get(uid=str(run.uid))
        self.assertEqual(run, saved_run)
        task_uid = str(uuid.uuid4())  # from celery
        export_provider_task = ExportProviderTask.objects.create(run=run)
        ExportTask.objects.create(export_provider_task=export_provider_task, uid=task_uid)
        saved_task = ExportTask.objects.get(uid=task_uid)
        self.assertIsNotNone(saved_task)
        tasks = run.provider_tasks.all()[0].tasks.all()
        self.assertEqual(tasks[0], saved_task)

    def test_get_runs_for_job(self, ):
        job = Job.objects.first()
        for x in range(5):
            run = ExportRun.objects.create(job=job, user=job.user)
            task_uid = str(uuid.uuid4())  # from celery
            export_provider_task = ExportProviderTask.objects.create(run=run)
            ExportTask.objects.create(export_provider_task=export_provider_task, uid=task_uid)
        runs = job.runs.all()
        tasks = runs[0].provider_tasks.all()[0].tasks.all()
        self.assertEquals(5, len(runs))
        self.assertEquals(1, len(tasks))

    def test_delete_export_run(self, ):
        job = Job.objects.first()
        run = ExportRun.objects.create(job=job, user=job.user)
        task_uid = str(uuid.uuid4())  # from celery
        export_provider_task = ExportProviderTask.objects.create(run=run)
        ExportTask.objects.create(export_provider_task=export_provider_task, uid=task_uid)
        runs = job.runs.all()
        self.assertEquals(1, runs.count())
        run.delete()


class TestExportTask(TestCase):
    """
    Test cases for ExportTask model
    """

    @classmethod
    def setUpTestData(cls):
        formats = ExportFormat.objects.all()
        Group.objects.create(name='TestDefaultExportExtentGroup')
        user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo', is_active=True)
        bbox = Polygon.from_bbox((-7.96, 22.6, -8.14, 27.12))
        the_geom = GEOSGeometry(bbox, srid=4326)
        Job.objects.create(name='TestExportTask', description='Test description', user=user, the_geom=the_geom)
        job = Job.objects.first()
        # add the formats to the job
        job.formats = formats
        job.save()

    def setUp(self):
        job = Job.objects.get(name='TestExportTask')
        self.run = ExportRun.objects.create(job=job, user=job.user)
        self.task_uid = uuid.uuid4()
        export_provider_task = ExportProviderTask.objects.create(run=self.run)
        self.task = ExportTask.objects.create(export_provider_task=export_provider_task, uid=self.task_uid)
        self.assertEqual(self.task_uid, self.task.uid)
        saved_task = ExportTask.objects.get(uid=self.task_uid)
        self.assertEqual(saved_task, self.task)

    def test_export_task_result(self, ):
        """
        Test ExportTaskResult.
        """
        task = ExportTask.objects.get(uid=self.task_uid)
        self.assertEqual(task, self.task)
        self.assertFalse(hasattr(task, 'result'))
        result = ExportTaskResult.objects.create(task=task,
                                                 download_url='http://testserver/media/{0}/file.txt'.format(self.run.uid))
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(task, 'result'))
        self.assertEquals('http://testserver/media/{0}/file.txt'.format(self.run.uid), result.download_url)
        saved_result = task.result
        self.assertIsNotNone(saved_result)
        self.assertEqual(result, saved_result)

    @patch('eventkit_cloud.tasks.models.delete_from_s3')
    def test_exportrun_delete_exports(self, delete_from_s3):
        job = Job.objects.first()
        run = ExportRun.objects.create(job=job, user=job.user)
        run_uid = run.uid
        task_uid = str(uuid.uuid4())  # from celery
        export_provider_task = ExportProviderTask.objects.create(run=run)
        ExportTask.objects.create(export_provider_task=export_provider_task, uid=task_uid)
        with self.settings(USE_S3=True):
            run.delete()
            delete_from_s3.assert_called_once_with(run_uid=str(run_uid))

    @patch('eventkit_cloud.tasks.models.ExportProvider')
    @patch('os.remove')
    @patch('eventkit_cloud.tasks.models.delete_from_s3')
    def test_exporttaskresult_delete_exports(self, delete_from_s3, remove, export_provider):

        #setup
        download_dir = "/test_download_dir"
        file_name = "file.txt"
        full_download_path = os.path.join(download_dir, str(self.run.uid), file_name)
        download_url = 'http://testserver/media/{0}/{1}'.format(str(self.run.uid), file_name)
        task = ExportTask.objects.get(uid=self.task_uid)
        self.assertEqual(task, self.task)
        self.assertFalse(hasattr(task, 'result'))
        result = ExportTaskResult.objects.create(task=task,
                                                 download_url=download_url)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(task, 'result'))
        self.assertEquals(download_url, result.download_url)
        saved_result = task.result
        self.assertIsNotNone(saved_result)
        self.assertEqual(result, saved_result)

        #Test
        with self.settings(USE_S3=True, EXPORT_DOWNLOAD_ROOT=download_dir):
            result.delete()
        delete_from_s3.assert_called_once_with(download_url=download_url)
        remove.assert_called_once_with(full_download_path)
